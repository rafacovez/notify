from typing import *

from telebot import TeleBot  # telegram bots interaction library
from telebot.types import *


class CommandHandler:
    def __init__(self, bot_token: str) -> None:
        self.bot: TeleBot = TeleBot(bot_token)
        self.user_id = self.bot.user_id
        self.chat_id = self.bot.chat_id
        self.command_list = self.bot.command_list
        self.database = self.bot.database
        self.spotify = self.bot.spotify
