# Notify

A modular, containerized Telegram bot for Spotify playlist tracking and personal listening statistics.

![Notify's website homepage](/src/static/homepage.png)

## Project Overview

**Notify** is an open-source Telegram bot designed to monitor Spotify playlists and provide personalized listening insights. It detects playlist changes (track additions and removals) and generates listening statistics such as Top Tracks across short, medium, and long-term periods.

The project emphasizes clean separation of concerns, service-oriented design, and full containerization to support both local development and self-hosted deployments.

## Features

- 🎶 Track Spotify playlist additions and removals
- 📊 View personal Spotify listening statistics
- 🤖 Telegram-based command interface
- 🐳 Fully Dockerized with multi-stage builds
- 🔁 Hot-reloading development environment

## Architecture

Notify follows a **service-oriented and modular architecture**:

- Bot logic is isolated from API and persistence layers
- Spotify integration and database access are abstracted behind service interfaces
- Configuration is centralized and environment-driven

## Technology Stack

- **Language:** [Python](https://www.python.org/doc/) 3.13
- **Telegram Bot:** `pyTelegramBotAPI` [(Telebot)](https://github.com/eternnoir/pyTelegramBotAPI)
- **Spotify API:** [Spotipy](https://github.com/spotipy-dev/spotipy)
- **Web Server:** [Flask](https://github.com/pallets/flask) (OAuth2 callback handling)
- **Database:** [PostgreSQL](https://www.postgresql.org/) (with SQLite fallback)
- **Containerization:** [Docker](https://docs.docker.com/)

## Environment Configuration

All runtime configuration is managed through environment variables loaded from the `.env` file at the root directory.

Use the `.env.example` file as a template.

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `TELEGRAM_BOT_API_TOKEN` | Telegram Bot API token | — |
| `TELEGRAM_ADMIN_USER_IDS` | Comma-separated Telegram usernames | — |
| `SPOTIFY_CLIENT_ID` | Spotify app client ID | — |
| `SPOTIFY_CLIENT_SECRET` | Spotify app client secret | — |
| `SPOTIFY_SCOPE` | OAuth scopes string | *(see .env.example)* |
| `HOST_ADDRESS` | External address for Spotify OAuth redirect | `http://127.0.0.1` |
| `HOST_PORT` | External port for redirect URI | `8080` |
| `CONTAINER_HOST` | Flask bind address inside container | `0.0.0.0` |
| `CONTAINER_PORT` | Flask port inside container | `8080` |
| `POSTGRES_USER` | PostgreSQL user (leave blank for SQLite) | — |
| `POSTGRES_PASSWORD` | PostgreSQL password | — |
| `POSTGRES_HOST` | PostgreSQL host | — |
| `POSTGRES_PORT` | PostgreSQL port | — |
| `POSTGRES_DB_NAME` | PostgreSQL database name | `notify` |
| `MAX_NOTIFY_PLAYLISTS_PER_USER` | Max tracked playlists per user | `3` |
| `NOTIFY_CHECK_INTERVAL_SECONDS` | Seconds between playlist checks | `1800` |
| `COMMAND_COOLDOWN_SECONDS` | Per-user command cooldown | `5` |

## Docker & Containerization

Notify is fully containerized using Docker, with an emphasis on reproducibility, minimal runtime images, and a clean separation between development and production environments.

### Multi-Stage Dockerfile

The project uses an Alpine-based **multi-stage Docker build**:

- **base** — Shared Python 3.13 runtime and common dependencies.
- **dev** — Extends base with development tooling and `watchdog` for hot-reloading.
- **prod** — Lean runtime image with build-time dependencies removed.

### CI/CD

GitHub Actions automatically builds and pushes multi-platform images (amd64 + arm64) to GHCR on version tags:

```
ghcr.io/<owner>/notify:latest
ghcr.io/<owner>/notify:<version>
```

### Self-Hosting (Unraid)

Pull the image from GHCR and run it on your Unraid server:

```bash
docker pull ghcr.io/<owner>/notify:latest

docker run -d \
  --name notify \
  --env-file /path/to/.env \
  -p 8080:8080 \
  ghcr.io/<owner>/notify:latest
```

If using PostgreSQL, make sure the `POSTGRES_HOST` env var points to your Unraid Postgres instance.

## Running Locally (Development)

```bash
# Create a virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Run with hot-reload (dev stage)
docker build --target dev -t notify-dev .
docker run -p 8080:8080 --env-file .env notify-dev

# Or run directly with Python
python src/main.py
```

## License

This project is licensed under the MIT License.  
See the `LICENSE` file for details.
