CREATE TYPE subscription_tier AS ENUM ('Free', 'Premium', 'Founder');

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    spotify_user_display TEXT,
    spotify_user_id TEXT UNIQUE,
    refresh_token TEXT,
    access_token TEXT,
    tier subscription_tier DEFAULT 'Free',
    request_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notify (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    playlist_id TEXT NOT NULL,
    snapshot_id TEXT,
    playlist_name TEXT,
    playlist_url TEXT,
    last_checked_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_user 
        FOREIGN KEY(telegram_user_id) 
        REFERENCES users(telegram_user_id) 
        ON DELETE CASCADE,
        
    UNIQUE(telegram_user_id, playlist_id)     
);

CREATE INDEX IF NOT EXISTS idx_notify_user ON notify(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_users_spotify_id ON users(spotify_user_id);