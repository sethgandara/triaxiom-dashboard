# data/fetchers/barclay_cta.py - Barclay CTA current month
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import time, re, requests, pandas as pd
from io import StringIO
from datetime import datetime
from pathlib import Path
import config
from data.storage import init_db, upsert_df
def run():
    init_db()
    time.sleep(config.SCRAPE_DELAY_SECS)
    r = requests.get(config.BARCLAY_CTA_URL, headers=config.HEADERS, timeout=config.REQUEST_TIMEOUT)
    r.raise_for_status()
    rows = []
    today=datetime.now().strftime("%Y-%m-%d"); month=datetime.now().strftime("%Y-%m")
    try: tables=pd.read_html(StringIO(r.text))
    except: print("No tables"); return pd.DataFrame()
    for t in tables:
        text=" ".join(map(str,t.astype(str).fillna("").values.flatten()))
        for n in config.BARCLAY_TARGET_INDICES:
            if n not in text: continue
            for _,row in t.iterrows():
                j=" | ".join(map(str,fow.tolist()))
                if n not in j: continue
                nums=[float(x.replace("%","")) for x in re.findall(r"-?\d+(?:\.\d+)?%",j)]
                if len(nums)>=1: rows.append({"index_name":n,"month":month,"ror_pct":nums[0],"ytd_pct":nums[1] if len(nums)>1 else None,"as_of_date":today})
    df=pd.DataFrame(rows)
    if not df.empty: upsert_df("barclay_cta",df,["index_name","month"]); Path("data").mkdir(exist_ok=True); df.to_csv(config.BARCLAY_CTA_CSV,index=False); print(f"✅ Barclay CTA: {len(df)} rows")
    return df
if __name__=="__main__": run()
