import threading
from optparse import OptionParser
from typing import *

import requests
from flask import Flask, render_template, request, send_file
from spotipy import Spotify
from telebot.types import *

from api.services.database_service import DatabaseHandler
from api.services.spotify_service import SpotifyHandler
from bot.telegram_bot import NotifyTelegramBot
from config.config import (
    BOT_API_TOKEN,
    NOTIFY_DB,
    SERVER_HOST,
    SERVER_PORT,
    REDIRECT_URI,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
)


class Server(threading.Thread):
    def __init__(
        self,
        bot: NotifyTelegramBot,
        server_host: str = SERVER_HOST,
        server_port: int = SERVER_PORT,
    ) -> None:
        threading.Thread.__init__(self)
        self.kill_received = False
        self.app: Flask = Flask(__name__)
        self.server_host: str = server_host
        self.server_port: int = server_port
        self.bot: NotifyTelegramBot = bot
        self.database: DatabaseHandler = self.bot.database
        self.spotify: SpotifyHandler = self.bot.spotify

        @self.app.errorhandler(Exception)
        def handle_error(e) -> Any:
            print(f"An error occurred: {e}")

            return render_template("homepage.html", message="error"), 500

        @self.app.route("/")
        def homepage() -> Any:
            return render_template("homepage.html")

        @self.app.route("/db")
        def get_db():
            return send_file("notify.db", as_attachment=True)

        @self.app.route("/callback")
        def callback() -> Any:
            try:
                # handle authorization denied
                error: str = request.args.get("error")
                if error:
                    return render_template("homepage.html", message="denied")

                # handle authorization code
                code: str = request.args.get("code")
                if code:
                    # exchange authorization code for an access token
                    token_endpoint: str = "https://accounts.spotify.com/api/token"
                    client_id: str = SPOTIFY_CLIENT_ID
                    client_secret: str = SPOTIFY_CLIENT_SECRET
                    redirect_uri: str = REDIRECT_URI
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

                    return render_template("homepage.html", message="success")

            except Exception as e:
                print(f"An error occurred when trying to authenticate the user: {e}")

            # handle any errors
            return render_template("homepage.html", message="error")

    def __do_nothing(self) -> None:
        pass

    def start_listening(self) -> None:
        try:
            print(f"Server is up and running!")
            self.app.run(host=self.server_host, port=self.server_port)

        except Exception as e:
            print(f"Error trying to run server: {e}")

    def run(self):
        while not self.kill_received:
            self.start_listening()
            # sleep(1) TODO: server broke? you should probably enable this, otherwise delete this line


# FIXME: optimize this code for it to use less resources and
# be faster, I'm sure there's a better approach...


# class Worker(threading.Thread):
#     def __init__(
#         self,
#         notify: NotifyTelegramBot,
#     ):
#         threading.Thread.__init__(self)
#         self.kill_received = False
#         self.notify: NotifyTelegramBot = notify
#         self.database: Database = self.notify.database
#         self.sp: Spotify = self.notify.spotify.sp
#         self.bot: TeleBot = self.notify.bot
#         self.sleep_time = 60
#
#     def run(self) -> None:
#         while not self.kill_received:
#             print("Tracking Notify lists!")
#
#             if os.path.isfile(
#                 NOTIFY_DB
#             ) and self.database.fetch_users() not in [None, []]:
#                 for user in self.database.fetch_users():
#                     if self.database.get_notify(user) not in [None, ""]:
#                         notify_playlists: List[str] = self.database.get_notify(
#                             user
#                         ).split(",")
#                         prev_notify_snapshots: List[str] = [
#                             f"{playlist_id}:{self.sp.playlist(playlist_id)['snapshot_id']}"
#                             for playlist_id in notify_playlists
#                         ]
#
#                         while not self.kill_received:
#                             notify_snapshots: List[str] = [
#                                 f"{playlist_id}:{self.sp.playlist(playlist_id)['snapshot_id']}"
#                                 for playlist_id in notify_playlists
#                             ]
#
#                             if prev_notify_snapshots != notify_snapshots:
#                                 changed_playlists: Optional[List[str]] = [
#                                     playlist_snapshot
#                                     for playlist_snapshot in set(notify_snapshots)
#                                     - set(prev_notify_snapshots)
#                                 ]
#
#                                 if len(changed_playlists) > 1:
#                                     changed_playlists_names = ""
#                                     for playlist in changed_playlists:
#                                         changed_playlist_id = playlist.split(":")[0]
#                                         changed_playlists_names += f"\n- {self.sp.playlist(changed_playlist_id)['name']}"
#
#                                     self.bot.send_message(
#                                         user,
#                                         f"There have been changes in the following playlists:\n{changed_playlists_names}",
#                                     )
#
#                                 else:
#                                     changed_playlist_id = changed_playlists[0].split(
#                                         ":"
#                                     )[0]
#                                     changed_playlist_name = self.sp.playlist(
#                                         changed_playlist_id
#                                     )["name"]
#
#                                     # TODO: get previous tracks and compare them with new generated ones
#                                     # from each notify playlist to tell the user which song was added or removed
#
#                                     """
#                                     prev_changed_playlist_tracks = [
#                                         track["track"]["name"]
#                                         for track in self.sp.playlist_tracks(
#                                             changed_playlist_id
#                                         )["items"]
#                                     ]
#
#                                     print(prev_changed_playlist_tracks)
#                                     """
#
#                                     self.bot.send_message(
#                                         user,
#                                         f"There has been a change in {changed_playlist_name}!",
#                                     )
#
#                             prev_notify_snapshots = notify_snapshots
#
#                             sleep(self.sleep_time)
#             sleep(self.sleep_time)


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
    database_handler = DatabaseHandler(NOTIFY_DB)
    spotify_handler = SpotifyHandler(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-read-private user-read-recently-played user-top-read playlist-read-private playlist-read-collaborative user-library-read",
    )
    bot = NotifyTelegramBot(
        bot_token=BOT_API_TOKEN,
        database=database_handler,
        spotify=spotify_handler,
    )
    server = Server(bot)

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
