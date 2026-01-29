import pandas as pd
import re
from pathlib import Path

RAW_DIR = Path("bets/historic/ncaab_old")
OUT_DIR = RAW_DIR / "stage_1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLS = {
    "Date", "Rot", "VH", "Team",
    "1st", "2nd", "Final",
    "Open", "Close", "ML"
}

def extract_season_start_year(filename: str) -> int:
    match = re.search(r"(19|20)\d{2}", filename)
    if not match:
        raise ValueError(f"{filename}: could not infer season year")
    return int(match.group())

def infer_season_year(mmdd: int, season_start_year: int) -> int:
    month = mmdd // 100
    return season_start_year if month >= 11 else season_start_year + 1

def parse_dates(df: pd.DataFrame, season_start_year: int) -> pd.DataFrame:
    df["mmdd"] = df["Date"].astype(int)
    df["year"] = df["mmdd"].apply(lambda x: infer_season_year(x, season_start_year))
    df["month"] = df["mmdd"] // 100
    df["day"] = df["mmdd"] % 100
    df["game_date"] = pd.to_datetime(
        dict(year=df["year"], month=df["month"], day=df["day"]),
        errors="raise"
    )
    return df

def clean_file(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")

    season_start_year = extract_season_start_year(path.name)
    df = parse_dates(df, season_start_year)

    df["rotation"] = df["Rot"].astype(int)
    df["is_home"] = df["VH"].map({"H": 1, "V": 0})
    if df["is_home"].isna().any():
        raise ValueError(f"{path.name}: invalid VH values")

    df["game_key"] = df["rotation"].where(
        df["rotation"] % 2 == 1,
        df["rotation"] - 1
    )

    df["open_spread"] = df.apply(
        lambda r: r["Open"] if r["is_home"] == 1 else pd.NA,
        axis=1
    )
    df["close_spread"] = df.apply(
        lambda r: r["Close"] if r["is_home"] == 1 else pd.NA,
        axis=1
    )
    df["open_total"] = df.apply(
        lambda r: r["Open"] if r["is_home"] == 0 else pd.NA,
        axis=1
    )
    df["close_total"] = df.apply(
        lambda r: r["Close"] if r["is_home"] == 0 else pd.NA,
        axis=1
    )

    df["team_score"] = df["Final"].astype(int)

    opp_scores = (
        df[["game_key", "team_score"]]
        .groupby("game_key")
        .transform(lambda x: x.iloc[::-1].values)
    )
    df["opp_score"] = opp_scores["team_score"]

    df["margin"] = df["team_score"] - df["opp_score"]
    df["win_flag"] = (df["margin"] > 0).astype(int)

    out_cols = [
        "game_date", "rotation", "game_key",
        "Team", "is_home",
        "team_score", "opp_score", "margin", "win_flag",
        "open_spread", "close_spread",
        "open_total", "close_total",
        "ML"
    ]

    return df[out_cols].sort_values(["game_date", "game_key", "is_home"])

def main():
    files = sorted(RAW_DIR.glob("ncaa-basketball-*.xlsx"))
    if not files:
        raise RuntimeError("No NCAA basketball XLSX files found")

    for f in files:
        cleaned = clean_file(f)
        out_path = OUT_DIR / f"{f.stem}_stage1.csv"
        cleaned.to_csv(out_path, index=False)

if __name__ == "__main__":
    main()
