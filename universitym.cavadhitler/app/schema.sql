PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    description      TEXT NOT NULL DEFAULT '',
    category_id      INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    event_date       TEXT NOT NULL,              -- YYYY-MM-DD
    event_time       TEXT NOT NULL,              -- HH:MM
    location         TEXT NOT NULL,
    max_participants INTEGER NOT NULL CHECK (max_participants > 0),
    created_by       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS registrations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id      INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
    registered_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (event_id, user_id)                   -- eyni tədbirə təkrar qeydiyyatın qarşısı
);

CREATE INDEX IF NOT EXISTS idx_events_date     ON events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category_id);
CREATE INDEX IF NOT EXISTS idx_reg_event       ON registrations(event_id);
CREATE INDEX IF NOT EXISTS idx_reg_user        ON registrations(user_id);
