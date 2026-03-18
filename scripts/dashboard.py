#!/usr/bin/env python3

import pandas as pd
import numpy as np
import streamlit as st
from pathlib import Path

# =========================
# CONFIG
# =========================

st.set_page_config(layout="wide")

BASE = Path("docs/win/final_scores/results")

# =========================
# LOAD DATA
# =========================

def load_data(league):
    if league == "NBA":
        path = BASE / "nba/graded/NBA_final.csv"
    else:
        path = BASE / "ncaab/graded/NCAAB_final.csv"

    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)

    if "game_date" in df.columns:
        df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce")

    return df


# =========================
# BET OUTCOME → PNL
# =========================

def compute_pnl(df):
    df = df.copy()

    def profit(row):
        if row["bet_result"] == "Push":
            return 0

        # assume -110 baseline if no odds available
        odds = row.get("selected_odds", -110)

        if odds > 0:
            win_return = odds / 100
        else:
            win_return = 100 / abs(odds)

        return win_return if row["bet_result"] == "Win" else -1

    df["profit"] = df.apply(profit, axis=1)
    df["cum_profit"] = df["profit"].cumsum()

    return df


# =========================
# SIDEBAR FILTERS
# =========================

st.sidebar.title("Filters")

league = st.sidebar.selectbox("League", ["NBA", "NCAAB"])

df = load_data(league)

if df.empty:
    st.warning("No data found")
    st.stop()

# Market filter
markets = df["market_type"].unique().tolist()
selected_markets = st.sidebar.multiselect("Market Type", markets, default=markets)

# Edge filter
min_edge = float(df["selected_edge"].min())
max_edge = float(df["selected_edge"].max())

edge_range = st.sidebar.slider(
    "Edge Range",
    min_value=float(min_edge),
    max_value=float(max_edge),
    value=(float(min_edge), float(max_edge))
)

# Date filter
if "game_date" in df.columns:
    min_date = df["game_date"].min()
    max_date = df["game_date"].max()

    date_range = st.sidebar.date_input(
        "Date Range",
        [min_date, max_date]
    )

# Apply filters
df = df[df["market_type"].isin(selected_markets)]
df = df[(df["selected_edge"] >= edge_range[0]) & (df["selected_edge"] <= edge_range[1])]

if "game_date" in df.columns and len(date_range) == 2:
    df = df[(df["game_date"] >= pd.to_datetime(date_range[0])) &
            (df["game_date"] <= pd.to_datetime(date_range[1]))]

# Compute PnL
df = compute_pnl(df)

# =========================
# HEADER METRICS
# =========================

wins = (df["bet_result"] == "Win").sum()
losses = (df["bet_result"] == "Loss").sum()
pushes = (df["bet_result"] == "Push").sum()

total = wins + losses
win_rate = wins / total if total > 0 else 0

roi = df["profit"].sum() / len(df) if len(df) > 0 else 0

col1, col2, col3, col4 = st.columns(4)

col1.metric("Wins", wins)
col2.metric("Losses", losses)
col3.metric("Win Rate", f"{win_rate:.2%}")
col4.metric("ROI (per bet)", f"{roi:.2%}")

# =========================
# BANKROLL CURVE
# =========================

st.subheader("Bankroll Curve")

st.line_chart(df["cum_profit"])

# =========================
# EDGE vs WIN RATE
# =========================

st.subheader("Edge Calibration")

df["edge_bucket"] = pd.cut(df["selected_edge"], bins=[0,0.02,0.04,0.06,1])

edge_perf = (
    df.groupby("edge_bucket")["bet_result"]
    .value_counts(normalize=True)
    .unstack()
)

st.dataframe(edge_perf)

# =========================
# EV vs ACTUAL
# =========================

st.subheader("EV vs Actual")

if "selected_ev" in df.columns:
    ev_mean = df["selected_ev"].mean()
    actual = df["profit"].mean()

    col1, col2 = st.columns(2)
    col1.metric("Avg EV", f"{ev_mean:.4f}")
    col2.metric("Actual Return", f"{actual:.4f}")

# =========================
# EV DISTRIBUTION
# =========================

if "selected_ev" in df.columns:
    st.subheader("EV Distribution")
    st.histogram = st.bar_chart(df["selected_ev"])

# =========================
# KELLY ANALYSIS
# =========================

st.subheader("Kelly Distribution")

kelly_cols = [c for c in df.columns if "kelly" in c.lower()]

if kelly_cols:
    st.dataframe(df[kelly_cols].describe())

# =========================
# MARKET BREAKDOWN
# =========================

st.subheader("Performance by Market")

market_perf = (
    df.groupby("market_type")["bet_result"]
    .value_counts(normalize=True)
    .unstack()
)

st.dataframe(market_perf)

# =========================
# DAILY PERFORMANCE
# =========================

if "game_date" in df.columns:
    st.subheader("Daily Profit")

    daily = df.groupby("game_date")["profit"].sum()

    st.bar_chart(daily)

# =========================
# RAW DATA
# =========================

st.subheader("Raw Data")

st.dataframe(df.tail(100))
