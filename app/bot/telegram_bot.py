import threading
from collections.abc import Callable
from typing import *

from telebot import TeleBot
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
                "func": self.under_development_message,
                "desc": "Start tracking a playlist to get notified when someone else adds or removes a song from it",
            },
            "removenotify": {
                "func": self.under_development_message,
                "desc": "Stop tracking a playlist",
            },
            "shownotify": {
                "func": self.under_development_message,
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

    def start_listening(self) -> None:
        try:
            print("Notify started!")

            self.bot.infinity_polling()

        except Exception as e:
            print(f"Bot polling error: {e}")

    def run(self):
        while not self.kill_received:
            self.start_listening()
