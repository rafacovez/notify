from typing import *

from spotipy import Spotify, SpotifyException
from spotipy.oauth2 import SpotifyOAuth

import random

class SpotifyHandler:
    def __init__(
        self, client_id: str, client_secret: str, redirect_uri: str, scope: str
    ) -> None:
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.redirect_uri: str = redirect_uri
        self.scope: str = scope
        self.sp_oauth: SpotifyOAuth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
        )
        self.sp: Spotify = Spotify(oauth_manager=self.sp_oauth)
        self.user_sp: Optional[Spotify] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def __do_nothing(self) -> None:
        pass

    def handle_exception(self, exception: SpotifyException) -> None:
        if exception.http_status == 403:
            print("403 Forbidden: Access to the resource is denied.")
        elif exception.http_status == 429:
            print("429 Too Many Requests: Rate limit exceeded.")
        else:
            print(f"An error occurred: {exception}")

    def get_user_sp(self, access_token: str) -> Spotify:
        try:
            self.user_sp: Spotify = Spotify(auth=access_token)
            return self.user_sp
        except SpotifyException as e:
            self.handle_exception(e)
            return None

    def refresh_access_token(self) -> str:
        try:
            self.access_token: str = self.sp_oauth.refresh_access_token(self.refresh_token)["access_token"]
            return self.access_token
        except SpotifyException as e:
            self.handle_exception(e)
            return None

    def get_user_playlists(self, offset: int = 0, limit: int = 50) -> List[Dict[str, any]]:
        user_playlists: List[Dict[str, any]] = []

        try:
            response: Dict[str, any] = self.user_sp.current_user_playlists(
                offset=offset, limit=limit
            )
            fetched_playlists = response["items"]
            user_playlists += fetched_playlists

            while len(fetched_playlists) > 50:
                offset += len(fetched_playlists)
                response: Dict[str, any] = self.user_sp.current_user_playlists(
                    offset=offset
                )
                fetched_playlists = response["items"]
                user_playlists += fetched_playlists
        except SpotifyException as e:
            self.handle_exception(e)
            return None

        return user_playlists
    
    def get_user_last_played(self) -> Dict[str, any]:
        try:
            currently_playing: Dict[str, any] = self.user_sp.current_user_playing_track()

            if currently_playing is None:
                last_played: Dict[str, any] = self.user_sp.current_user_recently_played(
                    limit=1
                )

                return last_played["items"][0]["track"]
            else:
                return currently_playing["item"]
        except SpotifyException as e:
            self.handle_exception(e)
            return None
        
    def get_user_top_tracks(self, time_range: str = "short_term", offset: int = 0, limit: int = 10) -> List[Dict[str, any]]:
        try:
            top_tracks: List[Dict[str, any]] = self.user_sp.current_user_top_tracks(
                offset=offset,
                limit=limit,
                time_range=time_range
            )["items"]

        except SpotifyException as e:
            self.handle_exception(e)
            return None

        return top_tracks
        
    def get_user_top_artists(self, time_range: str = "short_term", offset: int = 0, limit: int = 10) -> List[Dict[str, any]]:
        try:
            top_artists: List[Dict[str, any]] = self.user_sp.current_user_top_artists(
                offset=offset,
                limit=limit,
                time_range=time_range
            )["items"]

        except SpotifyException as e:
            self.handle_exception(e)
            return None

        return top_artists
        
    def get_user_top_genres(self, time_range: str = "short_term", offset: int = 0, limit: int = 10) -> Set[str]:
        top_genres: Set[str] = set()
    
        for artist in self.get_user_top_artists(time_range=time_range, offset=offset, limit=limit):
            for genre in artist["genres"]:
                if len(top_genres) >= limit:
                    return top_genres
                top_genres.add(genre)

        return top_genres
    
    def get_user_recommended_tracks(self, limit: int = 10):
        seed_tracks: List[str] = [track["id"] for track in self.get_user_top_tracks(limit=1)]
        seed_artists: List[str] = [artist["id"] for artist in self.get_user_top_artists(limit=1)]
        seed_genres: Set[str] = self.get_user_top_genres(limit=1)

        try:
            print(self.user_sp.recommendations(seed_tracks=seed_tracks, seed_artists=seed_artists, seed_genres=seed_genres, limit=limit))
        except SpotifyException as e:
            self.handle_exception(e)
            return None
        
        recommended_tracks = []

        return recommended_tracks
        
    def get_user_throwback(self) -> List[Dict[str, any]]:
        throwback_track: Dict[str, any] = self.get_user_top_tracks(time_range="long_term", offset=0, limit=50)[random.randint(0, 49)]

        return throwback_track