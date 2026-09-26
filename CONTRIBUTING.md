# Contributing to Notify

Thanks for your interest in contributing! This guide covers everything you need to get started.

## Prerequisites

- Python 3.13+
- A Telegram Bot token (create one via [@BotFather](https://t.me/BotFather))
- A Spotify Developer app (create one at [developer.spotify.com](https://developer.spotify.com/dashboard))
- A PostgreSQL instance (SQLite is no longer supported)

## Getting Started

1. **Fork & clone the repo**

   ```bash
   git clone https://github.com/<your-username>/notify.git
   cd notify
   ```

2. **Create a virtual environment and install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt -r requirements-dev.txt
   ```

3. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Fill in your Telegram bot token, Spotify credentials, and PostgreSQL connection details.

4. **Run the bot**

   ```bash
   python src/main.py
   ```

## Project Structure

```
src/
├── main.py                  # Entry point: starts Flask server, bot, and notifier threads
├── config.py                # Loads environment variables
├── notifier.py              # Background loop that checks playlists for changes
├── bot/
│   └── telegram_bot.py      # Telegram bot: command handling, callbacks, inline keyboards
├── database/
│   ├── database_handler.py  # PostgreSQL abstraction layer
│   └── schemas/
│       └── postgres_init.sql # Database schema
├── integrations/
│   ├── handlers/            # (Reserved for future handler separation)
│   └── spotify/
│       ├── spotify_service.py  # Spotify API wrapper
│       └── spotify_utils.py    # Utility functions (e.g. URL parsing)
├── templates/               # Flask HTML templates
└── static/                  # CSS, images, favicon
```

## Architecture

Notify runs three threads:

1. **Flask server** — handles the Spotify OAuth2 callback at `/callback`
2. **Notifier loop** — periodically checks tracked playlists for snapshot changes and notifies users
3. **Telegram bot** — polls for incoming messages and processes commands

The `DatabaseHandler` provides a thread-safe abstraction over PostgreSQL using a lock. All queries use `?` placeholders which are automatically converted to `%s` for psycopg2.

The `SpotifyHandler` wraps the Spotipy library. The bot thread sets `self.user_sp` for command execution; the notifier thread uses `create_user_sp()` to avoid clobbering that state (see issue #37).

## Coding Conventions

- **Type hints** — use modern syntax (`str | None`, `list[int]`, `dict[str, any]`)
- **Imports** — stdlib first, then third-party, then local (enforced by ruff)
- **Database queries** — use `?` placeholders; the `process()` method handles conversion to `%s`
- **Error handling** — wrap API calls in try/except, print meaningful messages, don't swallow exceptions silently
- **No SQLite** — the project is PostgreSQL-only

## Linting

The project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check src/
ruff format src/
```

## Docker

### Development (with hot-reload)

```bash
docker build --target dev -t notify-dev .
docker run -p 8080:8080 --env-file .env notify-dev
```

### Production

```bash
docker build --target prod -t notify .
docker run -d -p 8080:8080 --env-file .env notify
```

Or pull the prebuilt image from GHCR:

```bash
docker pull ghcr.io/rafacovez/notify:latest
docker run -d -p 8080:8080 --env-file .env ghcr.io/rafacovez/notify:latest
```

## Pull Request Checklist

- [ ] Code follows the existing style (run `ruff check` and `ruff format`)
- [ ] No new dependencies without justification
- [ ] Environment variables documented in `.env.example` if added
- [ ] Database schema changes reflected in `postgres_init.sql`
- [ ] Tested locally with a real Telegram bot and Spotify account

## Reporting Issues

Use [GitHub Issues](https://github.com/rafacovez/notify/issues) to report bugs or request features. Please include:

- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Relevant logs (redact tokens/credentials)
- Your environment (Docker vs local, Python version, PostgreSQL version)

## License

By contributing, you agree that your contributions are licensed under the MIT License.
