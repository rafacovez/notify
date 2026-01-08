import re

def extract_spotify_id(url: str) -> str:
    pattern = r"(?:spotify:|https?://open\.spotify\.com/(?:track|album|artist|playlist)/)([a-zA-Z0-9]+)"
    match = re.search(pattern, url)
    return match.group(1) if match else ""