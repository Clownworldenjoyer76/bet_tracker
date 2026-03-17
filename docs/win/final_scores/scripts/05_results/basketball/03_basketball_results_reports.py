#!/usr/bin/env python3
# docs/win/final_scores/scripts/05_results/basketball_results_reports.py

from datetime import datetime
from pathlib import Path

import pandas as pd

###############################################################
######################## PATH CONFIG ##########################
###############################################################

INTERMEDIATE_DIR = Path("docs/win/final_scores/intermediate")

DEEP_SUMMARY_BASE = Path("docs/win/final_scores/deeper_summaries")
NBA_DEEP_DIR = DEEP_SUMMARY_BASE / "nba"
NCAAB_DEEP_DIR = DEEP_SUMMARY_BASE / "ncaab"

NBA_MARKET_TALLY = Path("docs/win/final_scores/nba_market_tally.csv")
NCAAB_MARKET_TALLY = Path("docs/win/final_scores/ncaab_market_tally.csv")

ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

EDGE_REPORT = ERROR_DIR / "basketball_edge_summary.txt"
REPORTS_ERROR_LOG = ERROR_DIR / "basketball_results_reports_errors.txt"
REPORTS_SUMMARY_LOG = ERROR_DIR / "basketball_results_reports_summary.txt"

###############################################################
######################## LOGGING ##############################
###############################################################

def reset_logs():
    REPORTS_ERROR_LOG.write_text("", encoding="utf-8")
    REPORTS_SUMMARY_LOG.write_text("", encoding="utf-8")

