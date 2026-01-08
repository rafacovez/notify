from telebot import TeleBot  # telegram bots interaction library
from telebot.types import *

from database.database_handler import DatabaseHandler
from integrations.spotify.spotify_service import SpotifyHandler


class MessageHandler:
    def __init__(self, bot_token: str) -> None:
        self.bot: TeleBot = TeleBot(bot_token)
        self.message: Optional[Message] = None
        self.command_list: List[BotCommand] = self.bot.command_list
        self.database: DatabaseHandler = self.bot.database
        self.spotify: SpotifyHandler = self.bot.spotify
