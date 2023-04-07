import telegram
from telegram.ext import Updater, CommandHandler

# Replace YOUR_BOT_TOKEN with your actual bot token
bot_token = "6060982771:AAF_WeWw9CYT737td2YZupDF4ivZhKkYp6E"
bot_username = "@playlistNotificationBot"

# Define the /start command handler
def start(update, context):
    # Send a message to the user who typed /start
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hi!")

# Set up the Telegram bot
updater = Updater(token=bot_token, use_context=True)
dispatcher = updater.dispatcher

# Register the /start command handler
dispatcher.add_handler(CommandHandler("start", start))

# Start the bot
updater.start_polling()
