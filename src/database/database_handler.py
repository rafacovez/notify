import os
import threading
import psycopg2
from collections.abc import Callable
from typing import *

from src.config import (
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB_NAME,
)


class DatabaseHandler:
    def __init__(self) -> None:
        self.conn = None
        self.cursor_conn = None
        self.lock = threading.Lock()

        # Connect to Postgres immediately on initialization
        self.__connect_postgres()

    def __connect_postgres(self) -> None:
        try:
            self.conn = psycopg2.connect(
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname=POSTGRES_DB_NAME,
                connect_timeout=5,
            )
            self.conn.autocommit = True
            self.cursor_conn = self.conn.cursor()
            print(f"Successfully connected to PostgreSQL database: {POSTGRES_DB_NAME}")
        except Exception as e:
            print(f"CRITICAL DATABASE ERROR: Failed to connect to Postgres: {e}")
            raise e

    def process(self, func: Callable = None) -> Any:
        if func is None:
            return

        with self.lock:
            # Native PostgreSQL uses %s placeholders out-of-the-box
            def execute_wrapper(query: str, params: tuple = ()):
                return self.cursor_conn.execute(query, params)

            self.execute = execute_wrapper

            try:
                return func()
            except Exception as e:
                print(f"DATABASE RUNTIME ERROR: {e}")
                raise e
            finally:
                del self.execute

    def create_tables(self) -> None:
        def logic() -> None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            schemas_path = os.path.join(base_dir, "schemas", "postgres_init.sql")

            with open(schemas_path, "r") as f:
                sql_script = f.read()

            # Execute via the raw cursor connection to handle multi-statement scripts
            self.cursor_conn.execute(sql_script)
            print("Database schemas applied successfully via postgres_init.sql")

        try:
            self.process(logic)
        except Exception as e:
            print(f"CRITICAL: Failed to apply database schemas: {e}")
            raise e

    def add_user(
        self,
        telegram_user_id: int,
        spotify_user_display: str,
        spotify_user_id: str,
        refresh_token: str,
        access_token: str,
    ) -> None:
        def logic() -> None:
            self.execute(
                "INSERT INTO users (telegram_user_id, spotify_user_display, spotify_user_id, refresh_token, access_token) VALUES (%s, %s, %s, %s, %s)",
                (
                    telegram_user_id,
                    spotify_user_display,
                    spotify_user_id,
                    refresh_token,
                    access_token,
                ),
            )

        self.process(logic)

    def user_exists(self, user: int) -> bool:
        def logic() -> bool:
            self.execute(
                "SELECT telegram_user_id FROM users WHERE telegram_user_id = %s",
                (user,),
            )
            return self.cursor_conn.fetchone() is not None

        return self.process(logic)

    def delete_user(self, user: int) -> None:
        def logic() -> None:
            self.execute(
                "DELETE FROM users WHERE telegram_user_id = %s",
                (user,),
            )

        self.process(logic)

    def get_access_token(self, user: int) -> str:
        def logic() -> str:
            self.execute(
                "SELECT access_token from users WHERE telegram_user_id = %s", (user,)
            )
            return self.cursor_conn.fetchone()[0]

        return self.process(logic)

    def get_refresh_token(self, user: int) -> str:
        def logic() -> str:
            self.execute(
                "SELECT refresh_token from users WHERE telegram_user_id = %s", (user,)
            )
            return self.cursor_conn.fetchone()[0]

        return self.process(logic)

    def store_access_token(self, access_token: str, user: int) -> None:
        def logic() -> None:
            self.execute(
                "UPDATE users SET access_token = %s WHERE telegram_user_id = %s",
                (access_token, user),
            )

        self.process(logic)

    def fetch_telegram_users(self) -> List[int]:
        def logic() -> List[int]:
            self.execute("SELECT telegram_user_id FROM users")
            return [row[0] for row in self.cursor_conn.fetchall()]

        return self.process(logic)

    def add_notify(
        self, telegram_user_id: int, playlist_id: str, snapshot_id: str
    ) -> None:
        def logic() -> None:
            self.execute(
                "INSERT INTO notify (telegram_user_id, playlist_id, snapshot_id) VALUES (%s, %s, %s)",
                (telegram_user_id, playlist_id, snapshot_id),
            )

        self.process(logic)

    def delete_notify(self, telegram_user_id: int, playlist_id: str) -> None:
        def logic() -> None:
            self.execute(
                "DELETE FROM notify WHERE telegram_user_id = %s AND playlist_id = %s",
                (
                    telegram_user_id,
                    playlist_id,
                ),
            )

        self.process(logic)

    def delete_notify_user(self, telegram_user_id: int) -> None:
        def logic() -> None:
            self.execute(
                "DELETE FROM notify WHERE telegram_user_id = %s",
                (telegram_user_id,),
            )

        self.process(logic)

    def playlist_exists(self, telegram_user_id: int, playlist_id: str) -> bool:
        def logic() -> bool:
            self.execute(
                "SELECT id FROM notify WHERE telegram_user_id = %s AND playlist_id = %s",
                (
                    telegram_user_id,
                    playlist_id,
                ),
            )
            return self.cursor_conn.fetchone() is not None

        return self.process(logic)

    def get_notify_playlists_by_user(self, telegram_user_id: int) -> List[str]:
        def logic() -> List[str]:
            self.execute(
                "SELECT playlist_id FROM notify WHERE telegram_user_id = %s",
                (telegram_user_id,),
            )
            return [row[0] for row in self.cursor_conn.fetchall()]

        return self.process(logic)

    def update_notify_snapshot(
        self, telegram_user_id: int, playlist_id: str, snapshot_id: str
    ) -> None:
        def logic() -> None:
            self.execute(
                "UPDATE notify SET snapshot_id = %s WHERE telegram_user_id = %s AND playlist_id = %s",
                (snapshot_id, telegram_user_id, playlist_id),
            )

        self.process(logic)

    def get_notify_snapshot(self, telegram_user_id: int, playlist_id: str) -> str:
        def logic() -> str:
            self.execute(
                "SELECT snapshot_id FROM notify WHERE telegram_user_id = %s AND playlist_id = %s",
                (
                    telegram_user_id,
                    playlist_id,
                ),
            )
            return self.cursor_conn.fetchone()[0]

        return self.process(logic)
