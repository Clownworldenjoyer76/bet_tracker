#!/usr/bin/env python3
"""
scripts/filter_final_bets.py

Reads:
- Pre-final bets:
    docs/win/final/pre_final_{YYYY}_{MM}_{DD}.csv

Enriches:
- Pulls win_probability from EDGE files for the same date:
    docs/win/edge/edge_*_{YYYY-MM-DD}*.csv
    docs/win/edge/edge_*_{YYYY_MM_DD}*.csv

Applies per-league betting policy (v1) to produce:
- Final bets:
    docs/win/final/final_{YYYY}_{MM}_{DD}.csv

Notes:
- Does NOT modify join/math logic that produced pre_final.
- Strictly ignores any row where league == "soc".
"""

import os
import sys
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Tuple, Optional

import pandas as pd

ROOT = Path(".")
EDGE_DIR = ROOT / "docs" / "win" / "edge"
FINAL_DIR = ROOT / "docs" / "win" / "final"
FINAL_DIR.mkdir(parents=True, exist_ok=True)


def die(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def norm(s) -> str:
    return "" if s is None else str(s).strip()


def norm_league(s) -> str:
    return norm(s).lower()


def american_to_int(x) -> Optional[int]:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = norm(x).replace("−", "-")
    if not s:
        return None
    if s.startswith("+"):
        s = s[1:]
    try:
        return int(float(s))
    except ValueError:
        return None


def parse_date(s: Optional[str]) -> date:
    if not s:
        return date.today()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        die(f"Invalid --date '{s}'. Expected YYYY-MM-DD.")


def find_edge_files(target: date) -> List[Path]:
    y, m, d = target.year, f"{target.month:02}", f"{target.day:02}"
    pats = [
        f"edge_*_{y}-{m}-{d}*.csv",
        f"edge_*_{y}_{m}_{d}*.csv",
    ]
    files: List[Path] = []
    for p in pats:
        files.extend(sorted(EDGE_DIR.glob(p)))
    # de-dupe, preserve order
    return list(dict.fromkeys(files))


def load_edge_win_probs(target: date) -> pd.DataFrame:
    files = find_edge_files(target)
    if not files:
        die(f"No EDGE files found for {target.isoformat()} in {EDGE_DIR}")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df.columns = [norm(c) for c in df.columns]

        required = {"date", "team", "opponent", "win_probability", "league"}
        missing = required - set(df.columns)
        if missing:
            die(f"EDGE file missing columns {sorted(missing)}: {f}")

        df["league"] = df["league"].apply(norm_league)
        df["team"] = df["team"].apply(norm)
        df["opponent"] = df["opponent"].apply(norm)

        # Normalize date to YYYY-MM-DD for join
        # EDGE date often MM/DD/YYYY
        df["_date_norm"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        if df["_date_norm"].isna().any():
            bad = df[df["_date_norm"].isna()][["date", "league", "team", "opponent"]].head(10)
            die(f"Unparsable EDGE dates in {f} (showing up to 10):\n{bad.to_string(index=False)}")

        df["win_probability"] = pd.to_numeric(df["win_probability"], errors="coerce")
        if df["win_probability"].isna().any():
            bad = df[df["win_probability"].isna()][["date", "league", "team", "opponent", "win_probability"]].head(10)
            die(f"Non-numeric win_probability in {f} (showing up to 10):\n{bad.to_string(index=False)}")

        dfs.append(df[["_date_norm", "league", "team", "opponent", "win_probability"]])

    out = pd.concat(dfs, ignore_index=True)
    out = out[out["league"] != "soc"].copy()
    return out


def load_pre_final(target: date) -> pd.DataFrame:
    y, m, d = target.year, f"{target.month:02}", f"{target.day:02}"
    p = FINAL_DIR / f"pre_final_{y}_{m}_{d}.csv"
    if not p.exists():
        die(f"Missing pre_final file: {p}")

    df = pd.read_csv(p)
    df.columns = [norm(c) for c in df.columns]

    required = {"date", "league", "team", "opponent", "edge_american", "dk_odds"}
    missing = required - set(df.columns)
    if missing:
        die(f"pre_final missing columns {sorted(missing)}: {p}")

    df["league"] = df["league"].apply(norm_league)
    df["team"] = df["team"].apply(norm)
    df["opponent"] = df["opponent"].apply(norm)

    df["edge_american"] = pd.to_numeric(df["edge_american"], errors="coerce")
    if df["edge_american"].isna().any():
        bad = df[df["edge_american"].isna()][["date", "league", "team", "opponent", "edge_american"]].head(10)
        die(f"Non-numeric edge_american in {p} (showing up to 10):\n{bad.to_string(index=False)}")

    df["_dk_ml"] = df["dk_odds"].apply(american_to_int)
    if df["_dk_ml"].isna().any():
        bad = df[df["_dk_ml"].isna()][["date", "league", "team", "opponent", "dk_odds"]].head(10)
        die(f"Unparsable dk_odds in {p} (showing up to 10):\n{bad.to_string(index=False)}")

    # Normalize date
    df["_date_norm"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    if df["_date_norm"].isna().any():
        bad = df[df["_date_norm"].isna()][["date", "league", "team", "opponent"]].head(10)
        die(f"Unparsable pre_final dates in {p} (showing up to 10):\n{bad.to_string(index=False)}")

    # Hard ignore soccer
    df = df[df["league"] != "soc"].copy()

    return df


POLICY = {
    "ncaab": {
        "min_edge": 20,
        "fav_cap": -350,
        "min_wp": 0.38,
        "dog_min_odds": 120,
        "dog_min_edge": 25,
        "dog_min_wp": 0.38,
    },
    "nba": {
        "min_edge": 15,
        "fav_cap": -400,
        "min_wp": 0.40,
        "dog_min_odds": 130,
        "dog_min_edge": 20,
        "dog_min_wp": 0.40,
    },
    "nhl": {
        "min_edge": 12,
        "fav_cap": -220,
        "min_wp": 0.42,
        "dog_min_odds": 120,
        "dog_min_edge": 15,
        "dog_min_wp": 0.42,
    },
    "nfl": {
        "min_edge": 10,
        "fav_cap": -300,
        "min_wp": 0.45,
        "dog_min_odds": 110,
        "dog_min_edge": 15,
        "dog_min_wp": 0.45,
    },
}


def qualifies(row: pd.Series) -> bool:
    lg = row["league"]
    if lg == "soc":
        return False
    if lg not in POLICY:
        return False

    p = POLICY[lg]
    dk_ml = int(row["_dk_ml"])
    edge = float(row["edge_american"])
    wp = float(row["win_probability"])

    # Global floor
    if wp < p["min_wp"]:
        return False

    # Base edge requirement
    if edge < p["min_edge"]:
        return False

    # Favorites cap (exclude heavier favorites than cap)
    # Favorite = negative moneyline
    if dk_ml < 0 and dk_ml < p["fav_cap"]:
        return False

    # Underdog rules
    # Underdog = positive moneyline
    if dk_ml > 0:
        if dk_ml < p["dog_min_odds"]:
            return False
        if edge < p["dog_min_edge"]:
            return False
        if wp < p["dog_min_wp"]:
            return False

    return True


def pick_one_per_game(df: pd.DataFrame) -> pd.DataFrame:
    # Game key: league + date + sorted(team/opponent)
    def game_key(r: pd.Series) -> str:
        a = r["team"]
        b = r["opponent"]
        t1, t2 = (a, b) if a <= b else (b, a)
        return f"{r['league']}|{r['_date_norm'].isoformat()}|{t1}|{t2}"

    df = df.copy()
    df["_game_key"] = df.apply(game_key, axis=1)

    # Deterministic pick: highest edge_american, then higher dk odds (better price), then higher win_probability,
    # then stable sort by team name.
    df = df.sort_values(
        by=["_game_key", "edge_american", "_dk_ml", "win_probability", "team"],
        ascending=[True, False, False, False, True],
        kind="mergesort",
    )
    return df.groupby("_game_key", as_index=False, sort=False).head(1).copy()


def main() -> None:
    # Args: --date YYYY-MM-DD
    # Env: BET_STAKE (default 0.10)
    target = parse_date(sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else None)
    stake = float(os.environ.get("BET_STAKE", "0.10"))

    pre = load_pre_final(target)
    edge_wp = load_edge_win_probs(target)

    merged = pre.merge(
        edge_wp,
        how="left",
        left_on=["_date_norm", "league", "team", "opponent"],
        right_on=["_date_norm", "league", "team", "opponent"],
        validate="many_to_one",
    )

    if merged["win_probability"].isna().any():
        bad = merged[merged["win_probability"].isna()][["date", "league", "team", "opponent"]].head(20)
        die(
            "Missing win_probability for some pre_final rows (no exact EDGE match on date+league+team+opponent). "
            f"Showing up to 20:\n{bad.to_string(index=False)}"
        )

    # Apply policy
    filtered = merged[merged.apply(qualifies, axis=1)].copy()

    # Enforce one bet per game
    filtered = pick_one_per_game(filtered)

    # Output schema
    out_cols = [
        "date",
        "league",
        "team",
        "opponent",
        "win_probability",
        "edge_american",
        "dk_odds",
        "handle_pct",
        "bet_pct",
        "stake",
    ]
    filtered["stake"] = stake

    y, m, d = target.year, f"{target.month:02}", f"{target.day:02}"
    out_path = FINAL_DIR / f"final_{y}_{m}_{d}.csv"
    filtered[out_cols].to_csv(out_path, index=False)

    print(f"Wrote {out_path} ({len(filtered)} rows)")


if __name__ == "__main__":
    main()
