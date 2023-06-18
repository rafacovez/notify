import os
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

database = os.getenv("SPOTIFY_ACCOUNTS_DB")

# create a new Spotipy instance
scope = "user-read-private user-read-recently-played user-top-read playlist-read-private playlist-read-collaborative"

sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("REDIRECT_URI"),
    scope=scope,
)

sp = spotipy.Spotify(oauth_manager=sp_oauth)

# creates a dictionary of playlists to be notified about
notification_dict = {}


# looks for changes in users notify lists every second
def worker():
    while True:
        try:
            for refresh_token, notify_dict in notification_dict.items():
                playlist_list = notify_dict["playlist_list"]
                chat_id = notify_dict["chat_id"]
                info = sp_oauth.refresh_access_token(refresh_token)
                access_token = info["access_token"]
                user_sp = spotipy.Spotify(auth=access_token)
                for playlist_obj in playlist_list:
                    playlist = user_sp.playlist(playlist_obj["playlist_id"])
                    if playlist["snapshot_id"] != playlist_obj["snapshot_id"]:
                        playlist_obj["snapshot_id"] = playlist["snapshot_id"]
                        playlist_url = (
                            f"https://open.spotify.com/playlist/{playlist['id']}"
                        )
                        bot.send_message(
                            chat_id,
                            f"Playlist '<a href='{playlist_url}'>{playlist['name']}</a>' has changed!",
                            parse_mode="HTML",
                        )

            sleep(1)

        except Exception as e:
            print(f"Exception in worker thread! {e}")


# threading.Thread(target=worker, daemon=True).start()


# @bot.message_handler(commands=["notify"])
def notify_command(message):
    chat_id = message.chat.id

    create_table()
    store_user_ids(message)

    # ask for auth if it hasn't been done yet
    if get_access_token(message) is None:
        send_auth_url(message)
    else:
        msg: str = message.text
        playlist_name = msg.replace("/notify", "").strip()

        if not playlist_name:
            bot.send_message(
                chat_id,
                f"Please provide a playlist. \nEx: `/notify <PLAYLIST_NAME>`",
                parse_mode="Markdown",
            )
            return
        # get access to users spotify data
        access_token = refresh_access_token(message)
        user_sp = spotipy.Spotify(auth=access_token)

        user_playlists_arr = []
        user_playlists = user_sp.current_user_playlists(limit=50, offset=0)

        if len(user_playlists["items"]) > 0:
            user_playlists_arr = [playlist for playlist in user_playlists["items"]]
            if len(user_playlists["items"]) >= 50:
                offset = 50
                while True:
                    user_playlists = user_sp.current_user_playlists(
                        limit=50, offset=offset
                    )
                    if len(user_playlists["items"]) > 0:
                        user_playlists_arr += [
                            playlist for playlist in user_playlists["items"]
                        ]
                        if len(user_playlists["items"]) < 50:
                            break
                        offset += 50
                    else:
                        break

        for playlist in user_playlists_arr:
            if playlist["name"] == playlist_name:
                refresh_token = get_refresh_token(message)
                if refresh_token not in notification_dict.keys():
                    notification_dict[refresh_token] = {
                        "playlist_list": [],
                        "chat_id": chat_id,
                    }
                else:
                    for playlist_dict in notification_dict[refresh_token][
                        "playlist_list"
                    ]:
                        if playlist_dict["playlist_name"] == playlist["name"]:
                            bot.send_message(
                                chat_id,
                                f"Playlist '{playlist_name}' is in your Notify list already.",
                            )
                            return
                notification_dict[refresh_token]["playlist_list"].append(
                    {
                        "playlist_id": playlist["id"],
                        "playlist_name": playlist["name"],
                        "snapshot_id": playlist["snapshot_id"],
                    }
                )
                bot.send_message(
                    chat_id, f"Added playlist '{playlist_name}' to your Notify list."
                )
                return

        bot.send_message(chat_id, f"Playlist '{playlist_name}' was not found!")


