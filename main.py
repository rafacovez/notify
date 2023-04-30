import telebot
from dotenv import load_dotenv
import os

load_dotenv()

# Enter your Telegram Bot API token here
TOKEN = os.getenv("BOT_API_TOKEN")

# Initialize the bot
bot = telebot.TeleBot(TOKEN)

# Handle the /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hi!")

# Start the bot
bot.polling()