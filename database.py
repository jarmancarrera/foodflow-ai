import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).parent / "foodflow.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # More reliable for concurrent reads/writes in demo.
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS locations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            lat REAL, lng REAL,
            type TEXT,
            capacity_lbs REAL
        );
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id TEXT,
            item TEXT,
            quantity_lbs REAL,
            available_at TEXT,
            predicted_surplus REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS volunteers (
            id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            lat REAL, lng REAL,
            available INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS rescues (
            rescue_id TEXT PRIMARY KEY,
            location_id TEXT NOT NULL,
            location_name TEXT,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            result_json TEXT
        );
        CREATE TABLE IF NOT EXISTS pickups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rescue_id TEXT,
            supplier_id TEXT,
            foodbank_id TEXT,
            volunteer_id TEXT,
            item TEXT,
            quantity_lbs REAL,
            status TEXT DEFAULT 'dispatched',
            dispatched_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );
    """)
    _ensure_schema(conn)
    _seed(conn)
    conn.commit()
    conn.close()

def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)

def _ensure_schema(conn: sqlite3.Connection):
    # Soft-migrate existing hackathon DBs.
    if not _has_column(conn, "locations", "capacity_lbs"):
        conn.execute("ALTER TABLE locations ADD COLUMN capacity_lbs REAL")
    if not _has_column(conn, "pickups", "rescue_id"):
        conn.execute("ALTER TABLE pickups ADD COLUMN rescue_id TEXT")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rescues (
            rescue_id TEXT PRIMARY KEY,
            location_id TEXT NOT NULL,
            location_name TEXT,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            result_json TEXT
        )
    """)

def _seed(conn):
    if conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0] > 0:
        return
    conn.executemany(
        "INSERT OR IGNORE INTO locations(id,name,lat,lng,type,capacity_lbs) VALUES (?,?,?,?,?,?)",
        [
        ("cornell_statler",  "Cornell Statler Hall",        42.4467, -76.4851, "supplier", None),
        ("cornell_rpcc",     "Cornell RPCC Dining",         42.4534, -76.4758, "supplier", None),
        ("ithaca_food_bank", "Ithaca Food Bank",            42.4396, -76.4967, "foodbank", 500.0),
        ("southern_tier_fb", "Food Bank of Southern Tier",  42.1066, -76.8066, "foodbank", 2000.0),
        ],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO inventory(location_id,item,quantity_lbs,available_at,predicted_surplus) VALUES (?,?,?,?,?)", [
        ("cornell_statler", "Pasta & Marinara",  80.0, "20:15", 78.0),
        ("cornell_statler", "Caesar Salad",      22.0, "20:00", 18.0),
        ("cornell_rpcc",    "Grilled Chicken",   45.0, "20:30", 40.0),
    ])
    conn.executemany("INSERT OR IGNORE INTO volunteers VALUES (?,?,?,?,?,?)", [
        ("vol_001", "Alex M.",   "+16072221111", 42.4430, -76.4890, 1),
        ("vol_002", "Jordan P.", "+16072222222", 42.4500, -76.4800, 1),
        ("vol_003", "Sam R.",    "+16072223333", 42.4450, -76.4950, 0),
    ])

