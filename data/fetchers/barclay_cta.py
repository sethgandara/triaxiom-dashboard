# data/fetchers/barclay_cta.py - Barclay CTA current month + YTD

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


def fetch_html():
    time.sleep(config.SCRAPE_DELAY_SECS)
    r = requests.get(config.BARCLAY_CTA_URL, headers=config.HEADERS, timeout=config.REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def parse(html):
    rows = []
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")
    try:
        tables = pd.read_html(StringIO(html))
    except:
        print("  WARN: No HTML tables on Barclay CTA page")
        return pd.DataFrame()
    print(f"  Found {len(tables)} tables")
    for t in tables:
        text = " ".join(map(str, t.astype(str).fillna("").values.flatten()))
        for idx_name in config.BARCLAY_TARGET_INDICES:
            if idx_name not in text:
                continue
            for _, row in t.iterrows():
                joined = " | ".join(map(str, row.tolist()))
                if idx_name not in joined:
                    continue
                nums = [float(x.replace("%", "")) for x in re.findall(r"-?\d+(?:\.\d+)?%", joined)]
                if len(nums) >= 2:
                    rows.append({"index_name": idx_name, "month": month, "ror_pct": nums[0], "ytd_pct": nums[1], "as_of_date": today})
                    print(f"  OK: {idx_name}: ROR={nums[0]}%, YTD={nums[1]}%")
    if not rows:
        print("  WARN: Barclay CTA index rows not found. May be JS-rendered.")
    return pd.DataFrame(rows)


def run():
    init_db()
    print("Fetching Barclay CTA...")
    html = fetch_html()
    df = parse(html)
    if not df.empty:
        upsert_df("barclay_cta", df, ["index_name", "month"])
        Path("data").mkdir(exist_ok=True)
        df.to_csv(config.BARCLAY_CTA_CSV, index=False)
        print(f"OK: Barclay CTA {len(df)} rows")
    return df


if __name__ == "__main__":
    run()
