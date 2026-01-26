from pathlib import Path
import pandas as pd
import re

DATA_DIR = Path("bets/historic")
OUT_DIR = DATA_DIR / "schema_reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)


SCORE_PATTERNS = re.compile(r"(score|final|pts|runs|goals)", re.I)
ML_PATTERNS = re.compile(r"(ml|moneyline|odds)", re.I)
OU_PATTERNS = re.compile(r"(over|under|total|ou)", re.I)
SPREAD_PATTERNS = re.compile(r"(spread|line|handicap)", re.I)


def classify_columns(columns):
    classified = {
        "score_columns": [],
        "moneyline_columns": [],
        "total_columns": [],
        "spread_columns": [],
        "other_columns": [],
    }

    for col in columns:
        if SCORE_PATTERNS.search(col):
            classified["score_columns"].append(col)
        elif ML_PATTERNS.search(col):
            classified["moneyline_columns"].append(col)
        elif OU_PATTERNS.search(col):
            classified["total_columns"].append(col)
        elif SPREAD_PATTERNS.search(col):
            classified["spread_columns"].append(col)
        else:
            classified["other_columns"].append(col)

    return classified


def inspect_file(path: Path):
    df = pd.read_csv(path)

    classified = classify_columns(df.columns)

    # schema summary
    rows = []
    for group, cols in classified.items():
        for col in cols:
            rows.append(
                {
                    "file": path.name,
                    "category": group,
                    "column": col,
                    "dtype": str(df[col].dtype),
                    "non_null_pct": round(df[col].notna().mean(), 4),
                    "example": df[col].dropna().iloc[0] if df[col].notna().any() else None,
                }
            )

    schema_df = pd.DataFrame(rows)

    schema_out = OUT_DIR / f"{path.stem}_schema.csv"
    schema_df.to_csv(schema_out, index=False)

    # preview output (first 10 rows, raw)
    preview_out = OUT_DIR / f"{path.stem}_preview.csv"
    df.head(10).to_csv(preview_out, index=False)

    # console summary
    print(f"\n=== {path.name} ===")
    for k, v in classified.items():
        print(f"{k}: {v if v else 'NONE'}")

    print(f"[OK] wrote {schema_out}")
    print(f"[OK] wrote {preview_out}")


def main():
    files = DATA_DIR.glob("*_data.csv")

    for path in files:
        try:
            inspect_file(path)
        except Exception as e:
            print(f"[ERROR] {path.name}: {e}")


if __name__ == "__main__":
    main()
