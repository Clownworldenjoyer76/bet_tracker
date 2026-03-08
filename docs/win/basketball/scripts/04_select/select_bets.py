#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR = Path("docs/win/basketball/04_select")
ERROR_DIR = Path("docs/win/basketball/errors/04_select")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

REPORT_FILE = ERROR_DIR / "select_report.txt"


###############################################################
######################## HELPERS ##############################
###############################################################

def f(x):
    try:
        if pd.isna(x):
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def s(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def reset_report():
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("BASKETBALL 04_SELECT REPORT\n")
        fh.write("=" * 100 + "\n")


def report_line(text):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(REPORT_FILE, "a", encoding="utf-8") as fh:
        fh.write(f"[{ts}] {text}\n")


def game_label(row):
    away = s(row.get("away_team"))
    home = s(row.get("home_team"))
    game_id = s(row.get("game_id"))
    date = s(row.get("game_date"))
    return f"{date} | {away} @ {home} | game_id={game_id}"


def detect_market_from_filename(file_name):
    name = file_name.lower()
    if "moneyline" in name:
        return "moneyline"
    if "spread" in name:
        return "spread"
    if "total" in name:
        return "total"
    return ""


###############################################################
##################### STEP 1 NBA MONEYLINE ####################
###############################################################

def step1_nba_moneyline(row):
    home_edge = f(row.get("home_ml_edge_decimal"))
    away_edge = f(row.get("away_ml_edge_decimal"))

    home_ml = f(row.get("home_dk_moneyline_american"))
    away_ml = f(row.get("away_dk_moneyline_american"))

    home_cond1 = home_edge > 0.07
    home_cond2 = -180 <= home_ml <= 180

    away_cond1 = away_edge > 0.07
    away_cond2 = -180 <= away_ml <= 180

    if home_cond1 and home_cond2:
        return True, (
            f"PASS STEP 1 NBA MONEYLINE | HOME passed both conditions | "
            f"home_ml_edge_decimal={home_edge:.6f} > 0.07 and "
            f"home_dk_moneyline_american={home_ml:.2f} in [-180, 180]"
        )

    if away_cond1 and away_cond2:
        return True, (
            f"PASS STEP 1 NBA MONEYLINE | AWAY passed both conditions | "
            f"away_ml_edge_decimal={away_edge:.6f} > 0.07 and "
            f"away_dk_moneyline_american={away_ml:.2f} in [-180, 180]"
        )

    reasons = []
    reasons.append(
        f"HOME cond1 edge>0.07={home_cond1} (home_ml_edge_decimal={home_edge:.6f})"
    )
    reasons.append(
        f"HOME cond2 odds_in_range={home_cond2} (home_dk_moneyline_american={home_ml:.2f})"
    )
    reasons.append(
        f"AWAY cond1 edge>0.07={away_cond1} (away_ml_edge_decimal={away_edge:.6f})"
    )
    reasons.append(
        f"AWAY cond2 odds_in_range={away_cond2} (away_dk_moneyline_american={away_ml:.2f})"
    )

    return False, "FAIL STEP 1 NBA MONEYLINE | " + " | ".join(reasons)


###############################################################
##################### STEP 2 NBA SPREAD #######################
###############################################################

def step2_nba_spread(row):
    line = f(row.get("line"))
    home_edge = f(row.get("home_spread_edge_decimal"))
    away_edge = f(row.get("away_spread_edge_decimal"))

    home_cond1 = home_edge >= 0.07
    away_cond1 = away_edge >= 0.07

    cond2_range = -14.6 <= line <= 14.6
    fail_dead_zone = -2 <= line <= 2

    if fail_dead_zone:
        return False, (
            f"FAIL STEP 2 NBA SPREAD | dead zone triggered | "
            f"line={line:.2f} is between -2 and 2"
        )

    if not cond2_range:
        return False, (
            f"FAIL STEP 2 NBA SPREAD | line outside allowed range | "
            f"line={line:.2f} not in [-14.6, 14.6]"
        )

    if home_cond1:
        return True, (
            f"PASS STEP 2 NBA SPREAD | HOME passed | "
            f"home_spread_edge_decimal={home_edge:.6f} >= 0.07 and "
            f"line={line:.2f} allowed"
        )

    if away_cond1:
        return True, (
            f"PASS STEP 2 NBA SPREAD | AWAY passed | "
            f"away_spread_edge_decimal={away_edge:.6f} >= 0.07 and "
            f"line={line:.2f} allowed"
        )

    return False, (
        f"FAIL STEP 2 NBA SPREAD | no side met edge threshold | "
        f"home_spread_edge_decimal={home_edge:.6f}, "
        f"away_spread_edge_decimal={away_edge:.6f}, "
        f"line={line:.2f}"
    )


###############################################################
##################### STEP 3 NBA TOTAL ########################
###############################################################

def step3_nba_total(row):
    line = f(row.get("line"))
    proj = f(row.get("total_projected_points"))
    home_spread = abs(f(row.get("home_spread")))
    away_spread = abs(f(row.get("away_spread")))
    max_spread = max(home_spread, away_spread)

    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))
    proj_diff = abs(proj - line)

    if line > 245:
        return False, (
            f"FAIL STEP 3 NBA TOTAL | total limit failed | "
            f"line={line:.2f} > 245"
        )

    if proj_diff < 3:
        return False, (
            f"FAIL STEP 3 NBA TOTAL | projection diff failed | "
            f"abs(total_projected_points - line)={proj_diff:.2f} < 3 | "
            f"total_projected_points={proj:.2f}, line={line:.2f}"
        )

    if max_spread >= 13 and line >= 240:
        return False, (
            f"FAIL STEP 3 NBA TOTAL | blowout filter failed | "
            f"max(abs(home_spread), abs(away_spread))={max_spread:.2f} >= 13 "
            f"and line={line:.2f} >= 240"
        )

    if under_edge > over_edge:
        if line <= 205:
            return False, (
                f"FAIL STEP 3 NBA TOTAL | under side chosen but line too low | "
                f"under_edge_decimal={under_edge:.6f} > over_edge_decimal={over_edge:.6f} "
                f"and line={line:.2f} <= 205"
            )

        if under_edge < 0.06:
            return False, (
                f"FAIL STEP 3 NBA TOTAL | under edge too small | "
                f"under_edge_decimal={under_edge:.6f} < 0.06"
            )

        if under_edge > 0.40:
            return False, (
                f"FAIL STEP 3 NBA TOTAL | under edge too large | "
                f"under_edge_decimal={under_edge:.6f} > 0.40"
            )

        return True, (
            f"PASS STEP 3 NBA TOTAL | UNDER passed | "
            f"line={line:.2f}, total_projected_points={proj:.2f}, "
            f"proj_diff={proj_diff:.2f}, max_spread={max_spread:.2f}, "
            f"under_edge_decimal={under_edge:.6f}, over_edge_decimal={over_edge:.6f}"
        )

    if line <= 205:
        if over_edge < 0.04:
            return False, (
                f"FAIL STEP 3 NBA TOTAL | over side chosen with line<=205 but over edge too small | "
                f"over_edge_decimal={over_edge:.6f} < 0.04"
            )
    else:
        if over_edge < 0.06:
            return False, (
                f"FAIL STEP 3 NBA TOTAL | over side chosen with line>205 but over edge too small | "
                f"over_edge_decimal={over_edge:.6f} < 0.06"
            )

    if over_edge > 0.35:
        return False, (
            f"FAIL STEP 3 NBA TOTAL | over edge too large | "
            f"over_edge_decimal={over_edge:.6f} > 0.35"
        )

    return True, (
        f"PASS STEP 3 NBA TOTAL | OVER passed | "
        f"line={line:.2f}, total_projected_points={proj:.2f}, "
        f"proj_diff={proj_diff:.2f}, max_spread={max_spread:.2f}, "
        f"over_edge_decimal={over_edge:.6f}, under_edge_decimal={under_edge:.6f}"
    )


