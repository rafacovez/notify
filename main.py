import telebot

# Enter your Telegram Bot API token here
TOKEN = '6060982771:AAF_WeWw9CYT737td2YZupDF4ivZhKkYp6E'

# Initialize the bot
bot = telebot.TeleBot(TOKEN)

# Handle the /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hi!")

# Start the bot
bot.polling()