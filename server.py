import os
from typing import *

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request
from spotipy import Spotify

from main import Database, NotifyBot, SpotifyHandler

load_dotenv()

database: Database = Database(os.getenv("NOTIFY_DB"))
spotify: Spotify = SpotifyHandler(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("REDIRECT_URI"),
    scope="user-read-private user-read-recently-played user-top-read playlist-read-private playlist-read-collaborative",
)
bot: NotifyBot = NotifyBot(
    bot_token=os.getenv("BOT_API_TOKEN"),
    spotify=SpotifyHandler(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("REDIRECT_URI"),
        scope="user-read-private user-read-recently-played user-top-read playlist-read-private playlist-read-collaborative",
    ),
    database=Database(os.getenv("NOTIFY_DB")),
)
app: Flask = Flask(__name__)


@app.route("/callback")
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
            client_id: str = os.getenv("SPOTIFY_CLIENT_ID")
            client_secret: str = os.getenv("SPOTIFY_CLIENT_SECRET")
            redirect_uri: str = os.getenv("REDIRECT_URI")
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

            spotify_sp: Spotify = spotify.get_user_sp(access_token)
            spotify_user_display: str = spotify_sp.current_user()["display_name"]
            spotify_user_id: str = spotify_sp.current_user()["id"]

            if database.user_exists(telegram_user_id):
                print(
                    f"User {telegram_user_id} is already stored in {database.database}"
                )

            else:
                # store the access token in the database
                def update_table() -> None:
                    database.cursor.execute(
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

                database.process(update_table)

            return render_template("auth.html")

    except Exception as e:
        print(f"An error occurred: {e}")

    # handle any errors
    return render_template("error.html")


redirect_host: str = os.getenv("REDIRECT_HOST")
redirect_port: str = os.getenv("REDIRECT_PORT")

if __name__ == "__main__":
    try:
        app.run(host=redirect_host, port=redirect_port)
    except Exception as e:
        print(f"Error running app: {e}")