###############################################################
#################### STEP 4 NCAAB MONEYLINE ###################
###############################################################

def step4_ncaab_moneyline(row):
    home_ml = f(row.get("home_dk_moneyline_american"))
    away_ml = f(row.get("away_dk_moneyline_american"))

    away_cond = away_ml < 0
    home_cond = home_ml > -215

    if away_cond:
        return True, (
            f"PASS STEP 4 NCAAB MONEYLINE | away condition passed | "
            f"away_dk_moneyline_american={away_ml:.2f} < 0"
        )

    if home_cond:
        return True, (
            f"PASS STEP 4 NCAAB MONEYLINE | home condition passed | "
            f"home_dk_moneyline_american={home_ml:.2f} > -215"
        )

    return False, (
        f"FAIL STEP 4 NCAAB MONEYLINE | both conditions failed | "
        f"away_dk_moneyline_american={away_ml:.2f} not < 0 and "
        f"home_dk_moneyline_american={home_ml:.2f} not > -215"
    )


###############################################################
#################### STEP 5 NCAAB SPREAD ######################
###############################################################

def step5_ncaab_spread(row):
    line = f(row.get("line"))

    if 1 <= line <= 3:
        return False, (
            f"FAIL STEP 5 NCAAB SPREAD | blocked range 1 to 3 | line={line:.2f}"
        )

    if -10 <= line <= -5:
        return False, (
            f"FAIL STEP 5 NCAAB SPREAD | blocked range -10 to -5 | line={line:.2f}"
        )

    if 1 <= abs(line) <= 7 and line > 0:
        return False, (
            f"FAIL STEP 5 NCAAB SPREAD | blocked positive abs(line) 1 to 7 | line={line:.2f}"
        )

    return True, (
        f"PASS STEP 5 NCAAB SPREAD | line allowed | line={line:.2f}"
    )


