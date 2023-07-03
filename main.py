import os
import sqlite3

from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth  # spotify authentication handler
from telebot import TeleBot  # telegram bots interaction library
from telebot.types import BotCommand, Message

from my_functions import *

# loads environment variables
load_dotenv()

# creates a new Spotipy instance
scope: str = "user-read-private user-read-recently-played user-top-read playlist-read-private playlist-read-collaborative"

sp_oauth: SpotifyOAuth = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("REDIRECT_URI"),
    scope=scope,
)

sp: Spotify = Spotify(oauth_manager=sp_oauth)


class Database:
    def __init__(self, database) -> None:
        self.database: str = database
        self.conn = None
        self.cursor = None

    def __do_nothing(self) -> None:
        pass

    def __connect(self) -> None:
        try:
            self.conn = sqlite3.connect(self.database)
            print(f"Successfully connected to {self.database}")

        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")

        self.cursor = self.conn.cursor()

    def __disconnect(self) -> None:
        try:
            self.conn.commit()
            print(f"Successfully commited changes to {self.database}")
        except sqlite3.Error as e:
            print(f"Error commiting changes to {self.database}: {e}")
        self.cursor.close()
        self.conn.close()

    def process(self, func=None) -> None:
        if func is None:
            self.__do_nothing()
        else:
            self.__connect()
            func()
            self.__disconnect()

    def do_something(self) -> None:
        def logic():
            print("It's alive! IT'S ALIVEEE!")

        self.process(logic)


class NotifyBot:
    def __init__(
        self,
        bot_token,
        database,
    ) -> None:
        self.bot_token: str = bot_token
        self.bot: TeleBot = TeleBot(self.bot_token)
        self.database = database
        self.bot.register_message_handler(self.handle_message)
        self.commands = {
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

        self.command_list = []
        for key, val in self.commands.items():
            self.command_list.append(BotCommand(f"/{key}", val.get("desc", "")))

        self.bot.set_my_commands(self.command_list)

    def __do_nothing(self) -> None:
        pass

    def last_played(self) -> None:
        print("Last played func logic!")

    def determine_function(self, message: Message) -> None:
        if message.content_type == "text":
            message_text: str = message.text.strip()
            chat_id: int = message.chat.id
            command_exists: bool = False

            if message_text.startswith("/"):
                command: str = message.text
                for command_item in self.command_list:
                    if command == command_item.command:
                        command_func: function = self.commands[
                            command_item.command.strip("/")
                        ]["func"]
                        command_func()
                        command_exists = True

                if not command_exists:
                    self.bot.send_message(
                        chat_id,
                        "My creators didn't think about that one yet! <a href='https://github.com/rafacovez/notify'>is it a good idea though?</a>",
                        parse_mode="HTML",
                    )

            else:
                self.bot.send_message(chat_id, "Sorry, I only speak commands...")

    def handle_message(self, message: Message) -> None:
        if message.content_type == "text":
            self.determine_function(message)

    def start_listening(self) -> None:
        print("Notify started!")
        self.bot.infinity_polling()


if __name__ == "__main__":
    bot = NotifyBot(
        bot_token=os.getenv("BOT_API_TOKEN"), database=Database(os.getenv("NOTIFY_DB"))
    )

    try:
        bot.start_listening()

    except Exception as e:
        print(f"Error starting bot: {e}")
