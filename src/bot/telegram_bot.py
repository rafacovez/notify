import threading
import time
from collections.abc import Callable
from typing import *

from telebot import TeleBot
from telebot.types import *

from api.services.database_service import DatabaseHandler
from api.services.spotify_service import SpotifyHandler

from api.helpers.spotify_utils import extract_spotify_id


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
        self.callback: str = None
        self.bot.register_message_handler(self.handle_message)
        self.bot.register_callback_query_handler(self.handle_callback, func=lambda call: call.data)
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
                "func": lambda: self.manage_notify("add"),
                "desc": "Start tracking a playlist to get notified when someone else adds or removes a song from it",
            },
            "removenotify": {
                "func": lambda: self.manage_notify("remove"),
                "desc": "Stop tracking a playlist",
            },
            "shownotify": {
                "func": self.show_notify,
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
                "func": self.deprecated_message,
                "desc": "Get a list of 10 songs you might like based on what you've been listening to",
            },
            "throwback": {
                "func": self.throwback,
                "desc": "Get a track you had on repeat a while ago",
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

    def handle_callback(self, call: CallbackQuery) -> None:
        self.callback = call.data
        self.chat_id = call.message.chat.id
        self.user_id = call.from_user.id

        parts = self.callback.split(":")
        action = parts[0]
        
        if len(parts) >= 3 and parts[1] in ("next", "back"):
            try:
                offset = int(parts[2])
                markup = self.gen_playlist_markup(action, offset=offset)
                self.bot.edit_message_reply_markup(
                    chat_id=self.chat_id,
                    message_id=call.message.message_id,
                    reply_markup=markup
                )
            except (IndexError, ValueError) as e:
                print(f"Pagination error: {e}")
            return
        
        elif action == "add_playlist" and len(parts) >= 2:
            self.add_notify(parts[1])

        elif action == "remove_playlist" and len(parts) >= 2:
            self.remove_notify(parts[1])

        else:
            print(f"Unknown or malformed action: {self.callback}")


    def determine_function(self) -> None:
        command: str = self.message.text
        command_exists: bool = False

        for command_item in self.command_list:
            if command.startswith(command_item.command):
                command_exists = True

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
                    
                    try:
                        command_func()
                    except Exception as e:
                        print(f"Error executing command {command}: {e}")
                        self.bot.send_message(
                            self.chat_id,
                            "An error occurred while executing the command. Please try again later.",
                        )

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

    def under_development_message(self) -> None:
        self.bot.send_message(
            self.chat_id,
            "This feature is still under development... Try it again later!",
        )

    def disabled_message(self) -> None:
        self.bot.send_message(
            self.chat_id,
            "This command is temporarily disabled... Try it again later!",
        )

    def deprecated_message(self) -> None:
        self.bot.send_message(
            self.chat_id,
            "This command uses a method that has been deprecated by its API maintainers 😕... Try your luck another time!",
        )

    def help(self) -> None:
        commands: str = ""
        
        for command_item in self.command_list:
            commands += f"\n {command_item.command}: {command_item.description}"

        self.bot.send_message(
            self.chat_id,
            f"You can try one of these commands out: \n{commands}",
        )

    def last_played(self) -> None:
        last_played: Dict[str, any] = self.spotify.get_user_last_played()

        track_name: str = last_played["name"]
        track_url: str = last_played["external_urls"]["spotify"]
        artist_name: str = last_played["artists"][0]["name"]
        artist_url: str = last_played["artists"][0][
            "external_urls"
        ]["spotify"]

        self.bot.send_message(
            self.chat_id,
            f"You last played <a href='{track_url}'>{track_name}</a> by <a href='{artist_url}'>{artist_name}</a>.",
            parse_mode="HTML",
        )

    def retrieve_playlists(self) -> None:
        playlists = self.spotify.get_user_playlists()

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
        top_ten: Dict[str, any] = self.spotify.get_user_top_tracks(limit=10)

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
            f"⭐ You've got these 10 on repeat lately:\n{top_ten_message}",
            parse_mode="HTML",
        )

    def recommended(self) -> None:
        recommended_tracks = self.spotify.get_user_recommended_tracks()

        recommended_names: List[str] = [track["name"] for track in recommended_tracks]
        recommended_urls: List[str] = [
            track["external_urls"]["spotify"] for track in recommended_tracks
        ]
        recommended_artists: List[str] = [
            track["artists"][0]["name"] for track in recommended_tracks
        ]
        recommended_artists_urls: List[str] = [
            track["artists"][0]["external_urls"]["spotify"] for track in recommended_tracks
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
            f"❤️ You might like these tracks I found for you:\n{recommended_message}",
            parse_mode="HTML",
        )

    def throwback(self) -> None:
        throwback: Dict[str, any] = self.spotify.get_user_throwback()

        track_name: str = throwback["name"]
        track_url: str = throwback["external_urls"]["spotify"]
        artist_name: str = throwback["artists"][0]["name"]
        artist_url: str = throwback["artists"][0][
            "external_urls"
        ]["spotify"]

        self.bot.send_message(
            self.chat_id,
            f"⏳ Remember <a href='{track_url}'>{track_name}</a> by <a href='{artist_url}'>{artist_name}</a>? You had it on repeat a while ago!",
            parse_mode="HTML",
        )

    def gen_playlist_markup(self, callback_action: str, offset: int = 0, limit: int = 4) -> InlineKeyboardMarkup:
        self.callback: str = callback_action

        markup: InlineKeyboardMarkup = InlineKeyboardMarkup()
        markup.row_width = 2

        playlists = self.spotify.get_user_playlists(offset=offset, limit=limit + 1)
        
        theres_more: bool = len(playlists) > limit
        displayed_playlists: List[Dict[str, any]] = playlists[:limit]

        playlist_buttons: List[InlineKeyboardButton] = []

        for playlist in displayed_playlists:

            playlist_name: str = playlist["name"]
            playlist_id: str = playlist["id"]

            playlist_buttons.append(
                InlineKeyboardButton(
                    playlist_name,
                    callback_data=f"{callback_action}:{playlist_id}",
                )
            )

        markup.add(*playlist_buttons)
        
        nav_buttons = []

        if offset > 0:
            nav_buttons.append(
                InlineKeyboardButton("⬅️ Back", callback_data=f"{callback_action}:back:{offset - limit}")
            )
        if theres_more:
            nav_buttons.append(
                InlineKeyboardButton("➡️ Next", callback_data=f"{callback_action}:next:{offset + limit}")
            )
            
        if nav_buttons:
            if len(nav_buttons) == 1:
                markup.row(nav_buttons[0])
            else:
                markup.row(*nav_buttons)

        return markup

    def manage_notify(self, action: str) -> None:
        message_text = self.message.text.strip()
        parts = message_text.split(maxsplit=1)

        if len(parts) > 1:
            playlist_id = extract_spotify_id(parts[1].strip())
            playlist = self.spotify.get_playlist(playlist_id)

            print(playlist)

            self.bot.send_message(
                self.chat_id,
                f"Received playlist URL: {playlist_id}",
            )
        else:
            markup: InlineKeyboardMarkup = self.gen_playlist_markup(
                callback_action=f"{action}_playlist"
            )

            self.bot.send_message(
                self.chat_id,
                "Select a playlist",
                reply_markup=markup,
            )

    def add_notify(self, playlist_id: str) -> None:
        playlist: Dict[str, any] = self.spotify.get_playlist(playlist_id)

        if playlist:
            if self.database.playlist_exists(self.user_id, playlist["id"]):
                self.bot.send_message(
                    self.chat_id,
                    "You're already tracking this playlist.",
                )
            else:
                notify_count: int = len(self.database.get_notify_playlists_by_user(self.user_id))

                if notify_count >= 3:
                    self.bot.send_message(
                        self.chat_id,
                        "You can only track up to 3 playlists at a time. Please remove one before adding another.",
                    )
                else:
                    self.database.add_notify(
                        telegram_user_id=self.user_id,
                        playlist_id=playlist["id"],
                        snapshot_id=playlist["snapshot_id"],
                    )
                    self.bot.send_message(
                        self.chat_id,
                        f"Now tracking the playlist: {playlist['name']}",
                    )
        else:
            self.bot.send_message(
                self.chat_id,
                "The playlist you provided is not valid or does not exist.",
            )

    def remove_notify(self, playlist_id: str, telegram_user_id: str = None) -> None:
        if not telegram_user_id:
            telegram_user_id = self.user_id

        playlist: Dict[str, any] = self.spotify.get_playlist(playlist_id)

        if playlist:
            if self.database.playlist_exists(telegram_user_id, playlist["id"]):
                self.database.delete_notify(
                    telegram_user_id=telegram_user_id,
                    playlist_id=playlist["id"],
                )
                self.bot.send_message(
                    self.chat_id,
                    f"Stopped tracking the playlist: {playlist['name']}",
                )
            else:
                self.bot.send_message(
                    self.chat_id,
                    "You're not tracking this playlist.",
                )
        else:
            self.bot.send_message(
                self.chat_id,
                "The playlist you provided is not valid or does not exist.",
            )

    def show_notify(self) -> None:
        playlists_ids: List[str] = self.database.get_notify_playlists_by_user(self.user_id)

        if not playlists_ids:
            self.bot.send_message(
                self.chat_id,
                "You're not tracking any playlists.",
            )
        else:
            playlists: List[Dict[str, any]] = self.spotify.get_playlists_by_ids(playlists_ids)

            if not playlists:
                self.bot.send_message(
                    self.chat_id,
                    "No playlists found for the provided IDs.",
                )
            else:
                message: str = "You're currently tracking these playlists:\n"

                for playlist in playlists:
                    message += f"- <a href='{playlist['external_urls']['spotify']}'>{playlist['name']}</a>\n"

                self.bot.send_message(
                    self.chat_id,
                    message,
                    parse_mode="HTML",
                )

    def notify_changes(self) -> None:
        while True:
            try:
                users: List[int] = self.database.fetch_telegram_users()

                if users:
                    for user in users:
                        notify_playlists_ids: List[str] = self.database.get_notify_playlists_by_user(user)

                        if notify_playlists_ids:
                            self.spotify.refresh_token = self.database.get_refresh_token(
                                    user
                                )
                            self.spotify.access_token = self.spotify.refresh_access_token()
                            self.database.store_access_token(
                                self.spotify.access_token, user
                            )
                            self.spotify.user_sp = self.spotify.get_user_sp(
                                self.spotify.access_token
                            )

                            for playlist_id in notify_playlists_ids:
                                playlist: Dict[str, any] = self.spotify.get_playlist(playlist_id)

                                if playlist is not None:
                                    current_snapshot_id: str = playlist["snapshot_id"]
                                    stored_snapshot_id: str = self.database.get_notify_snapshot(user, playlist_id)
                                    
                                    if current_snapshot_id != stored_snapshot_id:
                                        self.database.update_notify_snapshot(
                                            telegram_user_id=user,
                                            playlist_id=playlist_id,
                                            snapshot_id=current_snapshot_id,
                                        )
                                        self.bot.send_message(
                                            user,
                                            f"The playlist {playlist['name']} has been updated! Check it out: {playlist['external_urls']['spotify']}",
                                        )
                                else:
                                    self.remove_notify(playlist_id, user)
                                    self.bot.send_message(
                                        user,
                                        f"Some of the playlists you were tracking no longer exists. They will be removed from your tracking list.",
                                    )
                else:
                    print("No users found in the database.")

                print("Ran Notify changes check at: ", time.strftime("%Y-%m-%d %H:%M:%S"))
            except Exception as e:
                print(f"Error checking playlists: {e}")
            time.sleep(1800)  # 30 minutos = 1800 segundos

    def start_listening(self) -> None:
        try:
            self.database.create_tables()
            self.bot.infinity_polling()

            print("Notify started!")

        except Exception as e:
            print(f"Error starting bot: {e}")

    def run(self):
        while not self.kill_received:
            self.start_listening()
