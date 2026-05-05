import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from backend.services.seed_service import seed_database


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "backend" / "database" / "eurotwingo.sqlite"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS progression (
    user_id INTEGER PRIMARY KEY,
    level INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    completed_trajets INTEGER NOT NULL DEFAULT 0,
    successful_events INTEGER NOT NULL DEFAULT 0,
    distance_km INTEGER NOT NULL DEFAULT 0,
    fuel INTEGER NOT NULL DEFAULT 35,
    coins INTEGER NOT NULL DEFAULT 0,
    repairs_needed INTEGER NOT NULL DEFAULT 0,
    current_node_id TEXT NOT NULL DEFAULT 'PAR',
    visited_nodes_json TEXT NOT NULL DEFAULT '["PAR"]',
    unlocked_skins_json TEXT NOT NULL DEFAULT '["twingo-93"]',
    equipped_skin_slug TEXT NOT NULL DEFAULT 'twingo-93',
    achievements_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS skins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    rarity TEXT NOT NULL,
    inspired_by TEXT NOT NULL,
    description TEXT NOT NULL,
    palette_json TEXT NOT NULL,
    min_level INTEGER NOT NULL DEFAULT 1,
    asset TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trajets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    city_ids_json TEXT NOT NULL,
    distance_hint INTEGER NOT NULL,
    reward_xp INTEGER NOT NULL,
    reward_coins INTEGER NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    rarity TEXT NOT NULL,
    description TEXT NOT NULL,
    effect_json TEXT NOT NULL,
    trajet_id INTEGER,
    FOREIGN KEY(trajet_id) REFERENCES trajets(id)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    effect_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id INTEGER,
    item_type TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS map_nodes (
    id TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    node_type TEXT NOT NULL,
    resource_json TEXT NOT NULL,
    weather TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_node_id TEXT NOT NULL,
    to_node_id TEXT NOT NULL,
    road_type TEXT NOT NULL,
    distance_km INTEGER NOT NULL,
    cost_coins INTEGER NOT NULL,
    fuel_cost INTEGER NOT NULL,
    event_rate REAL NOT NULL,
    FOREIGN KEY(from_node_id) REFERENCES map_nodes(id),
    FOREIGN KEY(to_node_id) REFERENCES map_nodes(id)
);

CREATE TABLE IF NOT EXISTS trip_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    trajet_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    distance_km INTEGER NOT NULL,
    reward_xp INTEGER NOT NULL,
    reward_coins INTEGER NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(trajet_id) REFERENCES trajets(id)
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    condition_key TEXT NOT NULL,
    threshold INTEGER NOT NULL,
    reward_xp INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_achievements (
    user_id INTEGER NOT NULL,
    achievement_id INTEGER NOT NULL,
    unlocked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, achievement_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(achievement_id) REFERENCES achievements(id)
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    visibility TEXT NOT NULL DEFAULT 'private',
    game_mode TEXT NOT NULL DEFAULT 'classic',
    status TEXT NOT NULL DEFAULT 'lobby',
    created_by_user_id INTEGER NOT NULL,
    current_turn_user_id INTEGER NOT NULL,
    turn_number INTEGER NOT NULL DEFAULT 1,
    round_number INTEGER NOT NULL DEFAULT 1,
    winner_user_id INTEGER,
    final_standings_json TEXT NOT NULL DEFAULT '[]',
    max_players INTEGER NOT NULL DEFAULT 6,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(created_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(current_turn_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(winner_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS session_players (
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    position_node_id TEXT NOT NULL DEFAULT 'PAR',
    spawn_node_id TEXT NOT NULL DEFAULT 'PAR',
    is_ready INTEGER NOT NULL DEFAULT 0,
    fuel INTEGER NOT NULL DEFAULT 35,
    coins INTEGER NOT NULL DEFAULT 140,
    durability INTEGER NOT NULL DEFAULT 100,
    repairs_needed INTEGER NOT NULL DEFAULT 0,
    board_position_json TEXT NOT NULL DEFAULT '{"kind":"city","node_id":"PAR"}',
    visited_board_cases_json TEXT NOT NULL DEFAULT '[]',
    dice_remaining INTEGER NOT NULL DEFAULT 0,
    turn_roll INTEGER NOT NULL DEFAULT 0,
    visited_nodes_json TEXT NOT NULL DEFAULT '["PAR"]',
    distance_km INTEGER NOT NULL DEFAULT 0,
    completed_trajets INTEGER NOT NULL DEFAULT 0,
    xp INTEGER NOT NULL DEFAULT 0,
    victory_points INTEGER NOT NULL DEFAULT 0,
    mission_locked_turns INTEGER NOT NULL DEFAULT 0,
    trajet_draws_long INTEGER NOT NULL DEFAULT 0,
    trajet_draws_short INTEGER NOT NULL DEFAULT 0,
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_action_at TEXT,
    PRIMARY KEY(session_id, user_id),
    FOREIGN KEY(session_id) REFERENCES game_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(position_node_id) REFERENCES map_nodes(id)
);

CREATE TABLE IF NOT EXISTS session_city_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    feature_type TEXT NOT NULL,
    feature_payload_json TEXT NOT NULL DEFAULT '{}',
    tasks_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE(session_id, node_id),
    FOREIGN KEY(session_id) REFERENCES game_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(node_id) REFERENCES map_nodes(id)
);

CREATE TABLE IF NOT EXISTS session_turn_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES game_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS session_carpoolers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    start_node_id TEXT NOT NULL,
    destination_node_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting',
    assigned_user_id INTEGER,
    victory_points INTEGER NOT NULL DEFAULT 30,
    reward_coins INTEGER NOT NULL DEFAULT 25,
    reward_durability INTEGER NOT NULL DEFAULT 0,
    min_turns INTEGER NOT NULL DEFAULT 2,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES game_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(assigned_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY(start_node_id) REFERENCES map_nodes(id),
    FOREIGN KEY(destination_node_id) REFERENCES map_nodes(id)
);

CREATE TABLE IF NOT EXISTS session_contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    reward_coins INTEGER NOT NULL DEFAULT 40,
    reward_victory_points INTEGER NOT NULL DEFAULT 8,
    reward_xp INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    claimed_by_user_id INTEGER,
    created_round INTEGER NOT NULL DEFAULT 1,
    expires_round INTEGER NOT NULL DEFAULT 3,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES game_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(target_node_id) REFERENCES map_nodes(id),
    FOREIGN KEY(claimed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);
"""


class Database:
    def __init__(self, path=None):
        configured = os.environ.get("EUROTWINGO_DB_PATH")
        self.path = Path(configured or path or DEFAULT_DB_PATH)

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init(self):
        conn = self.connect()
        try:
            conn.executescript(SCHEMA_SQL)
            apply_migrations(conn)
            seed_database(conn)
            conn.commit()
        finally:
            conn.close()

    @contextmanager
    def session(self):
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def row_to_dict(row):
    return dict(row) if row is not None else None


def apply_migrations(conn):
    ensure_columns(
        conn,
        "game_sessions",
        {
            "round_number": "INTEGER NOT NULL DEFAULT 1",
            "winner_user_id": "INTEGER",
            "final_standings_json": "TEXT NOT NULL DEFAULT '[]'",
            "visibility": "TEXT NOT NULL DEFAULT 'private'",
            "game_mode": "TEXT NOT NULL DEFAULT 'classic'",
        },
    )
    ensure_columns(
        conn,
        "session_players",
        {
            "spawn_node_id": "TEXT NOT NULL DEFAULT 'PAR'",
            "is_ready": "INTEGER NOT NULL DEFAULT 0",
            "durability": "INTEGER NOT NULL DEFAULT 100",
            "board_position_json": "TEXT NOT NULL DEFAULT '{\"kind\":\"city\",\"node_id\":\"PAR\"}'",
            "visited_board_cases_json": "TEXT NOT NULL DEFAULT '[]'",
            "dice_remaining": "INTEGER NOT NULL DEFAULT 0",
            "turn_roll": "INTEGER NOT NULL DEFAULT 0",
            "victory_points": "INTEGER NOT NULL DEFAULT 0",
            "mission_locked_turns": "INTEGER NOT NULL DEFAULT 0",
            "trajet_draws_long": "INTEGER NOT NULL DEFAULT 0",
            "trajet_draws_short": "INTEGER NOT NULL DEFAULT 0",
        },
    )
    ensure_columns(
        conn,
        "inventory",
        {
            "session_id": "INTEGER",
            "quantity": "INTEGER NOT NULL DEFAULT 1",
        },
    )
    ensure_columns(
        conn,
        "session_carpoolers",
        {
            "reward_coins": "INTEGER NOT NULL DEFAULT 25",
            "reward_durability": "INTEGER NOT NULL DEFAULT 0",
        },
    )
    conn.execute("UPDATE progression SET fuel = 35 WHERE fuel > 35")
    conn.execute("UPDATE progression SET coins = 0")
    conn.execute("UPDATE session_players SET fuel = 35 WHERE fuel > 35")
    conn.execute("""UPDATE map_nodes SET resource_json = REPLACE(resource_json, '"fuel": 100', '"fuel": 35')""")


def ensure_columns(conn, table_name, columns):
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    for column_name, column_sql in columns.items():
        if column_name not in existing:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
