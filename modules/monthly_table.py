# modules/monthly_table.py
# Module 2: Full monthly return comparison — Triaxiom vs BTOP50 vs Barclay CTA
# Replaces the basic table in app.py with a full side-by-side heat map grid

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config
from data.storage import read_table, get_staleness, load_triaxiom

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def _load_btop50() -> pd.DataFrame:
    df = read_table("btop50")
    if df.empty:
        path = Path(config.BTOP50_CSV)
        if path.exists():
            df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month_abbr"] = df["date"].dt.strftime("%b")
    return df


def _pivot(df: pd.DataFrame, value_col: str = "return_pct") -> pd.DataFrame:
    """Convert long-form to year × month pivot."""
    p = df.pivot_table(index="year", columns="month_abbr", values=value_col, aggfunc="first")
    p = p.reindex(columns=[m for m in MONTHS if m in p.columns])
    return p.sort_index(ascending=False)


def _annual_return(row: pd.Series) -> float:
    """Compound monthly returns into annual."""
    vals = row.dropna()
    if vals.empty:
        return np.nan
    return round((1 + vals / 100).prod() * 100 - 100, 2)


def _sharpe(series: pd.Series, rf: float = 0.0) -> float:
    """Annualized Sharpe from monthly returns."""
    clean = series.dropna()
    if len(clean) < 6:
        return np.nan
    excess = clean - rf / 12
    return round((excess.mean() / excess.std()) * np.sqrt(12), 2)


def _max_drawdown(series: pd.Series) -> float:
    """Max drawdown from monthly return series."""
    clean = series.dropna()
    if clean.empty:
        return np.nan
    cum = (1 + clean / 100).cumprod()
    roll_max = cum.cummax()
    dd = (cum - roll_max) / roll_max
    return round(dd.min() * 100, 2)


def _color_cell(val, vmin=-6, vmax=6):
    """Return inline CSS background + text color for a return value."""
    if pd.isna(val):
        return "background:#f8f8f8;color:#ccc;"
    if val > 0:
        intensity = min(val / vmax, 1.0)
        r = int(255 - intensity * 80)
        g = int(255 - intensity * 30)
        b = int(255 - intensity * 80)
        return f"background:rgba(39,174,96,{intensity*0.6:.2f});color:#0d4a1f;"
    else:
        intensity = min(abs(val) / abs(vmin), 1.0)
        return f"background:rgba(231,76,60,{intensity*0.6:.2f});color:#5a0a0a;"


