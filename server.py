import os
import sqlite3
from typing import List

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv()

database: str = os.getenv("NOTIFY_DB")

app: Flask = Flask(__name__)


@app.route("/callback")
def callback():
    try:
        conn = sqlite3.connect(database)

    except Exception as e:
        print(f"Error connecting to database: {e}")

    cursor = conn.cursor()

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

        # get user_id
        user_id: str = request.args.get("state")

        refresh_token: str = response_data.get("refresh_token")
        access_token: str = response_data.get("access_token")

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

        return render_template("auth.html")

    cursor.close()
    conn.close()

    # handle other errors
    return render_template("error.html")


redirect_host: str = os.getenv("REDIRECT_HOST")
redirect_port: str = os.getenv("REDIRECT_PORT")

if __name__ == "__main__":
    try:
        app.run(host=redirect_host, port=redirect_port)
    except Exception as e:
        print(f"Error running app: {e}")
