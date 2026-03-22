#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

INPUT_DIR = Path("docs/win/final_scores/intermediate")

BASE_OUTPUT_DIR = Path("docs/win/final_scores/deeper_summaries")
NBA_OUTPUT_DIR = BASE_OUTPUT_DIR / "nba"
NCAAB_OUTPUT_DIR = BASE_OUTPUT_DIR / "ncaab"
NBA_DETAIL_DIR = NBA_OUTPUT_DIR / "by_market"
NCAAB_DETAIL_DIR = NCAAB_OUTPUT_DIR / "by_market"

NBA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
NCAAB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
NBA_DETAIL_DIR.mkdir(parents=True, exist_ok=True)
NCAAB_DETAIL_DIR.mkdir(parents=True, exist_ok=True)


def summarize(df):
    wins = int((df["bet_result"] == "Win").sum())
    losses = int((df["bet_result"] == "Loss").sum())
    pushes = int((df["bet_result"] == "Push").sum())
    total = wins + losses + pushes
    win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0.0
    return wins, losses, pushes, total, round(win_pct, 4)


def aggregate_results(df, group_cols):
    if df.empty:
        return pd.DataFrame(columns=group_cols + ["Win", "Loss", "Push", "Total", "Win_Pct"])
    rows = []
    for keys, sub in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        wins, losses, pushes, total, win_pct = summarize(sub)
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


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


# -------------------------------------------------------
# ENRICHMENT  (take_odds, bet_units, kelly_bucket)
# -------------------------------------------------------

def _take_odds(row):
    mt   = str(row.get("market_type", "")).lower()
    side = str(row.get("bet_side",    "")).lower()
    if mt == "moneyline":
        col = "home_dk_moneyline_american" if side == "home" else "away_dk_moneyline_american"
    elif mt == "spread":
        col = "home_dk_spread_american" if side == "home" else "away_dk_spread_american"
    elif mt == "total":
        col = "dk_total_over_american" if side == "over" else "dk_total_under_american"
    else:
        return None
    return row.get(col, None)


def _kelly_value(row):
    mt   = str(row.get("market_type", "")).lower()
    side = str(row.get("bet_side",    "")).lower()
    if mt == "moneyline":
        col = "home_ml_kelly" if side == "home" else "away_ml_kelly"
    elif mt == "spread":
        col = "home_spread_kelly" if side == "home" else "away_spread_kelly"
    elif mt == "total":
        col = "over_kelly" if side == "over" else "under_kelly"
    else:
        return None
    return row.get(col, None)


def _kelly_bucket(k):
    try:
        k = float(k)
    except (TypeError, ValueError):
        return "UNBUCKETED"
    if k < 0.01:  return "0-1%"
    if k < 0.02:  return "1-2%"
    if k < 0.05:  return "2-5%"
    return "5%+"


def _units_won(odds, result):
    result = str(result)
    if result == "Push":  return 0.0
    if result == "Loss":  return -1.0
    try:
        odds = float(odds)
    except (TypeError, ValueError):
        return None
    return odds / 100.0 if odds >= 0 else 100.0 / abs(odds)


def enrich_work(df):
    """Add take_odds, bet_units, kelly_value, kelly_bucket columns."""
    df = df.copy()
    df["take_odds"]    = df.apply(_take_odds,   axis=1)
    df["kelly_value"]  = df.apply(_kelly_value, axis=1)
    df["kelly_bucket"] = df["kelly_value"].apply(_kelly_bucket)
    df["bet_units"]    = df.apply(
        lambda r: _units_won(r["take_odds"], r["bet_result"]), axis=1
    )
    return df


# -------------------------------------------------------
# FULL AGGREGATION  (dashboard-compatible columns)
# -------------------------------------------------------

