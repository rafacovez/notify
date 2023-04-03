from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

def start(update:Update, context:CallbackContext):
    update.message.reply_text("Hey buddy!")

if __name__ == "__main__":
    updater = Updater("6060982771:AAF_WeWw9CYT737td2YZupDF4ivZhKkYp6E")
    
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))

    updater.start_polling()
    updater.idle()