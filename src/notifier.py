from typing import List, Dict
import time
from bot.telegram_bot import NotifyTelegramBot
from database.database_handler import DatabaseHandler
from integrations.spotify.spotify_service import SpotifyHandler


def start_notifier_loop(
    telegram_bot: NotifyTelegramBot,
    database: DatabaseHandler,
    spotify: SpotifyHandler,
    notify_check_interval_seconds: int,
) -> None:
    while True:
        try:
            start_time = time.time()

            users: List[int] = database.fetch_telegram_users()

            for user in users:
                _check_user(user, telegram_bot, database, spotify)

            elapsed_time = time.time() - start_time

            print(
                f"Notifier loop completed at {time.strftime("%Y-%m-%d %H:%M:%S")} in {elapsed_time:.2f} seconds. Next check in {notify_check_interval_seconds} seconds."
            )

        except Exception as e:
            print(f"Worker Loop Error: {e}")

        time.sleep(notify_check_interval_seconds)


def _check_user(
    user,
    telegram_bot: NotifyTelegramBot,
    database: DatabaseHandler,
    spotify: SpotifyHandler,
) -> None:
    notify_playlists_ids: List[str] = database.get_notify_playlists_by_user(user)

    if not notify_playlists_ids:
        return

    spotify.refresh_token = database.get_refresh_token(user)
    spotify.access_token = spotify.refresh_access_token()
    database.store_access_token(spotify.access_token, user)

    user_sp = spotify.get_user_sp(spotify.access_token)

    for playlist_id in notify_playlists_ids:
        playlist: Dict[str, any] = spotify.get_playlist(
            user_sp, playlist_id, fields="snapshot_id,name,external_urls"
        )

        if playlist is not None:
            current_snapshot_id: str = playlist["snapshot_id"]
            stored_snapshot_id: str = database.get_notify_snapshot(user, playlist_id)

            if current_snapshot_id != stored_snapshot_id:
                database.update_notify_snapshot(
                    telegram_user_id=user,
                    playlist_id=playlist_id,
                    snapshot_id=current_snapshot_id,
                )
                telegram_bot.bot.send_message(
                    user,
                    f"The playlist {playlist['name']} has been updated! Check it out: {playlist['external_urls']['spotify']}",
                )
        else:
            telegram_bot.remove_notify(playlist_id, user)
            telegram_bot.bot.send_message(
                user,
                f"Some of the playlists you were tracking no longer exists. They will be removed from your tracking list.",
            )
