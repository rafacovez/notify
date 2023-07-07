import os
import sqlite3
from typing import *

from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth  # spotify authentication handler
from telebot import TeleBot  # telegram bots interaction library
from telebot.types import *

from my_functions import *

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

    def __do_nothing(self) -> None:
        pass

    def get_user_sp(self, access_token: str) -> Spotify:
        self.user_sp: Spotify = Spotify(auth=access_token)
        return self.user_sp


class NotifyBot:
    def __init__(self, bot_token: str, spotify: Spotify, database: Database) -> None:
        self.bot_token: str = bot_token
        self.bot: TeleBot = TeleBot(self.bot_token)
        self.spotify: Spotify = spotify
        self.database: Database = database
        self.message: Optional[Message] = None
        self.user_id: Optional[int] = None
        self.chat_id: Optional[int] = None
        self.bot.register_message_handler(self.handle_message)
        self.commands: Dict[str, Dict[str, Union[Callable[..., Any], str]]] = {
            "start": {"func": self.start, "desc": "Starts Notify"},
            "help": {
                "func": self.start,
                "desc": "Provides help for using Notify",
            },
            "login": {
                "func": self.auth_user,
                "desc": "Authorize Notify to access your Spotify account.",
            },
            "notify": {
                "func": self.__do_nothing,
                "desc": "Start tracking a playlist to get notified when someone else adds or removes a song from it.",
            },
            "removenotify": {
                "func": self.__do_nothing,
                "desc": "Stop tracking a playlist.",
            },
            "shownotify": {
                "func": self.__do_nothing,
                "desc": "Get a list of the tracked playlists.",
            },
            "lastplayed": {
                "func": self.last_played,
                "desc": "Get the last track you played.",
            },
            "playlists": {
                "func": self.__do_nothing,
                "desc": "Get a list of the playlists you own.",
            },
            "topten": {
                "func": self.__do_nothing,
                "desc": "Get a list of the top 10 songs you listen to the most lately.",
            },
            "recommended": {
                "func": self.__do_nothing,
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
                f"Please <a href='{auth_url}'>authorize me</a> to access your Spotify account, then try again.",
                parse_mode="HTML",
            )

    def start(self) -> None:
        self.bot.send_message(self.chat_id, "Start")

    def last_played(self) -> None:
        print("Last played func logic!")

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
