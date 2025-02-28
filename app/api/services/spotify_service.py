from typing import *

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth


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

    def get_user_sp(self, access_token: str) -> Spotify:
        self.user_sp: Spotify = Spotify(auth=access_token)
        return self.user_sp

    def refresh_access_token(self) -> str:
        return self.sp_oauth.refresh_access_token(self.refresh_token)["access_token"]
