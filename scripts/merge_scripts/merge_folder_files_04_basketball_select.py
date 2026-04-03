import pandas as pd
from pathlib import Path

INPUT_DIR = Path("docs/win/basketball/04_select/daily_slate")

def load_selected_files():
    dfs = []

    for f in INPUT_DIR.glob("*.csv"):
        fname = f.name.lower()

        # ✅ ONLY filter by league now (removed market requirement)
        if "nba" in fname or "ncssb" in fname:
            df = pd.read_csv(f)
            dfs.append(df)

    if not dfs:
        raise ValueError("No selected files found")

    return pd.concat(dfs, ignore_index=True)


if __name__ == "__main__":
    df = load_selected_files()
    print(df.head())
