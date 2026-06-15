import threading
import signal
import sys
import time
from typing import *

import requests
from flask import Flask, render_template, request
from spotipy import Spotify
from telebot.types import *

from database.database_handler import DatabaseHandler
from integrations.spotify.spotify_service import SpotifyHandler
from bot.telegram_bot import NotifyTelegramBot
import notifier
from config import (
    TELEGRAM_BOT_API_TOKEN,
    TELEGRAM_ADMIN_USERNAMES,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_SCOPE,
    REDIRECT_URI,
    CONTAINER_HOST,
    CONTAINER_PORT,
    MAX_NOTIFY_PLAYLISTS_PER_USER,
    NOTIFY_CHECK_INTERVAL_SECONDS,
    COMMAND_COOLDOWN_SECONDS,
)


class Server(threading.Thread):
    def __init__(
        self,
        bot: NotifyTelegramBot,
        CONTAINER_HOST: str = CONTAINER_HOST,
        CONTAINER_PORT: int = CONTAINER_PORT,
    ) -> None:
        threading.Thread.__init__(self)
        self.kill_received = False
        self.app: Flask = Flask(__name__)
        self.CONTAINER_HOST: str = CONTAINER_HOST
        self.CONTAINER_PORT: int = CONTAINER_PORT
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

                    # store user
                    self.database.add_user(
                        telegram_user_id,
                        spotify_user_display,
                        spotify_user_id,
                        refresh_token,
                        access_token,
                    )

                    return render_template("homepage.html", message="success")

            except Exception as e:
                print(f"An error occurred when trying to authenticate the user: {e}")

            # handle any errors
            return render_template("homepage.html", message="error")

    def start_listening(self) -> None:
        try:
            print(f"Server is up and running!")
            self.app.run(host=self.CONTAINER_HOST, port=self.CONTAINER_PORT)

        except Exception as e:
            print(f"Error trying to run server: {e}")


def shutdown_handler(sig, frame):
    print("Shutting down Notify...")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, shutdown_handler)

    database_handler = DatabaseHandler()

    spotify_handler = SpotifyHandler(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
    )

    bot = NotifyTelegramBot(
        bot_token=TELEGRAM_BOT_API_TOKEN,
        admin_user_ids=TELEGRAM_ADMIN_USERNAMES,
        max_playlists_per_user=MAX_NOTIFY_PLAYLISTS_PER_USER,
        notify_check_interval_seconds=NOTIFY_CHECK_INTERVAL_SECONDS,
        command_cooldown_seconds=COMMAND_COOLDOWN_SECONDS,
        database=database_handler,
        spotify=spotify_handler,
    )

    server = Server(bot)

    flask_thread = threading.Thread(target=server.start_listening, daemon=True)
    notifier_thread = threading.Thread(
        target=notifier.start_notifier_loop,
        args=(bot, database_handler, spotify_handler, NOTIFY_CHECK_INTERVAL_SECONDS),
        daemon=True,
    )
    bot_thread = threading.Thread(target=bot.start_listening, daemon=True)

    flask_thread.start()
    notifier_thread.start()
    bot_thread.start()

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        shutdown_handler(None, None)


if __name__ == "__main__":
    main()
