# app.py — Triaxiom CTA Benchmark Dashboard
# Focus: Triaxiom vs CTA peer benchmarks — monthly, YTD, annual, spread
# Deploy: streamlit run app.py  |  EC2: proverbsinvestor.com/CTA-dashboard

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta
import sys, os, json

sys.path.insert(0, os.path.dirname(__file__))
import config
from data.storage import init_db, read_table, get_staleness, load_triaxiom

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Triaxiom · CTA Benchmark Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
h1, h2, h3 { font-family: 'Playfair Display', serif; color: #1e2a4a; }
.stApp { background-color: #f7f4ee; }

.top-bar {
    background: #1e2a4a;
    color: white;
    padding: 20px 32px 16px;
    margin: -1rem -1rem 0;
    display: flex;
    align-items: baseline;
    gap: 20px;
}
.top-bar .fund-name {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    font-weight: 700;
}
.top-bar .sub {
    font-size: 0.82rem;
    opacity: 0.6;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.top-bar .as-of {
    margin-left: auto;
    font-size: 0.8rem;
    opacity: 0.55;
    font-family: 'IBM Plex Mono', monospace;
}

.kpi-row { display: flex; gap: 12px; margin: 20px 0 8px; flex-wrap: wrap; }
.kpi {
    background: white;
    border-top: 3px solid #1e2a4a;
    padding: 14px 20px;
    border-radius: 4px;
    flex: 1; min-width: 130px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.kpi .label { font-size: 10px; letter-spacing: 2px; text-transform: uppercase; color: #888; margin-bottom: 4px; }
.kpi .value { font-size: 1.55rem; font-weight: 700; font-family: 'Playfair Display', serif; color: #1e2a4a; }
.kpi .sub-value { font-size: 11px; color: #aaa; margin-top: 2px; }
.kpi.positive .value { color: #1a7a4a; }
.kpi.negative .value { color: #c0392b; }
.kpi.accent { border-top-color: #c9a84c; }

.section-label {
    font-size: 10px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #c9a84c;
    font-weight: 600;
    margin: 28px 0 10px;
}

.bench-note {
    background: #eef6ff;
    border-left: 3px solid #3498db;
    padding: 8px 14px;
    font-size: 12px;
    color: #2c3e50;
    border-radius: 0 4px 4px 0;
    margin-bottom: 16px;
}

.stale-warn {
    background: #fff8e6;
    border: 1px solid #f0c040;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 12px;
    margin-bottom: 10px;
}

.last-updated {
    font-size: 11px;
    color: #bbb;
    font-family: 'IBM Plex Mono', monospace;
    text-align: right;
    margin-top: -8px;
    margin-bottom: 8px;
}

table.ret-grid {
    border-collapse: collapse;
    width: 100%;
    font-size: 12px;
    font-family: 'IBM Plex Mono', monospace;
}
</style>
""", unsafe_allow_html=True)

# ─── INIT ─────────────────────────────────────────────────────────────────────
init_db()

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def load_btop50():
    df = read_table("btop50")
    if df.empty:
        p = Path(config.BTOP50_CSV)
        if p.exists(): df = pd.read_csv(p)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df

def load_etf():
    df = read_table("etf_daily")
    if df.empty:
        p = Path(config.ETF_DAILY_CSV)
        if p.exists(): df = pd.read_csv(p)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df

def load_sg():
    df = read_table("sg_spot")
    if df.empty:
        p = Path(config.SG_SPOT_CSV)
        if p.exists(): df = pd.read_csv(p)
    return df

def load_barclay_cta():
    df = read_table("barclay_cta")
    if df.empty:
        p = Path(config.BARCLAY_CTA_CSV)
        if p.exists(): df = pd.read_csv(p)
    return df

def pivot_monthly(df, value_col="return_pct"):
    df = df.copy()
    df["year"] = pd.to_datetime(df["date"]).dt.year
    df["mon"]  = pd.to_datetime(df["date"]).dt.strftime("%b")
    p = df.pivot_table(index="year", columns="mon", values=value_col, aggfunc="first")
    return p.reindex(columns=[m for m in MONTHS if m in p.columns]).sort_index(ascending=False)

def annual_ret(row):
    v = row.dropna()
    return round((1 + v/100).prod()*100 - 100, 2) if len(v) else np.nan

def sharpe(series):
    s = series.dropna()
    if len(s) < 6: return np.nan
    return round((s.mean()/s.std())*np.sqrt(12), 2)

def max_dd(series):
    s = series.dropna()
    if s.empty: return np.nan
    cum = (1+s/100).cumprod()
    return round(((cum - cum.cummax())/cum.cummax()).min()*100, 2)

def cell_style(val, vmin=-6, vmax=6):
    if pd.isna(val): return "background:#f5f5f5;color:#ccc;"
    if val > 0:
        i = min(val/vmax, 1.0)
        return f"background:rgba(39,174,96,{i*0.55:.2f});color:#0b3d20;font-weight:500;"
    else:
        i = min(abs(val)/abs(vmin), 1.0)
        return f"background:rgba(192,57,43,{i*0.55:.2f});color:#4a0a0a;font-weight:500;"

def render_grid(pivot_df, label, years, accent_col=None):
    cols = [m for m in MONTHS if m in pivot_df.columns] + ["YTD"]
    pivot_with_ytd = pivot_df.copy()
    pivot_with_ytd["YTD"] = pivot_with_ytd.apply(annual_ret, axis=1)

    hdr = "".join(
        f"<th style='padding:6px 8px;background:#1e2a4a;color:white;font-size:10px;"
        f"letter-spacing:0.5px;text-align:center;"
        f"{'border-left:2px solid rgba(201,168,76,0.6);' if c=='YTD' else ''}'>{c}</th>"
        for c in ["Year"] + cols
    )
    rows_html = ""
    for y in years:
        if y not in pivot_with_ytd.index: continue
        row = pivot_with_ytd.loc[y]
        tds = f"<td style='padding:5px 8px;font-weight:700;font-size:12px;white-space:nowrap;'>{y}</td>"
        for c in cols:
            v = row.get(c, np.nan)
            s = cell_style(v, -8 if c=="YTD" else -6, 8 if c=="YTD" else 6)
            extra = "border-left:2px solid rgba(201,168,76,0.4);" if c=="YTD" else ""
            disp = f"{v:+.2f}%" if not pd.isna(v) else "—"
            tds += f"<td style='{s}{extra}padding:5px 6px;text-align:center;font-size:11px;font-family:IBM Plex Mono,monospace;'>{disp}</td>"
        rows_html += f"<tr>{tds}</tr>"

    st.markdown(
        f"<div style='font-size:11px;font-weight:600;color:#1e2a4a;margin-bottom:4px;'>{label}</div>"
        f"<div style='overflow-x:auto;border-radius:6px;border:1px solid #e0ddd6;'>"
        f"<table style='border-collapse:collapse;width:100%;font-family:IBM Plex Mono,monospace;'>"
        f"<thead><tr>{hdr}</tr></thead><tbody>{rows_html}</tbody></table></div>",
        unsafe_allow_html=True
    )

# ─── LOAD ALL DATA ─────────────────────────────────────────────────────────────
tdf_all  = load_triaxiom()
btop50   = load_btop50()
etf      = load_etf()
sg       = load_sg()
barclay  = load_barclay_cta()

tdf = tdf_all[tdf_all.get("confirmed", pd.Series(["TRUE"]*len(tdf_all), index=tdf_all.index)).astype(str).str.upper() == "TRUE"].copy() if not tdf_all.empty else pd.DataFrame()

# ─── KPI STRIP ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="top-bar">'
    '<span class="fund-name">Triaxiom Global Symmetry Fund</span>'
    '<span class="sub">Global Futures · Market Neutral · Systematic CTA</span>'
    f'<span class="as-of">as of {datetime.now().strftime("%B %d, %Y")}</span>'
    '</div>',
    unsafe_allow_html=True
)

# Compute KPIs from confirmed data
if not tdf.empty and "return_pct" in tdf.columns:
    tdf_s = tdf.sort_values("date")
    ret   = tdf_s["return_pct"].dropna()

    this_year  = tdf_s[tdf_s["date"].dt.year == datetime.now().year]["return_pct"].dropna()
    ytd        = round((1+this_year/100).prod()*100-100, 2) if len(this_year) else None
    last_month = ret.iloc[-1] if len(ret) else None
    sharpe_val = sharpe(ret)
    mdd_val    = max_dd(ret)
    cum_val    = round((1+ret/100).prod()*100-100, 2)

    ytd_class  = "positive" if ytd and ytd > 0 else "negative"
    lm_class   = "positive" if last_month and last_month > 0 else "negative"
    cum_class  = "positive" if cum_val > 0 else "negative"

    latest_date = tdf_s["date"].max().strftime("%b %Y")

    kpis = [
        ("YTD Return",    f"{ytd:+.2f}%" if ytd is not None else "—",    f"{datetime.now().year}", ytd_class, ""),
        ("Last Month",    f"{last_month:+.2f}%" if last_month is not None else "—", latest_date, lm_class, ""),
        ("Since Inception",f"{cum_val:+.2f}%", "Aug 2019", cum_class, ""),
        ("Sharpe Ratio",  f"{sharpe_val:.2f}" if sharpe_val else "—",    "since inception", "", "accent"),
        ("Max Drawdown",  f"{mdd_val:.2f}%"  if mdd_val else "—",        "since inception", "negative", "accent"),
        ("Months of Data",f"{len(ret)}",                                  f"{tdf_s['date'].min().strftime('%b %Y')} →", "", ""),
    ]
    kpi_html = '<div class="kpi-row">'
    for label, val, sub, cls, extra_cls in kpis:
        kpi_html += (
            f'<div class="kpi {cls} {extra_cls}">'
            f'<div class="label">{label}</div>'
            f'<div class="value">{val}</div>'
            f'<div class="sub-value">{sub}</div>'
            f'</div>'
        )
    kpi_html += "</div>"
    st.markdown(kpi_html, unsafe_allow_html=True)
else:
    st.warning("No confirmed Triaxiom return data found. Check data/triaxiom_returns.csv.")

# ─── SIDEBAR — REFRESH + STATUS ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Data Status")
    status_map = {
        "BTOP50":      ("btop50",      not btop50.empty),
        "ETF Proxies": ("etf_daily",   not etf.empty),
        "Barclay CTA": ("barclay_cta", not barclay.empty),
        "SG CTA":      ("sg_spot",     not sg.empty),
    }
    for label, (source, has_data) in status_map.items():
        info = get_staleness(source)
        icon = "🟢" if (has_data and not info["stale"]) else ("🟡" if has_data else "🔴")
        age  = f"{info.get('hours_old','?')}h ago" if info.get('hours_old') else "never"
        st.markdown(f"{icon} **{label}** · {info.get('rows',0)} rows · {age}")

    st.divider()
    if st.button("🔄 Refresh Benchmarks", type="primary", use_container_width=True):
        with st.spinner("Fetching..."):
            import subprocess
            r = subprocess.run([sys.executable, "pipeline_runner.py"], capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            st.success("Done!")
        else:
            st.error(r.stderr[:300])
        st.rerun()

    st.divider()
    st.markdown("**Manual SG Entry**")
    sg_date  = st.date_input("Week of", value=datetime.now(), key="sg_d")
    sg_mtd   = st.number_input("SG CTA MTD %",  value=0.0, step=0.01, format="%.2f")
    sg_ytd   = st.number_input("SG CTA YTD %",  value=0.0, step=0.01, format="%.2f")
    tgs_mtd  = st.number_input("Triaxiom MTD %", value=0.0, step=0.01, format="%.2f")
    if st.button("Save Entry", use_container_width=True):
        from data.storage import upsert_df
        upsert_df("sg_spot", pd.DataFrame([{
            "date": str(sg_date), "index_name": "SG CTA Index (manual)",
            "mtd_pct": sg_mtd, "ytd_pct": sg_ytd, "daily_return_pct": None,
            "source_url": "manual_entry",
        }]), ["date","index_name"])
        st.success("Saved.")
        st.rerun()

# ─── TAB NAVIGATION ───────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Monthly Returns",
    "📈 Cumulative & Spread",
    "📊 Annual Comparison",
    "🔍 Peer Benchmarks",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MONTHLY RETURN GRIDS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-label">Monthly Net Returns — Heat Map Grid</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="bench-note">Triaxiom is a <strong>relative-value CTA</strong>, not a trend-follower. '
        'BTOP50 is trend-dominated — use for CTA peer context, not as a direct comparable. '
        'Green = positive month, Red = negative. Intensity scales with magnitude.</div>',
        unsafe_allow_html=True
    )

    # Year filter
    if not tdf.empty:
        all_years = sorted(tdf["date"].dt.year.unique(), reverse=True)
        yr_range  = st.select_slider("Year range", options=sorted(all_years), value=(min(all_years), max(all_years)), key="yr1")
        sel_years = [y for y in all_years if yr_range[0] <= y <= yr_range[1]]
    else:
        sel_years = list(range(2019, datetime.now().year+1))

    view = st.radio("Compare", ["Side-by-Side", "Spread (TGS − BTOP50)", "Triaxiom Only", "BTOP50 Only"],
                    horizontal=True, key="v1")

    # Build pivots
    t_pivot = pivot_monthly(tdf) if not tdf.empty else pd.DataFrame()
    b_pivot = pivot_monthly(btop50) if not btop50.empty else pd.DataFrame()

    if view == "Triaxiom Only":
        if not t_pivot.empty:
            render_grid(t_pivot, "Triaxiom Global Symmetry Fund — Net Monthly Returns (pro-forma, net of 1.75% mgmt + 20% incentive)", sel_years)
        else:
            st.info("No Triaxiom data.")

    elif view == "BTOP50 Only":
        if not b_pivot.empty:
            render_grid(b_pivot, "BTOP50 CTA Index — Monthly Returns", sel_years)
        else:
            st.info("Fetch BTOP50 data via sidebar Refresh.")

    elif view == "Spread (TGS − BTOP50)":
        if not t_pivot.empty and not b_pivot.empty:
            spread = pd.DataFrame(index=t_pivot.index)
            for m in MONTHS:
                if m in t_pivot.columns and m in b_pivot.columns:
                    spread[m] = t_pivot[m] - b_pivot.reindex(t_pivot.index)[m]
            render_grid(spread, "Spread: Triaxiom minus BTOP50 (positive = Triaxiom outperforms that month)", sel_years)
        else:
            st.info("Need both Triaxiom and BTOP50 data to show spread.")

    else:  # Side-by-Side
        c1, c2 = st.columns(2)
        with c1:
            if not t_pivot.empty:
                render_grid(t_pivot, "Triaxiom Global Symmetry Fund", sel_years)
            else:
                st.info("No Triaxiom data.")
        with c2:
            if not b_pivot.empty:
                render_grid(b_pivot, "BTOP50 CTA Index", sel_years)
            else:
                st.info("Refresh to fetch BTOP50.")

    st.caption("Source: Triaxiom — TGS-pub-op-202509 Table 1 (pro-forma net) · BTOP50 — BarclayHedge portal · Past performance ≠ future results.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CUMULATIVE & SPREAD CHART
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-label">Cumulative Performance & Benchmark Spread</div>', unsafe_allow_html=True)

    fig = go.Figure()
    if not tdf.empty:
        ts = tdf.sort_values("date")
        cum_t = (1 + ts["return_pct"]/100).cumprod() * 100
        fig.add_trace(go.Scatter(
            x=ts["date"], y=cum_t,
            name="Triaxiom (net)", line=dict(color="#1e2a4a", width=2.5),
            hovertemplate="<b>Triaxiom</b> %{x|%b %Y}<br>$%{y:.1f}<extra></extra>"
        ))

    if not btop50.empty:
        bs = btop50[btop50["date"] >= (tdf["date"].min() if not tdf.empty else pd.Timestamp("2019-08-01"))].sort_values("date")
        cum_b = (1 + bs["return_pct"]/100).cumprod() * 100
        fig.add_trace(go.Scatter(
            x=bs["date"], y=cum_b,
            name="BTOP50", line=dict(color="#e67e22", width=1.8, dash="dot"),
            hovertemplate="<b>BTOP50</b> %{x|%b %Y}<br>$%{y:.1f}<extra></extra>"
        ))

    if not etf.empty:
        for ticker, color, dash in [("DBMF","#27ae60","dash"),("KMLM","#8e44ad","dash"),("CTA","#16a085","dash")]:
            te = etf[etf["ticker"]==ticker].sort_values("date")
            if not te.empty and not tdf.empty:
                te = te[te["date"] >= tdf["date"].min()]
                cum_e = (1 + te["daily_return_pct"].fillna(0)/100).cumprod() * 100
                fig.add_trace(go.Scatter(
                    x=te["date"], y=cum_e,
                    name=f"{ticker} (ETF proxy)", line=dict(color=color, width=1.2, dash=dash),
                    opacity=0.6,
                    hovertemplate=f"<b>{ticker}</b> %{{x|%b %Y}}<br>$%{{y:.1f}}<extra></extra>"
                ))

    fig.update_layout(
        title="Cumulative Growth — $100 invested at Triaxiom inception (Aug 2019)",
        yaxis=dict(title="Cumulative Value ($)", gridcolor="#ede9e0", tickprefix="$"),
        xaxis=dict(gridcolor="#ede9e0"),
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans"), height=420,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Rolling 12-month spread bar chart
    if not tdf.empty and not btop50.empty:
        st.markdown('<div class="section-label" style="margin-top:12px;">Rolling 12-Month Spread — Triaxiom vs BTOP50</div>', unsafe_allow_html=True)

        ts2 = tdf.sort_values("date").set_index("date")["return_pct"]
        bs2 = btop50.sort_values("date").set_index("date")["return_pct"]

        # Monthly resample both to first-of-month
        ts2.index = ts2.index.to_period("M").to_timestamp()
        bs2.index = bs2.index.to_period("M").to_timestamp()

        aligned = pd.DataFrame({"tgs": ts2, "btop": bs2}).dropna()
        if len(aligned) >= 12:
            roll_t = aligned["tgs"].rolling(12).apply(lambda x: (1+x/100).prod()*100-100)
            roll_b = aligned["btop"].rolling(12).apply(lambda x: (1+x/100).prod()*100-100)
            spread_roll = (roll_t - roll_b).dropna()

            fig2 = go.Figure(go.Bar(
                x=spread_roll.index,
                y=spread_roll.values,
                marker_color=["#1a7a4a" if v >= 0 else "#c0392b" for v in spread_roll.values],
                name="TGS − BTOP50 (12m rolling)",
                hovertemplate="%{x|%b %Y}<br>Spread: %{y:+.2f}%<extra></extra>"
            ))
            fig2.add_hline(y=0, line_color="#888", line_width=1)
            fig2.update_layout(
                title="Rolling 12-Month Return: Triaxiom minus BTOP50",
                yaxis=dict(title="Spread (%)", ticksuffix="%", gridcolor="#ede9e0"),
                xaxis=dict(gridcolor="#ede9e0"),
                plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="IBM Plex Sans"), height=300,
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.caption("ETF proxies (DBMF/KMLM/CTA) are daily CTA ETFs — not actual CTA indices. For directional context only.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ANNUAL COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-label">Annual Returns — Year by Year Comparison</div>', unsafe_allow_html=True)

    ANNUAL_EXPECTED = {2019:-4.91, 2020:3.21, 2021:1.30, 2022:-14.32, 2023:8.62, 2024:-3.98, 2025:9.01}

    # Build annual table
    rows = []
    years_ann = sorted(ANNUAL_EXPECTED.keys(), reverse=True)

    for y in years_ann:
        tgs_ann = ANNUAL_EXPECTED.get(y)

        # BTOP50 annual
        btop_ann = None
        if not btop50.empty:
            by = btop50[btop50["date"].dt.year == y]["return_pct"].dropna()
            if len(by): btop_ann = round((1+by/100).prod()*100-100, 2)

        # Barclay CTA
        barclay_ann = None
        if not barclay.empty:
            bdf = barclay.copy()
            bdf["year_col"] = bdf["month"].astype(str).str[:4].astype(float, errors="ignore")
            by2 = bdf[(bdf["year_col"]==y) & (bdf["index_name"]=="Barclay CTA Index")]
            if not by2.empty:
                barclay_ann = by2["ytd_pct"].dropna().iloc[-1] if "ytd_pct" in by2.columns else None

        spread = round(tgs_ann - btop_ann, 2) if (tgs_ann is not None and btop_ann is not None) else None

        rows.append({
            "Year": y,
            "Triaxiom (net)": tgs_ann,
            "BTOP50": btop_ann,
            "Spread (TGS−BTOP50)": spread,
            "Barclay CTA": barclay_ann,
        })

    ann_df = pd.DataFrame(rows).set_index("Year")

    # Render as styled HTML table
    def fmt(v, is_spread=False):
        if v is None or (isinstance(v, float) and np.isnan(v)): return "<td style='text-align:center;color:#ccc;'>—</td>"
        color = "#1a7a4a" if v > 0 else "#c0392b"
        bg = "rgba(39,174,96,0.12)" if v > 0 else "rgba(192,57,43,0.10)"
        bold = "font-weight:700;" if is_spread else ""
        return f"<td style='text-align:center;color:{color};background:{bg};{bold}padding:8px 12px;font-family:IBM Plex Mono,monospace;font-size:13px;'>{v:+.2f}%</td>"

    tbl = "<table style='border-collapse:collapse;width:100%;'>"
    tbl += "<thead><tr>"
    for col in ["Year","Triaxiom (net)","BTOP50","Spread (TGS−BTOP50)","Barclay CTA"]:
        bg = "#c9a84c" if col == "Spread (TGS−BTOP50)" else "#1e2a4a"
        tbl += f"<th style='background:{bg};color:white;padding:9px 12px;text-align:center;font-size:11px;letter-spacing:0.5px;'>{col}</th>"
    tbl += "</tr></thead><tbody>"

    for _, row in ann_df.iterrows():
        tbl += f"<tr><td style='padding:8px 12px;font-weight:700;font-size:13px;text-align:center;'>{int(row.name)}</td>"
        tbl += fmt(row["Triaxiom (net)"])
        tbl += fmt(row["BTOP50"])
        tbl += fmt(row["Spread (TGS−BTOP50)"], is_spread=True)
        tbl += fmt(row["Barclay CTA"])
        tbl += "</tr>"

    tbl += "</tbody></table>"
    st.markdown(f"<div style='overflow-x:auto;border-radius:6px;border:1px solid #e0ddd6;'>{tbl}</div>", unsafe_allow_html=True)

    # Annual bar chart
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    fig3 = go.Figure()
    ann_years = list(ANNUAL_EXPECTED.keys())

    fig3.add_trace(go.Bar(
        name="Triaxiom (net)",
        x=ann_years,
        y=[ANNUAL_EXPECTED[y] for y in ann_years],
        marker_color=config.COLOR_TRIAXIOM, opacity=0.9,
    ))
    if not btop50.empty:
        btop_vals = []
        for y in ann_years:
            by = btop50[btop50["date"].dt.year == y]["return_pct"].dropna()
            btop_vals.append(round((1+by/100).prod()*100-100, 2) if len(by) else None)
        fig3.add_trace(go.Bar(
            name="BTOP50",
            x=ann_years, y=btop_vals,
            marker_color=config.COLOR_BTOP50, opacity=0.75,
        ))

    fig3.update_layout(
        barmode="group",
        title="Annual Returns — Triaxiom vs BTOP50",
        yaxis=dict(title="Annual Return (%)", ticksuffix="%", gridcolor="#ede9e0", zeroline=True, zerolinecolor="#ccc"),
        xaxis=dict(dtick=1),
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans"), height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.caption("Triaxiom annual returns from TGS-pub-op-202509 (confirmed). BTOP50 computed from BarclayHedge monthly data. Past performance ≠ future results.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — PEER BENCHMARKS
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-label">Peer Benchmark Summary — Current Snapshot</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="bench-note">'
        '<strong>Benchmark universe:</strong> BTOP50 (full history, automated) · Barclay CTA Index (current month, automated) · '
        'SG CTA Index (manual entry) · ETF proxies DBMF / KMLM / CTA (daily, automated). '
        'SG full history requires free registration at <a href="https://analytics.sgmarkets.com" target="_blank">analytics.sgmarkets.com</a>.'
        '</div>',
        unsafe_allow_html=True
    )

    # Since-inception stats table
    st.markdown("#### Risk-Adjusted Statistics Since Inception (Aug 2019)")

    stat_rows = []
    if not tdf.empty:
        r = tdf["return_pct"].dropna()
        ann_r = round((1+r/100).prod()**(12/len(r))*100-100, 2) if len(r) else None
        stat_rows.append({
            "Series": "Triaxiom (net)", "Annualized Return": ann_r,
            "Ann. Vol": round(r.std()*np.sqrt(12), 2),
            "Sharpe": sharpe(r), "Max DD": max_dd(r),
            "% Pos Months": round((r>0).mean()*100, 0),
            "Avg Up": round(r[r>0].mean(), 2), "Avg Down": round(r[r<0].mean(), 2),
            "Source": "TGS-pub-op-202509",
        })

    if not btop50.empty:
        incept = tdf["date"].min() if not tdf.empty else pd.Timestamp("2019-08-01")
        r = btop50[btop50["date"] >= incept]["return_pct"].dropna()
        if len(r):
            ann_r = round((1+r/100).prod()**(12/len(r))*100-100, 2)
            stat_rows.append({
                "Series": "BTOP50", "Annualized Return": ann_r,
                "Ann. Vol": round(r.std()*np.sqrt(12), 2),
                "Sharpe": sharpe(r), "Max DD": max_dd(r),
                "% Pos Months": round((r>0).mean()*100, 0),
                "Avg Up": round(r[r>0].mean(), 2), "Avg Down": round(r[r<0].mean(), 2),
                "Source": "BarclayHedge portal",
            })

    if not etf.empty:
        incept = tdf["date"].min() if not tdf.empty else pd.Timestamp("2019-08-01")
        for ticker in config.ETF_TICKERS:
            te = etf[(etf["ticker"]==ticker) & (etf["date"] >= incept)]["daily_return_pct"].dropna()
            # Convert to monthly
            te_m = etf[(etf["ticker"]==ticker) & (etf["date"] >= incept)].set_index("date")["close"].resample("MS").last().pct_change().dropna() * 100
            if len(te_m) >= 6:
                ann_r = round((1+te_m/100).prod()**(12/len(te_m))*100-100, 2)
                stat_rows.append({
                    "Series": f"{ticker} ETF proxy", "Annualized Return": ann_r,
                    "Ann. Vol": round(te_m.std()*np.sqrt(12), 2),
                    "Sharpe": sharpe(te_m), "Max DD": max_dd(te_m),
                    "% Pos Months": round((te_m>0).mean()*100, 0),
                    "Avg Up": round(te_m[te_m>0].mean(), 2), "Avg Down": round(te_m[te_m<0].mean(), 2),
                    "Source": "yfinance",
                })

    if stat_rows:
        sdf = pd.DataFrame(stat_rows).set_index("Series")
        fmt_pct = lambda v: f"{v:+.2f}%" if pd.notna(v) else "—"
        for col in ["Annualized Return","Ann. Vol","Max DD","Avg Up","Avg Down"]:
            if col in sdf.columns:
                sdf[col] = sdf[col].apply(fmt_pct)
        for col in ["Sharpe","% Pos Months"]:
            if col in sdf.columns:
                sdf[col] = sdf[col].apply(lambda v: f"{v:.2f}" if pd.notna(v) else "—")
        st.dataframe(sdf.drop(columns=["Source"], errors="ignore"), use_container_width=True)

    # SG CTA manual snapshot
    if not sg.empty:
        st.markdown("#### SG CTA Index — Latest Snapshot (manual entry)")
        sg_disp = sg[["date","index_name","mtd_pct","ytd_pct"]].tail(10).copy()
        sg_disp.columns = ["Date","Index","MTD %","YTD %"]
        st.dataframe(sg_disp, use_container_width=True, hide_index=True)
    else:
        st.info("SG CTA data: use the sidebar to enter this week's MTD/YTD manually.")

    # Barclay CTA current
    if not barclay.empty:
        st.markdown("#### Barclay CTA Index — Current Month")
        st.dataframe(barclay[["index_name","month","ror_pct","ytd_pct"]].tail(6), use_container_width=True, hide_index=True)

    st.caption(
        "⚠️ ETF proxies are imperfect CTA benchmarks — use for directional context only. "
        "BTOP50 is trend-dominated; Triaxiom is relative-value. "
        "Past performance is not indicative of future results."
    )

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center;color:#bbb;font-size:11px;letter-spacing:1px;'>"
    "TRIAXIOM CAPITAL · INTERNAL USE ONLY · CONFIDENTIAL · FOR QUALIFIED ELIGIBLE PERSONS · "
    "PAST PERFORMANCE IS NOT INDICATIVE OF FUTURE RESULTS"
    "</div>",
    unsafe_allow_html=True
)
