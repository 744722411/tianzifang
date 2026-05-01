"""数据库初始化与操作"""
import sqlite3
from config.settings import DB_PATH


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS crowd_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,                    -- ISO 时间戳
        source TEXT NOT NULL,                -- 数据源: gov_tour / amap / weather / news
        metric TEXT NOT NULL,                -- 指标名: in_park_count / congestion_index / temperature / ...
        value REAL,                          -- 数值
        unit TEXT,                           -- 单位: 人 / index / ℃ / ...
        confidence TEXT DEFAULT 'measured',  -- measured / estimated / scraped
        raw_json TEXT,                       -- 原始 JSON 数据
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_crowd_ts ON crowd_data(ts);
    CREATE INDEX IF NOT EXISTS idx_crowd_source ON crowd_data(source);
    CREATE INDEX IF NOT EXISTS idx_crowd_metric ON crowd_data(metric);

    CREATE TABLE IF NOT EXISTS daily_summary (
        date TEXT PRIMARY KEY,
        weekday INTEGER,                     -- 0=周一 6=周日
        is_holiday INTEGER DEFAULT 0,
        holiday_name TEXT,
        weather_desc TEXT,
        temperature_high REAL,
        temperature_low REAL,
        max_crowd INTEGER,
        avg_crowd REAL,
        peak_hour INTEGER,
        total_visitors INTEGER,
        amap_congestion_avg REAL,
        notes TEXT
    );
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
