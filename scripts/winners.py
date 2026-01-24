import csv
from pathlib import Path

FINAL_DIR = Path("docs/win/final")
NORM_DIR = Path("docs/win/manual/normalized")
OUT_DIR = FINAL_DIR / "winners"

OUT_DIR.mkdir(parents=True, exist_ok=True)


def american_to_decimal(a):
    a = float(a)
    if a > 0:
        return 1 + a / 100
    else:
        return 1 + 100 / abs(a)


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_key(row):
    return (
        row["date"].strip(),
        row["team"].strip(),
        row["opponent"].strip(),
        row["league"].strip(),
    )


def main():
    # Index normalized rows
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
            k = make_key(row)
            if k not in norm_index:
                continue

            norm = norm_index[k]

            try:
                final_odds = float(row["odds"])
                acceptable_odds = float(norm["personally_acceptable_american_odds"])
                dk_odds = float(norm["odds"])
            except (KeyError, ValueError):
                continue

            final_dec = american_to_decimal(final_odds)
            acceptable_dec = american_to_decimal(acceptable_odds)

            if final_dec >= acceptable_dec:
                winners.append({
                    "date": row["date"],
                    "time": row["time"],
                    "team": row["team"],
                    "opponent": row["opponent"],
                    "win_probability": row["win_probability"],
                    "league": row["league"],
                    "personally_acceptable_american_odds": acceptable_odds,
                    "odds": dk_odds,
                })

        if not winners:
            continue

        parts = file.stem.split("_")
        year, month, day = parts[-3], parts[-2], parts[-1]

        out_path = OUT_DIR / f"winners_{year}_{month}_{day}.csv"

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


if __name__ == "__main__":
    main()
