import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from scrapers.sportsbookreview import (
    NHLOddsScraper,
    NBAOddsScraper,
    NFLOddsScraper,
    MLBOddsScraper,
)

OUT_PATH = Path("bets/historic/odds_scraped.csv")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def normalize(df: pd.DataFrame, league: str) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["league"] = league

    # --- force numeric types safely ---
    numeric_cols = [
        "home_final",
        "away_final",
        "close_over_under",
        "home_close_ml",
        "away_close_ml",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- drop rows that cannot be evaluated ---
    df = df.dropna(subset=["home_final", "away_final", "close_over_under"])

    if df.empty:
        return df

    df["final_total"] = df["home_final"] + df["away_final"]

    # --- moneyline result (home perspective) ---
    df["ml_result_home"] = "Loss"
    df.loc[df["home_final"] > df["away_final"], "ml_result_home"] = "Win"

    # --- over / under result ---
    df["ou_result"] = "Push"
    df.loc[df["final_total"] > df["close_over_under"], "ou_result"] = "Over"
    df.loc[df["final_total"] < df["close_over_under"], "ou_result"] = "Under"

    return df[
        [
            "date",
            "league",
            "home_team",
            "away_team",
            "home_close_ml",
            "away_close_ml",
            "close_over_under",
            "home_final",
            "away_final",
            "final_total",
            "ml_result_home",
            "ou_result",
        ]
    ]


def main():
    years = range(2019, 2027)

    frames = []

    for league, scraper in [
        ("nhl", NHLOddsScraper),
        ("nba", NBAOddsScraper),
        ("nfl", NFLOddsScraper),
        ("mlb", MLBOddsScraper),
    ]:
        try:
            df = scraper(years).driver()
            df = normalize(df, league)
            if not df.empty:
                frames.append(df)
        except Exception as e:
            print(f"[WARN] {league.upper()} failed: {e}")

    if not frames:
        print("[WARN] No data collected — CSV not written")
        return

    out = pd.concat(frames, ignore_index=True)

    out.to_csv(OUT_PATH, index=False)
    print(f"[OK] Wrote {len(out):,} rows → {OUT_PATH}")


if __name__ == "__main__":
    main()
