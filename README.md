# Notify

Notify is a **Telegram bot** that allows you to manage your playlist notifications and receive updates whenever there are changes to your favorite playlists on Spotify. The name **Notify** comes from its core purpose: to **notify** users about updates to their chosen Spotify playlists. While the playlist update notification feature is still in development to deliver the best possible result, the bot already offers a range of features to help you interact with your Spotify data.

---

## Disclaimer: Notify App is in Development Mode

Please note that the Notify app is currently in development mode, and as a result, you won't be able to use it directly by visiting [https://t.me/playlistNotificationBot](https://t.me/playlistNotificationBot) without reaching out to me first.

### Usage Instructions:

1. If you are interested in using the Notify app, contact me to be manually added to the whitelist. You can reach out to me through **adanescollante@gmail.com** to request access.
2. Once you have contacted me and your request has been approved, you will receive further instructions on how to access and use the Notify app.

---

## Getting Started

To use the bot, you can either start a conversation with the [Notify Bot](https://t.me/playlistNotificationBot) link or by searching for `playlistNotificationBot` in your Telegram app search bar.

---

## Running Notify with Docker

Notify is now **Dockerized**, making it easy to run and deploy. Follow these steps to set it up:

### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/notify.git
cd notify
```

### 2. Set Up Environment Variables

1. Copy the `.env.example` file to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```
2. Open `.env.local` and fill in the required values:

   ```plaintext
   BOT_API_TOKEN=your-telegram-bot-token
   SPOTIFY_CLIENT_ID=your-spotify-client-id
   SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
   SERVER_HOST=0.0.0.0
   SERVER_PORT=80
   REDIRECT_URI=http://your-domain.com/callback
   NOTIFY_DB=/app/data/notify.db
   ```

   - **`SERVER_PORT`**: By default, this is set to `80` inside the Docker container. If you map it to a different port on your host (e.g., `8080`), update the `REDIRECT_URI` accordingly.
   - **`REDIRECT_URI`**: This must match the callback URL set in your Spotify Developer Dashboard.

### 3. Build the Docker Image

```bash
docker build -t notify-bot .
```

### 4. Run the Docker Container

Map the container's port `80` to a port on your host (e.g., `8080`):

```bash
docker run -p 8080:80 --env-file .env.local notify-bot
```

- **`-p 8080:80`**: Maps port `80` inside the container to port `8080` on your host.
- **`--env-file .env.local`**: Loads environment variables from `.env.local`.

### 5. Access the Bot

- If running locally, access the bot at:
  ```plaintext
  http://localhost:8080
  ```
- If running on a server, replace `localhost` with your server's IP or domain.

---

## Port Configuration

- **Inside the Container**: The app runs on port `80` by default (set in `.env.local`).
- **On the Host**: Map the container's port `80` to any available port on your host (e.g., `8080`).

#### Example:

- If you map port `80` in the container to port `8080` on the host:

  ```bash
  docker run -p 8080:80 --env-file .env.local notify-bot
  ```

  - Access the bot at `http://localhost:8080`.

- If you map port `80` in the container to port `80` on the host:
  ```bash
  docker run -p 80:80 --env-file .env.local notify-bot
  ```
  - Access the bot at `http://localhost`.

---

## Dependencies

This project is built using the following libraries and tools:

- [Telebot](https://github.com/eternnoir/pyTelegramBotAPI) - A Python wrapper for the Telegram Bot API.
- [Spotipy](https://spotipy.readthedocs.io/) - A lightweight Python library for the Spotify Web API.
- [sqlite3](https://docs.python.org/3/library/sqlite3.html) - A built-in Python module for working with SQLite databases.
- [Docker](https://www.docker.com) - A platform for containerizing applications.

---

## Contributing

Contributions to this project are welcome! If you're interested in contributing, please follow these guidelines:

1. Fork the repository and create your branch.
2. Make your changes and ensure they adhere to the code style and best practices.
3. Write clear and concise commit messages.
4. Test your changes thoroughly.
5. Submit a pull request with a detailed description of the changes you made.

---

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file. Please refer to the license file for more information.

---

## Resources

Here are some resources to help you get started:

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [Spotipy Documentation](https://spotipy.readthedocs.io/en/latest/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Docker Documentation](https://docs.docker.com/)

If you have any questions or need assistance, feel free to reach out.

---

This updated documentation reflects the Docker setup, port configuration, and the removal of DigitalOcean. It also clarifies the bot's purpose and provides clear instructions for running the bot locally or on a server. Let me know if you need further adjustments!