def aggregate_full(df, group_cols):
    """Produce bets/wins/losses/win_rate/units/roi/avg_edge/avg_odds per group."""
    extra = ["bets", "wins", "losses", "win_rate", "units", "roi", "avg_edge", "avg_odds"]
    if df.empty:
        return pd.DataFrame(columns=group_cols + extra)
    rows = []
    for keys, sub in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        wins   = int((sub["bet_result"] == "Win").sum())
        losses = int((sub["bet_result"] == "Loss").sum())
        pushes = int((sub["bet_result"] == "Push").sum())
        bets   = wins + losses + pushes
        win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0.0
        unit_col = sub["bet_units"].dropna()
        total_units = float(unit_col.sum()) if not unit_col.empty else 0.0
        roi = total_units / bets if bets > 0 else 0.0

        edge_col = sub["selected_edge"].dropna() if "selected_edge" in sub.columns else pd.Series(dtype=float)
        avg_edge = float(edge_col.mean()) if not edge_col.empty else None

        odds_col = sub["take_odds"].dropna() if "take_odds" in sub.columns else pd.Series(dtype=float)
        avg_odds = float(odds_col.mean()) if not odds_col.empty else None

        row = {col: keys[i] for i, col in enumerate(group_cols)}
        row.update({
            "bets":     bets,
            "wins":     wins,
            "losses":   losses,
            "win_rate": round(win_rate, 4),
            "units":    round(total_units, 4),
            "roi":      round(roi, 4),
            "avg_edge": round(avg_edge, 4) if avg_edge is not None else None,
            "avg_odds": round(avg_odds, 1) if avg_odds is not None else None,
        })
        rows.append(row)
    return pd.DataFrame(rows).sort_values(group_cols).reset_index(drop=True)


def market_tally(df):
    rows = []
    for (market, market_type), sub in df.groupby(["market", "market_type"]):
        wins = (sub["bet_result"] == "Win").sum()
        losses = (sub["bet_result"] == "Loss").sum()
        pushes = (sub["bet_result"] == "Push").sum()
        total = wins + losses + pushes
        win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0
        rows.append({
            "market": market,
            "market_type": market_type,
            "Win": wins,
            "Loss": losses,
            "Push": pushes,
            "Total": total,
            "Win_Pct": round(win_pct, 4)
        })
    return pd.DataFrame(rows)


# -------------------------------------------------------
# PER-MARKET DETAIL REPORTS (mirrors hockey by_market/)
# -------------------------------------------------------

def build_detail_reports(work, detail_dir, league_name):
    """
    Writes per-market detail files into detail_dir/by_market/:
      moneyline: by_edge, by_odds, by_kelly, by_side
      spread:    by_edge, by_odds, by_kelly, by_side
      total:     by_edge, by_odds, by_kelly, by_side
    """
    for market_name in ["moneyline", "spread", "total"]:
        mdf = work[work["market_type"] == market_name].copy()
        if mdf.empty:
            continue

        prefix = f"{league_name.lower()}_{market_name}"

        # --- by edge ---
        src = mdf[mdf["edge_bucket"] != "UNBUCKETED"]
        write_csv(aggregate_full(src, ["edge_bucket"]), detail_dir / f"{prefix}_by_edge.csv")

        # --- by odds ---
        if "odds_bucket" in mdf.columns:
            src = mdf[mdf["odds_bucket"] != "UNBUCKETED"]
            write_csv(aggregate_full(src, ["odds_bucket"]), detail_dir / f"{prefix}_by_odds.csv")

        # --- by kelly ---
        if "kelly_bucket" in mdf.columns:
            src = mdf[mdf["kelly_bucket"] != "UNBUCKETED"]
            write_csv(aggregate_full(src, ["kelly_bucket"]), detail_dir / f"{prefix}_by_kelly.csv")

        # --- by side ---
        write_csv(aggregate_full(mdf, ["side_group"]), detail_dir / f"{prefix}_by_side.csv")


# -------------------------------------------------------
# EXISTING REPORTS (unchanged)
# -------------------------------------------------------

