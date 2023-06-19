import os
import sqlite3
import threading
from time import sleep

import spotipy  # spotify api interaction library
import telebot  # telegram bots interaction library
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth  # spotify authentication handler

from my_functions import (
    create_table,
    get_access_token,
    get_refresh_token,
    refresh_access_token,
    send_auth_url,
    store_user_ids,
)

# loads variables in .env file
load_dotenv()

# initialize the bot
TOKEN = os.getenv("BOT_API_TOKEN")
bot = telebot.TeleBot(TOKEN)

database = os.getenv("NOTIFY_DB")

# create a new Spotipy instance
scope = "user-read-private user-read-recently-played user-top-read playlist-read-private playlist-read-collaborative"

sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("REDIRECT_URI"),
    scope=scope,
)

sp = spotipy.Spotify(oauth_manager=sp_oauth)


class BaseCommandHandler:
    def __init__(self, bot):
        self.bot = bot

    def handle_command(self, message):
        self.common_code(message)

        state, user_sp, chat_id, user_id = self.common_code(message)

        if state:
            self.specific_code(message, user_sp, chat_id, user_id)

    # base code every command goes through before executing specific command code
    def common_code(self, message):
        # implementation of common code
        create_table()
        store_user_ids(message)

        # ask for auth if it hasn't been done yet
        if get_access_token(message) is None:
            send_auth_url(message)

            return False, user_sp, chat_id, user_id

        else:
            chat_id = message.chat.id
            user_id = message.from_user.id

            # get access to users spotify data
            access_token = refresh_access_token(message)
            user_sp = spotipy.Spotify(auth=access_token)

            return True, user_sp, chat_id, user_id

    def specific_code(self, message, user_sp, chat_id, user_id):
        # implementation of specific code (to be overridden by derived classes)
        pass


class NotifyCommandHandler(BaseCommandHandler):
    def specific_code(self, message, user_sp, chat_id, user_id):
        conn = sqlite3.connect(database)
        cursor = conn.cursor()

        # create notify_list table if it doesn't exists yet
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS notify_list (id INTEGER PRIMARY KEY, user_id INTEGER, playlist_id INTEGER, playlist_name TEXT, playlist_snapshot TEXT)"
        )
        conn.commit()

        # get playlist name from user's message
        playlist_name = message.text.replace("/notify", "").strip()

        # handle /notify command when no playlist name is supplied
        if playlist_name == "":
            bot.send_message(
                chat_id,
                "I need a name to know which playlist you want to be added to your Notify list. \n\nTry something like this: <code>/notify yourplaylist</code>",
                parse_mode="HTML",
            )
        else:
            user_playlists = user_sp.current_user_playlists(limit=50, offset=0)
            user_playlists_arr = [playlist for playlist in user_playlists["items"]]
            playlist_exists = False

            for playlist in user_playlists_arr:
                if playlist_name == playlist["name"]:
                    playlist_exists = True
                    playlist_id = playlist["id"]
                    playlist_snapshot = playlist["snapshot_id"]

            if playlist_exists:
                playlist_id_in_db = cursor.execute(
                    "SELECT playlist_id FROM notify_list WHERE playlist_id = ?",
                    (playlist_id,),
                ).fetchone()

                if playlist_id_in_db is None:
                    cursor.execute(
                        "INSERT INTO notify_list (id, user_id, playlist_id, playlist_name, playlist_snapshot) VALUES (?, ?, ?, ?, ?)",
                        (None, user_id, playlist_id, playlist_name, playlist_snapshot),
                    )
                    conn.commit()

                    bot.send_message(
                        chat_id,
                        f"'{playlist_name}' was successfully added to your library!",
                    )

                else:
                    bot.send_message(
                        chat_id, f"'{playlist_name}' is on your Notify list already"
                    )

            # handle /notify command when playlists doesn't exists in user's library
            else:
                bot.send_message(
                    chat_id,
                    f"'{playlist_name}' is not in your library. Remember your input here is case sensitive. You need to type the name of your playlist just how it looks on Spotify.",
                )

        cursor.close()
        conn.close()


