# docs/win/final_scores/scripts/05_results/basketball/03_basketball_results_reports.py
#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

INPUT_DIR = Path("docs/win/final_scores/intermediate")
OUTPUT_DIR = Path("docs/win/final_scores/deeper_summaries")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def summarize(df):

    wins = (df["bet_result"] == "Win").sum()
    losses = (df["bet_result"] == "Loss").sum()
    pushes = (df["bet_result"] == "Push").sum()

    total = wins + losses + pushes
    win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0

    return wins, losses, pushes, total, win_pct

def build(df, league):

    rows = []

    for bucket, sub in df.groupby("edge_bucket"):

        w,l,p,t,wp = summarize(sub)

        rows.append({
            "league": league,
            "edge_bucket": bucket,
            "wins": w,
            "losses": l,
            "pushes": p,
            "total": t,
            "win_pct": round(wp,4)
        })

    return pd.DataFrame(rows)

def run():

    nba = pd.read_csv(INPUT_DIR / "work_nba.csv")
    ncaab = pd.read_csv(INPUT_DIR / "work_ncaab.csv")

    nba_report = build(nba, "NBA")
    ncaab_report = build(ncaab, "NCAAB")

    nba_report.to_csv(OUTPUT_DIR / "nba_edge_report.csv", index=False)
    ncaab_report.to_csv(OUTPUT_DIR / "ncaab_edge_report.csv", index=False)

    print("Reports complete.")

if __name__ == "__main__":
    run()
