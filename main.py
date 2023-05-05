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
scope = "user-read-private playlist-read-private"

sp_oauth = SpotifyOAuth(client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
                    redirect_uri=os.getenv("REDIRECT_URI"),
                    scope=scope)

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


def send_auth_url(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
        
    # get spotify auth url
    auth_url = sp_oauth.get_authorize_url(state=user_id)
    link = f'<a href="{auth_url}">authorize me</a>'

    # send auth url to the user
    bot.send_message(chat_id, f"Please {link} to access your Spotify account, then type this command again.", parse_mode="HTML")
    

@bot.message_handler(commands=['showplaylists'])
def showplaylists_command_handler(message):
    chat_id = message.chat.id

    create_table()
    store_user_ids(message)

    # ask for auth if it hasn't been done yet
    if get_access_token(message) is None:
        send_auth_url(message)

    else:
        sp = spotipy.Spotify(auth = get_access_token(message))
        user_playlists = sp.current_user_playlists()
        user_playlists_names_arr = [playlist['name'] for playlist in user_playlists['items']]
        user_playlists_names = ", ".join(user_playlists_names_arr)
            
        bot.send_message(chat_id, f"Here's a list of your playlists: {user_playlists_names}.")
    

@bot.message_handler(commands=['showplaylists'])
def showplaylists_command_handler(message):
    chat_id = message.chat.id

    create_table()
    store_user_ids(message)

    # ask for auth if it hasn't been done yet
    if get_access_token(message) is None:
        send_auth_url(message)

    else:
        sp = spotipy.Spotify(auth = get_access_token(message))
        user_previous_track = sp.previous_track()
        print(user_previous_track)


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