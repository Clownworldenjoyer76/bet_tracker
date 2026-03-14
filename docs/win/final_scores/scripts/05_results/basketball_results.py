#!/usr/bin/env python3
# docs/win/final_scores/scripts/05_results/basketball_results.py

import glob
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

###############################################################
######################## PATH CONFIG ##########################
###############################################################

BASE = Path("docs/win/basketball")
SELECT_DIR = BASE / "04_select/daily_slate"

NBA_SCORE_DIR = Path("docs/win/final_scores/results/nba/final_scores")
NCAAB_SCORE_DIR = Path("docs/win/final_scores/results/ncaab/final_scores")

NBA_OUTPUT = Path("docs/win/final_scores/results/nba/graded")
NCAAB_OUTPUT = Path("docs/win/final_scores/results/ncaab/graded")

DEEP_SUMMARY_BASE = Path("docs/win/final_scores/deeper_summaries")
NBA_DEEP_DIR = DEEP_SUMMARY_BASE / "nba"
NCAAB_DEEP_DIR = DEEP_SUMMARY_BASE / "ncaab"

NBA_MARKET_TALLY = Path("docs/win/final_scores/nba_market_tally.csv")
NCAAB_MARKET_TALLY = Path("docs/win/final_scores/ncaab_market_tally.csv")

ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)

EDGE_REPORT = ERROR_DIR / "basketball_edge_summary.txt"
LOG_FILE = ERROR_DIR / "basketball_results_log.txt"

###############################################################
######################## HELPERS ##############################
###############################################################

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {msg}\n")


def safe_read(path):
    try:
        path = Path(path)
        if not path.exists():
            log(f"MISSING FILE {path}")
            return pd.DataFrame()

        df = pd.read_csv(path)

        if df is None or df.empty:
            log(f"EMPTY FILE {path}")
            return pd.DataFrame()

        return df

    except Exception as e:
        log(f"READ ERROR {path} | {e}")
        return pd.DataFrame()


def clear_old_outputs():
    for outdir in [NBA_OUTPUT, NCAAB_OUTPUT]:
        outdir.mkdir(parents=True, exist_ok=True)
        for f in outdir.glob("*_results_*.csv"):
            f.unlink(missing_ok=True)
        for f in outdir.glob("*_final.csv"):
            f.unlink(missing_ok=True)

    for deep_dir in [NBA_DEEP_DIR, NCAAB_DEEP_DIR]:
        deep_dir.mkdir(parents=True, exist_ok=True)
        for f in deep_dir.glob("*.csv"):
            f.unlink(missing_ok=True)

    NBA_MARKET_TALLY.unlink(missing_ok=True)
    NCAAB_MARKET_TALLY.unlink(missing_ok=True)
    EDGE_REPORT.unlink(missing_ok=True)

###############################################################
######################## OUTCOME LOGIC ########################
###############################################################

def determine_outcome(row):
    try:
        market = str(row.get("market_type", "")).strip().lower()
        side = str(row.get("bet_side", "")).strip().lower()

        away = float(row["away_score"])
        home = float(row["home_score"])

        if market == "moneyline":
            if away == home:
                return "Push"
            if side == "home":
                return "Win" if home > away else "Loss"
            if side == "away":
                return "Win" if away > home else "Loss"

        if market == "spread":
            line = float(row.get("line", 0))
            if side == "home":
                diff = (home + line) - away
            elif side == "away":
                diff = (away + line) - home
            else:
                return "Unknown"

            if abs(diff) < 1e-9:
                return "Push"
            return "Win" if diff > 0 else "Loss"

        if market == "total":
            line = float(row.get("line", 0))
            total = away + home

            if abs(total - line) < 1e-9:
                return "Push"

            if side == "over":
                return "Win" if total > line else "Loss"
            if side == "under":
                return "Win" if total < line else "Loss"

    except Exception:
        pass

    return "Unknown"

###############################################################
######################## GRADING ##############################
###############################################################

