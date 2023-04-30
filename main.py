import telebot
from dotenv import load_dotenv
import os

load_dotenv()

# Enter your Telegram Bot API token here
TOKEN = os.getenv("BOT_API_TOKEN")

# Initialize the bot
bot = telebot.TeleBot(TOKEN)

# Define the help command handler
@bot.message_handler(commands=['help'])
def help_command_handler(message):
    chat_id = message.chat.id
    bot_reply = "I can help you get notified when your friends add or remove a song from the playlists you share together.\n\t\n\tYou can make me do this for you by using these commands:\n\t\n\tSet up Spotify:\n\t/logintospotify\n\t\n\tAdd a playlist:\n\t/addplaylist\n\t\n\tRemove a playlist:\n\t/removeplaylist"
    bot.send_message(chat_id, bot_reply)

# Handle any message that's not a recognized command
@bot.message_handler(func=lambda message: True, content_types=['text', 'number', 'document', 'photo'])
def message_handler(message):
    message_text = message.text
    chat_id = message.chat.id
    bot_help_reply = "I can help you get notified when your friends add or remove a song from the playlists you share together.\n\t\n\tYou can make me do this for you by using these commands:\n\t\n\tSet up Spotify:\n\t/logintospotify\n\t\n\tAdd a playlist:\n\t/addplaylist\n\t\n\tRemove a playlist:\n\t/removeplaylist"
    bot_contribute_reply = "My creator didn't think about that command. <a href='https://github.com/rafacovez/notify'>is it a good idea though?</a>"
    if message_text.startswith('/'):
        # Handle unknown commands
        bot.send_message(chat_id, bot_contribute_reply, parse_mode="HTML")
    else:
        # Handle regular text
        bot.send_message(chat_id, bot_help_reply)

# Start the bot
bot.polling()