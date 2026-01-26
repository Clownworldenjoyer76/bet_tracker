import pandas as pd
from pathlib import Path

from scraper import (
    NHLOddsScraper,
    NBAOddsScraper,
    NFLOddsScraper,
    MLBOddsScraper,
)

OUT_PATH = Path("bets/historic/odds_scraped.csv")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def normalize(df, league):
    df = df.copy()

    df["league"] = league
    df["final_total"] = df["home_final"] + df["away_final"]

    # Moneyline result (home team)
    df["ml_result_home"] = (
        df["home_final"] > df["away_final"]
    ).map({True: "Win", False: "Loss"})

    # Over / Under result
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
            "close_over_under_odds",
            "home_final",
            "away_final",
            "final_total",
            "ml_result_home",
            "ou_result",
        ]
    ]


def main():
    # 2019 → 2026 (present)
    years = range(2019, 2027)

    nhl = normalize(NHLOddsScraper(years).driver(), "nhl")
    nba = normalize(NBAOddsScraper(years).driver(), "nba")
    nfl = normalize(NFLOddsScraper(years).driver(), "nfl")
    mlb = normalize(MLBOddsScraper(years).driver(), "mlb")

    df = pd.concat([nhl, nba, nfl, mlb], ignore_index=True)

    # Drop junk rows
    df = df[
        (df["close_over_under"] > 0)
        & (df["home_close_ml"] != 0)
        & (df["away_close_ml"] != 0)
    ]

    df.to_csv(OUT_PATH, index=False)


if __name__ == "__main__":
    main()
