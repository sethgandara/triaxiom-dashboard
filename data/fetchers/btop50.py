# data/fetchers/btop50.py - BTOP50 full monthly history scraper
# Confirmed: static HTML table, full multi-year history, no login required

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
from pathlib import Path
import config
from data.storage import init_db, upsert_df

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def fetch_html():
    time.sleep(config.SCRAPE_DELAY_SECS)
    r = requests.get(config.BTOP50_URL, headers=config.HEADERS, timeout=config.REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def find_monthly_table(html):
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    print(f"  Found {len(tables)} tables on BTOP50 page")
    for i, table in enumerate(tables):
        try:
            df = pd.read_html(StringIO(str(table)))[0]
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [' '.join(map(str, c)).strip() for c in df.columns]
            cols = [str(c).strip() for c in df.columns]
            month_hits = sum(1 for m in MONTHS if any(m in c for c in cols))
            if month_hits >= 6:
                print(f"  OK: Monthly table found at index {i} ({month_hits} month cols)")
                df.columns = cols
                return df
        except Exception:
            continue
    print("  ERR: No monthly table found.")
    print(html[:2000])
    raise ValueError(f"No BTOP50 monthly table found. Verify: {config.BTOP50_URL}")


def normalize(df):
    records = []
    for _, row in df.iterrows():
        year_val = str(row.iloc[0]).strip().replace(".0", "")
        if not year_val.isdigit() or len(year_val) != 4:
            continue
        year = int(year_val)
        ytd_raw = None
        for col in df.columns:
            if "ytd" in col.lower() or "year" in col.lower():
                ytd_raw = row[col]
                break
        for m_idx, month_abbr in enumerate(MONTHS):
            month_col = None
            for col in df.columns:
                if col.strip().startswith(month_abbr):
                    month_col = col
                    break
            if month_col is None:
                continue
            val = row[month_col]
            if pd.isna(val) or str(val).strip() in ("", "-", "N/A", "nan"):
                continue
            estimated = "*" in str(val)
            clean = str(val).replace("*", "").replace("%", "").strip()
            try:
                return_pct = float(clean)
            except ValueError:
                continue
            ytd_clean = None
            if ytd_raw and not pd.isna(ytd_raw):
                try:
                    ytd_clean = float(str(ytd_raw).replace("*", "").replace("%", "").strip())
                except:
                    pass
            records.append({"date": f"{year}-{m_idx+1:02d}-01", "return_pct": return_pct, "ytd_pct": ytd_clean, "estimated": int(estimated)})
    df_out = pd.DataFrame(records)
    print(f"  Parsed {len(df_out)} monthly rows from BTOP50")
    return df_out


def run():
    init_db()
    print("FetPChing BTOP50...")
    html = fetch_html()
    df_raw = find_monthly_table(html)
    df = normalize(df_raw)
    if not df.empty:
        upsert_df("btop50", df, ["date"])
        Path("data").mkdir(exist_ok=True)
        df.to_csv(config.BTOP50_CSV, index=False)
        print(f"OK: BTOP50: {len(df)} rows -> {config.BTOP50_CSV}")
    return df


if __name__ == "__main__":
    run()
