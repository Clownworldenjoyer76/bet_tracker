import csv
from pathlib import Path

FINAL_DIR = Path("docs/win/final")
NORM_DIR = Path("docs/win/manual/normalized")
OUT_DIR = FINAL_DIR / "winners"

OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_key(row):
    return (
        row["date"],
        row["team"],
        row["opponent"],
        row["league"],
    )


def main():
    # Load normalized rows indexed by date, team, opponent, league
    norm_index = {}

    for file in NORM_DIR.glob("*.csv"):
        for row in load_csv(file):
            norm_index[make_key(row)] = row

    # Process final files
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
                norm_odds = float(norm["odds"])
            except (KeyError, ValueError):
                continue

            # EXACT CONDITION AS SPECIFIED
            if final_odds < acceptable_odds:
                winners.append({
                    "date": row["date"],
                    "time": row["time"],
                    "team": row["team"],
                    "opponent": row["opponent"],
                    "win_probability": row["win_probability"],
                    "league": row["league"],
                    "personally_acceptable_american_odds": acceptable_odds,
                    "odds": norm_odds,
                })

        if not winners:
            continue

        parts = file.stem.split("_")
        year, month, day = parts[-3], parts[-2], parts[-1]

        out_file = OUT_DIR / f"winners_{year}_{day}_{month}.csv"

        with open(out_file, "w", newline="", encoding="utf-8") as f:
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