def grade_league(league):
    if league == "NBA":
        score_dir = NBA_SCORE_DIR
        output_dir = NBA_OUTPUT
        pattern = "*_nba.csv"
        suffix = "NBA"
    else:
        score_dir = NCAAB_SCORE_DIR
        output_dir = NCAAB_OUTPUT
        pattern = "*_ncaab.csv"
        suffix = "NCAAB"

    output_dir.mkdir(parents=True, exist_ok=True)

    bet_files = glob.glob(str(SELECT_DIR / pattern))
    dates = set()

    for f in bet_files:
        m = re.search(r"(\d{4}_\d{2}_\d{2})", f)
        if m:
            dates.add(m.group(1))

    for date in sorted(dates):
        score_file = score_dir / f"{date}_final_scores_{suffix}.csv"
        if not score_file.exists():
            log(f"{league} SCORE FILE MISSING {score_file}")
            continue

        if league == "NBA":
            bet_paths = glob.glob(str(SELECT_DIR / f"{date}_nba.csv"))
        else:
            bet_paths = glob.glob(str(SELECT_DIR / f"{date}_ncaab.csv"))

        dfs = [safe_read(x) for x in bet_paths]
        dfs = [d for d in dfs if not d.empty]

        if not dfs:
            log(f"{league} NO BET FILES {date}")
            continue

        bets = pd.concat(dfs, ignore_index=True)
        scores = safe_read(score_file)

        if scores.empty:
            log(f"{league} SCORE FILE EMPTY {date}")
            continue

        try:
            df = pd.merge(
                bets,
                scores,
                on=["away_team", "home_team", "game_date"],
                validate="many_to_one"
            )
        except Exception as e:
            log(f"{league} MERGE ERROR {date} | {e}")
            continue

        df["bet_result"] = df.apply(determine_outcome, axis=1)

        outfile = output_dir / f"{date}_results_{suffix}.csv"
        df.to_csv(outfile, index=False)

        log(f"{league} GRADED {date} ROWS={len(df)}")


def build_master(league):
    if league == "NBA":
        outdir = NBA_OUTPUT
        suffix = "NBA"
    else:
        outdir = NCAAB_OUTPUT
        suffix = "NCAAB"

    files = sorted(glob.glob(str(outdir / f"*_results_{suffix}.csv")))
    dfs = [safe_read(f) for f in files]
    dfs = [d for d in dfs if not d.empty]

    if not dfs:
        log(f"{league} NO GRADED FILES FOR MASTER")
        return

    df = pd.concat(dfs, ignore_index=True)

    sort_cols = [c for c in ["game_date", "away_team", "home_team", "market_type", "bet_side"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols, kind="mergesort")

    master = outdir / f"{suffix}_final.csv"
    df.to_csv(master, index=False)

    log(f"{league} MASTER BUILT ROWS={len(df)}")

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

    return pd.DataFrame(rows)

###############################################################
######################## DERIVED FIELDS #######################
###############################################################

def to_float(value):
    return pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]


def side_group_from_bet_side(row):
    market_type = str(row.get("market_type", "")).strip().lower()
    bet_side = str(row.get("bet_side", "")).strip().lower()

    if market_type in {"moneyline", "spread"}:
        if bet_side == "home":
            return "HOME"
        if bet_side == "away":
            return "AWAY"

    if market_type == "total":
        if bet_side == "over":
            return "OVER"
        if bet_side == "under":
            return "UNDER"

    return ""


def selected_edge(row):
    market_type = str(row.get("market_type", "")).strip().lower()
    side_group = row.get("side_group", "")

    if market_type == "moneyline":
        if side_group == "HOME":
            return to_float(row.get("home_ml_edge_decimal"))
        if side_group == "AWAY":
            return to_float(row.get("away_ml_edge_decimal"))

    if market_type == "spread":
        if side_group == "HOME":
            return to_float(row.get("home_spread_edge_decimal"))
        if side_group == "AWAY":
            return to_float(row.get("away_spread_edge_decimal"))

    if market_type == "total":
        if side_group == "OVER":
            return to_float(row.get("over_edge_decimal"))
        if side_group == "UNDER":
            return to_float(row.get("under_edge_decimal"))

    return pd.NA


