CREATE TABLE IF NOT EXISTS subscription_tiers (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    max_requests INTEGER DEFAULT 100,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO subscription_tiers (name, max_requests)
VALUES ('Free', 100), ('Premium', 1000), ('Founder', 5000)
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    spotify_user_display TEXT,
    spotify_user_id TEXT UNIQUE,
    refresh_token TEXT,
    access_token TEXT,
    tier_id INTEGER DEFAULT 1, -- Defaults to the 'Free' tier (ID 1)
    request_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_subscription_tier
        FOREIGN KEY(tier_id) 
        REFERENCES subscription_tiers(id)
        ON DELETE SET DEFAULT
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