def build_moneyline_outputs(work, outdir):
    ml = work[work["market_type"] == "moneyline"].copy()
    if ml.empty:
        return

    src = ml[(ml["side_group"].isin(["HOME", "AWAY"])) & (ml["edge_bucket"] != "UNBUCKETED")]
    write_csv(aggregate_results(src, ["market", "side_group", "edge_bucket"]),
              outdir / "moneyline_edge_bucket_home_away_summary.csv")

    src = ml[ml["edge_bucket"] != "UNBUCKETED"]
    write_csv(aggregate_results(src, ["market", "edge_bucket"]),
              outdir / "moneyline_edge_bucket_summary.csv")

    src = ml[(ml["side_group"].isin(["HOME", "AWAY"])) & (ml["odds_bucket"] != "UNBUCKETED")]
    write_csv(aggregate_results(src, ["market", "side_group", "odds_bucket"]),
              outdir / "moneyline_odds_bucket_home_away_summary.csv")

    src = ml[ml["odds_bucket"] != "UNBUCKETED"]
    write_csv(aggregate_results(src, ["market", "odds_bucket"]),
              outdir / "moneyline_odds_bucket_summary.csv")

    src = ml[
        (ml["side_group"].isin(["HOME", "AWAY"])) &
        (ml["edge_bucket"] != "UNBUCKETED") &
        (ml["odds_bucket"] != "UNBUCKETED")
    ]
    write_csv(aggregate_results(src, ["market", "market_type", "side_group", "odds_bucket", "edge_bucket"]),
              outdir / "moneyline_summary.csv")


def build_spread_outputs(work, outdir):
    sp = work[work["market_type"] == "spread"].copy()
    if sp.empty:
        return

    src = sp[(sp["side_group"].isin(["HOME", "AWAY"])) & (sp["edge_bucket"] != "UNBUCKETED")]
    write_csv(aggregate_results(src, ["market", "side_group", "edge_bucket"]),
              outdir / "spread_edge_bucket_home_away_summary.csv")

    src = sp[sp["edge_bucket"] != "UNBUCKETED"]
    write_csv(aggregate_results(src, ["market", "edge_bucket"]),
              outdir / "spread_edge_bucket_summary.csv")

    src = sp[(sp["side_group"].isin(["HOME", "AWAY"])) & (sp["spread_bucket"] != "UNBUCKETED")]
    write_csv(aggregate_results(src, ["market", "side_group", "spread_bucket"]),
              outdir / "spread_bands_bucket_home_away_summary.csv")

    src = sp[sp["spread_bucket"] != "UNBUCKETED"]
    write_csv(aggregate_results(src, ["market", "spread_bucket"]),
              outdir / "spread_bands_bucket_summary.csv")

    src = sp[
        (sp["side_group"].isin(["HOME", "AWAY"])) &
        (sp["spread_bucket"] != "UNBUCKETED") &
        (sp["edge_bucket"] != "UNBUCKETED")
    ]
    write_csv(aggregate_results(src, ["market", "market_type", "side_group", "spread_bucket", "edge_bucket"]),
              outdir / "spread_summary.csv")


def build_total_outputs(work, outdir):
    tot = work[work["market_type"] == "total"].copy()
    if tot.empty:
        return

    src = tot[(tot["side_group"].isin(["OVER", "UNDER"])) & (tot["edge_bucket"] != "UNBUCKETED")]
    write_csv(aggregate_results(src, ["market", "side_group", "edge_bucket"]),
              outdir / "total_edge_bucket_home_away_summary.csv")

    src = tot[tot["edge_bucket"] != "UNBUCKETED"]
    write_csv(aggregate_results(src, ["market", "edge_bucket"]),
              outdir / "total_edge_bucket_summary.csv")

    src = tot[(tot["side_group"].isin(["OVER", "UNDER"])) & (tot["total_bucket"] != "UNBUCKETED")]
    write_csv(aggregate_results(src, ["market", "side_group", "total_bucket"]),
              outdir / "total_bands_bucket_home_away_summary.csv")

    src = tot[tot["total_bucket"] != "UNBUCKETED"]
    write_csv(aggregate_results(src, ["market", "total_bucket"]),
              outdir / "total_bands_bucket_summary.csv")

    src = tot[
        (tot["side_group"].isin(["OVER", "UNDER"])) &
        (tot["total_bucket"] != "UNBUCKETED") &
        (tot["edge_bucket"] != "UNBUCKETED")
    ]
    write_csv(aggregate_results(src, ["market", "market_type", "side_group", "total_bucket", "edge_bucket"]),
              outdir / "total_summary.csv")


