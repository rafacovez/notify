# Notify

A modular, containerized Telegram bot for Spotify playlist tracking and personal listening statistics.

![Notify's website homepage](/src/static/homepage.png)

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Environment Configuration](#environment-configuration)
- [Persistence & Infrastructure](#persistence--infrastructure)
- [Docker & Containerization](#docker--containerization)
  - [Multi-Stage Dockerfile](#multi-stage-dockerfile)
  - [Docker Compose](#docker-compose)
- [Running the Project](#running-the-project)
  - [Production Mode](#production-mode)
  - [Development Mode](#development-mode)
- [Roadmap](#roadmap)
- [License](#license)

## Project Overview

**Notify** is an open-source Telegram bot designed to monitor Spotify playlists and provide personalized listening insights. It detects playlist changes (track additions and removals) and generates listening statistics such as Top Tracks across short, medium, and long-term periods.

The project emphasizes clean separation of concerns, service-oriented design, and full containerization to support both local development and streamlined production deployments.

## Features

- 🎶 Track Spotify playlist additions and removals
- 📊 View personal Spotify listening statistics
- 🤖 Telegram-based command interface
- 🐳 Fully Dockerized with multi-stage builds
- 🔁 Hot-reloading development environment

## Architecture

Notify follows a **service-oriented and modular architecture**:

- Bot logic is isolated from API and persistence layers.
- Spotify integration and database access are abstracted behind service interfaces.
- Configuration is centralized, stateless, and entirely environment-driven.

This structure allows the project to scale in complexity without becoming tightly coupled or difficult to maintain.

## Technology Stack

- **Language:** [Python](https://www.python.org/doc/) 3.13
- **Telegram Bot:** `pyTelegramBotAPI` [(Telebot)](https://github.com/eternnoir/pyTelegramBotAPI)
- **Spotify API:** [Spotipy](https://github.com/spotipy-dev/spotipy)
- **Web Server:** [Flask](https://github.com/pallets/flask) (OAuth2 callback handling)
- **Database:** [PostgreSQL 16](https://www.postgresql.org/docs/16/index.html) (Hosted externally via Unraid)
- **Containerization:** [Docker](https://docs.docker.com/), [Docker Compose](https://docs.docker.com/compose/)

## Environment Configuration

All runtime configuration is managed through environment variables loaded from the dedicated `.env` file at the root directory.

Ensure your `.env` contains your PostgreSQL credentials alongside your API tokens:

```env
# Database Configuration
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=your_unraid_ip
POSTGRES_PORT=5432

# API Secrets
TELEGRAM_BOT_TOKEN=your_token
SPOTIFY_CLIENT_ID=your_id
SPOTIFY_CLIENT_SECRET=your_secret
```

## Persistence & Infrastructure

Persistence is managed externally via a centralized _PostgreSQL 16_ instance running on an Unraid host.
Because state is maintained over a secure network connection rather than local file system blocks, the application container remains entirely stateless. This simplifies development environments, removes local volume mount dependencies, and ensures high availability across container restarts and rebuilds.

## Docker & Containerization

Notify is fully containerized using Docker, with an emphasis on reproducibility, minimal runtime images, and a clean separation between development and production environments.

### Multi-Stage Dockerfile

The project uses an Alpine-based multi-stage Docker build:

- base Provides a shared Python 3.13 runtime and common system dependencies.
- dev Extends the base image with development tooling and `watchdog`, enabling hot-reloading when source files change.
- prod Produces a lean runtime image with all build-time dependencies (such as `gcc` and `musl-dev`) removed to reduce image size and attack surface.

This structure ensures fast iteration during development while keeping production images small and secure.

### Docker Compose

Docker Compose is used for orchestration and runtime configuration:

- Environment variables are injected from `.env`
- Ports are mapped dynamically using variable substitution
- Multiple compose files can be layered to switch behavior by environment

Example port mapping:

```yaml
ports:
  - "${HOST_PORT}:${CONTAINER_PORT}"
```

## Running the Project

The application can be executed in two distinct modes, depending on whether stability or rapid iteration is the priority.

### Production Mode

Build and run the optimized production container in detached mode:

```bash
docker compose up --build -d
```

### Development Mode

Run the application with hot-reloading enabled by combining the base and development compose files:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  up --build
```

This activates the dev Docker target and watches the source code for changes in real time, making it ideal for quick development.

## Roadmap

The project's evolution is tracked via strategic Milestones you can find in this repository's Issues section.

## License

This project is licensed under the MIT License.

See the `LICENSE` file for details.
