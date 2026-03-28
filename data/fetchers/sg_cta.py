# data/fetchers/sg_cta.py - SG CTA/Trend spot MTD/YTD

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import time, re
import requests
import pandas as pd
from io import StringIO
from datetime import datetime
from pathlib import Path
import config
from data.storage import init_db, upsert_df

CANDIDATE_URLS = [config.SG_TISCREEN_URL, config.SG_LANDING_URL]
SG_HEADERS = {**config.HEADERS, "Referer": config.SG_LANDING_URL}


def fetch_html(url):
    time.sleep(config.SCRAPE_DELAY_SECS)
    try:
        r = requests.get(url, headers=SG_HEADERS, timeout=config.REQUEST_TIMEOUT)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
        print(f"  WARN: {url} -> HTTP {r.status_code}")
    except Exception as e:
        print(f"  WARN: {url} -> {e}")
    return None


def parse(html, source_url):
    rows = []
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        tables = pd.read_html(StringIO(html))
    except:
        return []
    for t in tables:
        text = " ".join(map(str, t.astype(str).fillna("").values.flatten()))
        if not any(idx in text for idx in config.SG_TARGET_INDICES):
            continue
        for _, row in t.iterrows():
            joined = " | ".join(map(str, row.tolist()))
            for idx_name in config.SG_TARGET_INDICES:
                if idx_name not in joined:
                    continue
                nums = [float(x.replace("%", "")) for x in re.findall(r"-?\d+(?:\.\d+)?%", joined)]
                rows.append({"date": today, "index_name": idx_name, "mtd_pct": nums[0] if nums else None, "ytd_pct": nums[1] if len(nums) > 1 else None, "daily_return_pct": nums[2] if len(nums) > 2 else None, "source_url": source_url})
                print(f"  OK: {idx_name}: MTD={rows[-1]['mtd_pct']}%, YTD={rows[-1]['ytd_pct']}%")
    return rows


def run():
    init_db()
    print("Fetching SG CTA...")
    all_rows = []
    for url in CANDIDATE_URLS:
        print(f"  Trying: {url}")
        html = fetch_html(url)
        if html:
            rows = parse(html, url)
            if rows:
                all_rows.extend(rows)
                print(f"  OK: SG data found at: {url}")
                break
    if not all_rows:
        print("  WARN: SG historical feed not available on public pages.")
        print(f"  Register free at: {config.SG_REGISTRATION_URL}")
        return pd.DataFrame()
    df = pd.DataFrame(all_rows)
    upsert_df("sg_spot", df, ["date", "index_name"])
    Path("data").mkdir(exist_ok=True)
    df.to_csv(config.SG_SPOT_CSV, index=False)
    print(f"OK: SG CTA {len(df)} rows")
    return df


if __name__ == "__main__":
    run()
