import os
import sqlite3
import threading
from optparse import OptionParser
from time import sleep
from typing import *

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth  # spotify authentication handler
from telebot import TeleBot  # telegram bots interaction library
from telebot.types import *

load_dotenv(dotenv_path=".env.local")


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

    def add_notify(self, playlist: int, user: int) -> None:
        def logic() -> None:
            self.cursor.execute(
                "UPDATE users SET notify = ? WHERE telegram_user_id = ?",
                (playlist, user),
            )

        self.process(logic)

    def create_notify_table(self):
        def logic() -> None:
            self.cursor.execute("")


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


class NotifyBot(threading.Thread):
    def __init__(self, bot_token: str, spotify: Spotify, database: Database) -> None:
        threading.Thread.__init__(self)
        self.kill_received = False
        self.bot_token: str = bot_token
        self.bot: TeleBot = TeleBot(self.bot_token)
        self.database: Database = database
        self.spotify: SpotifyHandler = spotify
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
                "desc": "Authorize Notify to access your Spotify account",
            },
            "logout": {
                "func": self.delete_user,
                "desc": "Permanently deletes your data from Notify",
            },
            "notify": {
                "func": self.notify,
                "desc": "Start tracking a playlist to get notified when someone else adds or removes a song from it",
            },
            "removenotify": {
                "func": self.notify,
                "desc": "Stop tracking a playlist",
            },
            "shownotify": {
                "func": self.notify,
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

    def get_playlists(self) -> List[Dict[str, any]]:
        offset: int = 0
        user_playlists: List[Dict[str, any]] = []

        while True:
            response: Dict[str, any] = self.spotify.user_sp.current_user_playlists(
                offset=offset
            )
            fetched_playlists: List[Dict[str, any]] = response["items"]
            user_playlists += fetched_playlists
            offset += len(fetched_playlists)

            if len(fetched_playlists) < 50:
                break

        return user_playlists

    def notify(self) -> None:
        # TODO: code functionality to add selected playlist ID
        # to 'notify' cell on notifydb database

        playlists = self.get_playlists()

        print(playlists)

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
        playlists = self.get_playlists()

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

    def handle_message(self, message: Message) -> None:
        self.message: Message = message
        self.user_id: int = self.message.from_user.id
        self.chat_id: int = self.message.chat.id

        self.bot.send_chat_action(self.chat_id, "typing")

        if message.content_type == "text" and message.text.strip().startswith("/"):
            self.determine_function()

        else:
            self.bot.send_message(self.chat_id, "Sorry, I only speak commands...")

    def start_listening(self) -> None:
        try:
            print("Notify started!")
            self.bot.infinity_polling()

        except Exception as e:
            print(f"Bot polling error: {e}")

    def run(self):
        while not self.kill_received:
            self.start_listening()
            sleep(1)


class Server(threading.Thread):
    def __init__(
        self,
        redirect_host: str = os.environ.get("REDIRECT_HOST"),
        redirect_port: str = os.environ.get("REDIRECT_PORT"),
        bot: NotifyBot = NotifyBot,
    ) -> None:
        threading.Thread.__init__(self)
        self.kill_received = False
        self.app: Flask = Flask(__name__)
        self.redirect_host: str = redirect_host
        self.redirect_port: str = redirect_port
        self.bot: NotifyBot = bot
        self.database: Database = self.bot.database
        self.spotify: SpotifyHandler = self.bot.spotify

        @self.app.errorhandler(Exception)
        def handle_error(e) -> Any:
            print(f"An error occurred: {e}")

            return render_template("error.html"), 500

        @self.app.route("/callback")
        def callback() -> Any:
            try:
                # handle authorization denied
                error: str = request.args.get("error")
                if error:
                    return render_template("denied.html")

                # handle authorization code
                code: str = request.args.get("code")
                if code:
                    # exchange authorization code for an access token
                    token_endpoint: str = "https://accounts.spotify.com/api/token"
                    client_id: str = os.environ.get("SPOTIFY_CLIENT_ID")
                    client_secret: str = os.environ.get("SPOTIFY_CLIENT_SECRET")
                    redirect_uri: str = os.environ.get("REDIRECT_URI")
                    params: List[str] = {
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    }
                    response: str = requests.post(token_endpoint, data=params)
                    response_data: str = response.json()

                    telegram_user_id: str = request.args.get("state")

                    refresh_token: str = response_data.get("refresh_token")
                    access_token: str = response_data.get("access_token")

                    spotify_sp: Spotify = self.spotify.get_user_sp(access_token)
                    spotify_user_display: str = spotify_sp.current_user()[
                        "display_name"
                    ]
                    spotify_user_id: str = spotify_sp.current_user()["id"]

                    # store the access token in the database
                    def update_table() -> None:
                        self.database.cursor.execute(
                            "INSERT INTO users (id, telegram_user_id, spotify_user_display, spotify_user_id, refresh_token, access_token) VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                None,
                                telegram_user_id,
                                spotify_user_display,
                                spotify_user_id,
                                refresh_token,
                                access_token,
                            ),
                        )

                    self.database.process(update_table)

                    return render_template("auth.html")

            except Exception as e:
                print(f"An error occurred when trying to authenticate the user: {e}")

            # handle any errors
            return render_template("error.html")

    def __do_nothing(self) -> None:
        pass

    def start_listening(self) -> None:
        try:
            print(f"Server is up and running!")
            self.app.run(host=self.redirect_host, port=self.redirect_port)

        except Exception as e:
            print(f"Error trying to run server: {e}")

    def run(self):
        while not self.kill_received:
            self.start_listening()
            sleep(1)


# configuration for script threads
def parse_options():
    parser = OptionParser()
    parser.add_option(
        "-t",
        action="store",
        type="int",
        dest="threadNum",
        default=1,
        help="thread count [1]",
    )
    (options, args) = parser.parse_args()
    return options


# checks if there's any live threads
def has_live_threads(threads):
    return True in [t.is_alive() for t in threads]


def main():
    options = parse_options()
    threads = []
    bot = NotifyBot(
        bot_token=os.environ.get("BOT_API_TOKEN"),
        spotify=SpotifyHandler(
            client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
            client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.environ.get("REDIRECT_URI"),
            scope="user-read-private user-read-recently-played user-top-read playlist-read-private playlist-read-collaborative",
        ),
        database=Database(os.environ.get("NOTIFY_DB")),
    )
    server = Server(bot=bot)

    for i in range(options.threadNum):
        bot_thread = bot
        server_thread = server

        bot_thread.start()
        server_thread.start()

        threads.append(bot_thread)
        threads.append(server_thread)

    while has_live_threads(threads):
        try:
            # synchronization timeout of threads kill
            [t.join(1) for t in threads if t is not None and t.is_alive()]
        except KeyboardInterrupt:
            # Ctrl-C handling and send kill to threads
            print("Stopping Notify... Hit Ctrl + C again if the bot hasn't exited yet")
            for t in threads:
                t.kill_received = True

    print("Exited")


if __name__ == "__main__":
    main()
