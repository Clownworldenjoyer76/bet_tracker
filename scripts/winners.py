import csv
import os
from pathlib import Path
from collections import defaultdict

FINAL_DIR = Path("docs/win/final")
NORM_DIR = Path("docs/win/manual/normalized")
OUT_DIR = FINAL_DIR / "winners"

OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def key(row):
    return (
        row["date"],
        row["team"],
        row["opponent"],
        row["league"],
    )


def main():
    # Index normalized rows by (date, team, opponent, league)
    norm_index = {}

    for file in NORM_DIR.glob("*.csv"):
        rows = load_csv(file)
        for r in rows:
            norm_index[key(r)] = r

    # Process each final file
    for file in FINAL_DIR.glob("final_*.csv"):
        rows = load_csv(file)
        if not rows:
            continue

        winners = []

        for r in rows:
            k = key(r)
            if k not in norm_index:
                continue

            norm = norm_index[k]

            try:
                final_odds = float(r["odds"])
                acceptable = float(norm["personally_acceptable_american_odds"])
                dk_odds = float(norm["odds"])
            except (KeyError, ValueError):
                continue

            # Core rule
            if final_odds < acceptable:
                winners.append({
                    "date": r["date"],
                    "time": r["time"],
                    "team": r["team"],
                    "opponent": r["opponent"],
                    "win_probability": r["win_probability"],
                    "league": r["league"],
                    "personally_acceptable_american_odds": acceptable,
                    "odds": dk_odds,
                })

        if not winners:
            continue

        # Extract date from filename
        # final_ncaab_2026_01_24.csv → 2026_01_24
        parts = file.stem.split("_")
        y, m, d = parts[-3], parts[-2], parts[-1]

        out_path = OUT_DIR / f"winners_{y}_{m}_{d}.csv"

        with open(out_path, "w", newline="", encoding="utf-8") as f:
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

        print(f"Wrote {len(winners)} winners → {out_path}")


if __name__ == "__main__":
    main()
