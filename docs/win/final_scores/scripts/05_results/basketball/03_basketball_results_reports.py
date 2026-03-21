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
    Writes 12 per-market detail files into detail_dir/by_market/:
      moneyline: by_edge, by_odds, by_kelly, by_side
      spread:    by_edge, by_spread, by_kelly, by_side
      total:     by_edge, by_total, by_kelly, by_side
    """

    has_kelly = "kelly_bucket" in work.columns

    for market_name in ["moneyline", "spread", "total"]:
        mdf = work[work["market_type"] == market_name].copy()
        if mdf.empty:
            continue

        slug = market_name
        prefix = f"{league_name.lower()}_{slug}"

        # --- by edge ---
        src = mdf[mdf["edge_bucket"] != "UNBUCKETED"]
        out = aggregate_results(src, ["edge_bucket"])
        write_csv(out, detail_dir / f"{prefix}_by_edge.csv")

        # --- by odds (moneyline only) ---
        if market_name == "moneyline" and "odds_bucket" in mdf.columns:
            src = mdf[mdf["odds_bucket"] != "UNBUCKETED"]
            out = aggregate_results(src, ["odds_bucket"])
            write_csv(out, detail_dir / f"{prefix}_by_odds.csv")

        # --- by spread bucket (spread only) ---
        if market_name == "spread" and "spread_bucket" in mdf.columns:
            src = mdf[mdf["spread_bucket"] != "UNBUCKETED"]
            out = aggregate_results(src, ["spread_bucket"])
            write_csv(out, detail_dir / f"{prefix}_by_spread.csv")

        # --- by total bucket (total only) ---
        if market_name == "total" and "total_bucket" in mdf.columns:
            src = mdf[mdf["total_bucket"] != "UNBUCKETED"]
            out = aggregate_results(src, ["total_bucket"])
            write_csv(out, detail_dir / f"{prefix}_by_total.csv")

        # --- by kelly ---
        if has_kelly:
            out = aggregate_results(mdf, ["kelly_bucket"])
            write_csv(out, detail_dir / f"{prefix}_by_kelly.csv")

        # --- by side ---
        out = aggregate_results(mdf, ["side_group"])
        write_csv(out, detail_dir / f"{prefix}_by_side.csv")


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


def run():
    nba = pd.read_csv(INPUT_DIR / "work_nba.csv")
    ncaab = pd.read_csv(INPUT_DIR / "work_ncaab.csv")

    # Existing reports
    build_moneyline_outputs(nba, NBA_OUTPUT_DIR)
    build_spread_outputs(nba, NBA_OUTPUT_DIR)
    build_total_outputs(nba, NBA_OUTPUT_DIR)

    build_moneyline_outputs(ncaab, NCAAB_OUTPUT_DIR)
    build_spread_outputs(ncaab, NCAAB_OUTPUT_DIR)
    build_total_outputs(ncaab, NCAAB_OUTPUT_DIR)

    # Per-market detail reports (new — mirrors hockey by_market/)
    build_detail_reports(nba, NBA_DETAIL_DIR, "nba")
    build_detail_reports(ncaab, NCAAB_DETAIL_DIR, "ncaab")

    # Market tally
    nba_market = market_tally(nba)
    ncaab_market = market_tally(ncaab)
    nba_market.to_csv("docs/win/final_scores/nba_market_tally.csv", index=False)
    ncaab_market.to_csv("docs/win/final_scores/ncaab_market_tally.csv", index=False)

    print("Reports complete.")


if __name__ == "__main__":
    run()
