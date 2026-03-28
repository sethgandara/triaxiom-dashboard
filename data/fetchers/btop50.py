# data/fetchers/btop50.py — BTOP50 full monthly history scraper
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import time, requests, pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
from pathlib import Path
import config
from data.storage import init_db, upsert_df
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
def fetch_html():
    time.sleep(config.SCRAPE_DELAY_SECS)
    r = requests.get(config.BTOP50_URL, headers=config.HEADERS, timeout=config.REQUEST_TIMEOUT)
    r.raise_for_status(); return r.text
def find_monthly_table(html):
    soup = BeautifulSoup(html, "html.parser")
    for i, table in enumerate(soup.find_all("table")):
        try:
            df = pd.read_html(StringIO(str(table)))[0]
            if isinstance(df.columns, pd.MultiIndex): df.columns = [' '.join(map(str,c)).strip() for c in df.columns]
            cols = [str(c).strip() for c in df.columns]
            if sum(1 for m in MONTHS if any(m in c for c in cols)) >= 6: df.columns=cols; return df
        except: pass
    raise ValueError("No BTOP50 monthly table found")
def normalize(df):
    records = []
    for _, row in df.iterrows():
        y = str(row.iloc[0]).strip().replace(".0","")
        if not y.isdigit() or len(y)!=4: continue
        year=int(y)
        for i_m, m in enumerate(MONTHS):
            col=Next((c for c in df.columns if c.strip().startswith(m)), None)
            if not col: continue
            v=row[col]
            if pd.isna(v) or str(v).strip() in ("","-","N/A","nan"): continue
            try: records.append({"date":f"{year}-{i_m+1:02d}-01","return_pct":float(str(v).replace("*","").replace("%","").strip()),"estimated":int("*" in str(v))})
            except: pass
    return pd.DataFrame(records)
def run():
    init_db(); html=fetch_html(); df=normalize(find_monthly_table(html))
    if not df.empty: upsert_df("btop50",df,["date"]); Path("data").mkdir(exist_ok=True); df.to_csv(config.BTOP50_CSV,index=False); print(f"✅ BTOP50: {len(df)} rows")
    return df
if __name__=="__main__": run()
