import threading
import signal
import sys
from typing import *

import requests
from flask import Flask, render_template, request
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
            

def shutdown_handler(sig, frame):
    print("Shutting down Notify...")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, shutdown_handler)

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
    
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    try:
        bot.start()
    except KeyboardInterrupt:
        shutdown_handler(None, None)

if __name__ == "__main__":
    main()