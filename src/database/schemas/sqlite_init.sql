CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER UNIQUE NOT NULL,
    spotify_user_display TEXT,
    spotify_user_id TEXT UNIQUE,
    refresh_token TEXT,
    access_token TEXT,
    tier TEXT DEFAULT 'Free',
    request_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notify (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    playlist_id TEXT NOT NULL,
    snapshot_id TEXT,
    playlist_name TEXT,
    playlist_url TEXT,
    last_checked_at DATETIME,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(telegram_user_id) 
        REFERENCES users(telegram_user_id) 
        ON DELETE CASCADE,
        
    UNIQUE(telegram_user_id, playlist_id)     
);

CREATE INDEX IF NOT EXISTS idx_notify_user ON notify(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_users_spotify_id ON users(spotify_user_id);