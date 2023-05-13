import telebot
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
from my_functions import create_table, store_user_ids, get_access_token, send_auth_url, refresh_access_token

load_dotenv()

# initialize the bot
TOKEN = os.getenv("BOT_API_TOKEN")
bot = telebot.TeleBot(TOKEN)

database = os.getenv("SPOTIFY_ACCOUNTS_DB")

# create a new Spotipy instance
scope = "user-read-private user-read-recently-played user-top-read playlist-read-private"

sp_oauth = SpotifyOAuth(client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
                    redirect_uri=os.getenv("REDIRECT_URI"),
                    scope=scope)

sp = spotipy.Spotify(oauth_manager=sp_oauth)

@bot.message_handler(commands=['track'])
def track_command_handler(message):
    chat_id = message.chat.id

    create_table()
    store_user_ids(message)

    # ask for auth if it hasn't been done yet
    if get_access_token(message) is None:
        send_auth_url(message)

    else:
        # get access to users spotify data
        access_token = refresh_access_token(message)
        sp = spotipy.Spotify(auth = access_token)

        # command code
        user_display_name = sp.current_user()['display_name']
        bot.send_message(chat_id, f"Sorry, {user_display_name}, but I'm still working on this one.")


@bot.message_handler(commands=['myplaylists'])
def myplaylists_command_handler(message):
    chat_id = message.chat.id

    create_table()
    store_user_ids(message)

    # ask for auth if it hasn't been done yet
    if get_access_token(message) is None:
        send_auth_url(message)

    else:
        # get access to users spotify data
        access_token = refresh_access_token(message)
        sp = spotipy.Spotify(auth = access_token)

        # command code
        user_spotify_id = sp.current_user()['id']

        user_playlists = sp.current_user_playlists(limit=50, offset=0)

        if len(user_playlists) > 0:
            user_playlists_arr = [playlist for playlist in user_playlists['items'] if playlist['owner']['id'] == user_spotify_id]
            user_playlists_names_arr = [playlist['name'] for playlist in user_playlists_arr]
            user_playlists_names = ", ".join(user_playlists_names_arr)
            bot.send_message(chat_id, f"Here's a list of your playlists: {user_playlists_names}.")
        else:
            bot.send_message(chat_id, "You don't have any playlists of your own yet!")


@bot.message_handler(commands=['mytopten'])
def mytopten_command_handler(message):
    chat_id = message.chat.id

    create_table()
    store_user_ids(message)

    # ask for auth if it hasn't been done yet
    if get_access_token(message) is None:
        send_auth_url(message)

    else:
        # get access to users spotify data
        access_token = refresh_access_token(message)
        sp = spotipy.Spotify(auth = access_token)

        # command code
        user_top_ten = sp.current_user_top_tracks(limit=10, offset=0, time_range='medium_term')['items']
        if len(user_top_ten) > 10:
            user_top_ten_arr = [(track['name'], track['external_urls']['spotify'], track['artists'][0]['name']) for track in user_top_ten]
            user_top_ten_names = ""
            for i, track in enumerate(user_top_ten_arr):
                user_top_ten_names += f"{i+1}- <a href='{track[1]}'>{track[0]}</a> by {track[2]}\n"
            bot.send_message(chat_id, f"You've got these 10 on repeat lately:\n\n{user_top_ten_names}", parse_mode='HTML')
        else:
            bot.send_message(chat_id, "You haven't been listening to anything, really...")


@bot.message_handler(commands=['recommended'])
def recommended_command_handler(message):
    chat_id = message.chat.id

    create_table()
    store_user_ids(message)

    # ask for auth if it hasn't been done yet
    if get_access_token(message) is None:
        send_auth_url(message)

    else:
        # get access to users spotify data
        access_token = refresh_access_token(message)
        sp = spotipy.Spotify(auth = access_token)

        # command code
        user_top_ten = sp.current_user_top_tracks(limit=5, offset=0, time_range='short_term')['items']

        if len(user_top_ten) > 5:
            user_top_ten_uris = [track['uri'] for track in user_top_ten]
            
            recommendations = sp.recommendations(limit=10, seed_tracks=user_top_ten_uris)
    
            tracks_list = []
    
            for track in recommendations['tracks']:
                track_name = track['name']
                artist_name = track['artists'][0]['name']
                track_url = track['external_urls']['spotify']
                recommended_track = f"- <a href='{track_url}'>{track_name}</a> by {artist_name}"
                tracks_list.append(recommended_track)
    
            message_text = "\n".join(tracks_list)
            bot.send_message(chat_id, f"You might like these tracks I found for you:\n\n{message_text}", parse_mode="HTML")
        else:
            bot.send_message(chat_id, "Go play some tracks first!")


@bot.message_handler(commands=['lastplayed'])
def lastplayed_command_handler(message):
    chat_id = message.chat.id

    create_table()
    store_user_ids(message)

    # ask for auth if it hasn't been done yet
    if get_access_token(message) is None:
        send_auth_url(message)

    else:
        # get access to users spotify data
        access_token = refresh_access_token(message)
        sp = spotipy.Spotify(auth = access_token)

        # command code
        user_previous_track = sp.current_user_recently_played(limit=1)

        if len(user_previous_track['items']) > 0:
            track_uri = user_previous_track['items'][0]['track']['uri']
            track_id = track_uri.split(':')[-1]
            track_link = f"https://open.spotify.com/track/{track_id}"
            track_name = user_previous_track['items'][0]['track']['name']
            artist_uri = user_previous_track['items'][0]['track']['artists'][0]['uri']
            artist_id = artist_uri.split(':')[-1]
            artist_url = f"https://open.spotify.com/artist/{artist_id}"
            artist_name = user_previous_track['items'][0]['track']['artists'][0]['name']

            reply_message = f"You last played <a href='{track_link}'>{track_name}</a> by <a href='{artist_url}'>{artist_name}</a>."

            bot.send_message(chat_id, reply_message, parse_mode="HTML")

        else:
            bot.send_message(chat_id, "You haven't played any tracks recently.")


# bot help message
bot_help_reply = "I can help you get notified when your friends add or remove a song from the playlists you share together, show you which are your top 10 songs right now or even recommend you some new tracks.\n\nYou can make me do this for you by using these commands:\n\n/track - Start tracking a collaborative playlist to get notified when someone else adds or removes a song from it\n/myplaylists - Get a list of the playlists you own\n/mytopten - Get a list of the top 10 songs you listen to the most lately\n/recommended - Get a list of 5 tracks you might like based on what you're listening to these days\n/lastplayed - Get the last track you played"

@bot.message_handler(commands=['help'])
def help_command_handler(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, bot_help_reply)
    

@bot.message_handler(commands=['start'])
def start_command_handler(message):
    help_command_handler(message)


# fallback for any message
@bot.message_handler(func=lambda message: True, content_types=['text', 'number', 'document', 'photo'])
def message_handler(message):
    message_text = message.text
    chat_id = message.chat.id
    bot_contribute_reply = "My creator didn't think about that command, <a href='https://github.com/rafacovez/notify'>is it a good idea</a> though?"
    if message_text.startswith('/'):
        # handle unknown commands
        bot.send_message(chat_id, bot_contribute_reply, parse_mode="HTML")
    else:
        # handle others
        bot.send_message(chat_id, bot_help_reply)


# start the bot
bot.infinity_polling()