def selected_moneyline_odds(row):
    side_group = row.get("side_group", "")
    if side_group == "HOME":
        return to_float(row.get("home_dk_moneyline_american"))
    if side_group == "AWAY":
        return to_float(row.get("away_dk_moneyline_american"))
    return pd.NA


def selected_spread_line(row):
    side_group = row.get("side_group", "")
    if side_group == "HOME":
        return to_float(row.get("home_spread"))
    if side_group == "AWAY":
        return to_float(row.get("away_spread"))
    return pd.NA


def selected_total_line(row):
    return to_float(row.get("total"))


###############################################################
######################## BUCKETS ##############################
###############################################################

def edge_bucket(value):
    val = to_float(value)

    if pd.isna(val):
        return ""

    if val < 0:
        return "<0"
    if val < 0.01:
        return "0.00_to_0.0099"
    if val < 0.02:
        return "0.01_to_0.0199"
    if val < 0.03:
        return "0.02_to_0.0299"
    if val < 0.04:
        return "0.03_to_0.0399"
    if val < 0.05:
        return "0.04_to_0.0499"
    if val < 0.075:
        return "0.05_to_0.0749"
    if val < 0.10:
        return "0.075_to_0.0999"
    return "0.10_plus"


def odds_bucket(value):
    val = to_float(value)

    if pd.isna(val):
        return ""

    if val <= -200:
        return "minus_200_or_lower"
    if val <= -150:
        return "minus_199_to_minus_150"
    if val <= -125:
        return "minus_149_to_minus_125"
    if val <= -110:
        return "minus_124_to_minus_110"
    if val <= -101:
        return "minus_109_to_minus_101"
    if val <= 100:
        return "minus_100_to_plus_100"
    if val <= 125:
        return "plus_101_to_plus_125"
    if val <= 150:
        return "plus_126_to_plus_150"
    if val <= 200:
        return "plus_151_to_plus_200"
    return "plus_201_or_higher"


def spread_bucket(value):
    val = to_float(value)

    if pd.isna(val):
        return ""

    bands = [
        (-99, -15, "minus_99_to_minus_15.0"),
        (-15, -10, "minus_15.0_to_minus_10.0"),
        (-10, -7.5, "minus_10.0_to_minus_7.5"),
        (-7.5, -5, "minus_7.5_to_minus_5.0"),
        (-5, -3, "minus_5.0_to_minus_3.0"),
        (-3, -2, "minus_3.0_to_minus_2.0"),
        (-2, -1, "minus_2.0_to_minus_1.0"),
        (-1, 1, "minus_1.0_to_plus_1.0"),
        (1, 2, "plus_1.0_to_plus_2.0"),
        (2, 3, "plus_2.0_to_plus_3.0"),
        (3, 5, "plus_3.0_to_plus_5.0"),
        (5, 7.5, "plus_5.0_to_plus_7.5"),
        (7.5, 10, "plus_7.5_to_plus_10.0"),
        (10, 15, "plus_10.0_to_plus_15.0"),
        (15, 99, "plus_15.0_or_higher"),
    ]

    for low, high, label in bands:
        if low <= val < high:
            return label

    if val == 99:
        return "plus_15.0_or_higher"

    return ""