def build_summary_files(work, outdir, league_name):
    """Generate the 5 summary CSVs consumed by the dashboard."""
    lg = league_name.lower()

    # Overall
    write_csv(aggregate_full(work, []).assign(league=league_name) if work.empty
              else pd.DataFrame([{
                  "bets":     len(work),
                  "wins":     int((work["bet_result"] == "Win").sum()),
                  "losses":   int((work["bet_result"] == "Loss").sum()),
                  "win_rate": round(
                      (work["bet_result"] == "Win").sum() /
                      max((work["bet_result"].isin(["Win","Loss"])).sum(), 1), 4),
                  "units":    round(float(work["bet_units"].dropna().sum()), 4),
                  "roi":      round(float(work["bet_units"].dropna().sum()) / max(len(work), 1), 4),
                  "avg_edge": round(float(work["selected_edge"].dropna().mean()), 4)
                              if "selected_edge" in work.columns and not work["selected_edge"].dropna().empty else None,
                  "avg_odds": round(float(work["take_odds"].dropna().mean()), 1)
                              if "take_odds" in work.columns and not work["take_odds"].dropna().empty else None,
              }]),
              outdir / f"{lg}_summary_overall.csv")

    # By market
    write_csv(aggregate_full(work, ["market_type"]),
              outdir / f"{lg}_summary_by_market.csv")

    # By side group
    write_csv(aggregate_full(work, ["side_group"]),
              outdir / f"{lg}_summary_by_side_group.csv")

    # By date
    write_csv(aggregate_full(work, ["game_date"]),
              outdir / f"{lg}_summary_by_date.csv")

    # Bet log
    log_cols = ["game_date", "away_team", "home_team", "market_type",
                "bet_side", "line", "take_odds", "selected_edge", "bet_result", "bet_units"]
    available = [c for c in log_cols if c in work.columns]
    log_df = work[available].copy()
    if "bet_units" in log_df.columns:
        log_df = log_df.rename(columns={"bet_units": "units"})
    write_csv(log_df, outdir / f"{lg}_bet_log.csv")


def run():
    nba   = enrich_work(pd.read_csv(INPUT_DIR / "work_nba.csv"))
    ncaab = enrich_work(pd.read_csv(INPUT_DIR / "work_ncaab.csv"))

    # Existing reports
    build_moneyline_outputs(nba, NBA_OUTPUT_DIR)
    build_spread_outputs(nba, NBA_OUTPUT_DIR)
    build_total_outputs(nba, NBA_OUTPUT_DIR)

    build_moneyline_outputs(ncaab, NCAAB_OUTPUT_DIR)
    build_spread_outputs(ncaab, NCAAB_OUTPUT_DIR)
    build_total_outputs(ncaab, NCAAB_OUTPUT_DIR)

    # Per-market detail reports
    build_detail_reports(nba, NBA_DETAIL_DIR, "nba")
    build_detail_reports(ncaab, NCAAB_DETAIL_DIR, "ncaab")

    # Dashboard summary files
    build_summary_files(nba,   NBA_OUTPUT_DIR,   "nba")
    build_summary_files(ncaab, NCAAB_OUTPUT_DIR, "ncaab")

    # Market tally
    nba_market   = market_tally(nba)
    ncaab_market = market_tally(ncaab)
    nba_market.to_csv("docs/win/final_scores/nba_market_tally.csv", index=False)
    ncaab_market.to_csv("docs/win/final_scores/ncaab_market_tally.csv", index=False)

    print("Reports complete.")


if __name__ == "__main__":
    run()
