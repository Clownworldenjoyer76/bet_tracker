#!/usr/bin/env python3
"""
find_winning_bets.py

Rule (authoritative):
- A bet qualifies if DK moneyline >= acceptable_american_odds
- edge_american = DK moneyline - acceptable_american_odds

Joins:
- EDGE uses canonical team names
- DK uses dk_team names
- Join via mappings/team_map.csv (league, canonical_team -> dk_team)

Behavior:
- Reads EDGE league from column (not filename)
- Supports edge_*_{YYYY-MM-DD}*.csv and edge_*_{YYYY_MM_DD}*.csv
- Handles multiple DK rows per team (selects best DK moneyline)
- Writes headers even if no rows qualify
"""

import sys
import csv
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Tuple, List, Optional
import pandas as pd

ROOT = Path(".")
EDGE_DIR = ROOT / "docs" / "win" / "edge"
DK_DIR = ROOT / "docs" / "win"
MAP_PATH = ROOT / "mappings" / "team_map.csv"
OUT_DIR = ROOT / "docs" / "win" / "final"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def die(msg: str):
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
    if s.startswith("+"):
        s = s[1:]
    try:
        return int(float(s))
    except ValueError:
        return None


def load_mapping() -> Dict[Tuple[str, str], str]:
    if not MAP_PATH.exists():
        die(f"Missing mapping file: {MAP_PATH}")
    out: Dict[Tuple[str, str], str] = {}
    with MAP_PATH.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lg = norm_league(r["league"])
            canon = norm(r["canonical_team"])
            dk = norm(r["dk_team"])
            if not lg or not canon or not dk:
                die(f"Blank mapping row: {r}")
            key = (lg, canon)
            if key in out and out[key] != dk:
                die(f"Conflicting mapping for {key}: {out[key]} vs {dk}")
            out[key] = dk
    return out


def find_edge_files(target: date) -> List[Path]:
    y, m, d = target.year, f"{target.month:02}", f"{target.day:02}"
    pats = [f"edge_*_{y}-{m}-{d}*.csv", f"edge_*_{y}_{m}_{d}*.csv"]
    files: List[Path] = []
    for p in pats:
        files.extend(sorted(EDGE_DIR.glob(p)))
    return list(dict.fromkeys(files))


def load_dk(target: date) -> pd.DataFrame:
    y, m, d = target.year, f"{target.month:02}", f"{target.day:02}"
    p = DK_DIR / f"DK_{y}_{m}_{d}.xlsx"
    if not p.exists():
        die(f"Missing DK file: {p}")
    df = pd.read_excel(p)
    df.columns = [norm(c) for c in df.columns]
    if "bet_pct" not in df.columns and "bets_pct" in df.columns:
        df = df.rename(columns={"bets_pct": "bet_pct"})
    for col in ["league", "team", "moneyline"]:
        if col not in df.columns:
            die(f"DK missing column: {col}")
    if "opponent" not in df.columns:
        df["opponent"] = ""
    if "handle_pct" not in df.columns:
        df["handle_pct"] = pd.NA
    if "bet_pct" not in df.columns:
        df["bet_pct"] = pd.NA

    df["league"] = df["league"].apply(norm_league)
    df["team"] = df["team"].apply(norm)
    df["opponent"] = df["opponent"].apply(norm)
    df["_ml"] = df["moneyline"].apply(american_to_int)
    if df["_ml"].isna().any():
        bad = df[df["_ml"].isna()][["league", "team", "moneyline"]].head(10)
        die(f"Unparsable DK moneylines:\n{bad}")
    return df


def main():
    target = date.today()
    dk = load_dk(target)
    canon_to_dk = load_mapping()
    edge_files = find_edge_files(target)
    if not edge_files:
        die("No edge files found for target date")

    out_cols = ["date","league","team","opponent","edge_american","dk_odds","handle_pct","bet_pct"]
    out_rows = []

    for ef in edge_files:
        ed = pd.read_csv(ef)
        ed.columns = [norm(c) for c in ed.columns]
        for col in ["league","team","opponent","acceptable_american_odds"]:
            if col not in ed.columns:
                die(f"Edge missing column {col} in {ef}")
        ed["league"] = ed["league"].apply(norm_league)
        ed["acceptable_american_odds"] = pd.to_numeric(ed["acceptable_american_odds"], errors="coerce")
        if ed["acceptable_american_odds"].isna().any():
            die(f"Non-numeric acceptable_american_odds in {ef}")

        for _, r in ed.iterrows():
            lg = r["league"]
            team = norm(r["team"])
            opp = norm(r["opponent"])
            acc = int(r["acceptable_american_odds"])

            if (lg, team) not in canon_to_dk:
                die(f"Missing mapping for {(lg, team)}")
            dk_team = canon_to_dk[(lg, team)]

            dkm = dk[(dk["league"]==lg) & (dk["team"]==dk_team)]
            if dkm.empty:
                continue

            # choose best DK price (max moneyline)
            best = dkm.loc[dkm["_ml"].idxmax()]
            if best["_ml"] >= acc:
                out_rows.append({
                    "date": target.isoformat(),
                    "league": lg,
                    "team": team,
                    "opponent": opp,
                    "edge_american": best["_ml"] - acc,
                    "dk_odds": best["_ml"],
                    "handle_pct": best["handle_pct"],
                    "bet_pct": best["bet_pct"],
                })

    out = OUT_DIR / f"winning_bets_{target.year}_{target.month:02}_{target.day:02}.csv"
    pd.DataFrame(out_rows, columns=out_cols).to_csv(out, index=False)
    print(f"Wrote {out} ({len(out_rows)} rows)")


if __name__ == "__main__":
    main()
