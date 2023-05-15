import os
import sqlite3

import spotipy
import telebot
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

# initialize the bot
TOKEN = os.getenv("BOT_API_TOKEN")
bot = telebot.TeleBot(TOKEN)

database = os.getenv("SPOTIFY_ACCOUNTS_DB")

# create a new Spotipy instance
scope = (
    "user-read-private user-read-recently-played user-top-read playlist-read-private"
)

sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("REDIRECT_URI"),
    scope=scope,
)

sp = spotipy.Spotify(oauth_manager=sp_oauth)


def get_spotify_oauth():
    return sp_oauth


def create_table():
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # create users table if it doesn't exists yet
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, user_id INTEGER, refresh_token TEXT, access_token TEXT)"
    )
    conn.commit()

    cursor.close()
    conn.close()


def store_user_ids(message):
    user_id = message.from_user.id

    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # check if user IDs are already stored in the database
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user_already_exists = cursor.fetchone()

    # inserts if not
    if user_already_exists is None:
        cursor.execute(
            "INSERT INTO users (id, user_id) VALUES (?, ?)",
            (
                None,
                user_id,
            ),
        )
        conn.commit()

    cursor.close()
    conn.close()


def get_access_token(message):
    user_id = message.from_user.id

    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # checks if there's an available access_token
    cursor.execute("SELECT access_token FROM users WHERE user_id = ?", (user_id,))
    access_token = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return access_token


def get_refresh_token(message):
    user_id = message.from_user.id

    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # checks if there's an available refresh_token
    cursor.execute("SELECT refresh_token FROM users WHERE user_id = ?", (user_id,))
    refresh_token = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return refresh_token


def send_auth_url(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # get spotify auth url
    auth_url = sp_oauth.get_authorize_url(state=user_id)
    link = f'<a href="{auth_url}">authorize me</a>'

    # send auth url to the user
    bot.send_message(
        chat_id,
        f"Please {link} to access your Spotify account, then type this command again.",
        parse_mode="HTML",
    )


def refresh_access_token(message):
    auth_manager = get_spotify_oauth()
    refresh_token = get_refresh_token(message)
    new_token_info = auth_manager.refresh_access_token(refresh_token)
    access_token = new_token_info["access_token"]

    return access_token
