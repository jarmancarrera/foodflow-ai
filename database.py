import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "foodflow.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS locations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            lat REAL, lng REAL,
            type TEXT
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
        CREATE TABLE IF NOT EXISTS pickups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    _seed(conn)
    conn.commit()
    conn.close()

def _seed(conn):
    if conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0] > 0:
        return
    conn.executemany("INSERT OR IGNORE INTO locations VALUES (?,?,?,?,?)", [
        ("cornell_statler",  "Cornell Statler Hall",        42.4467, -76.4851, "supplier"),
        ("cornell_rpcc",     "Cornell RPCC Dining",         42.4534, -76.4758, "supplier"),
        ("ithaca_food_bank", "Ithaca Food Bank",            42.4396, -76.4967, "foodbank"),
        ("southern_tier_fb", "Food Bank of Southern Tier",  42.1066, -76.8066, "foodbank"),
    ])
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

def log_pickup(supplier_id, foodbank_id, volunteer_id, item, quantity_lbs):
    conn = get_db()
    conn.execute(
        "INSERT INTO pickups(supplier_id,foodbank_id,volunteer_id,item,quantity_lbs) VALUES (?,?,?,?,?)",
        (supplier_id, foodbank_id, volunteer_id, item, quantity_lbs)
    )
    conn.execute("UPDATE volunteers SET available=0 WHERE id=?", (volunteer_id,))
    conn.commit()
    conn.close()

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