def get_surplus_items():
    conn = get_db()
    rows = conn.execute("""
        SELECT i.*, l.name as location_name, l.lat, l.lng
        FROM inventory i JOIN locations l ON i.location_id = l.id
        WHERE i.predicted_surplus > 0
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_available_volunteers():
    conn = get_db()
    rows = conn.execute("SELECT * FROM volunteers WHERE available=1").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_foodbanks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM locations WHERE type='foodbank'").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_locations():
    conn = get_db()
    rows = conn.execute("SELECT * FROM locations ORDER BY type, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_inventory(limit: int = 100):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT i.*, l.name as location_name
        FROM inventory i JOIN locations l ON i.location_id = l.id
        ORDER BY i.created_at DESC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_volunteers():
    conn = get_db()
    rows = conn.execute("SELECT * FROM volunteers ORDER BY available DESC, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_pickups(limit: int = 200):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT p.*, s.name as supplier_name, f.name as foodbank_name, v.name as volunteer_name, v.phone as volunteer_phone
        FROM pickups p
        LEFT JOIN locations s ON p.supplier_id = s.id
        LEFT JOIN locations f ON p.foodbank_id = f.id
        LEFT JOIN volunteers v ON p.volunteer_id = v.id
        ORDER BY p.dispatched_at DESC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_rescues(limit: int = 100):
    cleanup_stale_running_rescues(max_age_seconds=90)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM rescues ORDER BY started_at DESC LIMIT ?",
        (int(limit),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_pickup(supplier_id, foodbank_id, volunteer_id, item, quantity_lbs, rescue_id: Optional[str] = None):
    conn = get_db()
    conn.execute(
        "INSERT INTO pickups(rescue_id,supplier_id,foodbank_id,volunteer_id,item,quantity_lbs) VALUES (?,?,?,?,?,?)",
        (rescue_id, supplier_id, foodbank_id, volunteer_id, item, quantity_lbs)
    )
    conn.execute("UPDATE volunteers SET available=0 WHERE id=?", (volunteer_id,))
    conn.commit()
    conn.close()

def create_rescue(rescue_id: str, location_id: str, location_name: str):
    conn = get_db()
    # Use SQLite datetime format for reliable comparisons in queries.
    conn.execute(
        "INSERT OR REPLACE INTO rescues(rescue_id,location_id,location_name,status,started_at) VALUES (?,?,?,?,datetime('now'))",
        (rescue_id, location_id, location_name, "running"),
    )
    conn.commit()
    conn.close()

def complete_rescue(rescue_id: str, status: str, result_json: str):
    conn = get_db()
    conn.execute(
        "UPDATE rescues SET status=?, completed_at=datetime('now'), result_json=? WHERE rescue_id=?",
        (status, result_json, rescue_id),
    )
    conn.commit()
    conn.close()

def get_last_rescue() -> dict:
    # Keep the UI sane even if a background task crashed.
    cleanup_stale_running_rescues(max_age_seconds=90)
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM rescues ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else {}

def get_rescue(rescue_id: str) -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM rescues WHERE rescue_id=?", (rescue_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}

def cleanup_stale_running_rescues(max_age_seconds: int = 90) -> int:
    conn = get_db()
    cur = conn.execute(
        """
        UPDATE rescues
        SET status='timeout', completed_at=datetime('now'), result_json=COALESCE(result_json, '{"status":"timeout"}')
        WHERE status='running'
          AND julianday(replace(started_at,'T',' ')) < julianday(datetime('now', ?))
        """,
        (f"-{int(max_age_seconds)} seconds",),
    )
    conn.commit()
    conn.close()
    return cur.rowcount

def get_recent_running_rescue(location_id: str, window_seconds: int = 120) -> dict:
    conn = get_db()
    row = conn.execute(
        """
        SELECT *
        FROM rescues
        WHERE location_id = ?
          AND status = 'running'
          AND julianday(replace(started_at,'T',' ')) >= julianday(datetime('now', ?))
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (location_id, f"-{int(window_seconds)} seconds"),
    ).fetchone()
    conn.close()
    return dict(row) if row else {}

def get_stats():
    conn = get_db()
    row = conn.execute("""
        SELECT
            COUNT(*) as total_pickups,
            COALESCE(SUM(quantity_lbs),0) as total_lbs,
            COALESCE(SUM(quantity_lbs)*0.6,0) as total_meals,
            COALESCE(SUM(quantity_lbs)*0.154,0) as total_co2_kg
        FROM pickups WHERE status='dispatched'
    """).fetchone()
    conn.close()
    return dict(row)
