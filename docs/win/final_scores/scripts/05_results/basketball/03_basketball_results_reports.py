#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

INPUT_DIR = Path("docs/win/final_scores/intermediate")

BASE_OUTPUT_DIR = Path("docs/win/final_scores/deeper_summaries")
NBA_OUTPUT_DIR = BASE_OUTPUT_DIR / "nba"
NCAAB_OUTPUT_DIR = BASE_OUTPUT_DIR / "ncaab"

NBA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
NCAAB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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


def build_moneyline_outputs(work, outdir):
    ml = work[work["market_type"] == "moneyline"].copy()
    if ml.empty:
        return

    src = ml[(ml["side_group"].isin(["HOME", "AWAY"])) & (ml["edge_bucket"] != "UNBUCKETED")]
    out = aggregate_results(src, ["market", "side_group", "edge_bucket"])
    write_csv(out, outdir / "moneyline_edge_bucket_home_away_summary.csv")

    src = ml[ml["edge_bucket"] != "UNBUCKETED"]
    out = aggregate_results(src, ["market", "edge_bucket"])
    write_csv(out, outdir / "moneyline_edge_bucket_summary.csv")

    src = ml[(ml["side_group"].isin(["HOME", "AWAY"])) & (ml["odds_bucket"] != "UNBUCKETED")]
    out = aggregate_results(src, ["market", "side_group", "odds_bucket"])
    write_csv(out, outdir / "moneyline_odds_bucket_home_away_summary.csv")

    src = ml[ml["odds_bucket"] != "UNBUCKETED"]
    out = aggregate_results(src, ["market", "odds_bucket"])
    write_csv(out, outdir / "moneyline_odds_bucket_summary.csv")

    src = ml[
        (ml["side_group"].isin(["HOME", "AWAY"])) &
        (ml["edge_bucket"] != "UNBUCKETED") &
        (ml["odds_bucket"] != "UNBUCKETED")
    ]
    out = aggregate_results(src, ["market", "market_type", "side_group", "odds_bucket", "edge_bucket"])
    write_csv(out, outdir / "moneyline_summary.csv")


def build_spread_outputs(work, outdir):
    sp = work[work["market_type"] == "spread"].copy()
    if sp.empty:
        return

    src = sp[(sp["side_group"].isin(["HOME", "AWAY"])) & (sp["edge_bucket"] != "UNBUCKETED")]
    out = aggregate_results(src, ["market", "side_group", "edge_bucket"])
    write_csv(out, outdir / "spread_edge_bucket_home_away_summary.csv")

    src = sp[sp["edge_bucket"] != "UNBUCKETED"]
    out = aggregate_results(src, ["market", "edge_bucket"])
    write_csv(out, outdir / "spread_edge_bucket_summary.csv")

    src = sp[(sp["side_group"].isin(["HOME", "AWAY"])) & (sp["spread_bucket"] != "UNBUCKETED")]
    out = aggregate_results(src, ["market", "side_group", "spread_bucket"])
    write_csv(out, outdir / "spread_bands_bucket_home_away_summary.csv")

    src = sp[sp["spread_bucket"] != "UNBUCKETED"]
    out = aggregate_results(src, ["market", "spread_bucket"])
    write_csv(out, outdir / "spread_bands_bucket_summary.csv")

    src = sp[
        (sp["side_group"].isin(["HOME", "AWAY"])) &
        (sp["spread_bucket"] != "UNBUCKETED") &
        (sp["edge_bucket"] != "UNBUCKETED")
    ]
    out = aggregate_results(src, ["market", "market_type", "side_group", "spread_bucket", "edge_bucket"])
    write_csv(out, outdir / "spread_summary.csv")


def build_total_outputs(work, outdir):
    tot = work[work["market_type"] == "total"].copy()
    if tot.empty:
        return

    src = tot[(tot["side_group"].isin(["OVER", "UNDER"])) & (tot["edge_bucket"] != "UNBUCKETED")]
    out = aggregate_results(src, ["market", "side_group", "edge_bucket"])
    write_csv(out, outdir / "total_edge_bucket_home_away_summary.csv")

    src = tot[tot["edge_bucket"] != "UNBUCKETED"]
    out = aggregate_results(src, ["market", "edge_bucket"])
    write_csv(out, outdir / "total_edge_bucket_summary.csv")

    src = tot[(tot["side_group"].isin(["OVER", "UNDER"])) & (tot["total_bucket"] != "UNBUCKETED")]
    out = aggregate_results(src, ["market", "side_group", "total_bucket"])
    write_csv(out, outdir / "total_bands_bucket_home_away_summary.csv")

    src = tot[tot["total_bucket"] != "UNBUCKETED"]
    out = aggregate_results(src, ["market", "total_bucket"])
    write_csv(out, outdir / "total_bands_bucket_summary.csv")

    src = tot[
        (tot["side_group"].isin(["OVER", "UNDER"])) &
        (tot["total_bucket"] != "UNBUCKETED") &
        (tot["edge_bucket"] != "UNBUCKETED")
    ]
    out = aggregate_results(src, ["market", "market_type", "side_group", "total_bucket", "edge_bucket"])
    write_csv(out, outdir / "total_summary.csv")


def run():
    nba = pd.read_csv(INPUT_DIR / "work_nba.csv")
    ncaab = pd.read_csv(INPUT_DIR / "work_ncaab.csv")

    build_moneyline_outputs(nba, NBA_OUTPUT_DIR)
    build_spread_outputs(nba, NBA_OUTPUT_DIR)
    build_total_outputs(nba, NBA_OUTPUT_DIR)

    build_moneyline_outputs(ncaab, NCAAB_OUTPUT_DIR)
    build_spread_outputs(ncaab, NCAAB_OUTPUT_DIR)
    build_total_outputs(ncaab, NCAAB_OUTPUT_DIR)

    print("Reports complete.")


if __name__ == "__main__":
    run()
