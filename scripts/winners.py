#!/usr/bin/env python3

import csv
from pathlib import Path

FINAL_DIR = Path("docs/win/final")
NORM_DIR = Path("docs/win/manual/normalized")
OUT_DIR = FINAL_DIR / "winners"

OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def normalize_date(value: str) -> str:
    """
    Normalize dates like:
    1/24/2026 or 01/24/2026  ->  2026-01-24
    """
    month, day, year = value.split("/")
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def make_key(row: dict):
    """
    Strict match key:
    date, team, opponent, league
    """
    return (
        normalize_date(row["date"].strip()),
        row["team"].strip(),
        row["opponent"].strip(),
        row["league"].strip(),
    )


def american_odds_is_acceptable(final_odds: float, acceptable_odds: float) -> bool:
    """
    Returns True if final_odds is BETTER THAN OR EQUAL TO acceptable_odds
    using correct American odds logic.
    """
    # Both positive (underdogs): higher is better
    if final_odds > 0 and acceptable_odds > 0:
        return final_odds >= acceptable_odds

    # Both negative (favorites): closer to zero is better
    if final_odds < 0 and acceptable_odds < 0:
        return final_odds <= acceptable_odds

    # Mixed signs: positive is always better than negative
    return final_odds > acceptable_odds


def main():
    # ------------------------------------------------------------
    # Load normalized rows indexed by normalized key
    # ------------------------------------------------------------
    norm_index = {}

    for file in NORM_DIR.glob("*.csv"):
        for row in load_csv(file):
            key = make_key(row)
            norm_index[key] = row

    if not norm_index:
        raise RuntimeError("No normalized rows loaded")

    # ------------------------------------------------------------
    # Process final files
    # ------------------------------------------------------------
    for file in FINAL_DIR.glob("final_*.csv"):
        final_rows = load_csv(file)
        if not final_rows:
            continue

        winners = []

        for row in final_rows:
            key = make_key(row)
            if key not in norm_index:
                continue

            norm = norm_index[key]

            try:
                final_odds = float(row["odds"])
                acceptable_odds = float(norm["personally_acceptable_american_odds"])
                normalized_odds = float(norm["odds"])
            except (KeyError, ValueError):
                continue

            if american_odds_is_acceptable(final_odds, acceptable_odds):
                winners.append({
                    "date": row["date"],
                    "time": row["time"],
                    "team": row["team"],
                    "opponent": row["opponent"],
                    "win_probability": norm["win_probability"],
                    "league": row["league"],
                    "personally_acceptable_american_odds": acceptable_odds,
                    "odds": normalized_odds,
                })

        if not winners:
            continue

        # final_{league}_{YYYY}_{MM}_{DD}.csv
        parts = file.stem.split("_")
        year, month, day = parts[-3], parts[-2], parts[-1]

        out_file = OUT_DIR / f"winners_{year}_{day}_{month}.csv"

        with out_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "date",
                    "time",
                    "team",
                    "opponent",
                    "win_probability",
                    "league",
                    "personally_acceptable_american_odds",
                    "odds",
                ],
            )
            writer.writeheader()
            writer.writerows(winners)


if __name__ == "__main__":
    main()
