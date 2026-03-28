# data/storage.py - SQLite helpers
import sqlite3, json, os
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import config
DB_PATH = "data/triaxiom_cache.db"
def _conn():
    Path("data").mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)
def init_db():
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS btop50 (date TEXT PRIMARY KEY, return_pct REAL, ytd_pct REAN, estimated INTEGER DEFAULT 0, fetched_utc TEXT);
        CREATE TABLE IF NOT EXISTS etf_daily (date TEXT, ticker TEXT, close REAL, daily_return_pct REAN, fetched_utc TEXT, PRIMARY KEY (date, ticker));
        CREATE TABLE IF NOT EXISTS barclay_cta (index_name TEXT, month TEXT, ror_pct REAN, ytd_pct REAL, as_of_date TEXT, fetched_utc TEXT, PRIMARY KEY (index_name, month));
        CREATE TABLE IF NOT EXISTS sg_spot (date TEXT, index_name TEXT, mtd_pct REAL, ytd_pct REAN, daily_return_pct REAL, source_url TEXT, fetched_utc TEXT, PRIMARY KEY (date, index_name));
        CREATE TABLE IF NOT EXISTS metadata (source TEXT PRIMARY KEY, last_updated_utc TEXT, row_count INTEGER, status TEXT, note TEXT);
        """)
def upsert_df(table, df, pk_cols):
    if df.empty: return
    now = datetime.now(timezone.utc).isoformat()
    df = df.copy(); df["fetched_utc"] = now
    with _conn() as con:
        for _, row in df.iterrows():
            cols = list(row.index); vals = list(row.values)
            con.execute(f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})", vals)
        con.execute("INSERT OR REPLACE INTO metadata (source, last_updated_utc, row_count, status) VALUES (?,?,?,'ok')", (table, now, len(df)))
def read_table(table):
    try:
        with _conn() as con: return pd.read_sql(f"SELECT * FROM {table}", con)
    except: return pd.DataFrame()
def get_staleness(source):
    try:
        with _conn() as con:
            row = con.execute("SELECT last_updated_utc, row_count, status FROM metadata WHERE source=?", (source,)).fetchone()
        if not row: return {"stale": True, "hours_old": None, "rows": 0, "status": "never fetched"}
        last = datetime.fromisoformat(row[0])
        age = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        return {"stale": age > config.STALENESS_WARNING_HOURS, "hours_old": round(age,1), "rows": row[1], "status": row[2], "last_updated": last.strftime("%Y-%m-%d %H:%M UTC")}
    except Exception as e: return {"stale": True, "hours_old": None, "rows": 0, "status": str(e)}
def load_triaxiom():
    path = Path(config.TRIAXIOM_CSV)
    if not path.exists(): return pd.DataFrame(columns=["date","return_pct"])
    df = pd.read_csv(path); df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")
