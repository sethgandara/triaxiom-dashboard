# data/fetchers/etf_proxies.py - DBMF/KMLM/CTA via yfinance
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import yfinance as yf, pandas as pd
from pathlib import Path
import config
from data.storage import init_db, upsert_df
def fetch():
    print(f"Fetching ETF proxies: {config.ETF_TICKERS}...")
    return yf.download(config.ETF_TICKERS,period="max",interval="1d",group_by="ticker",auto_adjust=True,progress=False,threads=True)
def normalize(df):
    records = []
    for ticker in config.ETF_TICKERS:
        try:
            close = df[ticker]["Close"].dropna() if isinstance(df.columns,pd.MultiIndex) else df["Close"].dropna()
        except KeyError: continue
        if close.empty: continue
        dret = close.pct_change()
        for date, price in close.items():
            dr = dret.get(date, float("nan"))
            records.append({"date":date.strftime("%Y-%m-%d"),"ticker":ticker,"close":round(float(price),4),"daily_return_pct":round(float(dr)*100,4) if pd.notna(dr) else None})
        print(f"  ✅ {ticker}: {len(close)} rows")
    return pd.DataFrame(records)
def run():
    init_db(); df=normalize(fetch())
    if not df.empty: upsert_df("etf_daily",df,["date","ticker"]); Path("data").mkdir(exist_ok=True); df.to_csv(config.ETF_DAILY_CSV,index=False); print(f"✅ ETF: {len(df)} rows")
    return df
if __name__=="__main__": run()
