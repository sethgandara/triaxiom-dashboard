# data/fetchers/run_all.py - direct runner for Streamlit Cloud
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from data.storage import init_db

def run_all():
    init_db()
    results = {}
    try:
        from data.fetchers.etf_proxies import run as run_etf
        run_etf()
        results['etf_proxies'] = 'ok'
    except Exception as e:
        results['etf_proxies'] = f'error: {str(e)[:100]}'
    try:
        from data.fetchers.btop50 import run as run_btop
        run_btop()
        results['btop50'] = 'ok'
    except Exception as e:
        results['btop50'] = f'error: {str(e)[:100]}'
    try:
        from data.fetchers.barclay_cta import run as run_barclay
        run_barclay()
        results['barclay_cta'] = 'ok'
    except Exception as e:
        results['barclay_cta'] = f'error: {str(e)[:100]}'
    try:
        from data.fetchers.sg_cta import run as run_sg
        run_sg()
        results['sg_cta'] = 'ok'
    except Exception as e:
        results['sg_cta'] = f'error: {str(e)[:100]}'
    return results
