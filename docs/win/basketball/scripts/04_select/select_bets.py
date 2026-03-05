#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime

# =========================
# OPTIONAL OVERRIDE CONFIG
# =========================
# This lets your optimizer write a simple python file:
#   docs/win/basketball/model_testing/rule_config.py
# and the selector will automatically pick up those values without editing code.

OVERRIDE_CONFIG_PATH = Path("docs/win/basketball/model_testing/rule_config.py")


def load_override_config():
    """
    Load override values from rule_config.py if it exists.
    Expected to contain simple assignments like:
        EDGE_MIN = 0.10
        EDGE_MAX = 0.30
        SPREAD_MAX = 20
        TOTAL_MIN = 140
        ML_LOW = -180
        ML_HIGH = -150

    Returns: dict of variables found, else {}.
    """
    if not OVERRIDE_CONFIG_PATH.exists():
        return {}

    scope = {}
    try:
        content = OVERRIDE_CONFIG_PATH.read_text(encoding="utf-8")
        exec(compile(content, str(OVERRIDE_CONFIG_PATH), "exec"), {}, scope)
        # remove dunder keys
        return {k: v for k, v in scope.items() if not k.startswith("__")}
    except Exception:
        return {}


OVR = load_override_config()

# =========================
# RULES (easy tuning blocks)
# =========================

NCAAB_RULES = {
    "edge_min": 0.10,
    "edge_max": 0.30,
    "skip_home_ml_range": (-180, -150),
    "skip_under_below": 140,
    "spread_max": 20,
    "ml_min_prob": 0.60,
}

NBA_RULES = {
    "edge_min": 0.06,
    "edge_max": 0.35,
    "spread_max": 15,
    "total_diff_min": 3,
    "total_max": 245,
    "low_total_cutoff": 205,
    "over_low_total_edge_bonus": 0.02,
}

# =========================
# APPLY OVERRIDES (if present)
# =========================
# These are the ONLY things the optimizer needs to write to control selection:
#   EDGE_MIN, EDGE_MAX, SPREAD_MAX, TOTAL_MIN, ML_LOW, ML_HIGH
#
# Notes:
# - EDGE_MIN/EDGE_MAX apply to BOTH markets unless you later split them.
# - TOTAL_MIN applies ONLY to NCAAB "skip_under_below" per your rule.
# - ML_LOW/ML_HIGH apply to NCAAB "skip_home_ml_range".

if "EDGE_MIN" in OVR:
    NCAAB_RULES["edge_min"] = float(OVR["EDGE_MIN"])
    NBA_RULES["edge_min"] = float(OVR["EDGE_MIN"])

if "EDGE_MAX" in OVR:
    NCAAB_RULES["edge_max"] = float(OVR["EDGE_MAX"])
    NBA_RULES["edge_max"] = float(OVR["EDGE_MAX"])

if "SPREAD_MAX" in OVR:
    NCAAB_RULES["spread_max"] = float(OVR["SPREAD_MAX"])
    NBA_RULES["spread_max"] = float(OVR["SPREAD_MAX"])

if "TOTAL_MIN" in OVR:
    # Your requested rule: "Skip UNDER when total line < 140"
    NCAAB_RULES["skip_under_below"] = float(OVR["TOTAL_MIN"])

if "ML_LOW" in OVR and "ML_HIGH" in OVR:
    NCAAB_RULES["skip_home_ml_range"] = (float(OVR["ML_LOW"]), float(OVR["ML_HIGH"]))

# =========================
# SAFE FLOAT CONVERTER
# =========================

def f(x):
    try:
        return float(x)
    except Exception:
        return 0.0

# =========================
# LOGGER UTILITY
# =========================

def audit(log_path, stage, status, msg="", df=None):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg:
            fh.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            fh.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            fh.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        fh.write("-" * 40 + "\n")

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR = Path("docs/win/basketball/04_select")
ERROR_DIR = Path("docs/win/basketball/errors/04_select")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = ERROR_DIR / "select_bets_audit.txt"

# =========================
# MAIN
# =========================

