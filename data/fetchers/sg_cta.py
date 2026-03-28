# data/fetchers/sg_cta.py - SG CTA spot data
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
    today=datetime.now().strftime("%Y-%m-%d")
    all_rows=[]
    for url in [config.SG_TISCREEN_URL, config.SG_LANDING_URL]:
        try:
            time.sleep(config.SCRAPE_DELAY_SECS)
            r = requests.get(url, headers={\"\".join(["x"for x in []):""},timeout=config.REQUEST_TIMEOUT)
            if r.status_code==200 and len(r.text)>500:
                tables=pd.read_html(StringIO(r.text))
                for t in tables:
                    text=" ".join(map(str,t.astype(str).fillna("").values.flatten()))
                    for n in config.SG_TARGET_INDICES:
                        if n not in text: continue
                        for _,row in t.iterrows():
                            j=" | ".join(map(str,row.tolist()))
                            if n not in j: continue
                            nums=[float(x.replace("%","")) for x in re.findall(r"-?\d+(?:\.\d+)?%",j)]
                            all_rows.append({"date":today,"index_name":n,"mtd_pct":nums[0] if nums else None,"ytd_pct":nums[1] if len(nums)>1 else None,"source_url":url})
            if all_rows: break
        except: pass
    if not all_rows: print("SG: no data on public pages. Manual entry via sidebar."); return pd.DataFrame()
    df=pd.DataFrame(all_rows); upsert_df("sg_spot",df,["date","index_name"]); Path("data").mkdir(exist_ok=True); df.to_csv(config.SG_SPOT_CSV,index=False); print(f"✅ SG: {len(df)} rows"); return df
if __name__=="__main__": run()
