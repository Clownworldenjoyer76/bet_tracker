import pandas as pd

from scraper import (
    NHLOddsScraper,
    NBAOddsScraper,
    NFLOddsScraper,
    MLBOddsScraper,
)


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
    nhl = NHLOddsScraper(range(2014, 2025)).driver()
    nba = NBAOddsScraper(range(2006, 2025)).driver()
    nfl = NFLOddsScraper(range(2006, 2025)).driver()
    mlb = MLBOddsScraper(range(2006, 2025)).driver()

    nhl = normalize(nhl, "nhl")
    nba = normalize(nba, "nba")
    nfl = normalize(nfl, "nfl")
    mlb = normalize(mlb, "mlb")

    df = pd.concat([nhl, nba, nfl, mlb], ignore_index=True)

    # Drop junk rows
    df = df[
        (df["close_over_under"] > 0)
        & (df["home_close_ml"] != 0)
        & (df["away_close_ml"] != 0)
    ]

    df.to_csv("closing_odds_with_results.csv", index=False)


if __name__ == "__main__":
    main()