def total_bucket(value):
    val = to_float(value)

    if pd.isna(val):
        return ""

    start = int(val // 5) * 5
    end = start + 4.9
    return f"{start}_to_{end:.1f}"


###############################################################
######################## PREP ANALYTICS #######################
###############################################################

def prepare_work_df(df, league):
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    if "bet_result" in work.columns:
        work["bet_result"] = work["bet_result"].astype(str).str.strip().str.title()

    work["market"] = league
    work["market_type"] = work["market_type"].astype(str).str.strip().str.lower()
    work["side_group"] = work.apply(side_group_from_bet_side, axis=1)
    work["selected_edge"] = work.apply(selected_edge, axis=1)
    work["moneyline_odds_value"] = work.apply(selected_moneyline_odds, axis=1)
    work["spread_value"] = work.apply(selected_spread_line, axis=1)
    work["total_value"] = work.apply(selected_total_line, axis=1)

    work["edge_bucket"] = work["selected_edge"].apply(edge_bucket)
    work["odds_bucket"] = work["moneyline_odds_value"].apply(odds_bucket)
    work["spread_bucket"] = work["spread_value"].apply(spread_bucket)
    work["total_bucket"] = work["total_value"].apply(total_bucket)

    return work

###############################################################
######################## WRITE DIAGNOSTICS ####################
###############################################################

def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    log(f"WROTE {path}")


def build_moneyline_outputs(work, league, outdir):
    ml = work[work["market_type"] == "moneyline"].copy()
    if ml.empty:
        return

    df1 = aggregate_results(
        ml[(ml["side_group"].isin(["HOME", "AWAY"])) & (ml["edge_bucket"] != "")],
        ["market", "side_group", "edge_bucket"]
    )
    write_csv(df1, outdir / "moneyline_edge_bucket_home_away_summary.csv")

    df2 = aggregate_results(
        ml[ml["edge_bucket"] != ""],
        ["market", "edge_bucket"]
    )
    write_csv(df2, outdir / "moneyline_edge_bucket_summary.csv")

    df3 = aggregate_results(
        ml[(ml["side_group"].isin(["HOME", "AWAY"])) & (ml["odds_bucket"] != "")],
        ["market", "side_group", "odds_bucket"]
    )
    write_csv(df3, outdir / "moneyline_odds_bucket_home_away_summary.csv")

    df4 = aggregate_results(
        ml[ml["odds_bucket"] != ""],
        ["market", "odds_bucket"]
    )
    write_csv(df4, outdir / "moneyline_odds_bucket_summary.csv")

    df5 = aggregate_results(
        ml[(ml["side_group"].isin(["HOME", "AWAY"])) & (ml["odds_bucket"] != "") & (ml["edge_bucket"] != "")],
        ["market", "market_type", "side_group", "odds_bucket", "edge_bucket"]
    )
    write_csv(df5, outdir / "moneyline_summary.csv")


def build_spread_outputs(work, league, outdir):
    sp = work[work["market_type"] == "spread"].copy()
    if sp.empty:
        return

    df1 = aggregate_results(
        sp[(sp["side_group"].isin(["HOME", "AWAY"])) & (sp["edge_bucket"] != "")],
        ["market", "side_group", "edge_bucket"]
    )
    write_csv(df1, outdir / "spread_edge_bucket_home_away_summary.csv")

    df2 = aggregate_results(
        sp[sp["edge_bucket"] != ""],
        ["market", "edge_bucket"]
    )
    write_csv(df2, outdir / "spread_edge_bucket_summary.csv")

    df3 = aggregate_results(
        sp[(sp["side_group"].isin(["HOME", "AWAY"])) & (sp["spread_bucket"] != "")],
        ["market", "side_group", "spread_bucket"]
    )
    write_csv(df3, outdir / "spread_bands_bucket_home_away_summary.csv")

    df4 = aggregate_results(
        sp[sp["spread_bucket"] != ""],
        ["market", "spread_bucket"]
    )
    write_csv(df4, outdir / "spread_bands_bucket_summary.csv")

    df5 = aggregate_results(
        sp[(sp["side_group"].isin(["HOME", "AWAY"])) & (sp["spread_bucket"] != "") & (sp["edge_bucket"] != "")],
        ["market", "market_type", "side_group", "spread_bucket", "edge_bucket"]
    )
    write_csv(df5, outdir / "spread_summary.csv")


def build_total_outputs(work, league, outdir):
    tot = work[work["market_type"] == "total"].copy()
    if tot.empty:
        return

    df1 = aggregate_results(
        tot[(tot["side_group"].isin(["OVER", "UNDER"])) & (tot["edge_bucket"] != "")],
        ["market", "side_group", "edge_bucket"]
    )
    write_csv(df1, outdir / "total_edge_bucket_home_away_summary.csv")

    df2 = aggregate_results(
        tot[tot["edge_bucket"] != ""],
        ["market", "edge_bucket"]
    )
    write_csv(df2, outdir / "total_edge_bucket_summary.csv")

    df3 = aggregate_results(
        tot[(tot["side_group"].isin(["OVER", "UNDER"])) & (tot["total_bucket"] != "")],
        ["market", "side_group", "total_bucket"]
    )
    write_csv(df3, outdir / "total_bands_bucket_home_away_summary.csv")

    df4 = aggregate_results(
        tot[tot["total_bucket"] != ""],
        ["market", "total_bucket"]
    )
    write_csv(df4, outdir / "total_bands_bucket_summary.csv")

    df5 = aggregate_results(
        tot[(tot["side_group"].isin(["OVER", "UNDER"])) & (tot["total_bucket"] != "") & (tot["edge_bucket"] != "")],
        ["market", "market_type", "side_group", "total_bucket", "edge_bucket"]
    )
    write_csv(df5, outdir / "total_summary.csv")


def build_market_tally(df, league):
    out_rows = []

    for market_type in ["moneyline", "spread", "total"]:
        sub = df[df["market_type"] == market_type]
        w, l, p, t, pct = summarize(sub)
        out_rows.append({
            "market": league,
            "market_type": market_type,
            "Win": w,
            "Loss": l,
            "Push": p,
            "Total": t,
            "Win_Pct": pct
        })

    out = pd.DataFrame(out_rows)

    if league == "NBA":
        write_csv(out, NBA_MARKET_TALLY)
    else:
        write_csv(out, NCAAB_MARKET_TALLY)


###############################################################
######################## EDGE REPORT ##########################
###############################################################

def build_edge_report():
    rows = []

    for league, path in [
        ("NBA", NBA_OUTPUT / "NBA_final.csv"),
        ("NCAAB", NCAAB_OUTPUT / "NCAAB_final.csv"),
    ]:
        df = safe_read(path)
        if df.empty:
            continue

        work = prepare_work_df(df, league)
        if work.empty:
            continue

        win_edges = work.loc[work["bet_result"] == "Win", "selected_edge"].dropna().tolist()
        loss_edges = work.loc[work["bet_result"] == "Loss", "selected_edge"].dropna().tolist()

        win_avg = sum(win_edges) / len(win_edges) if win_edges else 0
        loss_avg = sum(loss_edges) / len(loss_edges) if loss_edges else 0

        rows.append("")
        rows.append(league)
        rows.append(f"Win edge avg: {win_avg:.4f}")
        rows.append(f"Loss edge avg: {loss_avg:.4f}")
        rows.append(f"Signal: {'CORRECT' if win_avg > loss_avg else 'INVERTED'}")

    with open(EDGE_REPORT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(r + "\n")

    log(f"WROTE {EDGE_REPORT}")

###############################################################
######################## MAIN #################################
###############################################################

def main():
    open(LOG_FILE, "w", encoding="utf-8").close()
    clear_old_outputs()

    for league in ["NBA", "NCAAB"]:
        grade_league(league)
        build_master(league)

        if league == "NBA":
            path = NBA_OUTPUT / "NBA_final.csv"
            outdir = NBA_DEEP_DIR
        else:
            path = NCAAB_OUTPUT / "NCAAB_final.csv"
            outdir = NCAAB_DEEP_DIR

        df = safe_read(path)
        if df.empty:
            log(f"{league} MASTER EMPTY AFTER BUILD")
            continue

        work = prepare_work_df(df, league)
        if work.empty:
            log(f"{league} WORK DF EMPTY")
            continue

        build_market_tally(work, league)
        build_moneyline_outputs(work, league, outdir)
        build_spread_outputs(work, league, outdir)
        build_total_outputs(work, league, outdir)

    build_edge_report()
    print("Basketball results pipeline complete.")


if __name__ == "__main__":
    main()
