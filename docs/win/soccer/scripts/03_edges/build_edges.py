#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
from datetime import datetime

BASE = Path(__file__).resolve().parents[2]

INPUT_DIR = BASE / "02_juice"
OUTPUT_DIR = BASE / "03_edges"
OUTPUT_DIR.mkdir(exist_ok=True)

ERROR_DIR = BASE / "errors" / "03_edges"
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "edges_log.txt"


def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")


# =========================
# CORE CALCS
# =========================

def calc_edge(book_odds, fair_odds):
    if book_odds and fair_odds:
        return (book_odds / fair_odds) - 1
    return None


def calc_ev(p, odds):
    if p and odds:
        return (p * (odds - 1)) - (1 - p)
    return None


def calc_kelly(p, odds):
    if p and odds:
        k = ((p * odds) - 1) / (odds - 1)
        return max(0, k)  # no negative bets
    return None


# =========================
# MATCH ODDS
# =========================

def process_match(df):
    rows = []

    for _, r in df.iterrows():
        row = r.to_dict()

        for side in ["home", "draw", "away"]:
            p = row.get(f"{side}_prob")
            book = row.get(f"dk_{side}_decimal")
            fair = row.get(f"juiced_{side}_decimal")

            row[f"{side}_edge"] = calc_edge(book, fair)
            row[f"{side}_ev"] = calc_ev(p, book)
            row[f"{side}_kelly"] = calc_kelly(p, book)

        rows.append(row)

    return pd.DataFrame(rows)


# =========================
# TOTALS
# =========================

def process_totals(df):
    rows = []

    for _, r in df.iterrows():
        row = r.to_dict()

        # over
        p_over = row.get("engine_over_prob")
        book_over = row.get("dk_over25_decimal") or row.get("dk_over35_decimal")
        fair_over = row.get("fair_over_decimal")

        row["over_edge"] = calc_edge(book_over, fair_over)
        row["over_ev"] = calc_ev(p_over, book_over)
        row["over_kelly"] = calc_kelly(p_over, book_over)

        # under
        p_under = row.get("engine_under_prob")
        book_under = row.get("dk_under25_decimal") or row.get("dk_under35_decimal")
        fair_under = row.get("fair_under_decimal")

        row["under_edge"] = calc_edge(book_under, fair_under)
        row["under_ev"] = calc_ev(p_under, book_under)
        row["under_kelly"] = calc_kelly(p_under, book_under)

        rows.append(row)

    return pd.DataFrame(rows)


# =========================
# BTTS
# =========================

def process_btts(df):
    rows = []

    for _, r in df.iterrows():
        row = r.to_dict()

        # yes
        p_yes = row.get("engine_btts_yes_prob")
        book_yes = row.get("btts_yes")
        fair_yes = row.get("fair_btts_yes_decimal")

        row["yes_edge"] = calc_edge(book_yes, fair_yes)
        row["yes_ev"] = calc_ev(p_yes, book_yes)
        row["yes_kelly"] = calc_kelly(p_yes, book_yes)

        # no
        p_no = row.get("engine_btts_no_prob")
        book_no = row.get("btts_no")
        fair_no = row.get("fair_btts_no_decimal")

        row["no_edge"] = calc_edge(book_no, fair_no)
        row["no_ev"] = calc_ev(p_no, book_no)
        row["no_kelly"] = calc_kelly(p_no, book_no)

        rows.append(row)

    return pd.DataFrame(rows)


# =========================
# MAIN
# =========================

def main():
    with open(LOG_FILE, "w") as f:
        f.write("=== edges run ===\n")

    for file in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(file)

        name = file.name

        if "match_odds" in name:
            out = process_match(df)
        elif "total" in name:
            out = process_totals(df)
        elif "btts" in name:
            out = process_btts(df)
        else:
            continue

        out_path = OUTPUT_DIR / name
        out.to_csv(out_path, index=False)

        log(f"WROTE {out_path}")

    print("edges complete")


if __name__ == "__main__":
    main()