###############################################################
#################### STEP 6 NCAAB TOTAL #######################
###############################################################

def step6_ncaab_total(row):
    line = f(row.get("line"))
    over_edge = f(row.get("over_edge_decimal"))
    under_edge = f(row.get("under_edge_decimal"))

    over_pass = 145 <= line <= 155 and 0.12 <= over_edge <= 0.18
    under_pass = 141 <= line <= 150 and 0.10 <= under_edge <= 0.22

    if over_pass:
        return True, (
            f"PASS STEP 6 NCAAB TOTAL | OVER passed | "
            f"line={line:.2f} in [145,155] and "
            f"over_edge_decimal={over_edge:.6f} in [0.12,0.18]"
        )

    if under_pass:
        return True, (
            f"PASS STEP 6 NCAAB TOTAL | UNDER passed | "
            f"line={line:.2f} in [141,150] and "
            f"under_edge_decimal={under_edge:.6f} in [0.10,0.22]"
        )

    return False, (
        f"FAIL STEP 6 NCAAB TOTAL | neither side passed | "
        f"line={line:.2f}, over_edge_decimal={over_edge:.6f}, "
        f"under_edge_decimal={under_edge:.6f}"
    )


###############################################################
#################### EDGE SELECTION ENGINE ####################
###############################################################

def process_file(csv_file):
    df = pd.read_csv(csv_file)

    if df.empty:
        report_line(f"FILE {csv_file.name} | INFO | empty input file")
        return

    fname = csv_file.name.lower()
    league = "NBA" if "nba" in fname else "NCAAB"
    market_type = detect_market_from_filename(csv_file.name)

    if not market_type:
        report_line(f"FILE {csv_file.name} | ERROR | could not detect market type from filename")
        return

    report_line(f"FILE {csv_file.name} | START | league={league} | market_type={market_type} | rows={len(df)}")

    selected_rows = []
    pass_count = 0
    fail_count = 0

    for _, row in df.iterrows():
        label = game_label(row)

        if league == "NBA":
            if market_type == "moneyline":
                allowed, reason = step1_nba_moneyline(row)
            elif market_type == "spread":
                allowed, reason = step2_nba_spread(row)
            elif market_type == "total":
                allowed, reason = step3_nba_total(row)
            else:
                allowed, reason = False, f"FAIL | unknown NBA market_type={market_type}"
        else:
            if market_type == "moneyline":
                allowed, reason = step4_ncaab_moneyline(row)
            elif market_type == "spread":
                allowed, reason = step5_ncaab_spread(row)
            elif market_type == "total":
                allowed, reason = step6_ncaab_total(row)
            else:
                allowed, reason = False, f"FAIL | unknown NCAAB market_type={market_type}"

        if allowed:
            selected_rows.append(row.to_dict())
            pass_count += 1
            report_line(f"PASS | {league} | {market_type} | {label} | {reason}")
        else:
            fail_count += 1
            report_line(f"FAIL | {league} | {market_type} | {label} | {reason}")

    if selected_rows:
        out_df = pd.DataFrame(selected_rows)
        out_path = OUTPUT_DIR / csv_file.name
        out_df.to_csv(out_path, index=False)
        report_line(
            f"FILE {csv_file.name} | DONE | selected_rows={len(out_df)} | passed={pass_count} | failed={fail_count} | output={out_path}"
        )
        print(f"Selected {len(out_df)} rows -> {out_path.name}")
    else:
        report_line(
            f"FILE {csv_file.name} | DONE | selected_rows=0 | passed={pass_count} | failed={fail_count} | no output file written"
        )
        print(f"Selected 0 rows -> {csv_file.name}")


###############################################################
############################ MAIN #############################
###############################################################

def main():
    reset_report()

    files = sorted(INPUT_DIR.glob("*.csv"))

    if not files:
        report_line("MAIN | INFO | No input files found")
        return

    for fpath in files:
        try:
            process_file(fpath)
        except Exception as e:
            report_line(f"FILE {fpath.name} | ERROR | {type(e).__name__}: {e}")

    report_line("MAIN | SUCCESS | Selection run complete")


if __name__ == "__main__":
    main()
