import pandas as pd
import glob
from pathlib import Path

BASE_IN = Path("docs/win/juice")
BASE_OUT = Path("docs/win/final/step_1")

FILES_PROCESSED = 0
ROWS_IN = 0
ROWS_OUT = 0


def run():
    global FILES_PROCESSED, ROWS_IN, ROWS_OUT

    for subdir in [
        "nba/ml",
        "nba/spreads",
        "nba/totals",
        "ncaab/ml",
        "ncaab/spreads",
        "ncaab/totals",
    ]:
        in_dir = BASE_IN / subdir
        out_dir = BASE_OUT / subdir
        out_dir.mkdir(parents=True, exist_ok=True)

        is_ml = subdir.endswith("/ml")

        for f in glob.glob(str(in_dir / "*.csv")):
            df = pd.read_csv(f)
            FILES_PROCESSED += 1
            ROWS_IN += len(df)

            if is_ml and "time" not in df.columns:
                df["time"] = "00:00"

            out_path = out_dir / Path(f).name
            df.to_csv(out_path, index=False)

            ROWS_OUT += len(df)
            print(f"Wrote {out_path} | rows={len(df)}")

    print("\n=== FINAL_01 SUMMARY ===")
    print(f"Files processed: {FILES_PROCESSED}")
    print(f"Rows in: {ROWS_IN}")
    print(f"Rows out: {ROWS_OUT}")

    if FILES_PROCESSED == 0:
        raise RuntimeError("final_01: 0 files processed")

    if ROWS_OUT == 0:
        raise RuntimeError("final_01: 0 rows written")


if __name__ == "__main__":
    run()
