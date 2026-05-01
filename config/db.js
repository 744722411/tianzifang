import initSqlJs from 'sql.js';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { dirname } from 'path';
import { DB_PATH } from './settings.js';

let _db = null;

export async function getDb() {
  if (_db) return _db;
  const SQL = await initSqlJs();
  if (existsSync(DB_PATH)) {
    const buf = readFileSync(DB_PATH);
    _db = new SQL.Database(buf);
  } else {
    _db = new SQL.Database();
  }
  return _db;
}

export function saveDb(db) {
  mkdirSync(dirname(DB_PATH), { recursive: true });
  const data = db.export();
  writeFileSync(DB_PATH, Buffer.from(data));
}

export async function initDb() {
  const db = await getDb();
  db.run(`
    CREATE TABLE IF NOT EXISTS crowd_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      source TEXT NOT NULL,
      metric TEXT NOT NULL,
      value REAL,
      unit TEXT,
      confidence TEXT DEFAULT 'measured',
      raw_json TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    )
  `);
  db.run(`CREATE INDEX IF NOT EXISTS idx_crowd_ts ON crowd_data(ts)`);
  db.run(`CREATE INDEX IF NOT EXISTS idx_crowd_source ON crowd_data(source)`);
  db.run(`CREATE INDEX IF NOT EXISTS idx_crowd_metric ON crowd_data(metric)`);
  db.run(`
    CREATE TABLE IF NOT EXISTS daily_summary (
      date TEXT PRIMARY KEY,
      weekday INTEGER,
      is_holiday INTEGER DEFAULT 0,
      holiday_name TEXT,
      weather_desc TEXT,
      temperature_high REAL,
      temperature_low REAL,
      max_crowd INTEGER,
      avg_crowd REAL,
      peak_hour INTEGER,
      total_visitors INTEGER,
      notes TEXT
    )
  `);
  saveDb(db);
  return db;
}
