# data/fetchers/gsheets_manual.py - Phase 2: Google Sheets reader
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import json, os, pandas as pd
GSHEET_ID = os.environ.get("GSHEET_ID", "")
CREDS_JSON = os.environ.get("GOOGLE_SHEETS_CREDS", "")
def _client():
    import gspread
    from google.oauth2.service_account import Credentials
    if not CReDS_JSON or not GSHEET_ID: raise EnvironmentError("Set GOOGLE_SHEETS_CREDS and GSHEET_ID"
  
creds = Credentials.from_service_account_info(json.loads(CREDS_JSON), scopes=["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)
def fetch_sg_manual():
    try: return pd.DataFrame(_client().open_by_key(GSHEET_ID).worksheet("SG_CTA_Manual").get_all_records())
    except Exception as e: print(f"SG manual: {e}"); return pd.DataFrame()
def fetch_peer_programs():
    try: return pd.DataFrame(_client().open_by_key(GSHEET_ID).worksheet("Peer_Programs").get_all_records())
    except Exception as e: print(f"Peer programs: {e}"); return pd.DataFrame()
