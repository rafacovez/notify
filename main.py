import telebot
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sqlite3
from dotenv import load_dotenv
import os

load_dotenv()

# initialize the bot
TOKEN = os.getenv("BOT_API_TOKEN")
bot = telebot.TeleBot(TOKEN)

# create a new Spotipy instance
scope = "user-read-private user-read-recently-played user-top-read playlist-read-private"

sp_oauth = SpotifyOAuth(client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
                    redirect_uri=os.getenv("REDIRECT_URI"),
                    scope=scope)

def get_spotify_oauth():
    return sp_oauth

sp = spotipy.Spotify(oauth_manager=sp_oauth)

database = os.getenv("SPOTIFY_ACCOUNTS_DB")

def create_table():
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # create users table if it doesn't exists yet
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, user_id INTEGER, refresh_token TEXT, access_token TEXT)')
    conn.commit()

    cursor.close()
    conn.close()


def store_user_ids(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # check if user IDs are already stored in the database
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    user_already_exists = cursor.fetchone()

    # inserts if not
    if user_already_exists is None:
        cursor.execute('INSERT INTO users (id, user_id) VALUES (?, ?)', (None, user_id,))
        conn.commit()

    cursor.close()
    conn.close()


def get_access_token(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # checks if there's an available access_token
    cursor.execute('SELECT access_token FROM users WHERE user_id = ?', (user_id,))
    access_token = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()

    return access_token


def get_refresh_token(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # checks if there's an available refresh_token
    cursor.execute('SELECT refresh_token FROM users WHERE user_id = ?', (user_id,))
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
    bot.send_message(chat_id, f"Please {link} to access your Spotify account, then type this command again.", parse_mode="HTML")


def refresh_access_token(message):
    user_id = message.from_user.id

    auth_manager = get_spotify_oauth()
    refresh_token = get_refresh_token(message)
    new_token_info = auth_manager.refresh_access_token(refresh_token)
    access_token = new_token_info['access_token']
    
    return access_token
    

@bot.message_handler(commands=['showmyplaylists'])
def showmyplaylists_command_handler(message):
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
        user_playlists = [playlist for playlist in user_playlists['items'] if playlist['owner']['id'] == user_spotify_id]
        user_playlists_names_arr = [playlist['name'] for playlist in user_playlists]
        user_playlists_names = ", ".join(user_playlists_names_arr)
        bot.send_message(chat_id, f"Here's a list of your playlists: {user_playlists_names}.")


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
        user_top_ten = sp.current_user_top_tracks(limit=10, offset=0, time_range='short_term')['items']
        user_top_ten_arr = [(track['name'], track['external_urls']['spotify'], track['artists'][0]['name']) for track in user_top_ten]
        user_top_ten_names = ""
        for i, track in enumerate(user_top_ten_arr):
            user_top_ten_names += f"{i+1}- <a href='{track[1]}'>{track[0]}</a> by {track[2]}\n"
        bot.send_message(chat_id, f"You've got these 10 on repeat lately:\n\n{user_top_ten_names}", parse_mode='HTML')
    

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
bot_help_reply = "I can help you get notified when your friends add or remove a song from the playlists you share together.\n\nYou can make me do this for you by using these commands:\n\n/logintospotify - Set up your Spotify account\n\n/addplaylist - Add a playlist\n\n/removeplaylist - Remove a playlist"

# define the help command handler
@bot.message_handler(commands=['help'])
def help_command_handler(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, bot_help_reply)


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


# Start the bot
bot.polling()