def main():
    all_candidates = []

    for csv_file in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(csv_file)
        fname = csv_file.name.lower()
        league = "NBA" if "nba" in fname else "NCAAB"

        records = df.to_dict("records")

        for row in records:
            game_key = (row.get("game_date"), row.get("away_team"), row.get("home_team"))

            # =========================
            # TOTAL FILE
            # =========================
            if "total" in fname:
                line = f(row.get("total"))
                proj = f(row.get("total_projected_points"))
                diff = abs(proj - line)

                edges = {
                    "over": f(row.get("over_edge_decimal")),
                    "under": f(row.get("under_edge_decimal")),
                }

                for side, edge in edges.items():
                    odds = f(row.get(f"total_{side}_juice_odds"))
                    if odds <= -300:
                        continue

                    # ---------- NCAAB TOTAL ----------
                    if league == "NCAAB":
                        if edge > NCAAB_RULES["edge_max"]:
                            continue
                        if edge < NCAAB_RULES["edge_min"]:
                            continue
                        if side == "under" and line < NCAAB_RULES["skip_under_below"]:
                            continue

                        # keep your existing over logic (even though edge_min is stricter)
                        if side == "over":
                            if line < 150 and not (edge >= 0.02 and diff >= 4):
                                continue
                            if line >= 150 and not (edge > 0.001 and diff >= 2):
                                continue

                    # ---------- NBA TOTAL ----------
                    if league == "NBA":
                        edge_required = NBA_RULES["edge_min"]

                        if line <= NBA_RULES["low_total_cutoff"] and side == "over":
                            edge_required -= NBA_RULES["over_low_total_edge_bonus"]

                        if line <= NBA_RULES["low_total_cutoff"] and side == "under":
                            continue

                        if line > NBA_RULES["total_max"]:
                            continue

                        if diff < NBA_RULES["total_diff_min"]:
                            continue

                        if edge > NBA_RULES["edge_max"]:
                            continue

                        if edge < edge_required:
                            continue

                    new_row = row.copy()
                    new_row["market_type"] = "total"
                    new_row["bet_side"] = side
                    new_row["line"] = line
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key
                    all_candidates.append(new_row)

            # =========================
            # SPREAD FILE
            # =========================
            elif "spread" in fname:
                for side in ["home", "away"]:
                    edge = f(row.get(f"{side}_edge_decimal"))
                    spread = f(row.get(f"{side}_spread"))
                    odds = f(row.get(f"{side}_spread_juice_odds"))

                    if odds <= -300:
                        continue

                    # ---------- NCAAB SPREAD ----------
                    if league == "NCAAB":
                        if edge > NCAAB_RULES["edge_max"]:
                            continue
                        if edge < NCAAB_RULES["edge_min"]:
                            continue
                        # explicit away-spread rule (redundant with edge_min but kept)
                        if side == "away" and edge < 0.10:
                            continue
                        if abs(spread) > NCAAB_RULES["spread_max"]:
                            continue

                    # ---------- NBA SPREAD ----------
                    if league == "NBA":
                        if edge < NBA_RULES["edge_min"]:
                            continue
                        if abs(spread) > NBA_RULES["spread_max"]:
                            continue

                    new_row = row.copy()
                    new_row["market_type"] = "spread"
                    new_row["bet_side"] = side
                    new_row["line"] = spread
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key
                    all_candidates.append(new_row)

            # =========================
            # MONEYLINE FILE
            # =========================
            elif "moneyline" in fname:
                for side in ["home", "away"]:
                    edge = f(row.get(f"{side}_edge_decimal"))
                    prob = f(row.get(f"{side}_prob"))
                    odds = f(row.get(f"{side}_juice_odds"))

                    if odds <= -300:
                        continue

                    # ---------- NCAAB MONEYLINE ----------
                    if league == "NCAAB":
                        if edge > NCAAB_RULES["edge_max"]:
                            continue
                        if edge < NCAAB_RULES["edge_min"]:
                            continue

                        low, high = NCAAB_RULES["skip_home_ml_range"]
                        if side == "home" and (low <= odds <= high):
                            continue

                        if prob < NCAAB_RULES["ml_min_prob"]:
                            continue

                    # ---------- NBA MONEYLINE ----------
                    if league == "NBA":
                        if edge < NBA_RULES["edge_min"]:
                            continue

                    new_row = row.copy()
                    new_row["market_type"] = "moneyline"
                    new_row["bet_side"] = side
                    new_row["line"] = odds
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key
                    all_candidates.append(new_row)

    # =========================
    # POST FILTER RULES
    # =========================

    cand_df = pd.DataFrame(all_candidates)

    if cand_df.empty:
        audit(LOG_FILE, "SELECTION", "INFO", msg="No bets selected")
        return

    final_rows = []
    for _, g in cand_df.groupby("game_key"):
        totals = g[g.market_type == "total"]
        sides = g[g.market_type.isin(["spread", "moneyline"])]

        chosen_total = totals.sort_values("candidate_edge", ascending=False).iloc[0] if not totals.empty else None
        chosen_side = sides.sort_values("candidate_edge", ascending=False).iloc[0] if not sides.empty else None

        if chosen_total is not None:
            final_rows.append(chosen_total)
        if chosen_side is not None:
            final_rows.append(chosen_side)

    res_df = pd.DataFrame(final_rows).drop_duplicates()

    if not res_df.empty:
        res_df.drop(columns=["candidate_edge", "game_key"], errors="ignore").to_csv(
            OUTPUT_DIR / "selected_bets.csv",
            index=False,
        )
        audit(LOG_FILE, "SELECTION", "SUCCESS", msg=f"Selected {len(res_df)} bets", df=res_df)
    else:
        audit(LOG_FILE, "SELECTION", "INFO", msg="No bets selected")


if __name__ == "__main__":
    main()
