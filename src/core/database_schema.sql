-- ============================================================================
-- Steam Library Manager - Complete Database Schema
-- Version: 2.0
-- Purpose: Fast metadata cache + ALL advanced features
-- ============================================================================
--
-- Features:
-- ✅ Game metadata (fast startup)
-- ✅ Custom artwork sync (multi-device)
-- ✅ HLTB integration
-- ✅ Personal notes & journal
-- ✅ Smart collections
-- ✅ Device performance tracking
-- ✅ Mod tracking
-- ✅ Achievement progress
-- ✅ Play sessions
-- ✅ Controller configs
-- ✅ Screenshots gallery
-- ✅ Wishlist & price tracking
-- ✅ Friend recommendations
--
-- Author: Sarah (Senior Python/PyQt6 Developer)
-- Created: 2026-02-13
-- ============================================================================

-- ============================================================================
-- CORE GAME METADATA
-- ============================================================================

-- Main games table (PRIMARY SOURCE OF TRUTH)
CREATE TABLE IF NOT EXISTS games (
    app_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    sort_as TEXT,  -- "The LEGO" → "LEGO"
    app_type TEXT NOT NULL,  -- game, dlc, application, video, music, demo, tool, config

    -- Developer & Publisher
    developer TEXT,
    publisher TEXT,

    -- Release Dates (UNIX timestamps)
    original_release_date INTEGER,
    steam_release_date INTEGER,
    release_date INTEGER,

    -- Review Data
    review_score INTEGER,  -- Steam review category (1-9)
    review_percentage INTEGER,  -- Steam review positive percentage (0-100)
    review_count INTEGER,

    -- Price & Status
    is_free BOOLEAN DEFAULT 0,
    is_early_access BOOLEAN DEFAULT 0,

    -- Technical Features
    vr_support TEXT,  -- none, optional, required
    controller_support TEXT,  -- none, partial, full
    cloud_saves BOOLEAN DEFAULT 0,
    workshop BOOLEAN DEFAULT 0,
    trading_cards BOOLEAN DEFAULT 0,
    achievements_total INTEGER DEFAULT 0,

    -- Platform Support (JSON array)
    platforms TEXT,  -- ["windows", "linux", "mac"]

    -- Metadata Management
    is_modified BOOLEAN DEFAULT 0,
    last_synced INTEGER,
    last_updated INTEGER,

    -- Timestamps
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

-- ============================================================================
-- MULTI-VALUE TABLES (Normalized)
-- ============================================================================

CREATE TABLE IF NOT EXISTS game_genres (
    app_id INTEGER NOT NULL,
    genre TEXT NOT NULL,
    PRIMARY KEY (app_id, genre),
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_tags (
    app_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    tag_id INTEGER,
    PRIMARY KEY (app_id, tag),
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- TAG DEFINITIONS (Reference table for TagID → localized name)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tag_definitions (
    tag_id INTEGER NOT NULL,
    language TEXT NOT NULL,
    name TEXT NOT NULL,
    PRIMARY KEY (tag_id, language)
);

CREATE TABLE IF NOT EXISTS game_franchises (
    app_id INTEGER NOT NULL,
    franchise TEXT NOT NULL,
    PRIMARY KEY (app_id, franchise),
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_languages (
    app_id INTEGER NOT NULL,
    language TEXT NOT NULL,
    interface BOOLEAN DEFAULT 0,
    audio BOOLEAN DEFAULT 0,
    subtitles BOOLEAN DEFAULT 0,
    PRIMARY KEY (app_id, language),
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- STEAMGRID ARTWORK (SIMPLIFIED!)
-- ============================================================================

-- Custom artwork metadata
CREATE TABLE IF NOT EXISTS custom_artwork (
    app_id INTEGER NOT NULL,
    artwork_type TEXT NOT NULL,  -- grid_p, grid_h, hero, logo, icon
    source TEXT NOT NULL,  -- steamgriddb, local, custom
    source_url TEXT,
    file_hash TEXT,
    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    set_at INTEGER,
    PRIMARY KEY (app_id, artwork_type),
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- Naming rules reference
CREATE TABLE IF NOT EXISTS artwork_naming_rules (
    artwork_type TEXT PRIMARY KEY,
    filename_pattern TEXT NOT NULL,
    description TEXT,
    required_format TEXT,
    typical_dimensions TEXT
);

INSERT OR REPLACE INTO artwork_naming_rules VALUES
    ('grid_p', '{app_id}p.png', 'Vertical Grid (Portrait)', 'png,jpg', '600x900'),
    ('grid_h', '{app_id}.png', 'Horizontal Grid (Big Picture)', 'png,jpg', '460x215'),
    ('hero', '{app_id}_hero.png', 'Hero Background', 'png,jpg', '1920x620'),
    ('logo', '{app_id}_logo.png', 'Logo (Transparent)', 'png', 'variable'),
    ('icon', '{app_id}_icon.png', 'Icon (MUST BE PNG!)', 'png', '256x256');

-- ============================================================================
-- HOWLONGTOBEAT DATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS hltb_data (
    app_id INTEGER PRIMARY KEY,
    main_story REAL,
    main_extras REAL,
    completionist REAL,
    last_updated INTEGER,
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hltb_id_cache (
    steam_app_id INTEGER PRIMARY KEY,
    hltb_game_id INTEGER NOT NULL,
    cached_at INTEGER NOT NULL
);

-- ============================================================================
-- PROTONDB RATINGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS protondb_ratings (
    app_id INTEGER PRIMARY KEY,
    tier TEXT NOT NULL,
    confidence TEXT DEFAULT '',
    trending_tier TEXT DEFAULT '',
    score REAL DEFAULT 0.0,
    best_reported TEXT DEFAULT '',
    last_updated INTEGER NOT NULL
);

-- ============================================================================
-- PERSONAL NOTES & JOURNAL
-- ============================================================================

CREATE TABLE IF NOT EXISTS game_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER NOT NULL,
    note_type TEXT,  -- review, memory, tip, bug, mod, general
    title TEXT,
    content TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- CUSTOM METADATA (USER-DEFINED FIELDS)
-- ============================================================================

CREATE TABLE IF NOT EXISTS game_custom_meta (
    app_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (app_id, key),
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- USER COLLECTIONS (SMART & MANUAL)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_collections (
    collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    icon TEXT,  -- emoji or icon name
    is_smart BOOLEAN DEFAULT 0,
    rules TEXT,  -- JSON rules for smart collections
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS collection_games (
    collection_id INTEGER NOT NULL,
    app_id INTEGER NOT NULL,
    added_at INTEGER NOT NULL,
    PRIMARY KEY (collection_id, app_id),
    FOREIGN KEY (collection_id) REFERENCES user_collections(collection_id) ON DELETE CASCADE,
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- DEVICE PERFORMANCE TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS device_performance (
    app_id INTEGER NOT NULL,
    device TEXT NOT NULL,  -- PC, Deck_LCD, Deck_OLED, or custom
    works BOOLEAN NOT NULL,
    fps_average INTEGER,
    graphics_settings TEXT,  -- low, medium, high, ultra
    proton_version TEXT,
    notes TEXT,
    tested_at INTEGER NOT NULL,
    PRIMARY KEY (app_id, device),
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- MOD TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS installed_mods (
    mod_id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER NOT NULL,
    mod_name TEXT NOT NULL,
    mod_source TEXT,  -- workshop, nexus, manual
    mod_url TEXT,
    version TEXT,
    installed_at INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- ACHIEVEMENT TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS achievements (
    app_id INTEGER NOT NULL,
    achievement_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_unlocked BOOLEAN DEFAULT 0,
    unlock_time INTEGER,
    is_hidden BOOLEAN DEFAULT 0,
    rarity_percentage REAL,
    PRIMARY KEY (app_id, achievement_id),
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS achievement_stats (
    app_id INTEGER PRIMARY KEY,
    total_achievements INTEGER NOT NULL,
    unlocked_achievements INTEGER NOT NULL,
    completion_percentage REAL NOT NULL,
    perfect_game BOOLEAN DEFAULT 0,
    last_achievement_time INTEGER,
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- PLAY SESSIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS play_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER NOT NULL,
    start_time INTEGER NOT NULL,
    end_time INTEGER,
    duration_minutes INTEGER,
    device TEXT,
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS playtime (
    app_id INTEGER PRIMARY KEY,
    playtime_minutes INTEGER DEFAULT 0,
    playtime_2weeks INTEGER DEFAULT 0,
    last_played INTEGER,
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- CONTROLLER CONFIGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS controller_configs (
    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER NOT NULL,
    config_name TEXT NOT NULL,
    config_data TEXT,  -- JSON controller layout
    device TEXT,
    created_at INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT 0,
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- SCREENSHOTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS screenshots (
    screenshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    thumbnail_path TEXT,
    taken_at INTEGER NOT NULL,
    description TEXT,
    tags TEXT,  -- JSON array
    is_favorite BOOLEAN DEFAULT 0,
    device TEXT,
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- WISHLIST & PRICE TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS wishlist (
    wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER UNIQUE NOT NULL,
    added_at INTEGER NOT NULL,
    priority INTEGER DEFAULT 3,  -- 1-5 (1=must have, 5=maybe)
    max_price REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS price_history (
    app_id INTEGER NOT NULL,
    price REAL NOT NULL,
    currency TEXT NOT NULL,
    on_sale BOOLEAN DEFAULT 0,
    discount_percentage INTEGER,
    checked_at INTEGER NOT NULL,
    PRIMARY KEY (app_id, checked_at)
);

-- ============================================================================
-- FRIEND RECOMMENDATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS friend_games (
    friend_id TEXT NOT NULL,
    friend_name TEXT NOT NULL,
    app_id INTEGER NOT NULL,
    owns_game BOOLEAN NOT NULL,
    last_played INTEGER,
    playtime_minutes INTEGER,
    PRIMARY KEY (friend_id, app_id)
);

CREATE TABLE IF NOT EXISTS coop_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER NOT NULL,
    friends TEXT,  -- JSON array of friend IDs
    start_time INTEGER NOT NULL,
    end_time INTEGER,
    notes TEXT,
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- MODIFICATION TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS metadata_modifications (
    app_id INTEGER PRIMARY KEY,
    original_data TEXT,  -- JSON
    modified_data TEXT,  -- JSON
    modification_time INTEGER NOT NULL,
    synced_to_appinfo BOOLEAN DEFAULT 0,
    sync_time INTEGER,
    FOREIGN KEY (app_id) REFERENCES games(app_id) ON DELETE CASCADE
);

-- ============================================================================
-- METADATA TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS import_history (
    import_id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_time INTEGER NOT NULL,
    source TEXT NOT NULL,
    games_imported INTEGER NOT NULL,
    games_updated INTEGER NOT NULL,
    games_failed INTEGER NOT NULL,
    notes TEXT
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Games
CREATE INDEX IF NOT EXISTS idx_games_name ON games(name);
CREATE INDEX IF NOT EXISTS idx_games_sort_as ON games(sort_as);
CREATE INDEX IF NOT EXISTS idx_games_type ON games(app_type);
CREATE INDEX IF NOT EXISTS idx_games_developer ON games(developer);
CREATE INDEX IF NOT EXISTS idx_games_publisher ON games(publisher);
CREATE INDEX IF NOT EXISTS idx_games_release_date ON games(release_date);
CREATE INDEX IF NOT EXISTS idx_games_review_score ON games(review_score);
CREATE INDEX IF NOT EXISTS idx_games_is_modified ON games(is_modified);

-- Multi-value
CREATE INDEX IF NOT EXISTS idx_genres_genre ON game_genres(genre);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON game_tags(tag);
CREATE INDEX IF NOT EXISTS idx_tags_tag_id ON game_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_tag_definitions_name ON tag_definitions(name);
CREATE INDEX IF NOT EXISTS idx_tag_definitions_lang ON tag_definitions(language);
CREATE INDEX IF NOT EXISTS idx_franchises_franchise ON game_franchises(franchise);
CREATE INDEX IF NOT EXISTS idx_languages_language ON game_languages(language);

-- Artwork
CREATE INDEX IF NOT EXISTS idx_artwork_hash ON custom_artwork(file_hash);

-- Notes
CREATE INDEX IF NOT EXISTS idx_notes_type ON game_notes(note_type);
CREATE INDEX IF NOT EXISTS idx_notes_created ON game_notes(created_at);

-- Collections
CREATE INDEX IF NOT EXISTS idx_collections_smart ON user_collections(is_smart);

-- Performance
CREATE INDEX IF NOT EXISTS idx_performance_device ON device_performance(device);

-- Mods
CREATE INDEX IF NOT EXISTS idx_mods_active ON installed_mods(is_active);

-- Achievements
CREATE INDEX IF NOT EXISTS idx_achievements_unlocked ON achievements(is_unlocked);
CREATE INDEX IF NOT EXISTS idx_achievement_stats_perfect ON achievement_stats(perfect_game);

-- Playtime
CREATE INDEX IF NOT EXISTS idx_playtime_last_played ON playtime(last_played);

-- Screenshots
CREATE INDEX IF NOT EXISTS idx_screenshots_favorite ON screenshots(is_favorite);

-- Wishlist
CREATE INDEX IF NOT EXISTS idx_wishlist_priority ON wishlist(priority);

-- ============================================================================
-- VIEWS FOR CONVENIENCE
-- ============================================================================

-- All real games
CREATE VIEW IF NOT EXISTS v_real_games AS
SELECT * FROM games WHERE app_type IN ('game', 'demo');

-- Modified games needing sync
CREATE VIEW IF NOT EXISTS v_needs_sync AS
SELECT g.*, mm.modification_time
FROM games g
JOIN metadata_modifications mm ON g.app_id = mm.app_id
WHERE mm.synced_to_appinfo = 0;

-- Games with full metadata
CREATE VIEW IF NOT EXISTS v_games_full AS
SELECT
    g.*,
    GROUP_CONCAT(DISTINCT gg.genre) as genres,
    GROUP_CONCAT(DISTINCT gt.tag) as tags,
    GROUP_CONCAT(DISTINCT gf.franchise) as franchises,
    h.main_story, h.main_extras, h.completionist,
    p.playtime_minutes, p.last_played,
    a.total_achievements, a.unlocked_achievements, a.completion_percentage
FROM games g
LEFT JOIN game_genres gg ON g.app_id = gg.app_id
LEFT JOIN game_tags gt ON g.app_id = gt.app_id
LEFT JOIN game_franchises gf ON g.app_id = gf.app_id
LEFT JOIN hltb_data h ON g.app_id = h.app_id
LEFT JOIN playtime p ON g.app_id = p.app_id
LEFT JOIN achievement_stats a ON g.app_id = a.app_id
GROUP BY g.app_id;

-- Games close to 100% achievements
CREATE VIEW IF NOT EXISTS v_achievement_hunting AS
SELECT g.*, a.completion_percentage, a.unlocked_achievements, a.total_achievements
FROM games g
JOIN achievement_stats a ON g.app_id = a.app_id
WHERE a.completion_percentage >= 75 AND a.completion_percentage < 100
ORDER BY a.completion_percentage DESC;

-- Recently played games
CREATE VIEW IF NOT EXISTS v_recently_played AS
SELECT g.*, p.last_played, p.playtime_minutes
FROM games g
JOIN playtime p ON g.app_id = p.app_id
WHERE p.last_played IS NOT NULL
ORDER BY p.last_played DESC
LIMIT 50;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update timestamps
CREATE TRIGGER IF NOT EXISTS update_games_timestamp
AFTER UPDATE ON games
BEGIN
    UPDATE games SET updated_at = strftime('%s', 'now')
    WHERE app_id = NEW.app_id;
END;

-- Auto-set is_modified
CREATE TRIGGER IF NOT EXISTS set_is_modified
AFTER UPDATE ON games
BEGIN
    UPDATE games SET is_modified = 1
    WHERE app_id = NEW.app_id
    AND (
        NEW.name != OLD.name OR
        NEW.sort_as != OLD.sort_as OR
        NEW.developer != OLD.developer OR
        NEW.publisher != OLD.publisher
    );
END;

-- Auto-update achievement stats
CREATE TRIGGER IF NOT EXISTS update_achievement_stats_after_unlock
AFTER UPDATE ON achievements
WHEN NEW.is_unlocked = 1 AND OLD.is_unlocked = 0
BEGIN
    UPDATE achievement_stats
    SET
        unlocked_achievements = unlocked_achievements + 1,
        completion_percentage = (CAST(unlocked_achievements + 1 AS REAL) / total_achievements) * 100,
        perfect_game = CASE WHEN unlocked_achievements + 1 = total_achievements THEN 1 ELSE 0 END,
        last_achievement_time = strftime('%s', 'now')
    WHERE app_id = NEW.app_id;
END;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

INSERT OR IGNORE INTO schema_version (version, applied_at, description)
VALUES (6, strftime('%s', 'now'), 'Add review_percentage column');

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
