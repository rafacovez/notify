import os

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env.local")

load_dotenv(dotenv_path)

BOT_API_TOKEN = os.getenv("BOT_API_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
REDIRECT_HOST = os.getenv("REDIRECT_HOST")
REDIRECT_PORT = os.getenv("REDIRECT_PORT")
NOTIFY_DB = os.getenv("NOTIFY_DB")
