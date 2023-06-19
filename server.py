import os
import sqlite3

import requests
from dotenv import load_dotenv
from flask import Flask, request

load_dotenv()

database = os.getenv("NOTIFY_DB")

app = Flask(__name__)


@app.route("/callback")
def callback():
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # handle if error or authorization denied
    error = request.args.get("error")
    if error:
        cursor.close()
        conn.close()
        return "Authorization denied"

    code = request.args.get("code")
    if code:
        # exchange authorization code for an access token
        token_endpoint = "https://accounts.spotify.com/api/token"
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        redirect_uri = os.getenv("REDIRECT_URI")
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        response = requests.post(token_endpoint, data=params)
        response_data = response.json()

        # get user_id
        user_id = request.args.get("state")

        refresh_token = response_data.get("refresh_token")
        access_token = response_data.get("access_token")

        # store the access token in the database
        try:
            cursor.execute(
                "UPDATE users SET refresh_token = ?, access_token = ? WHERE user_id = ?",
                (refresh_token, access_token, user_id),
            )
            conn.commit()
        except sqlite3.Error as e:
            print("Error storing access token:", e)
            conn.rollback()

        cursor.close()
        conn.close()

        return "The authorization process was successful, you can close this page and return to Telegram now."

    # handle other errors
    cursor.close()
    conn.close()
    return "Unexpected error"


redirect_host = os.getenv("REDIRECT_HOST")
redirect_port = os.getenv("REDIRECT_PORT")

if __name__ == "__main__":
    app.run(host=redirect_host, port=redirect_port)