class ShowNotifyListCommandHandler(BaseCommandHandler):
    def specific_code(self, message, user_sp, chat_id, user_id):
        conn = sqlite3.connect(database)
        cursor = conn.cursor()

        user_id_in_db = cursor.execute(
            "SELECT user_id FROM notify_list WHERE user_id = ?", (user_id,)
        ).fetchone()

        if user_id_in_db is None:
            bot.send_message(
                chat_id, "You don't have any playlist in your Notify list yet."
            )

        else:
            user_playlists_name = cursor.execute(
                "SELECT playlist_name FROM notify_list WHERE user_id = ?", (user_id,)
            ).fetchall()
            user_playlists_name_arr = [result[0] for result in user_playlists_name]
            notify_list = "\n- ".join(user_playlists_name_arr)

            bot.send_message(
                chat_id, f"This is your Notify list right now: \n\n- {notify_list}"
            )

        cursor.close()
        conn.close()


class RemoveNotifyCommandHandler(BaseCommandHandler):
    def specific_code(self, message, user_sp, chat_id, user_id):
        conn = sqlite3.connect(database)
        cursor = conn.cursor()

        # get playlist name from user's message
        playlist_name = message.text.replace("/removenotify", "").strip()

        # handle /notify command when no playlist name is supplied
        if playlist_name == "":
            bot.send_message(
                chat_id,
                "I need a name to know which playlist you want to be removed from your Notify list. \n\nTry something like this: <code>/removenotify yourplaylist</code>",
                parse_mode="HTML",
            )
        else:
            user_playlists = user_sp.current_user_playlists(limit=50, offset=0)
            user_playlists_arr = [playlist for playlist in user_playlists["items"]]
            playlist_exists = False

            for playlist in user_playlists_arr:
                if playlist_name == playlist["name"]:
                    playlist_exists = True
                    playlist_id = playlist["id"]

            if playlist_exists:
                playlist_id_in_db = cursor.execute(
                    "SELECT playlist_id FROM notify_list WHERE playlist_id = ?",
                    (playlist_id,),
                ).fetchone()

                if playlist_id_in_db is None:
                    bot.send_message(
                        chat_id, f"'{playlist_name}' is not on your Notify list."
                    )

                else:
                    cursor.execute(
                        "DELETE FROM notify_list WHERE playlist_id = ?",
                        (playlist_id,),
                    )
                    conn.commit()

                    bot.send_message(
                        chat_id,
                        f"'{playlist_name}' was removed to your library.",
                    )

            # handle /notify command when playlists doesn't exists in user's library
            else:
                bot.send_message(
                    chat_id,
                    f"'{playlist_name}' is not in your library. Remember your input here is case sensitive. You need to type the name of your playlist just how it looks on Spotify.",
                )

        cursor.close()
        conn.close()


class LastPlayedCommandHandler(BaseCommandHandler):
    def specific_code(self, message, user_sp, chat_id, user_id):
        user_previous_track = user_sp.current_user_recently_played(limit=1)

        if len(user_previous_track["items"]) > 0:
            track_uri = user_previous_track["items"][0]["track"]["uri"]
            track_id = track_uri.split(":")[-1]
            track_link = f"https://open.spotify.com/track/{track_id}"
            track_name = user_previous_track["items"][0]["track"]["name"]
            artist_uri = user_previous_track["items"][0]["track"]["artists"][0]["uri"]
            artist_id = artist_uri.split(":")[-1]
            artist_url = f"https://open.spotify.com/artist/{artist_id}"
            artist_name = user_previous_track["items"][0]["track"]["artists"][0]["name"]

            reply_message = f"You last played <a href='{track_link}'>{track_name}</a> by <a href='{artist_url}'>{artist_name}</a>."

            bot.send_message(chat_id, reply_message, parse_mode="HTML")

        else:
            bot.send_message(chat_id, "You haven't played any tracks recently.")


class MyPlaylistsCommandHandler(BaseCommandHandler):
    def specific_code(self, message, user_sp, chat_id, user_id):
        user_playlists = user_sp.current_user_playlists(limit=50, offset=0)

        if len(user_playlists["items"]) > 0:
            user_playlists_arr = [playlist for playlist in user_playlists["items"]]
            user_playlists_names_arr = []

            for playlist in user_playlists_arr:
                playlist_url = f"https://open.spotify.com/playlist/{playlist['id']}"
                user_playlists_names_arr.append(
                    f"<a href='{playlist_url}'>{playlist['name']}</a>"
                )
            user_playlists_names = "\n".join(user_playlists_names_arr)
            bot.send_message(
                chat_id,
                f"Here's a list of your playlists: \n\n{user_playlists_names}.",
                parse_mode="HTML",
            )
        else:
            bot.send_message(chat_id, "You don't have any playlists of your own yet!")


