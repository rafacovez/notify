from telebot import TeleBot  # telegram bots interaction library
from telebot.types import *

from api.services.database_service import DatabaseHandler
from api.services.spotify_service import SpotifyHandler


class MessageHandler:
    def __init__(self, bot_token: str) -> None:
        self.bot: TeleBot = TeleBot(bot_token)
        self.message: Optional[Message] = None
        self.command_list: List[BotCommand] = self.bot.command_list
        self.database: DatabaseHandler = self.bot.database
        self.spotify: SpotifyHandler = self.bot.spotify
