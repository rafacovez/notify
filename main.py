import os
import sqlite3
from typing import *

from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth  # spotify authentication handler
from telebot import TeleBot  # telegram bots interaction library
from telebot.types import *

load_dotenv()


class Database:
    def __init__(self, database: str, backup: str = "backup.db") -> None:
        self.database: str = database
        self.backup: str = backup
        self.conn: sqlite3.Connection = None
        self.backup_conn: sqlite3.Connection = None
        self.cursor: sqlite3.Cursor = None

    def __do_nothing(self) -> None:
        pass

    def __connect(self) -> None:
        try:
            self.conn = sqlite3.connect(self.database)

        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")

        self.cursor = self.conn.cursor()

    def __disconnect(self) -> None:
        try:
            self.conn.commit()
            self.backup_conn = sqlite3.connect(self.backup)
            self.conn.backup(self.backup_conn)
            self.backup_conn.close()
        except sqlite3.Error as e:
            print(f"Error commiting changes: {e}")
        self.cursor.close()
        self.conn.close()

    def process(self, func: Callable = None) -> Any:
        if func is None:
            self.__do_nothing()
        else:
            self.__connect()
            result = func()
            self.__disconnect()
            return result

    def create_users_table(self) -> None:
        def logic() -> None:
            self.cursor.execute(
                "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, telegram_user_id INTEGER, spotify_user_display TEXT, spotify_user_id TEXT, refresh_token TEXT, access_token TEXT)"
            )

        self.process(logic)

    def user_exists(self, user: int) -> bool:
        def logic() -> bool:
            self.cursor.execute(
                "SELECT telegram_user_id FROM users WHERE telegram_user_id = ?",
                (user,),
            )
            user_id: int = self.cursor.fetchone()

            if user_id is None:
                return False
            else:
                return True

        return self.process(logic)

    def delete_user(self, user: int) -> None:
        def logic() -> None:
            self.cursor.execute(
                "DELETE FROM users WHERE telegram_user_id = ?",
                (user,),
            )

        self.process(logic)

    def get_access_token(self, user: int) -> str:
        def logic() -> str:
            self.cursor.execute(
                "SELECT access_token from users WHERE telegram_user_id = ?", (user,)
            )

            return self.cursor.fetchone()[0]

        return self.process(logic)

    def get_refresh_token(self, user: int) -> str:
        def logic() -> str:
            self.cursor.execute(
                "SELECT refresh_token from users WHERE telegram_user_id = ?", (user,)
            )

            return self.cursor.fetchone()[0]

        return self.process(logic)

    def store_access_token(self, access_token: str, user: int) -> None:
        def logic() -> None:
            self.cursor.execute(
                "UPDATE users SET access_token = ? WHERE telegram_user_id = ?",
                (access_token, user),
            )

        self.process(logic)


class SpotifyHandler:
    def __init__(
        self, client_id: str, client_secret: str, redirect_uri: str, scope: str
    ) -> None:
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.redirect_uri: str = redirect_uri
        self.scope: str = scope
        self.sp_oauth: SpotifyOAuth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
        )
        self.sp: Spotify = Spotify(oauth_manager=self.sp_oauth)
        self.user_sp: Optional[Spotify] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def __do_nothing(self) -> None:
        pass

    def get_user_sp(self, access_token: str) -> Spotify:
        self.user_sp: Spotify = Spotify(auth=access_token)
        return self.user_sp

    def refresh_access_token(self) -> str:
        return self.sp_oauth.refresh_access_token(self.refresh_token)["access_token"]