# @bot.message_handler(commands=["shownotifylist"])
def get_notify_list(message):
    chat_id = message.chat.id

    for refresh_token, notify_dict in notification_dict.items():
        if chat_id == notify_dict["chat_id"]:
            notify_playlist_names = []
            if len(notify_dict["playlist_list"]) == 0:
                bot.send_message(
                    chat_id, f"You dont have any playlist in your Notify list"
                )
                return
            for playlist in notify_dict["playlist_list"]:
                playlist_url = (
                    f"https://open.spotify.com/playlist/{playlist['playlist_id']}"
                )
                notify_playlist_names.append(
                    f"<a href='{playlist_url}'>{playlist['playlist_name']}</a>"
                )
                name_list_str = "\n".join(notify_playlist_names)
            bot.send_message(
                chat_id,
                f"You will be notified if any of the following playlists change: \n{name_list_str}",
                parse_mode="HTML",
            )
            return
    bot.send_message(chat_id, f"You dont have any playlist in your Notify list")


# @bot.message_handler(commands=["removenotify"])
def remove_notify(message):
    chat_id = message.chat.id

    create_table()
    store_user_ids(message)

    # ask for auth if it hasn't been done yet
    if get_access_token(message) is None:
        send_auth_url(message)

    else:
        msg: str = message.text
        playlist_name = msg.replace("/removenotify", "").strip()
        if not playlist_name:
            bot.send_message(
                chat_id,
                f"Please provide a playlist to remove from your notify list. \nEx: `/removenotify <PLAYLIST_NAME>`",
                parse_mode="Markdown",
            )
            return
        for refresh_token, notify_dict in notification_dict.items():
            if chat_id == notify_dict["chat_id"]:
                if len(notify_dict["playlist_list"]) == 0:
                    bot.send_message(
                        chat_id, f"You dont have any playlist in your Notify list"
                    )
                    return
                for i in range(len(notify_dict["playlist_list"])):
                    if (
                        notify_dict["playlist_list"][i]["playlist_name"]
                        == playlist_name
                    ):
                        del notify_dict["playlist_list"][i]
                        bot.send_message(
                            chat_id,
                            f"Removed playlist '{playlist_name}' from your Notify list!",
                        )
                        return
                bot.send_message(chat_id, f"Playlist '{playlist_name}' was not found!")
                return

        bot.send_message(chat_id, f"You dont have any playlist in your Notify list")


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
        # Implementation of common code
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
        # Implementation of specific code (to be overridden by derived classes)
        pass


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
        user_playlists_arr = []
        user_playlists = user_sp.current_user_playlists(limit=50, offset=0)

        if len(user_playlists["items"]) > 0:
            user_playlists_arr = [playlist for playlist in user_playlists["items"]]
            if len(user_playlists["items"]) >= 50:
                offset = 50
                while True:
                    user_playlists = user_sp.current_user_playlists(
                        limit=50, offset=offset
                    )
                    if len(user_playlists["items"]) > 0:
                        user_playlists_arr += [
                            playlist for playlist in user_playlists["items"]
                        ]
                        if len(user_playlists["items"]) < 50:
                            break
                        offset += 50
                    else:
                        break

            user_playlists_names_arr = []
            for playlist in user_playlists_arr:
                playlist_url = f"https://open.spotify.com/playlist/{playlist['id']}"
                user_playlists_names_arr.append(
                    f"<a href='{playlist_url}'>{playlist['name']}</a>"
                )
            user_playlists_names = " \n".join(user_playlists_names_arr)
            bot.send_message(
                chat_id,
                f"Here's a list of your playlists: \n{user_playlists_names}.",
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


lastplayed_handler = LastPlayedCommandHandler(bot)
myplaylists_handler = MyPlaylistsCommandHandler(bot)
mytopten_handler = MyTopTenCommandHandler(bot)
recommended_handler = RecommendedCommandHandler(bot)


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
