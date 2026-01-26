from pathlib import Path
import pandas as pd

from scrapers.sportsbookreview import (
    NHLOddsScraper,
    NBAOddsScraper,
    NFLOddsScraper,
    MLBOddsScraper,
)

OUT_PATH = Path("bets/historic/odds_scraped.csv")


def normalize(df: pd.DataFrame, league: str) -> pd.DataFrame:
    """
    Normalize scraped odds into a common schema.
    This function is intentionally defensive:
    - If required columns are missing, returns empty DF
    """

    if df.empty:
        print(f"[WARN] {league.upper()}: empty dataframe, skipping normalize")
        return pd.DataFrame()

    required_cols = {
        "home_final",
        "away_final",
        "close_over_under",
        "home_close_ml",
        "away_close_ml",
    }

    missing = required_cols - set(df.columns)
    if missing:
        print(
            f"[WARN] {league.upper()}: missing columns {sorted(missing)}, "
            "skipping normalize"
        )
        return pd.DataFrame()

    out = pd.DataFrame()
    out["date"] = df["date"]
    out["league"] = league

    # moneyline
    out["home_team"] = df["home_team"]
    out["away_team"] = df["away_team"]
    out["home_close_ml"] = pd.to_numeric(df["home_close_ml"], errors="coerce")
    out["away_close_ml"] = pd.to_numeric(df["away_close_ml"], errors="coerce")

    # totals
    out["close_over_under"] = pd.to_numeric(
        df["close_over_under"], errors="coerce"
    )

    out["home_final"] = pd.to_numeric(df["home_final"], errors="coerce")
    out["away_final"] = pd.to_numeric(df["away_final"], errors="coerce")
    out["final_total"] = out["home_final"] + out["away_final"]

    out["ou_result"] = None
    out.loc[out["final_total"] > out["close_over_under"], "ou_result"] = "Over"
    out.loc[out["final_total"] < out["close_over_under"], "ou_result"] = "Under"
    out.loc[out["final_total"] == out["close_over_under"], "ou_result"] = "Push"

    return out.dropna(how="all")


def main():
    years = list(range(2019, 2027))
    all_data = []

    print("Scraping NHL…")
    nhl_raw = NHLOddsScraper(years).driver()
    nhl = normalize(nhl_raw, "nhl")
    if not nhl.empty:
        all_data.append(nhl)

    print("Scraping NBA…")
    nba_raw = NBAOddsScraper(years).driver()
    nba = normalize(nba_raw, "nba")
    if not nba.empty:
        all_data.append(nba)

    print("Scraping NFL…")
    nfl_raw = NFLOddsScraper(years).driver()
    nfl = normalize(nfl_raw, "nfl")
    if not nfl.empty:
        all_data.append(nfl)

    print("Scraping MLB…")
    mlb_raw = MLBOddsScraper(years).driver()
    mlb = normalize(mlb_raw, "mlb")
    if not mlb.empty:
        all_data.append(mlb)

    if not all_data:
        print("[WARN] No data scraped for any league")
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame().to_csv(OUT_PATH, index=False)
        return

    final = pd.concat(all_data, ignore_index=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(OUT_PATH, index=False)

    print(f"[OK] Wrote {len(final)} rows → {OUT_PATH}")


if __name__ == "__main__":
    main()
