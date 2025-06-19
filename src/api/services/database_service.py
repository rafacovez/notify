import os
import sqlite3
import threading
from collections.abc import Callable
from typing import *


class DatabaseHandler:
    def __init__(self, database: str) -> None:
        self.database: str = f"data/{database}"
        self.backup: str = "data/backup.db"
        self.conn: sqlite3.Connection = None
        self.backup_conn: sqlite3.Connection = None
        self.cursor: sqlite3.Cursor = None
        self.databases: bool = False
        self.lock = threading.Lock()

    def __do_nothing(self) -> None:
        pass

    def __connect(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.database), exist_ok=True)

            self.conn = sqlite3.connect(self.database)
            self.cursor = self.conn.cursor()

        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")

    def __disconnect(self) -> None:
        try:
            self.conn.commit()
            self.backup_conn = sqlite3.connect(self.backup)
            self.conn.backup(self.backup_conn)
            self.backup_conn.close()
        except sqlite3.Error as e:
            print(f"Error commiting changes: {e}")
        self.cursor.close()
        self.conn.close()

    def process(self, func: Callable = None) -> Any:
        if func is None:
            self.__do_nothing()
        else:
            with self.lock:
                self.__connect()
                result = func()
                self.__disconnect()
            return result
        
    def create_tables(self) -> None:
        def logic() -> None:
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    telegram_user_id INTEGER UNIQUE,
                    spotify_user_display TEXT,
                    spotify_user_id TEXT,
                    refresh_token TEXT,
                    access_token TEXT
                )
                """
            )
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notify (
                    id INTEGER PRIMARY KEY,
                    telegram_user_id INTEGER,
                    playlist_id TEXT,
                    snapshot_id TEXT,
                    FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id) ON DELETE CASCADE ON UPDATE CASCADE
                )
                """
            )
        self.process(logic)

    def user_exists(self, user: int) -> bool:
        def logic() -> bool:
            self.cursor.execute(
                "SELECT telegram_user_id FROM users WHERE telegram_user_id = ?",
                (user,),
            )
            user_id: int = self.cursor.fetchone()

            if user_id is None:
                return False
            else:
                return True

        return self.process(logic)

    def delete_user(self, user: int) -> None:
        def logic() -> None:
            self.cursor.execute(
                "DELETE FROM users WHERE telegram_user_id = ?",
                (user,),
            )

        self.process(logic)

    def get_access_token(self, user: int) -> str:
        def logic() -> str:
            self.cursor.execute(
                "SELECT access_token from users WHERE telegram_user_id = ?", (user,)
            )

            return self.cursor.fetchone()[0]

        return self.process(logic)

    def get_refresh_token(self, user: int) -> str:
        def logic() -> str:
            self.cursor.execute(
                "SELECT refresh_token from users WHERE telegram_user_id = ?", (user,)
            )

            return self.cursor.fetchone()[0]

        return self.process(logic)

    def store_access_token(self, access_token: str, user: int) -> None:
        def logic() -> None:
            self.cursor.execute(
                "UPDATE users SET access_token = ? WHERE telegram_user_id = ?",
                (access_token, user),
            )

        self.process(logic)

    def fetch_telegram_users(self) -> List[int]:
        def logic() -> List[int]:
            self.cursor.execute("SELECT telegram_user_id FROM users")
            return [row[0] for row in self.cursor.fetchall()]

        return self.process(logic)

    def add_notify(self, telegram_user_id: int, playlist_id: str, snapshot_id: str) -> None:
        def logic() -> None:
            self.cursor.execute(
                "INSERT INTO notify (telegram_user_id, playlist_id, snapshot_id) VALUES (?, ?, ?)",
                (telegram_user_id, playlist_id, snapshot_id),
            )

        self.process(logic)

    def delete_notify(self, telegram_user_id: int, playlist_id: str) -> None:
        def logic() -> None:
            self.cursor.execute(
                "DELETE FROM notify WHERE telegram_user_id = ? AND playlist_id = ?",
                (telegram_user_id, playlist_id,),
            )

        self.process(logic)

    def delete_notify_user(self, telegram_user_id: int) -> None:
        def logic() -> None:
            self.cursor.execute(
                "DELETE FROM notify WHERE telegram_user_id = ?",
                (telegram_user_id,),
            )

        self.process(logic)

    def playlist_exists(self, telegram_user_id: int, playlist_id: str) -> bool:
        def logic() -> bool:
            self.cursor.execute(
                "SELECT id FROM notify WHERE telegram_user_id = ? AND playlist_id = ?",
                (telegram_user_id, playlist_id,),
            )
            notify_id: int = self.cursor.fetchone()

            if notify_id is None:
                return False
            else:
                return True

        return self.process(logic)

    def get_notify_playlists_by_user(self, telegram_user_id: int) -> List[str]:
        def logic() -> List[str]:
            self.cursor.execute(
                "SELECT playlist_id FROM notify WHERE telegram_user_id = ?", (telegram_user_id,)
            )
            return [row[0] for row in self.cursor.fetchall()]

        return self.process(logic)

    def update_notify_snapshot(self, telegram_user_id: int, playlist_id: str, snapshot_id: str) -> None:
        def logic() -> None:
            self.cursor.execute(
                "UPDATE notify SET snapshot_id = ? WHERE telegram_user_id = ? AND playlist_id = ?", (snapshot_id, telegram_user_id, playlist_id)
            )

        self.process(logic)

    def get_notify_snapshot(self, telegram_user_id: int, playlist_id: str) -> str:
        def logic() -> str:
            self.cursor.execute(
                "SELECT snapshot_id FROM notify WHERE telegram_user_id = ? AND playlist_id = ?", (telegram_user_id, playlist_id,)
            )
            return self.cursor.fetchone()[0]

        return self.process(logic)