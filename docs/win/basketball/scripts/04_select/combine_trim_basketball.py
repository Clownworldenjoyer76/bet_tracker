#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/combine_trim_basketball.py

import pandas as pd
from pathlib import Path

###############################################################
######################## PATH CONFIG ##########################
###############################################################

SELECT_DIR = Path("docs/win/basketball/04_select")
OUTPUT_DIR = SELECT_DIR / "daily_slate"
TOTALS_DIR = OUTPUT_DIR / "totals"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TOTALS_DIR.mkdir(parents=True, exist_ok=True)

###############################################################
######################## EDGE CALCULATION #####################
###############################################################

def safe_float(x):
    try:
        if pd.isna(x):
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def compute_edge(row):
    market_type = str(row.get("market_type", "")).lower()
    bet_side = str(row.get("bet_side", "")).lower()

    if market_type == "total":
        if bet_side == "over":
            return safe_float(row.get("over_edge_decimal"))
        if bet_side == "under":
            return safe_float(row.get("under_edge_decimal"))
        return 0.0

    if market_type == "moneyline":
        if bet_side == "home":
            return safe_float(row.get("home_ml_edge_decimal"))
        if bet_side == "away":
            return safe_float(row.get("away_ml_edge_decimal"))
        return max(
            safe_float(row.get("home_ml_edge_decimal")),
            safe_float(row.get("away_ml_edge_decimal")),
        )

    if market_type == "spread":
        if bet_side == "home":
            return safe_float(row.get("home_spread_edge_decimal"))
        if bet_side == "away":
            return safe_float(row.get("away_spread_edge_decimal"))
        return max(
            safe_float(row.get("home_spread_edge_decimal")),
            safe_float(row.get("away_spread_edge_decimal")),
        )

    return 0.0


###############################################################
######################## GAME TRIMMING ########################
###############################################################

def trim_games(df):
    cleaned_rows = []

    grouped = df.groupby(["game_date", "away_team", "home_team"], dropna=False)

    for _, game_df in grouped:
        totals = game_df[game_df["market_type"] == "total"].copy()
        sides = game_df[game_df["market_type"].isin(["spread", "moneyline"])].copy()

        best_total = None
        best_side = None

        if not totals.empty:
            totals["edge"] = totals.apply(compute_edge, axis=1)
            totals = totals.sort_values("edge", ascending=False, kind="mergesort")
            best_total = totals.iloc[0]

        if not sides.empty:
            sides["edge"] = sides.apply(compute_edge, axis=1)
            sides = sides.sort_values("edge", ascending=False, kind="mergesort")
            best_side = sides.iloc[0]

        if best_side is not None:
            cleaned_rows.append(best_side)

        if best_total is not None:
            cleaned_rows.append(best_total)

    if not cleaned_rows:
        return pd.DataFrame()

    out = pd.DataFrame(cleaned_rows).copy()
    if "edge" in out.columns:
        out = out.drop(columns=["edge"], errors="ignore")
    return out


###############################################################
######################## TOTAL HISTORY ########################
###############################################################

def build_totals():
    nba_files = sorted(OUTPUT_DIR.glob("*_nba.csv"))
    ncaab_files = sorted(OUTPUT_DIR.glob("*_ncaab.csv"))

    nba_final_path = TOTALS_DIR / "NBA_final.csv"
    ncaab_final_path = TOTALS_DIR / "NCAAB_final.csv"

    if nba_files:
        nba_dfs = [pd.read_csv(f) for f in nba_files if f.is_file()]
        if nba_dfs:
            nba_final = pd.concat(nba_dfs, ignore_index=True)
            nba_final.to_csv(nba_final_path, index=False)
    elif nba_final_path.exists():
        nba_final_path.unlink()

    if ncaab_files:
        ncaab_dfs = [pd.read_csv(f) for f in ncaab_files if f.is_file()]
        if ncaab_dfs:
            ncaab_final = pd.concat(ncaab_dfs, ignore_index=True)
            ncaab_final.to_csv(ncaab_final_path, index=False)
    elif ncaab_final_path.exists():
        ncaab_final_path.unlink()

    print("Totals history files created.")


###############################################################
######################## MAIN PIPELINE ########################
###############################################################

def clear_daily_slate_outputs():
    for f in OUTPUT_DIR.glob("*.csv"):
        f.unlink(missing_ok=True)

    for f in TOTALS_DIR.glob("*.csv"):
        f.unlink(missing_ok=True)


def main():
    clear_daily_slate_outputs()

    files = [
        f for f in SELECT_DIR.glob("*.csv")
        if f.is_file() and f.name not in ["nba_selected.csv", "ncaab_selected.csv"]
    ]

    if not files:
        print("No select files found.")
        return

    dfs = []

    for f in files:
        try:
            df = pd.read_csv(f)
            if not df.empty:
                dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")

    if not dfs:
        print("No data to process.")
        return

    df = pd.concat(dfs, ignore_index=True)

    nba_df = df[df["market"].astype(str).str.contains("NBA", na=False)].copy()
    ncaab_df = df[df["market"].astype(str).str.contains("NCAAB", na=False)].copy()

    nba_trimmed = trim_games(nba_df) if not nba_df.empty else pd.DataFrame()
    ncaab_trimmed = trim_games(ncaab_df) if not ncaab_df.empty else pd.DataFrame()

    nba_master = OUTPUT_DIR / "nba_selected.csv"
    ncaab_master = OUTPUT_DIR / "ncaab_selected.csv"

    if not nba_trimmed.empty:
        nba_trimmed.to_csv(nba_master, index=False)
        print(f"NBA master file created: {nba_master}")
    elif nba_master.exists():
        nba_master.unlink(missing_ok=True)

    if not ncaab_trimmed.empty:
        ncaab_trimmed.to_csv(ncaab_master, index=False)
        print(f"NCAAB master file created: {ncaab_master}")
    elif ncaab_master.exists():
        ncaab_master.unlink(missing_ok=True)

    if not nba_trimmed.empty:
        for date, g in nba_trimmed.groupby("game_date", dropna=False):
            path = OUTPUT_DIR / f"{date}_nba.csv"
            g.to_csv(path, index=False)

    if not ncaab_trimmed.empty:
        for date, g in ncaab_trimmed.groupby("game_date", dropna=False):
            path = OUTPUT_DIR / f"{date}_ncaab.csv"
            g.to_csv(path, index=False)

    print("Daily slate files created.")

    build_totals()


if __name__ == "__main__":
    main()