def render_comparison_table():
    """Render the full side-by-side monthly comparison — Triaxiom vs BTOP50."""

    st.subheader("📋 Module 2: Monthly Return Comparison — Triaxiom vs BTOP50")

    # ── Load data ──────────────────────────────────────────────────────────
    triaxiom_df = load_triaxiom()
    btop50_df = _load_btop50()

    triaxiom_ok = not triaxiom_df.empty and "return_pct" in triaxiom_df.columns
    btop50_ok = not btop50_df.empty

    if not triaxiom_ok:
        st.warning("Triaxiom returns not loaded. Check data/triaxiom_returns.csv.")
        return
    if not btop50_ok:
        st.info("No BTOP50 data yet — click **Refresh All Data** in the sidebar.")

    # ── Stale warnings ─────────────────────────────────────────────────────
    btop50_info = get_staleness("btop50")
    if btop50_info["stale"] and btop50_ok:
        st.markdown(
            f'<div style="background:#fff3cd;border:1px solid #ffc107;padding:6px 12px;'
            f'border-radius:4px;font-size:0.83rem;">⚠️ BTOP50 data is '
            f'{btop50_info.get("hours_old","?")}h old — refresh recommended.</div>',
            unsafe_allow_html=True
        )

    # ── Prep Triaxiom ───────────────────────────────────────────────────────
    tdf = triaxiom_df[triaxiom_df["confirmed"].astype(str).str.upper() == "TRUE"].copy()
    tdf["year"] = tdf["date"].dt.year
    tdf["month_abbr"] = tdf["date"].dt.strftime("%b")
    t_pivot = _pivot(tdf)

    # ── Annual stats ────────────────────────────────────────────────────────
    t_pivot["Annual"] = t_pivot.apply(_annual_return, axis=1)

    # ── BTOP50 pivot ────────────────────────────────────────────────────────
    b_pivot = _pivot(btop50_df) if btop50_ok else pd.DataFrame()
    if not b_pivot.empty:
        b_pivot["Annual"] = b_pivot.apply(_annual_return, axis=1)

    # ── Align years ─────────────────────────────────────────────────────────
    all_years = sorted(set(t_pivot.index.tolist() +
                           (b_pivot.index.tolist() if not b_pivot.empty else [])),
                       reverse=True)

    # ── Spread pivot (Triaxiom - BTOP50) ────────────────────────────────────
    spread_pivot = pd.DataFrame(index=t_pivot.index)
    if not b_pivot.empty:
        for col in [m for m in MONTHS if m in t_pivot.columns and m in b_pivot.columns]:
            spread_pivot[col] = t_pivot[col] - b_pivot.reindex(t_pivot.index)[col]
        spread_pivot["Annual"] = t_pivot["Annual"] - b_pivot.reindex(t_pivot.index)["Annual"]

    # ── View toggle ─────────────────────────────────────────────────────────
    col_toggle, col_filter = st.columns([2, 2])
    with col_toggle:
        view = st.radio(
            "View",
            ["Side-by-Side", "Triaxiom Only", "BTOP50 Only", "Spread (TGS − BTOP50)"],
            horizontal=True,
        )
    with col_filter:
        year_range = st.select_slider(
            "Year range",
            options=sorted(all_years),
            value=(min(all_years), max(all_years)),
        )

    selected_years = [y for y in all_years if year_range[0] <= y <= year_range[1]]

    # ── Render ──────────────────────────────────────────────────────────────
    col_defs = [m for m in MONTHS if m in t_pivot.columns] + ["Annual"]

    def render_single(pivot_df, label, years, vmin=-8, vmax=8):
        rows_html = ""
        for y in years:
            if y not in pivot_df.index:
                continue
            row = pivot_df.loc[y]
            cells = f"<td style='font-weight:600;padding:4px 8px;'>{y}</td>"
            for col in col_defs:
                val = row.get(col, np.nan)
                style = _color_cell(val, vmin, vmax)
                display = f"{val:+.2f}%" if not pd.isna(val) else "—"
                fw = "font-weight:700;" if col == "Annual" else ""
                cells += f"<td style='{style}{fw}padding:4px 6px;text-align:center;font-size:0.82rem;'>{display}</td>"
            rows_html += f"<tr>{cells}</tr>"

        headers = "".join(
            f"<th style='padding:4px 6px;text-align:center;background:#2d3561;color:white;"
            f"font-size:0.78rem;{'border-left:2px solid #fff;' if c=='Annual' else ''}'>{c}</th>"
            for c in ["Year"] + col_defs
        )
        table_html = (
            f"<div style='font-size:0.8rem;font-weight:600;color:#2d3561;margin-bottom:4px;'>{label}</div>"
            f"<div style='overflow-x:auto;'>"
            f"<table style='border-collapse:collapse;width:100%;font-family:IBM Plex Sans,sans-serif;'>"
            f"<thead><tr>{headers}</tr></thead><tbody>{rows_html}</tbody></table></div>"
        )
        st.markdown(table_html, unsafe_allow_html=True)

    if view == "Triaxiom Only":
        render_single(t_pivot, "Triaxiom Global Symmetry Fund — Net Monthly Returns", selected_years)

    elif view == "BTOP50 Only":
        if b_pivot.empty:
            st.info("Fetch BTOP50 data first.")
        else:
            render_single(b_pivot, "BTOP50 CTA Index — Monthly Returns", selected_years)

    elif view == "Spread (TGS − BTOP50)":
        if spread_pivot.empty:
            st.info("Need BTOP50 data to compute spread.")
        else:
            render_single(spread_pivot, "Spread: Triaxiom − BTOP50 (positive = TGS outperforms)", selected_years, vmin=-5, vmax=5)

    else:  # Side-by-Side
        t_col, b_col = st.columns(2)
        with t_col:
            render_single(t_pivot, "Triaxiom Global Symmetry Fund", selected_years)
        with b_col:
            if not b_pivot.empty:
                render_single(b_pivot, "BTOP50 CTA Index", selected_years)
            else:
                st.info("Fetch BTOP50 to compare.")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Summary Stats ────────────────────────────────────────────────────────
    with st.expander("📊 Risk-Adjusted Statistics (Since Inception)"):
        all_t = tdf["return_pct"].dropna()
        stats_data = {
            "Metric": [
                "Annualized Return", "Annualized Volatility",
                "Sharpe Ratio (0% rf)", "Max Drawdown",
                "% Positive Months", "Avg Up Month", "Avg Down Month",
                "Best Month", "Worst Month",
            ],
            "Triaxiom": [
                f"{(1 + all_t/100).prod() ** (12/len(all_t)) * 100 - 100:.2f}%",
                f"{all_t.std() * np.sqrt(12):.2f}%",
                f"{_sharpe(all_t):.2f}",
                f"{_max_drawdown(all_t):.2f}%",
                f"{(all_t > 0).mean() * 100:.0f}%",
                f"{all_t[all_t > 0].mean():+.2f}%",
                f"{all_t[all_t < 0].mean():+.2f}%",
                f"{all_t.max():+.2f}%",
                f"{all_t.min():+.2f}%",
            ],
        }

        if btop50_ok and not b_pivot.empty:
            all_b = btop50_df["return_pct"].dropna()
            # Align to same date range as Triaxiom
            btop50_aligned = btop50_df[btop50_df["date"] >= tdf["date"].min()]["return_pct"].dropna()
            stats_data["BTOP50 (aligned)"] = [
                f"{(1 + btop50_aligned/100).prod() ** (12/len(btop50_aligned)) * 100 - 100:.2f}%",
                f"{btop50_aligned.std() * np.sqrt(12):.2f}%",
                f"{_sharpe(btop50_aligned):.2f}",
                f"{_max_drawdown(btop50_aligned):.2f}%",
                f"{(btop50_aligned > 0).mean() * 100:.0f}%",
                f"{btop50_aligned[btop50_aligned > 0].mean():+.2f}%",
                f"{btop50_aligned[btop50_aligned < 0].mean():+.2f}%",
                f"{btop50_aligned.max():+.2f}%",
                f"{btop50_aligned.min():+.2f}%",
            ]
            if not spread_pivot.empty:
                spread_series = spread_pivot.drop(columns=["Annual"], errors="ignore").stack().dropna()
                stats_data["Spread (TGS − BTOP50)"] = [
                    f"{spread_series.mean() * 12:.2f}% ann.",
                    "—", "—", "—",
                    f"{(spread_series > 0).mean() * 100:.0f}% months TGS leads",
                    f"{spread_series[spread_series > 0].mean():+.2f}%",
                    f"{spread_series[spread_series < 0].mean():+.2f}%",
                    f"{spread_series.max():+.2f}%",
                    f"{spread_series.min():+.2f}%",
                ]

        st.dataframe(pd.DataFrame(stats_data).set_index("Metric"), use_container_width=True)

        st.caption(
            "Source: Triaxiom tearsheet TGS-pub-op-202509 (Table 1) · Pro-forma net of 1.75% mgmt + 20% incentive · "
            "BTOP50 from BarclayHedge portal · Past performance is not indicative of future results."
        )

    # ── Cumulative Growth Chart ───────────────────────────────────────────────
    with st.expander("📈 Cumulative Growth Chart (Since Inception)"):
        tdf_sorted = tdf.sort_values("date")
        fig = go.Figure()

        # Triaxiom cumulative
        t_cum = (1 + tdf_sorted["return_pct"] / 100).cumprod() * 100
        fig.add_trace(go.Scatter(
            x=tdf_sorted["date"], y=t_cum,
            name="Triaxiom (net)", line=dict(color=config.COLOR_TRIAXIOM, width=2.5),
            hovertemplate="<b>Triaxiom</b><br>%{x|%b %Y}: %{y:.1f}<extra></extra>"
        ))

        # BTOP50 aligned
        if btop50_ok and not btop50_df.empty:
            b_aligned = btop50_df[btop50_df["date"] >= tdf_sorted["date"].min()].sort_values("date")
            b_cum = (1 + b_aligned["return_pct"] / 100).cumprod() * 100
            fig.add_trace(go.Scatter(
                x=b_aligned["date"], y=b_cum,
                name="BTOP50", line=dict(color=config.COLOR_BTOP50, width=1.8, dash="dash"),
                hovertemplate="<b>BTOP50</b><br>%{x|%b %Y}: %{y:.1f}<extra></extra>"
            ))

        fig.update_layout(
            title="Cumulative Growth — $100 invested at inception (Aug 2019)",
            yaxis_title="Cumulative Value ($)",
            xaxis_title="",
            plot_bgcolor="white",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Sans"),
            height=380,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            yaxis=dict(gridcolor="#f0f0f0", tickprefix="$"),
            xaxis=dict(gridcolor="#f0f0f0"),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "⚠️ BTOP50 is the closest free benchmark for a CTA peer universe. "
            "Triaxiom is a relative-value strategy; BTOP50 is trend-dominated. "
            "Use for context, not direct comparison."
        )
