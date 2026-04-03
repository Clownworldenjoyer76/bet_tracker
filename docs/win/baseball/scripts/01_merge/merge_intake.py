#!/usr/bin/env python3
# docs/win/baseball/scripts/01_merge/merge_intake.py

import csv
from pathlib import Path
from datetime import datetime, timezone

PRED_DIR = Path("docs/win/baseball/00_intake/predictions")
BOOK_DIR = Path("docs/win/baseball/00_intake/sportsbook")
OUT_DIR  = Path("docs/win/baseball/01_merge")
LOG_DIR  = Path("docs/win/baseball/errors/01_merge")

OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "merge_intake_log.txt"


def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {msg}\n")


def norm(s):
    return (s or "").strip().lower()


def load_csv(path):
    rows = []
    if not path.exists():
        log(f"MISSING FILE: {path}")
        return rows

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def build_team_index(rows):
    idx = {}
    for r in rows:
        key = (norm(r["home_team"]), norm(r["away_team"]))
        idx[key] = r
    return idx


def american_to_prob(odds):
    try:
        odds = float(odds)
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return -odds / (-odds + 100)
    except:
        return None


def normalize_probs(p1, p2):
    if p1 is None or p2 is None:
        return "", ""
    total = p1 + p2
    if total == 0:
        return "", ""
    return str(p1 / total), str(p2 / total)


def process_date(date):

    pred_path = PRED_DIR / f"{date}_MLB.csv"
    book_path = BOOK_DIR / f"{date}_MLB.csv"

    preds = load_csv(pred_path)
    books = load_csv(book_path)

    pred_idx = build_team_index(preds)

    matched = 0
    unmatched = 0

    ml_rows = []
    rl_rows = []
    tot_rows = []

    for b in books:

        key = (norm(b["home_team"]), norm(b["away_team"]))
        p = pred_idx.get(key)

        if not p:
            unmatched += 1
            log(f"UNMATCHED: {key}")
            continue

        matched += 1

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
        # RUN LINE (FIXED BASELINE)
        # -------------------------
        try:
            home_prob_ml = float(p["home_prob"])
            away_prob_ml = float(p["away_prob"])

            # 🔥 KEY FIX: ML → RL conversion
            home_rl_prob = home_prob_ml * 0.75
            away_rl_prob = away_prob_ml * 0.75

        except:
            home_rl_prob, away_rl_prob = "", ""

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
        # TOTAL (vig removed)
        # -------------------------
        over_raw = american_to_prob(b["dk_total_over_american"])
        under_raw = american_to_prob(b["dk_total_under_american"])

        over_prob, under_prob = normalize_probs(over_raw, under_raw)

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

    log(f"{date} | matched={matched} | unmatched={unmatched}")

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


if __name__ == "__main__":
    with open(LOG_FILE, "w") as f:
        f.write("")

    for file in sorted(PRED_DIR.glob("*_MLB.csv")):
        date = file.stem.replace("_MLB", "")
        process_date(date)