class NotifyBot:
    def __init__(self, bot_token: str, spotify: Spotify, database: Database) -> None:
        self.bot_token: str = bot_token
        self.bot: TeleBot = TeleBot(self.bot_token)
        self.spotify: SpotifyHandler = spotify
        self.database: Database = database
        self.message: Optional[Message] = None
        self.user_id: Optional[int] = None
        self.chat_id: Optional[int] = None
        self.bot.register_message_handler(self.handle_message)
        self.commands: Dict[str, Dict[str, Union[Callable[..., Any], str]]] = {
            "start": {"func": self.help, "desc": "Starts Notify"},
            "help": {
                "func": self.help,
                "desc": "Provides help for using Notify",
            },
            "login": {
                "func": self.auth_user,
                "desc": "Authorize Notify to access your Spotify account.",
            },
            "logout": {
                "func": self.delete_user,
                "desc": "Permanently deletes your data from Notify",
            },
            "notify": {
                "func": self.notify,
                "desc": "Start tracking a playlist to get notified when someone else adds or removes a song from it.",
            },
            "removenotify": {
                "func": self.notify,
                "desc": "Stop tracking a playlist.",
            },
            "shownotify": {
                "func": self.notify,
                "desc": "Get a list of the tracked playlists.",
            },
            "lastplayed": {
                "func": self.last_played,
                "desc": "Get the last track you played.",
            },
            "playlists": {
                "func": self.playlists,
                "desc": "Get a list of the playlists you own.",
            },
            "topten": {
                "func": self.top_ten,
                "desc": "Get a list of the top 10 songs you listen to the most lately.",
            },
            "recommended": {
                "func": self.recommended,
                "desc": "Get a list of 5 tracks you might like based on what you're listening to these days.",
            },
        }
        self.command_list: List[BotCommand] = []
        for key, val in self.commands.items():
            self.command_list.append(BotCommand(f"/{key}", val.get("desc", "")))
        self.bot.set_my_commands(self.command_list)

    def __do_nothing(self) -> None:
        pass

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

    def help(self) -> None:
        commands: str = ""
        for command_item in self.command_list:
            commands += f"\n {command_item.command}: {command_item.description}"

        self.bot.send_message(
            self.chat_id,
            f"You can try one of these commands out: \n{commands}",
        )

    def notify(self) -> None:
        self.bot.send_message(
            self.chat_id, "My developers are working on that... Try it later!"
        )

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

    def playlists(self) -> None:
        offset = 0
        playlists: List[Dict[str, any]] = []

        while True:
            response: Dict[str, any] = self.spotify.user_sp.current_user_playlists(
                offset=offset
            )
            fetched_playlists: List[Dict[str, any]] = response["items"]
            playlists += fetched_playlists
            offset += len(fetched_playlists)

            if len(fetched_playlists) < 50:
                break

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

        for track_name, track_url, artist_name in zip(
            top_ten_names, top_ten_urls, top_ten_artists
        ):
            top_ten_message += (
                f"\n- <a href='{track_url}'>{track_name}</a> by {artist_name}"
            )

        self.bot.send_message(
            self.chat_id,
            f"⭐ You've got these ten on repeat lately:\n{top_ten_message}",
            parse_mode="HTML",
        )

    def recommended(self) -> None:
        self.bot.send_message(self.chat_id, "Let me think...", parse_mode="HTML")
        top_five_artists: Dict[
            str, any
        ] = self.spotify.user_sp.current_user_top_artists(
            limit=5, time_range="short_term"
        )[
            "items"
        ]
        seed_artists: List[int] = [artist["id"] for artist in top_five_artists]

        recommended: Dict[str, any] = self.spotify.user_sp.recommendations(
            seed_artists=seed_artists, limit=10
        )["tracks"]

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

    def determine_function(self, message: Message) -> None:
        self.message = message
        message_text: str = self.message.text.strip()
        self.user_id: int = self.message.from_user.id
        self.chat_id: int = self.message.chat.id
        command_exists: bool = False

        if message_text.startswith("/"):
            command: str = self.message.text
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
                        self.spotify.user_sp = Spotify(auth=self.spotify.access_token)
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

        else:
            self.bot.send_message(self.chat_id, "Sorry, I only speak commands...")

    def handle_message(self, message: Message) -> None:
        if message.content_type == "text":
            self.determine_function(message)

    def start_listening(self) -> None:
        print("Notify started!")
        self.bot.infinity_polling()

    def stop_listening(self) -> None:
        print("Notify stopped.")
        self.bot.stop_polling()


if __name__ == "__main__":
    bot = NotifyBot(
        bot_token=os.getenv("BOT_API_TOKEN"),
        spotify=SpotifyHandler(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("REDIRECT_URI"),
            scope="user-read-private user-read-recently-played user-top-read playlist-read-private playlist-read-collaborative",
        ),
        database=Database(os.getenv("NOTIFY_DB")),
    )

    try:
        bot.start_listening()
    except Exception as e:
        print(f"Error starting bot: {e}")
