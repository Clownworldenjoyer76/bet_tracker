import pandas as pd
import glob
from pathlib import Path

STEP2 = Path("docs/win/final/step_2")
STEP3 = Path("docs/win/final/step_3")

FILES = 0
ROWS_IN = 0
ROWS_OUT = 0

def run():
    global FILES, ROWS_IN, ROWS_OUT

    for f in glob.glob(str(STEP2 / "**/*.csv"), recursive=True):
        df = pd.read_csv(f)
        FILES += 1
        ROWS_IN += len(df)

        if df.empty:
            continue

        mask = pd.Series(False, index=df.index)  # FIXED

        pairs = [
            ("deci_home_ml_juice_odds", "deci_dk_home_odds"),
            ("deci_away_ml_juice_odds", "deci_dk_away_odds"),
        ]

        for juice_col, dk_col in pairs:
            if juice_col in df.columns and dk_col in df.columns:
                valid = df[juice_col].notna() & df[dk_col].notna()
                mask |= valid & (df[juice_col] > df[dk_col])

        filtered = df[mask].copy()

        rel = Path(f).relative_to(STEP2)
        out = STEP3 / rel
        out.parent.mkdir(parents=True, exist_ok=True)

        filtered.to_csv(out, index=False)
        ROWS_OUT += len(filtered)

        print(f"Wrote {out} | kept={len(filtered)} of {len(df)}")

    print("\n=== FINAL_06 SUMMARY ===")
    print(f"Files: {FILES}")
    print(f"Rows in: {ROWS_IN}")
    print(f"Rows out (value edges): {ROWS_OUT}")

    if FILES == 0:
        raise RuntimeError("final_06: 0 files processed")

    if ROWS_OUT == 0:
        raise RuntimeError("final_06: 0 value rows produced")

    # FINAL INTEGRITY CHECK
    if ROWS_OUT > ROWS_IN:
        raise RuntimeError("Integrity error: rows_out > rows_in")

if __name__ == "__main__":
    run()
