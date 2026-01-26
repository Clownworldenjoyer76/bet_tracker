# scripts/zhistoric_odds.py

import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "bets" / "historic"


def load_json(path: Path) -> pd.DataFrame:
    with open(path, "r") as f:
        data = json.load(f)
    return pd.DataFrame(data)


def save_csv(df: pd.DataFrame, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"[OK] wrote {out_path} ({len(df)} rows)")


def process_nba():
    df = load_json(DATA_DIR / "nba_archive_10Y.json")

    cols = [
        "season",
        "date",
        "home_team",
        "away_team",
        "home_final",
        "away_final",
        "home_close_ml",
        "away_close_ml",
        "home_open_spread",
        "away_open_spread",
        "home_close_spread",
        "away_close_spread",
        "open_over_under",
        "close_over_under",
    ]

    df = df[[c for c in cols if c in df.columns]]
    save_csv(df, DATA_DIR / "nba_data.csv")


def process_nfl():
    df = load_json(DATA_DIR / "nfl_archive_10Y.json")

    cols = [
        "season",
        "date",
        "home_team",
        "away_team",
        "home_final",
        "away_final",
        "home_close_ml",
        "away_close_ml",
        "home_open_spread",
        "away_open_spread",
        "home_close_spread",
        "away_close_spread",
        "open_over_under",
        "close_over_under",
    ]

    df = df[[c for c in cols if c in df.columns]]
    save_csv(df, DATA_DIR / "nfl_data.csv")


def process_nhl():
    df = load_json(DATA_DIR / "nhl_archive_10Y.json")

    cols = [
        "season",
        "date",
        "home_team",
        "away_team",
        "home_final",
        "away_final",
        "home_close_ml",
        "away_close_ml",
        "home_close_spread",
        "away_close_spread",
        "open_over_under",
        "close_over_under",
    ]

    df = df[[c for c in cols if c in df.columns]]
    save_csv(df, DATA_DIR / "nhl_data.csv")


def process_mlb():
    df = load_json(DATA_DIR / "mlb_archive_10Y.json")

    cols = [
        "season",
        "date",
        "home_team",
        "away_team",
        "home_final",
        "away_final",
        "home_close_ml",
        "away_close_ml",
        "home_close_spread",
        "away_close_spread",
        "open_over_under",
        "close_over_under",
    ]

    df = df[[c for c in cols if c in df.columns]]
    save_csv(df, DATA_DIR / "mlb_data.csv")


def main():
    process_nba()
    process_nfl()
    process_nhl()
    process_mlb()


if __name__ == "__main__":
    main()