class MyTopTenCommandHandler(BaseCommandHandler):
    def specific_code(self, message, user_sp, chat_id, user_id):
        user_top_ten = user_sp.current_user_top_tracks(
            limit=10, offset=0, time_range="medium_term"
        )["items"]
        if len(user_top_ten) >= 10:
            user_top_ten_arr = [
                (
                    track["name"],
                    track["external_urls"]["spotify"],
                    track["artists"][0]["name"],
                )
                for track in user_top_ten
            ]
            user_top_ten_names = ""
            for i, track in enumerate(user_top_ten_arr):
                user_top_ten_names += (
                    f"{i+1}- <a href='{track[1]}'>{track[0]}</a> by {track[2]}\n"
                )
            bot.send_message(
                chat_id,
                f"You've got these 10 on repeat lately:\n\n{user_top_ten_names}",
                parse_mode="HTML",
            )
        else:
            bot.send_message(
                chat_id, "You haven't been listening to anything, really..."
            )


class RecommendedCommandHandler(BaseCommandHandler):
    def specific_code(self, message, user_sp, chat_id, user_id):
        user_top_ten = user_sp.current_user_top_tracks(
            limit=5, offset=0, time_range="short_term"
        )["items"]

        if len(user_top_ten) >= 5:
            user_top_ten_uris = [track["uri"] for track in user_top_ten]

            recommendations = user_sp.recommendations(
                limit=10, seed_tracks=user_top_ten_uris
            )

            tracks_list = []

            for track in recommendations["tracks"]:
                track_name = track["name"]
                artist_name = track["artists"][0]["name"]
                track_url = track["external_urls"]["spotify"]
                recommended_track = (
                    f"- <a href='{track_url}'>{track_name}</a> by {artist_name}"
                )
                tracks_list.append(recommended_track)

            message_text = "\n".join(tracks_list)
            bot.send_message(
                chat_id,
                f"You might like these tracks I found for you:\n\n{message_text}",
                parse_mode="HTML",
            )
        else:
            bot.send_message(chat_id, "Go play some tracks first!")


notify_handler = NotifyCommandHandler(bot)
shownotifylist_handler = ShowNotifyListCommandHandler(bot)
removenotify_handler = RemoveNotifyCommandHandler(bot)
lastplayed_handler = LastPlayedCommandHandler(bot)
myplaylists_handler = MyPlaylistsCommandHandler(bot)
mytopten_handler = MyTopTenCommandHandler(bot)
recommended_handler = RecommendedCommandHandler(bot)


@bot.message_handler(commands=["notify"])
def notify_command_handler(message):
    notify_handler.handle_command(message)


@bot.message_handler(commands=["shownotifylist"])
def notifylist_command_handler(message):
    shownotifylist_handler.handle_command(message)


@bot.message_handler(commands=["removenotify"])
def removenotify_command_handler(message):
    removenotify_handler.handle_command(message)


@bot.message_handler(commands=["lastplayed"])
def lastplayed_command_handler(message):
    lastplayed_handler.handle_command(message)


@bot.message_handler(commands=["myplaylists"])
def myplaylists_command_handler(message):
    myplaylists_handler.handle_command(message)


@bot.message_handler(commands=["mytopten"])
def mytopten_command_handler(message):
    mytopten_handler.handle_command(message)


@bot.message_handler(commands=["recommended"])
def recommended_command_handler(message):
    recommended_handler.handle_command(message)


# bot help message
bot_help_reply = "I can notify you about playlists activity, recommend you songs or show you your top ten.\n\nYou can make me do this for you by using these commands:\n\n/lastplayed - Get the last track you played\n/myplaylists - Get a list of the playlists you own\n/mytopten - Get a list of the top 10 songs you listen to the most lately\n/recommended - Get a list of 5 tracks you might like based on what you're listening to these days"


@bot.message_handler(commands=["help"])
def help_command_handler(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, bot_help_reply)


@bot.message_handler(commands=["start"])
def start_command_handler(message):
    help_command_handler(message)


# fallback for any message that's not a command
@bot.message_handler(
    func=lambda message: True, content_types=["text", "number", "document", "photo"]
)
def message_handler(message):
    message_text = message.text
    chat_id = message.chat.id
    bot_contribute_reply = "My creator didn't think about that command, <a href='https://github.com/rafacovez/notify'>is it a good idea</a> though?"
    if message_text.startswith("/"):
        # handle unknown commands
        bot.send_message(chat_id, bot_contribute_reply, parse_mode="HTML")
    else:
        # handle others
        bot.send_message(chat_id, bot_help_reply)


# start the bot
bot.infinity_polling()
