#!/usr/bin/env python3
"""
Build NHL Totals Evaluation File (Model-Anchored)

Input (latest):
  docs/win/edge/edge_nhl_*.csv

Output:
  docs/win/nhl/edge_nhl_totals_YYYY_MM_DD.csv

Config-driven (ONLY):
  config/nhl/nhl_juice_table.csv

Notes:
- market_total: best_ou (preferred), fallback: market_total
- model mean: total_goals (preferred), fallback: total_points
- Poisson totals model
- Applies juice rules for market_type="totals" based on market_total + side (over/under)
"""

import csv
import glob
import math
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Optional


EDGE_BUFFER_TOTALS = 0.07
MIN_LAM = 2.0
MAX_LAM = 15.0

INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/nhl")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JUICE_TABLE_PATH = Path("config/nhl/nhl_juice_table.csv")


@dataclass(frozen=True)
class JuiceRule:
    market_type: str
    band_low: float
    band_high: float
    side: str
    extra_juice_pct: float
    notes: str = ""


def load_juice_rules(path: Path) -> List[JuiceRule]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config: {path}")

    rules: List[JuiceRule] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"market_type", "band_low", "band_high", "side", "extra_juice_pct"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"Invalid schema in {path}. Required columns: {sorted(required)}"
            )

        for row in reader:
            mt = (row.get("market_type") or "").strip().lower()
            if not mt:
                continue

            rules.append(
                JuiceRule(
                    market_type=mt,
                    band_low=float(row["band_low"]),
                    band_high=float(row["band_high"]),
                    side=(row.get("side") or "any").strip().lower(),
                    extra_juice_pct=float(row["extra_juice_pct"]),
                    notes=(row.get("notes") or "").strip(),
                )
            )

    rules.sort(key=lambda r: (r.market_type, r.side, r.band_low, r.band_high))
    return rules


def match_rule(
    rules: List[JuiceRule],
    market_type: str,
    value: float,
    side: str,
) -> Optional[JuiceRule]:
    mt = market_type.strip().lower()
    sd = side.strip().lower()

    exact = [r for r in rules if r.market_type == mt and r.side == sd]
    any_side = [r for r in rules if r.market_type == mt and r.side == "any"]

    def find_match(cands: List[JuiceRule]) -> Optional[JuiceRule]:
        for r in cands:
            if r.band_low <= value < r.band_high:
                return r
        if cands:
            top = max(cands, key=lambda x: x.band_high)
            if value == top.band_high:
                return top
        return None

    return find_match(exact) or find_match(any_side)


def poisson_cdf(k: int, lam: float) -> float:
    """P(X <= k) for Poisson(lam)"""
    if k < 0:
        return 0.0
    term = math.exp(-lam)
    s = term
    for i in range(1, k + 1):
        term *= lam / i
        s += term
    return min(max(s, 0.0), 1.0)


def fair_decimal(p: float) -> float:
    return 1.0 / p


def decimal_to_american(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1) * 100))
    return int(round(-100 / (d - 1)))


def acceptable_decimal(p: float) -> float:
    return 1.0 / max(p - EDGE_BUFFER_TOTALS, 0.0001)


def american_to_decimal(a: int) -> float:
    if a > 0:
        return 1 + (a / 100)
    return 1 + (100 / abs(a))


def to_float(x: str) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    rules = load_juice_rules(JUICE_TABLE_PATH)

    input_files = sorted(glob.glob(str(INPUT_DIR / "edge_nhl_*.csv")))
    if not input_files:
        raise FileNotFoundError(f"No NHL edge files found in {INPUT_DIR}")

    latest_file = input_files[-1]

    today = datetime.utcnow()
    out_path = OUTPUT_DIR / f"edge_nhl_totals_{today.year}_{today.month:02d}_{today.day:02d}.csv"

    games = defaultdict(list)
    with open(latest_file, newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            gid = (row.get("game_id") or "").strip()
            if gid:
                games[gid].append(row)

    with open(out_path, "w", newline="", encoding="utf-8") as outfile:
        fieldnames = [
            "game_id",
            "date",
            "time",
            "team_1",
            "team_2",
            "market_total",
            "side",
            "model_probability",
            "fair_decimal_odds",
            "fair_american_odds",
            "acceptable_decimal_odds",
            "acceptable_american_odds",
            "personally_acceptable_decimal_odds",
            "personally_acceptable_american_odds",
            "league",
        ]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for game_id, rows in games.items():
            if not rows:
                continue

            # One row has shared game fields; teams are swapped in each row
            row = rows[0]
            team_1 = row.get("team", "") or row.get("team_1", "")
            team_2 = row.get("opponent", "") or row.get("team_2", "")
            date = row.get("date", "")
            time = row.get("time", "")

            lam = to_float(row.get("total_goals", ""))  # NHL model mean
            if lam is None:
                lam = to_float(row.get("total_points", ""))  # fallback if named differently

            market_total = to_float(row.get("best_ou", ""))
            if market_total is None:
                market_total = to_float(row.get("market_total", ""))

            side = "NO PLAY"
            p_selected: Optional[float] = None

            if lam is not None and market_total is not None and (MIN_LAM <= lam <= MAX_LAM):
                # For totals like 6.5, "under" is T <= 6, "over" is T >= 7
                k_under = int(math.floor(market_total))
                p_under = poisson_cdf(k_under, lam)
                p_over = 1.0 - p_under

                if lam > market_total:
                    side = "OVER"
                    p_selected = p_over
                elif lam < market_total:
                    side = "UNDER"
                    p_selected = p_under

            if p_selected is None or market_total is None:
                writer.writerow({
                    "game_id": game_id,
                    "date": date,
                    "time": time,
                    "team_1": team_1,
                    "team_2": team_2,
                    "market_total": market_total if market_total is not None else "",
                    "side": "NO PLAY",
                    "model_probability": "",
                    "fair_decimal_odds": "",
                    "fair_american_odds": "",
                    "acceptable_decimal_odds": "",
                    "acceptable_american_odds": "",
                    "personally_acceptable_decimal_odds": "",
                    "personally_acceptable_american_odds": "",
                    "league": "nhl_ou",
                })
                continue

            fair_d = fair_decimal(p_selected)
            fair_a = decimal_to_american(fair_d)
            acc_d = acceptable_decimal(p_selected)
            acc_a = decimal_to_american(acc_d)

            # Apply config-driven juice for totals based on *market_total* + side
            rule = match_rule(rules, market_type="totals", value=market_total, side=side.lower())
            edge_pct = rule.extra_juice_pct if rule else 0.0

            personal_d = acc_d * (1.0 + edge_pct)
            personal_a = decimal_to_american(personal_d)

            writer.writerow({
                "game_id": game_id,
                "date": date,
                "time": time,
                "team_1": team_1,
                "team_2": team_2,
                "market_total": market_total,
                "side": side,
                "model_probability": round(p_selected, 4),
                "fair_decimal_odds": round(fair_d, 4),
                "fair_american_odds": fair_a,
                "acceptable_decimal_odds": round(acc_d, 4),
                "acceptable_american_odds": acc_a,
                "personally_acceptable_decimal_odds": round(personal_d, 6),
                "personally_acceptable_american_odds": personal_a,
                "league": "nhl_ou",
            })

    print(f"Created {out_path} (from {Path(latest_file).name})")


if __name__ == "__main__":
    main()
