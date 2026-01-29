import pandas as pd
import re
from pathlib import Path

RAW_DIR = Path("bets/historic/ncaab_old")
OUT_DIR = RAW_DIR / "stage_1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLS = {"Date","Rot","VH","Team","Final","Open","Close","ML"}

def season_start_year(name):
    m = re.search(r"(19|20)\d{2}", name)
    if not m:
        raise ValueError(f"{name}: cannot infer season year")
    return int(m.group())

def infer_year(mmdd, start):
    return start if mmdd // 100 >= 11 else start + 1

def clean_file(path: Path):
    df = pd.read_csv(path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: missing {missing}")

    start = season_start_year(path.name)

    # date
    df["mmdd"] = pd.to_numeric(df["Date"], errors="coerce")
    df = df.dropna(subset=["mmdd"])
    df["mmdd"] = df["mmdd"].astype(int)
    df["year"] = df["mmdd"].apply(lambda x: infer_year(x, start))
    df["month"] = df["mmdd"] // 100
    df["day"] = df["mmdd"] % 100
    df["game_date"] = pd.to_datetime(
        dict(year=df["year"], month=df["month"], day=df["day"]),
        errors="coerce"
    )
    df = df.dropna(subset=["game_date"])

    # rotation / game key
    df["rotation"] = pd.to_numeric(df["Rot"], errors="coerce")
    df = df.dropna(subset=["rotation"])
    df["rotation"] = df["rotation"].astype(int)
    df["game_key"] = df["rotation"].where(df["rotation"] % 2 == 1, df["rotation"] - 1)

    # VH
    vh = df["VH"].astype(str).str.upper().str.strip()
    df["is_home"] = (vh == "H").astype(int)
    df["is_away"] = (vh == "V").astype(int)
    df["is_neutral"] = (~vh.isin(["H","V"])).astype(int)

    # scores
    df["team_score"] = pd.to_numeric(df["Final"], errors="coerce")
    df = df.dropna(subset=["team_score"])
    df["team_score"] = df["team_score"].astype(int)

    # keep only complete games
    counts = df.groupby("game_key").size()
    valid = counts[counts == 2].index
    df = df[df["game_key"].isin(valid)]

    # opponent score (explicit pair)
    df = df.sort_values(["game_key","rotation"])
    df["opp_score"] = df.groupby("game_key")["team_score"].shift(-1)
    df.loc[df["opp_score"].isna(), "opp_score"] = (
        df.groupby("game_key")["team_score"].shift(1)
    )

    df["margin"] = df["team_score"] - df["opp_score"]
    df["win_flag"] = (df["margin"] > 0).astype(int)

    # odds (numeric)
    def num(s):
        s = s.astype(str).str.upper().str.strip().replace({"PK":"0","PICK":"0","":pd.NA})
        return pd.to_numeric(s, errors="coerce")

    df["Open_n"] = num(df["Open"])
    df["Close_n"] = num(df["Close"])

    df["open_spread"] = pd.NA
    df["close_spread"] = pd.NA
    df["open_total"] = pd.NA
    df["close_total"] = pd.NA

    for gk, g in df.groupby("game_key"):
        r = g.index.tolist()
        o1, o2 = g.loc[r[0],"Open_n"], g.loc[r[1],"Open_n"]
        if pd.isna(o1) or pd.isna(o2):
            continue
        if abs(o1) > 50:
            total, spread = r[0], r[1]
        else:
            spread, total = r[0], r[1]
        df.loc[r, "open_total"] = df.loc[total,"Open_n"]
        df.loc[r, "close_total"] = df.loc[total,"Close_n"]
        df.loc[r, "open_spread"] = df.loc[spread,"Open_n"]
        df.loc[r, "close_spread"] = df.loc[spread,"Close_n"]

    out = [
        "game_date","rotation","game_key","Team",
        "is_home","is_away","is_neutral",
        "team_score","opp_score","margin","win_flag",
        "open_spread","close_spread","open_total","close_total","ML"
    ]
    return df[out].sort_values(["game_date","game_key","is_home"], ascending=[True,True,False])

def main():
    files = RAW_DIR.glob("ncaa-basketball-*.csv")
    for f in files:
        clean = clean_file(f)
        clean.to_csv(OUT_DIR / f"{f.stem}_stage1.csv", index=False)

if __name__ == "__main__":
    main()
