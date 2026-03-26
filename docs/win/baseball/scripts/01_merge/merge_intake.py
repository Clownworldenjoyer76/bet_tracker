#!/usr/bin/env python3
# docs/win/baseball/scripts/01_merge/merge_intake.py

import csv
from pathlib import Path

PRED_DIR = Path("docs/win/baseball/00_intake/predictions")
BOOK_DIR = Path("docs/win/baseball/00_intake/sportsbook")
OUT_DIR  = Path("docs/win/baseball/01_merge")

OUT_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------
# LOAD CSV
# -------------------------

def load_csv(path):
    rows = []
    if not path.exists():
        return rows

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


# -------------------------
# INDEX BUILD
# -------------------------

def build_index(rows):
    idx = {}

    for r in rows:
        gid = r.get("game_id")

        key = gid if gid else (r["home_team"], r["away_team"])
        idx[key] = r

    return idx


# -------------------------
# PROBABILITY PLACEHOLDERS
# -------------------------

def run_line_probs(home_prob, away_prob):
    try:
        hp = float(home_prob)
        ap = float(away_prob)
        return str(hp), str(ap)
    except:
        return "", ""


def total_probs(total_proj, total_line):
    try:
        proj = float(total_proj)
        line = float(total_line)

        if proj > line:
            return "1", "0"
        elif proj < line:
            return "0", "1"
        else:
            return "0.5", "0.5"
    except:
        return "", ""


# -------------------------
# PROCESS
# -------------------------

def process_date(date):

    pred_path = PRED_DIR / f"{date}_MLB.csv"
    book_path = BOOK_DIR / f"{date}_MLB.csv"

    preds = load_csv(pred_path)
    books = load_csv(book_path)

    pred_idx = build_index(preds)

    ml_rows = []
    rl_rows = []
    tot_rows = []

    for b in books:
        gid = b.get("game_id")
        key = gid if gid else (b["home_team"], b["away_team"])

        p = pred_idx.get(key)
        if not p:
            continue

        # -------------------------
        # MONEYLINE
        # -------------------------
        ml_rows.append([
            b["game_id"], b["sport"], b["league"], b["game_date"], b["game_time"],
            b["home_team"], b["away_team"],
            b["away_run_line"], b["home_run_line"], b["total"],
            b["away_dk_moneyline_american"], b["home_dk_moneyline_american"],
            b["away_dk_moneyline_decimal"], b["home_dk_moneyline_decimal"],
            p["home_pitcher"], p["away_pitcher"],
            p["home_prob"], p["away_prob"],
            p["away_projected_runs"], p["home_projected_runs"], p["total_projected_runs"]
        ])

        # -------------------------
        # RUN LINE
        # -------------------------
        home_rl_prob, away_rl_prob = run_line_probs(
            p["home_prob"], p["away_prob"]
        )

        rl_rows.append([
            b["game_id"], b["sport"], b["league"], b["game_date"], b["game_time"],
            b["home_team"], b["away_team"],
            b["away_run_line"], b["home_run_line"], b["total"],
            b["away_dk_run_line_american"], b["home_dk_run_line_american"],
            b["away_dk_run_line_decimal"], b["home_dk_run_line_decimal"],
            p["home_pitcher"], p["away_pitcher"],
            p["home_prob"], p["away_prob"],
            p["away_projected_runs"], p["home_projected_runs"], p["total_projected_runs"],
            home_rl_prob, away_rl_prob
        ])

        # -------------------------
        # TOTAL
        # -------------------------
        over_prob, under_prob = total_probs(
            p["total_projected_runs"], b["total"]
        )

        tot_rows.append([
            b["game_id"], b["sport"], b["league"], b["game_date"], b["game_time"],
            b["home_team"], b["away_team"],
            b["away_run_line"], b["home_run_line"], b["total"],
            b["dk_total_over_american"], b["dk_total_under_american"],
            b["dk_total_over_decimal"], b["dk_total_under_decimal"],
            p["home_pitcher"], p["away_pitcher"],
            p["home_prob"], p["away_prob"],
            p["away_projected_runs"], p["home_projected_runs"], p["total_projected_runs"],
            over_prob, under_prob
        ])

    # -------------------------
    # WRITE FILES
    # -------------------------

    def write(path, header, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

    write(
        OUT_DIR / f"{date}_mlb_moneyline.csv",
        [
            "game_id","sport","league","game_date","game_time","home_team","away_team",
            "away_run_line","home_run_line","total",
            "away_dk_moneyline_american","home_dk_moneyline_american",
            "away_dk_moneyline_decimal","home_dk_moneyline_decimal",
            "home_pitcher","away_pitcher","home_prob","away_prob",
            "away_projected_runs","home_projected_runs","total_projected_runs"
        ],
        ml_rows
    )

    write(
        OUT_DIR / f"{date}_mlb_run_line.csv",
        [
            "game_id","sport","league","game_date","game_time","home_team","away_team",
            "away_run_line","home_run_line","total",
            "away_dk_run_line_american","home_dk_run_line_american",
            "away_dk_run_line_decimal","home_dk_run_line_decimal",
            "home_pitcher","away_pitcher","home_prob","away_prob",
            "away_projected_runs","home_projected_runs","total_projected_runs",
            "home_run_line_prob","away_run_line_prob"
        ],
        rl_rows
    )

    write(
        OUT_DIR / f"{date}_mlb_total.csv",
        [
            "game_id","sport","league","game_date","game_time","home_team","away_team",
            "away_run_line","home_run_line","total",
            "dk_total_over_american","dk_total_under_american",
            "dk_total_over_decimal","dk_total_under_decimal",
            "home_pitcher","away_pitcher","home_prob","away_prob",
            "away_projected_runs","home_projected_runs","total_projected_runs",
            "total_runs_over_prob","total_runs_under_prob"
        ],
        tot_rows
    )


# -------------------------
# ENTRY
# -------------------------

if __name__ == "__main__":
    for file in sorted(PRED_DIR.glob("*_MLB.csv")):
        date = file.stem.replace("_MLB", "")
        process_date(date)
