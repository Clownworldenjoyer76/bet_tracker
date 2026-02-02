import pandas as pd
from pathlib import Path

# ---------------- CONFIG ----------------

INPUT_DIR = Path("bets/historic/juice_files")
OUTPUT_DIR = INPUT_DIR / "tables"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BIN_SIZE = 0.05        # 5% probability buckets
MIN_BETS = 500         # drop noisy bins

# ---------------------------------------

def build_juice_table(file_path: Path) -> pd.DataFrame:
    df = pd.read_csv(file_path)

    # Safety checks
    required_cols = {"prob_dec", "wins", "bets"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"{file_path.name} missing columns: {missing}")

    # Assign probability bins
    df["prob_bin"] = (df["prob_dec"] // BIN_SIZE) * BIN_SIZE

    grouped = (
        df.groupby("prob_bin")
        .agg(
            bets=("bets", "sum"),
            wins=("wins", "sum"),
            avg_prob=("prob_dec", "mean"),
        )
        .reset_index()
    )

    # Drop low-sample bins
    grouped = grouped[grouped["bets"] >= MIN_BETS]

    # Actual win %
    grouped["actual_win_pct"] = grouped["wins"] / grouped["bets"]

    # Extra juice (pricing penalty)
    grouped["extra_juice"] = (
        grouped["avg_prob"] / grouped["actual_win_pct"] - 1
    )

    grouped["prob_bin_min"] = grouped["prob_bin"]
    grouped["prob_bin_max"] = grouped["prob_bin"] + BIN_SIZE

    return grouped[
        ["prob_bin_min", "prob_bin_max", "extra_juice"]
    ].sort_values("prob_bin_min")


def run():
    files = list(INPUT_DIR.glob("*.csv"))

    if not files:
        print(f"No files found in {INPUT_DIR}")
        return

    for file_path in files:
        try:
            juice_df = build_juice_table(file_path)
            out_path = OUTPUT_DIR / file_path.name.replace(".csv", "_juice.csv")
            juice_df.to_csv(out_path, index=False)
            print(f"Built juice table: {out_path}")
        except Exception as e:
            print(f"FAILED {file_path.name}: {e}")


if __name__ == "__main__":
    run()
