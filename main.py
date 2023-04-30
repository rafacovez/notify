import telebot
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

load_dotenv()

# Enter your Telegram Bot API token here
TOKEN = os.getenv("BOT_API_TOKEN")

# Initialize the bot
bot = telebot.TeleBot(TOKEN)

# Create a new Spotipy instance
scope = "user-read-private playlist-read-private"
sp_oauth = SpotifyOAuth(client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
                    redirect_uri=os.getenv("REDIRECT_URI"),
                    scope=scope)
sp = spotipy.Spotify(oauth_manager=sp_oauth)

@bot.message_handler(commands=['logintospotify'])
def login_command_handler(message):
    chat_id = message.chat.id
    # get authorization from the user
    auth_url = sp_oauth.get_authorize_url()
    # create a hyperlink
    link = f'<a href="{auth_url}">authorize me</a>'
    # send the authorization URL to the user
    bot.send_message(chat_id, f"Please {link} to access your Spotify account.", parse_mode="HTML")

# Define the help command handler
@bot.message_handler(commands=['help'])
def help_command_handler(message):
    chat_id = message.chat.id
    bot_reply = "I can help you get notified when your friends add or remove a song from the playlists you share together.\n\nYou can make me do this for you by using these commands:\n\n/logintospotify - Set up your Spotify account\n\n/addplaylist - Add a playlist\n\n/removeplaylist - Remove a playlist"
    bot.send_message(chat_id, bot_reply)

# Handle any message that's not a recognized command
@bot.message_handler(func=lambda message: True, content_types=['text', 'number', 'document', 'photo'])
def message_handler(message):
    message_text = message.text
    chat_id = message.chat.id
    bot_help_reply = "I can help you get notified when your friends add or remove a song from the playlists you share together.\n\nYou can make me do this for you by using these commands:\n\n/logintospotify - Set up your Spotify account\n\n/addplaylist - Add a playlist\n\n/removeplaylist - Remove a playlist"
    bot_contribute_reply = "My creator didn't think about that command, <a href='https://github.com/rafacovez/notify'>is it a good idea</a> though?"
    if message_text.startswith('/'):
        # Handle unknown commands
        bot.send_message(chat_id, bot_contribute_reply, parse_mode="HTML")
    else:
        # Handle regular text
        bot.send_message(chat_id, bot_help_reply)

# Start the bot
bot.polling()