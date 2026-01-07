import os

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), "../.env")

load_dotenv(dotenv_path)

TELEGRAM_BOT_API_TOKEN = os.getenv("TELEGRAM_BOT_API_TOKEN")
TELEGRAM_ADMIN_USER_IDS = [
    i.strip().lstrip("@").lower()
    for i in os.getenv("TELEGRAM_ADMIN_USER_IDS", "").split(",")
    if i.strip()
]

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_SCOPE = (
    os.getenv(
        "SPOTIFY_SCOPE",
        "user-read-private user-read-currently-playing user-read-recently-played user-top-read playlist-read-private playlist-read-collaborative user-library-read",
    )
    .strip('"')
    .strip("'")
)

HOST_ADDRESS = os.getenv("HOST_ADDRESS", "http://127.0.0.1")
HOST_PORT = int(os.getenv("HOST_PORT", 8080))

REDIRECT_URI = f"{HOST_ADDRESS}:{HOST_PORT}/callback"

CONTAINER_HOST = os.getenv("CONTAINER_HOST", "0.0.0.0")
CONTAINER_PORT = int(os.getenv("CONTAINER_PORT", 8080))

DB_NAME = os.getenv("DB_NAME", "notify")

MAX_NOTIFY_PLAYLISTS_PER_USER = int(os.getenv("MAX_NOTIFY_PLAYLISTS_PER_USER", 3))
REFRESH_INTERVAL_SECONDS = int(os.getenv("REFRESH_INTERVAL_SECONDS", 1800))
COMMAND_COOLDOWN_SECONDS = int(os.getenv("COMMAND_COOLDOWN_SECONDS", 5))
