#!/usr/bin/env python3
# docs/win/final_scores/scripts/05_results/results.py

import os
import glob
import re
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd

ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_LOG = ERROR_DIR / "results_summary.txt"
ERROR_LOG = ERROR_DIR / "results_errors.txt"


def log_summary(message: str):
    with open(SUMMARY_LOG, "a", encoding="utf-8") as f:
        f.write(message.rstrip() + "\n")


def log_error(message: str):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(message.rstrip() + "\n")


def determine_outcome(row):

    try:

        m_type = str(row.get("market_type", "")).lower()
        side = str(row.get("bet_side", "")).lower()

        away_s = float(row["away_score"])
        home_s = float(row["home_score"])

        # =========================
        # SOCCER RESULT MARKET
        # =========================

        if m_type == "result":

            if home_s == away_s:
                winner = "draw"
            elif home_s > away_s:
                winner = "home"
            else:
                winner = "away"

            return "Win" if side == winner else "Loss"

        # =========================
        # SOCCER TOTALS
        # =========================

        if m_type == "total":

            line = 2.5
            total_score = home_s + away_s

            if side == "over25":
                return "Win" if total_score > line else "Loss"

            if side == "under25":
                return "Win" if total_score < line else "Loss"

        # =========================
        # ORIGINAL LOGIC (unchanged)
        # =========================

        line = float(row.get("line", 0))

        if m_type == "moneyline":

            if away_s == home_s:
                return "Push"

            if side == "away":
                return "Win" if away_s > home_s else "Loss"

            if side == "home":
                return "Win" if home_s > away_s else "Loss"

        if m_type in ["spread", "puck_line"]:

            if side == "away":
                diff = (away_s + line) - home_s
            else:
                diff = (home_s + line) - away_s

            if diff == 0:
                return "Push"

            return "Win" if diff > 0 else "Loss"

        if m_type in ["total","totals"]:

            total_score = away_s + home_s

            if total_score == line:
                return "Push"

            if side == "over":
                return "Win" if total_score > line else "Loss"

            if side == "under":
                return "Win" if total_score < line else "Loss"

        return "Unknown"

    except Exception:
        return "Unknown"