def log_error(msg):
    with open(REPORTS_ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {msg}\n")

def log_summary(msg):
    with open(REPORTS_SUMMARY_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {msg}\n")

###############################################################
######################## HELPERS ##############################
###############################################################

def safe_read(path):
    try:
        path = Path(path)

        if not path.exists():
            log_error(f"MISSING FILE | {path}")
            return pd.DataFrame()

        df = pd.read_csv(path)

        if df is None or df.empty:
            log_error(f"EMPTY FILE | {path}")
            return pd.DataFrame()

        return df

    except Exception as e:
        log_error(f"READ ERROR | {path} | {e}")
        return pd.DataFrame()


def write_csv(df, path):
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        log_summary(f"WROTE CSV | ROWS={len(df)} | OUT={path}")
    except Exception as e:
        log_error(f"WRITE CSV ERROR | {path} | {e}")

###############################################################
######################## SUMMARY CORE #########################
###############################################################

def summarize(df):
    if df is None or df.empty or "bet_result" not in df.columns:
        return 0, 0, 0, 0, 0.0

    wins = int((df["bet_result"] == "Win").sum())
    losses = int((df["bet_result"] == "Loss").sum())
    pushes = int((df["bet_result"] == "Push").sum())
    total = wins + losses + pushes
    win_pct = (wins / (wins + losses)) if (wins + losses) > 0 else 0.0

    return wins, losses, pushes, total, round(win_pct, 4)


def aggregate_results(df, group_cols):
    if df is None or df.empty:
        return pd.DataFrame()

    rows = []

    grouped = df.groupby(group_cols, dropna=False)
    for keys, sub in grouped:
        wins, losses, pushes, total, win_pct = summarize(sub)

        if not isinstance(keys, tuple):
            keys = (keys,)

        row = {}
        for i, col in enumerate(group_cols):
            row[col] = keys[i]

        row["Win"] = wins
        row["Loss"] = losses
        row["Push"] = pushes
        row["Total"] = total
        row["Win_Pct"] = win_pct
        rows.append(row)

    return pd.DataFrame(rows).sort_values(group_cols).reset_index(drop=True)

###############################################################
######################## VALIDATION ###########################
###############################################################

def validate_aggregation(df_source, df_grouped, label):
    try:
        source_total = len(df_source)
        grouped_total = df_grouped["Total"].sum() if not df_grouped.empty else 0

        if source_total != grouped_total:
            log_error(f"VALIDATION FAIL | {label} | SOURCE={source_total} GROUPED={grouped_total}")
        else:
            log_summary(f"VALIDATION PASS | {label} | TOTAL={source_total}")

    except Exception as e:
        log_error(f"VALIDATION ERROR | {label} | {e}")

###############################################################
######################## REPORT BUILDERS ######################
###############################################################

def build_moneyline_outputs(work, league, outdir):
    try:
        ml = work[work["market_type"] == "moneyline"].copy()
        if ml.empty:
            return

        df1_src = ml[(ml["side_group"].isin(["HOME","AWAY"])) & (ml["edge_bucket"] != "UNBUCKETED")]
        df1 = aggregate_results(df1_src, ["market","side_group","edge_bucket"])
        write_csv(df1, outdir / "moneyline_edge_bucket_home_away_summary.csv")
        validate_aggregation(df1_src, df1, "moneyline_edge_bucket_home_away")

        df2_src = ml[ml["edge_bucket"] != "UNBUCKETED"]
        df2 = aggregate_results(df2_src, ["market","edge_bucket"])
        write_csv(df2, outdir / "moneyline_edge_bucket_summary.csv")
        validate_aggregation(df2_src, df2, "moneyline_edge_bucket")

    except Exception as e:
        log_error(f"{league} MONEYLINE ERROR | {e}")


def build_spread_outputs(work, league, outdir):
    try:
        sp = work[work["market_type"] == "spread"].copy()
        if sp.empty:
            return

        df1_src = sp[(sp["side_group"].isin(["HOME","AWAY"])) & (sp["edge_bucket"] != "UNBUCKETED")]
        df1 = aggregate_results(df1_src, ["market","side_group","edge_bucket"])
        write_csv(df1, outdir / "spread_edge_bucket_home_away_summary.csv")
        validate_aggregation(df1_src, df1, "spread_edge_home_away")

        df2_src = sp[sp["edge_bucket"] != "UNBUCKETED"]
        df2 = aggregate_results(df2_src, ["market","edge_bucket"])
        write_csv(df2, outdir / "spread_edge_bucket_summary.csv")
        validate_aggregation(df2_src, df2, "spread_edge")

        df3_src = sp[(sp["side_group"].isin(["HOME","AWAY"])) & (sp["spread_bucket"] != "UNBUCKETED")]
        df3 = aggregate_results(df3_src, ["market","side_group","spread_bucket"])
        write_csv(df3, outdir / "spread_bands_bucket_home_away_summary.csv")
        validate_aggregation(df3_src, df3, "spread_bucket_home_away")

        df4_src = sp[sp["spread_bucket"] != "UNBUCKETED"]
        df4 = aggregate_results(df4_src, ["market","spread_bucket"])
        write_csv(df4, outdir / "spread_bands_bucket_summary.csv")
        validate_aggregation(df4_src, df4, "spread_bucket")

        df5_src = sp[(sp["side_group"].isin(["HOME","AWAY"])) &
                     (sp["spread_bucket"] != "UNBUCKETED") &
                     (sp["edge_bucket"] != "UNBUCKETED")]

        df5 = aggregate_results(df5_src,
            ["market","market_type","side_group","spread_bucket","edge_bucket"])

        write_csv(df5, outdir / "spread_summary.csv")
        validate_aggregation(df5_src, df5, "spread_full")

    except Exception as e:
        log_error(f"{league} SPREAD ERROR | {e}")

###############################################################
######################## MAIN #################################
###############################################################

def main():
    reset_logs()

    for league in ["NBA","NCAAB"]:
        path = INTERMEDIATE_DIR / f"work_{league.lower()}.csv"
        outdir = NBA_DEEP_DIR if league=="NBA" else NCAAB_DEEP_DIR

        df = safe_read(path)
        if df.empty:
            continue

        build_moneyline_outputs(df, league, outdir)
        build_spread_outputs(df, league, outdir)

    print("Basketball reports generated.")

if __name__ == "__main__":
    main()
