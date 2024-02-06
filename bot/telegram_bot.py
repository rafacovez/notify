import threading
from collections.abc import Callable, Iterable, Mapping
from typing import *

import requests
from flask import Flask, render_template, request
from spotipy import Spotify
from telebot import TeleBot  # telegram bots interaction library
from telebot.types import *

from api.services.database_service import DatabaseHandler
from api.services.spotify_service import SpotifyHandler


class NotifyTelegramBot(threading.Thread):
    def __init__(
        self,
        bot_token: str,
        database: DatabaseHandler,
        spotify: SpotifyHandler,
    ) -> None:
        threading.Thread.__init__(self)
        self.kill_received = False
        self.bot_token: str = bot_token
        self.bot: TeleBot = TeleBot(self.bot_token)
        self.database: DatabaseHandler = database
        self.spotify: SpotifyHandler = spotify
        self.user_id: Optional[int] = None
        self.chat_id: Optional[int] = None
        self.message: Optional[Message] = None
        # TODO: delete this code if not used in notify function update
        #
        # self.bot.register_callback_query_handler(
        #     self.message, self.message_handler.handle_callback_query
        # )
        self.bot.register_message_handler(self.handle_message)
        self.commands: Dict[str, Dict[str, Union[Callable[..., Any], str]]] = {
            "start": {"func": self.help, "desc": "Starts Notify"},
            "help": {
                "func": self.help,
                "desc": "Provides help for using Notify",
            },
            "login": {
                "func": self.auth_user,
                "desc": "Authorize Notify to access your Spotify account",
            },
            "logout": {
                "func": self.delete_user,
                "desc": "Permanently deletes your data from Notify",
            },
            "notify": {
                "func": self.disabled,
                "desc": "Start tracking a playlist to get notified when someone else adds or removes a song from it",
            },
            "removenotify": {
                "func": self.disabled,
                "desc": "Stop tracking a playlist",
            },
            "shownotify": {
                "func": self.disabled,
                "desc": "Get a list of the playlists you're currently tracking",
            },
            "lastplayed": {
                "func": self.last_played,
                "desc": "Get the last song you played",
            },
            "playlists": {
                "func": self.retrieve_playlists,
                "desc": "Get a list of the playlists you own",
            },
            "topten": {
                "func": self.top_ten,
                "desc": "Get a list of the top 10 songs you've listen to the most lately",
            },
            "recommended": {
                "func": self.recommended,
                "desc": "Get a list of 10 songs you might like based on what you've been listening to",
            },
        }
        self.command_list: List[BotCommand] = []
        for key, val in self.commands.items():
            self.command_list.append(BotCommand(f"/{key}", val.get("desc", "")))
        self.bot.set_my_commands(self.command_list)

    def __do_nothing(self) -> None:
        pass

    def handle_message(self, message: Message) -> None:
        self.message: Message = message
        self.user_id: int = self.message.from_user.id
        self.chat_id: int = self.message.chat.id

        self.bot.send_chat_action(self.chat_id, "typing")

        if message.content_type == "text" and message.text.strip().startswith("/"):
            self.determine_function()

        else:
            self.bot.send_message(self.chat_id, "Sorry, I only speak commands...")

    # TODO: delete this code if not used in notify function update
    #
    # def handle_callback_query(self, call) -> None:
    #     if self.current_action == "add_notify":
    #         self.handle_add_notify_callback(call)
    #     elif self.current_action == "remove_notify":
    #         self.handle_remove_notify_callback(call)

    def determine_function(self) -> None:
        command: str = self.message.text
        command_exists: bool = False

        for command_item in self.command_list:
            if command == command_item.command:
                command_exists = True
                self.database.create_users_table()

                if self.database.user_exists(self.user_id):
                    self.spotify.refresh_token = self.database.get_refresh_token(
                        self.user_id
                    )
                    self.spotify.access_token = self.spotify.refresh_access_token()
                    self.database.store_access_token(
                        self.spotify.access_token, self.user_id
                    )
                    self.spotify.user_sp = self.spotify.get_user_sp(
                        self.spotify.access_token
                    )
                    command_func: function = self.commands[
                        command_item.command.strip("/")
                    ]["func"]
                    command_func()
                else:
                    self.auth_user()

        if not command_exists:
            self.bot.send_message(
                self.chat_id,
                "My creators didn't think about that one yet! <a href='https://github.com/rafacovez/notify'>is it a good idea though?</a>",
                parse_mode="HTML",
            )

    def auth_user(self) -> None:
        if self.database.user_exists(self.user_id):
            self.bot.send_message(self.chat_id, "You're already logged in.")
        else:
            auth_url: Any = self.spotify.sp_oauth.get_authorize_url(state=self.user_id)
            self.bot.send_message(
                self.chat_id,
                f"Please <a href='{auth_url}'>authorize me</a> to access your Spotify account.",
                parse_mode="HTML",
            )

    def delete_user(self) -> None:
        if self.database.user_exists(self.user_id):
            self.database.delete_user(self.user_id)
            self.bot.send_message(
                self.chat_id,
                "Your data has been deleted from Notify. Sorry to see you go!",
            )
        else:
            self.bot.send_message(self.chat_id, "You're not logged in yet...")

    def under_development(self) -> None:
        self.bot.send_message(
            self.chat_id,
            "This feature is still under development... Try it again later!",
        )

    def disabled(self) -> None:
        self.bot.send_message(
            self.chat_id,
            "This command is temporarily disabled... Try it again later!",
        )

    def help(self) -> None:
        commands: str = ""
        for command_item in self.command_list:
            commands += f"\n {command_item.command}: {command_item.description}"

        self.bot.send_message(
            self.chat_id,
            f"You can try one of these commands out: \n{commands}",
        )

    def get_user_playlists(self) -> Optional[List[Dict[str, any]]]:
        offset: int = 0
        user_playlists: Optional[List[Dict[str, any]]] = []

        response: Dict[str, any] = self.spotify.user_sp.current_user_playlists(
            offset=offset
        )
        fetched_playlists = response["items"]
        user_playlists += fetched_playlists

        while len(fetched_playlists) > 50:
            offset += len(fetched_playlists)
            response: Dict[str, any] = self.spotify.user_sp.current_user_playlists(
                offset=offset
            )
            fetched_playlists = response["items"]
            user_playlists += fetched_playlists

        return user_playlists

    # TODO: study how this functions work after worker refactory

    # def add_notify(self) -> None:
    #     if len(self.get_user_playlists()) > 0:
    #         self.current_action = "add_notify"
    #
    #         playlists = [
    #             InlineKeyboardButton(playlist["name"], callback_data=playlist["id"])
    #             for playlist in self.get_user_playlists()
    #         ]
    #
    #         keyboard = InlineKeyboardMarkup(row_width=2)
    #
    #         keyboard.add(*playlists)
    #
    #         self.bot.send_message(
    #             self.chat_id,
    #             "Click on the playlist you'd like to get notified about.",
    #             reply_markup=keyboard,
    #         )
    #
    #     else:
    #         self.bot.send_message(
    #             self.chat_id,
    #             "You don't seem to have any playlists in your library yet...",
    #         )
    #
    # def handle_add_notify_callback(self, call):
    #     selected_playlist_id: str = call.data
    #     selected_playlist_name: str = self.spotify.sp.playlist(selected_playlist_id)[
    #         "name"
    #     ]
    #     playlist_is_stored: bool = False
    #     limit_was_reached: bool = False
    #
    #     if self.database.get_notify(self.user_id) in ["", None]:
    #         self.database.update_notify(selected_playlist_id, self.user_id)
    #         self.bot.send_message(
    #             self.chat_id,
    #             f"{selected_playlist_name} was successfully added to your notify list!",
    #         )
    #
    #     else:
    #         notify_playlists: List[str] = self.database.get_notify(self.user_id)
    #         notify_playlists_list: List[str] = notify_playlists.split(",")
    #
    #         for playlist_id in notify_playlists_list:
    #             if selected_playlist_id == playlist_id:
    #                 playlist_is_stored = True
    #
    #         if len(notify_playlists_list) > 2:
    #             limit_was_reached = True
    #
    #         if playlist_is_stored:
    #             self.bot.send_message(
    #                 self.chat_id,
    #                 f"{selected_playlist_name} is already in your notify list.",
    #             )
    #         elif limit_was_reached:
    #             self.bot.send_message(
    #                 self.chat_id,
    #                 "Sorry, but you can't have more than 3 playlists in your notify list at a time...",
    #             )
    #         else:
    #             notify_playlists += f",{selected_playlist_id}"
    #             self.database.update_notify(notify_playlists, self.user_id)
    #             self.bot.send_message(
    #                 self.chat_id,
    #                 f"{selected_playlist_name} was successfully added to your notify list!",
    #             )
    #
    #     self.bot.answer_callback_query(call.id)
    #
    # def remove_notify(self) -> None:
    #     self.current_action = "remove_notify"
    #
    #     if self.database.get_notify(self.user_id) in ["", None]:
    #         self.bot.send_message(
    #             self.chat_id, "You don't have any playlist in your notify list yet..."
    #         )
    #
    #     else:
    #         notify_playlists_list: List[str] = self.database.get_notify(
    #             self.user_id
    #         ).split(",")
    #
    #         playlists = [
    #             InlineKeyboardButton(
    #                 self.spotify.user_sp.playlist(playlist_id)["name"],
    #                 callback_data=playlist_id,
    #             )
    #             for playlist_id in notify_playlists_list
    #         ]
    #
    #         keyboard = InlineKeyboardMarkup(row_width=2)
    #
    #         keyboard.add(*playlists)
    #
    #         self.bot.send_message(
    #             self.chat_id,
    #             "Click on the playlist you'd like to remove from your notify list.",
    #             reply_markup=keyboard,
    #         )
    #
    # def handle_remove_notify_callback(self, call):
    #     selected_playlist_id: str = call.data
    #     selected_playlist_name: str = self.spotify.sp.playlist(selected_playlist_id)[
    #         "name"
    #     ]
    #     playlist_is_stored: bool = False
    #
    #     if self.database.get_notify(self.user_id) in ["", None]:
    #         self.bot.send_message(
    #             self.chat_id,
    #             "You don't have any playlist in your notify list yet...",
    #         )
    #
    #     else:
    #         notify_playlists: List[str] = self.database.get_notify(self.user_id)
    #         notify_playlists_list: List[str] = notify_playlists.split(",")
    #
    #         for playlist_id in notify_playlists_list:
    #             if selected_playlist_id == playlist_id:
    #                 playlist_is_stored = True
    #
    #         if playlist_is_stored:
    #             notify_playlists_list.remove(selected_playlist_id)
    #
    #             notify_playlists = ",".join(notify_playlists_list)
    #
    #             self.database.update_notify(notify_playlists, self.user_id)
    #
    #             self.bot.send_message(
    #                 self.chat_id,
    #                 f"{selected_playlist_name} was removed from your notify list.",
    #             )
    #         else:
    #             self.bot.send_message(
    #                 self.chat_id,
    #                 "That playlist is not in your notify list anymore...",
    #             )
    #
    #     self.bot.answer_callback_query(call.id)
    #
    # def show_notify(self) -> None:
    #     if self.database.get_notify(self.user_id) in ["", None]:
    #         self.bot.send_message(
    #             self.chat_id, "You don't have any playlists in your notify list yet..."
    #         )
    #
    #     else:
    #         notify_playlists_list: List[str] = self.database.get_notify(
    #             self.user_id
    #         ).split(",")
    #         notify_playlists_message: str = ""
    #
    #         for playlist_id in notify_playlists_list:
    #             notify_playlists_message += (
    #                 f"\n- {self.spotify.user_sp.playlist(playlist_id)['name']}"
    #             )
    #
    #         self.bot.send_message(
    #             self.chat_id,
    #             f"These are the playlist in your notify list:\n{notify_playlists_message}",
    #         )

    def last_played(self) -> None:
        last_played: Dict[str, any] = self.spotify.user_sp.current_user_recently_played(
            limit=1
        )
        track_name: str = last_played["items"][0]["track"]["name"]
        track_url: str = last_played["items"][0]["track"]["external_urls"]["spotify"]
        artist_name: str = last_played["items"][0]["track"]["artists"][0]["name"]
        artist_url: str = last_played["items"][0]["track"]["artists"][0][
            "external_urls"
        ]["spotify"]

        self.bot.send_message(
            self.chat_id,
            f"You last played <a href='{track_url}'>{track_name}</a> by <a href='{artist_url}'>{artist_name}</a>.",
            parse_mode="HTML",
        )

    def retrieve_playlists(self) -> None:
        playlists = self.get_user_playlists()

        playlist_names: List[str] = [playlist["name"] for playlist in playlists]
        playlist_urls: List[str] = [
            playlist["external_urls"]["spotify"] for playlist in playlists
        ]
        playlists_message: str = ""

        for name, url in zip(playlist_names, playlist_urls):
            playlists_message += f"\n<a href='{url}'>{name}</a>"

        self.bot.send_message(
            self.chat_id,
            f"Here's a list of the playlists in your library:\n{playlists_message}",
            parse_mode="HTML",
        )

    def top_ten(self) -> None:
        top_ten: Dict[str, any] = self.spotify.user_sp.current_user_top_tracks(
            limit=10, offset=0, time_range="medium_term"
        )["items"]
        top_ten_names: List[str] = [track["name"] for track in top_ten]
        top_ten_urls: List[str] = [
            track["external_urls"]["spotify"] for track in top_ten
        ]
        top_ten_artists: List[str] = [track["artists"][0]["name"] for track in top_ten]
        top_ten_message: str = ""

        for i, (track_name, track_url, artist_name) in enumerate(
            zip(top_ten_names, top_ten_urls, top_ten_artists), start=1
        ):
            top_ten_message += (
                f"\n{i}- <a href='{track_url}'>{track_name}</a> by {artist_name}"
            )

        self.bot.send_message(
            self.chat_id,
            f"⭐ You've got these ten on repeat lately:\n{top_ten_message}",
            parse_mode="HTML",
        )

    def recommended(self) -> None:
        # TODO: create loops to increment known_tracks data to filter through and
        # create a loop to complete recommended tracks list to 10 if any track is actually removed

        recently_played: List[str] = [
            track["track"]["id"]
            for track in self.spotify.user_sp.current_user_recently_played(limit=50)[
                "items"
            ]
        ]
        liked_tracks: List[str] = [
            track["track"]["id"]
            for track in self.spotify.user_sp.current_user_saved_tracks(limit=20)[
                "items"
            ]
        ]
        favorite_tracks: List[str] = [
            track["id"]
            for track in self.spotify.user_sp.current_user_top_tracks(
                limit=20, time_range="short_term"
            )["items"]
        ]

        known_tracks: List[str] = recently_played + liked_tracks + favorite_tracks

        top_five_artists: Dict[
            str, any
        ] = self.spotify.user_sp.current_user_top_artists(
            limit=5, time_range="short_term"
        )[
            "items"
        ]
        seed_artists: List[int] = [artist["id"] for artist in top_five_artists]

        recommended: List[str, any] = [
            track
            for track in self.spotify.user_sp.recommendations(
                seed_artists=seed_artists, limit=10
            )["tracks"]
            if track["id"] not in known_tracks
        ]

        # recommended_ids: List[str] = [track["id"] for track in recommended] TODO: remove this line if not used in function update
        recommended_names: List[str] = [track["name"] for track in recommended]
        recommended_urls: List[str] = [
            track["external_urls"]["spotify"] for track in recommended
        ]
        recommended_artists: List[str] = [
            track["artists"][0]["name"] for track in recommended
        ]
        recommended_artists_urls: List[str] = [
            track["artists"][0]["external_urls"]["spotify"] for track in recommended
        ]
        recommended_message: str = ""

        for name, url, artist, artist_url in zip(
            recommended_names,
            recommended_urls,
            recommended_artists,
            recommended_artists_urls,
        ):
            recommended_message += (
                f"\n- <a href='{url}'>{name}</a> by <a href='{artist_url}'>{artist}</a>"
            )

        self.bot.send_message(
            self.chat_id,
            f"❤ You might like these tracks I found for you:\n{recommended_message}",
            parse_mode="HTML",
        )

    def start_listening(self) -> None:
        try:
            print("Notify started!")

            # TODO: check why this code is not working on production

            # if os.path.isfile(
            #     NOTIFY_DB
            # ) and self.database.fetch_users() not in [None, []]:
            #     for user in self.database.fetch_users():
            #         self.bot.send_message(
            #             user,
            #             "Updates have been made to Notify!\n\n- Commands /notify, /removenotify and /shownotify have been temporarily disabled.",
            #         )

            self.bot.infinity_polling()

        except Exception as e:
            print(f"Bot polling error: {e}")

    def run(self):
        while not self.kill_received:
            self.start_listening()
