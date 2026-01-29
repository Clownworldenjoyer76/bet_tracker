import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_3")
OUT_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def process_file(path: Path):
    df = pd.read_csv(path, dtype=str)

    # drop rows with ML = NL
    df = df[df["ML"] != "NL"]

    # normalize flags
    df["favorite"] = df["favorite"].str.upper().str.strip()
    df["underdog"] = df["underdog"].str.upper().str.strip()

    # build spread column per rules
    def resolve_spread(row):
        val = row["spread"]
        if row["favorite"] == "YES":
            return val
        if row["underdog"] == "YES":
            return val.lstrip("-") if isinstance(val, str) else val
        return ""

    df["spread_out"] = df.apply(resolve_spread, axis=1)

    out = df[
        [
            "game_id",
            "VH",
            "Team",
            "Final",
            "Close",
            "ML",
            "favorite",
            "underdog",
            "over_under",
        ]
    ].copy()

    out["spread"] = df["spread_out"]

    out_path = OUT_DIR / path.name.replace("_stage3", "_stage2")
    out.to_csv(out_path, index=False)

def main():
    for f in IN_DIR.glob("ncaa-basketball-*_stage3.csv"):
        process_file(f)

if __name__ == "__main__":
    main()
