import os
import sqlite3

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv()

database = os.getenv("NOTIFY_DB")

app = Flask(__name__)


@app.route("/callback")
def callback():
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # handle authorization denied
    error = request.args.get("error")
    if error:
        return render_template("denied.html")

    # handle authorization code
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

        return render_template("auth.html")

    cursor.close()
    conn.close()

    # handle other errors
    return render_template("error.html")


redirect_host = os.getenv("REDIRECT_HOST")
redirect_port = os.getenv("REDIRECT_PORT")

if __name__ == "__main__":
    try:
        app.run(host=redirect_host, port=redirect_port)
    except Exception as e:
        print(f"Error running app: {e}")
