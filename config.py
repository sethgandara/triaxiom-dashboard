# config.py — Single source of truth. Edit here; never hardcode elsewhere.

BTOP50_URL = (
    "https://portal.barclayhedge.com/cgi-bin/indices/displayHfIndex.cgi"
    "?indexCat=Barclay-Investable-Benchmarks&indexName=BTOP50-Index"
)
BARCLAY_CTA_URL = (
    "https://portal.barclayhedge.com/cgi-bin/indices/displayIndices.cgi?indexID=cta"
)
BARCLAY_CTA_DETAIL_URL = (
    "https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi"
    "?indexCat=Barclay-CTA-Indices&indexName=Barclay-CTA-Index"
)
SG_LANDING_URL = (
    "https://wholesale.banking.societegenerale.com/en/prime-services-indices/"
)
SG_TISCREEN_URL = (
    "https://wholesale.banking.societegenerale.com/fileadmin/indices_feeds/ti_screen/index.html"
)
SG_REGISTRATION_URL = "https://analytics.sgmarkets.com"
ETF_TICKERS = ["DBMF", "KMLM", "CTA"]
ETF_LABELS = {
    "DBMF": "iM DBi Managed Futures (DBMF)",
    "KMLM": "KFA Mount Lucas Trend (KMLM)",
    "CTA":  "Simplify Managed Futures (CTA)",
}
ETF_NOTE = "\u26a0\ufe0f ETF proxies \u2014 not actual CTA indices. Use for directional context only."
BARCLAY_TARGET_INDICES = ["Barclay CTA Index", "Barclay Systematic Traders Index"]
SG_TARGET_INDICES = ["SG CTA Index", "SG Trend Index"]
SCRAPE_DELAY_SECS = 2
QEQUEST_TIMEOUT = 30
HEADERS = {
    "User-Agent": "Mozilla/5.0 (triaxiom-benchmark-dashboard/1.0; contact: seth@early.vc)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://portal.barclayhedge.com/",
}
DATA_DIR = "data"
BTOP50_CSV = "data/btop50_monthly.csv"
BARCLAY_CTA_CSV = "data/barclay_cta_current.csv"
SG_SPOT_CSV = "data/sg_cta_spot.csv"
ETF_DAILY_CSV = "data/etf_daily.csv"
TRIAXIOM_CSV = "data/triaxiom_returns.csv"
PIPELINE_LOG = "data/pipeline_log.json"
STALENESS_WARNING_HOURS = 48
MANUAL_ENTRY_STALENESS_DAYS = 35
OURA_LOW_READINESS = 70
OURA_HIGH_READINESS = 85
FUND_NAME = "Triaxiom Global Symmetry Fund"
FUND_MANAGER = "Matt Lee"
COACH = "Seth Gandara"
FUND_INCEPTION = "2019-10-01"
COLOR_TRIAXIOM = "#2d3561"
color_BTOP50 = "#e67e22"
COLOR_BTOP50 = "#e67e22"
COLOR_DBMF = "#27ae60"
COLOR_KMLM = "#8e44ad"
COLOR_CTA_ETF = "#16a085"
COLOR_SG_CTA = "#c0392b"
COLOR_POSITIVE = "#27ae60"
COLOR_NEGATIVE = "#e74c3c"
COLOR_NEUTRAL = "#95a5a6"
REQUEST_TIMEOUT = 30
