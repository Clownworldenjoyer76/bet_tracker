#!/usr/bin/env python3

import csv
import math
import os
import sys
from pathlib import Path

# =========================
# Paths
# =========================
TOTALS_DIR = Path("docs/win/nba")
EDGE_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# Constants
# =========================
LEAGUE_STD = 7.2
JUICE = 1.047619  # >1 means "worse" odds when dividing fair odds by JUICE
EPS = 1e-6
SPREAD_OFFSETS = [-4.0, -2.0, 0.0, 2.0, 4.0]  # keeps .5 when anchor is .5

STRICT = os.getenv("STRICT_VALIDATE", "0") == "1"

# =========================
# Helpers
# =========================
def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def clamp_prob(p: float) -> float:
    return max(EPS, min(1.0 - EPS, p))

def dec_to_amer(d: float) -> int:
    # Decimal odds d = 1 + profit/1
    # If d >= 2: + (d-1)*100
    # else: -100/(d-1)
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))

def is_half_point(x: float) -> bool:
    return abs((abs(x) % 1.0) - 0.5) < 1e-9

def snap_to_half_point(x: float) -> float:
    """
    Snap x to the nearest number with fractional part .5 (i.e., ...,-1.5,-0.5,0.5,1.5,...).
    Guarantees |snap - x| <= 0.5 (ties broken toward +0.5 direction).
    """
    n = math.floor(x)
    c1 = n + 0.5
    c2 = n - 0.5
    d1 = abs(c1 - x)
    d2 = abs(c2 - x)
    if d1 < d2:
        return c1
    if d2 < d1:
        return c2
    # tie (exactly halfway): choose the one closer to +infinity to keep deterministic
    return max(c1, c2)

def warn(msg: str) -> None:
    print(f"[spreads_nba] {msg}", file=sys.stderr)

# =========================
# Main
# =========================
def main():
    totals_files = sorted(TOTALS_DIR.glob("edge_nba_totals_*.csv"))
    if not totals_files:
        raise RuntimeError(f"No totals files found in {TOTALS_DIR}")
    totals_file = totals_files[-1]

    with totals_file.open(newline="", encoding="utf-8") as f:
        totals = list(csv.DictReader(f))
    if not totals:
        raise RuntimeError("Totals file empty")

    edge_files = sorted(EDGE_DIR.glob("edge_nba_*.csv"))
    if not edge_files:
        raise RuntimeError(f"No edge files found in {EDGE_DIR}")
    edge_file = edge_files[-1]

    edge_by_game = {}
    with edge_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            edge_by_game.setdefault(r["game_id"], []).append(r)

    mm, dd, yyyy = totals[0]["date"].split("/")
    out_path = OUTPUT_DIR / f"edge_nba_spreads_ladder_{yyyy}_{mm.zfill(2)}_{dd.zfill(2)}.csv"

    fields = [
        "game_id","date","time","away_team","home_team","league",
        "away_team_proj_pts","home_team_proj_pts",
        "proj_margin","sigma",
        "model_home_spread","model_away_spread",
        "away_ml_prob","home_ml_prob",
    ]

    for k in SPREAD_OFFSETS:
        tag = f"m{abs(int(k))}" if k < 0 else f"p{int(k)}"
        fields += [
            f"home_spread_{tag}",
            f"away_spread_{tag}",
            f"fav_team_{tag}",
            f"fav_cover_prob_{tag}",
            f"dog_cover_prob_{tag}",
            f"fair_fav_dec_{tag}",
            f"fair_fav_amer_{tag}",
            f"fair_dog_dec_{tag}",
            f"fair_dog_amer_{tag}",
            f"acc_fav_dec_{tag}",
            f"acc_fav_amer_{tag}",
            f"acc_dog_dec_{tag}",
            f"acc_dog_amer_{tag}",
        ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for r in totals:
            gid = r["game_id"]
            away = r["team_1"]
            home = r["team_2"]

            rows = edge_by_game.get(gid)
            if not rows or len(rows) != 2:
                continue

            # Map edge rows to away/home teams reliably
            if rows[0].get("team") == away:
                a, h = rows
            elif rows[1].get("team") == away:
                a, h = rows[1], rows[0]
            else:
                # Cannot map; skip
                continue

            away_pts = float(a["points"])
            home_pts = float(h["points"])
            away_ml = float(a["win_probability"])
            home_ml = float(h["win_probability"])

            proj_margin = home_pts - away_pts
            sigma = LEAGUE_STD

            # -------------------------
            # Correct Option-B anchor:
            # home_spread ≈ -proj_margin, snapped to .5-only grid
            # -------------------------
            model_home_spread = snap_to_half_point(-proj_margin)
            model_away_spread = -model_home_spread

            # Optional strict checks (never required)
            if STRICT:
                if not is_half_point(model_home_spread):
                    raise AssertionError(f"{gid}: model_home_spread not .5 -> {model_home_spread}")
                if abs((proj_margin + model_home_spread)) > 0.500000001:
                    raise AssertionError(
                        f"{gid}: anchor drift > 0.5: drift={abs(proj_margin + model_home_spread):.6f}, "
                        f"proj_margin={proj_margin:.6f}, model_home_spread={model_home_spread:.6f}"
                    )

            row = {
                "game_id": gid,
                "date": r["date"],
                "time": r["time"],
                "away_team": away,
                "home_team": home,
                "league": "nba",
                "away_team_proj_pts": round(away_pts, 1),
                "home_team_proj_pts": round(home_pts, 1),
                "proj_margin": round(proj_margin, 3),
                "sigma": sigma,
                "model_home_spread": model_home_spread,
                "model_away_spread": model_away_spread,
                "away_ml_prob": round(away_ml, 6),
                "home_ml_prob": round(home_ml, 6),
            }

            # -------------------------
            # Ladder (no re-snapping needed; offsets preserve .5)
            # -------------------------
            last_home_spread = None
            last_home_prob = None

            for k in SPREAD_OFFSETS:
                tag = f"m{abs(int(k))}" if k < 0 else f"p{int(k)}"

                home_spread = model_home_spread + k
                away_spread = -home_spread

                if STRICT:
                    if not is_half_point(home_spread):
                        raise AssertionError(f"{gid}: home_spread_{tag} not .5 -> {home_spread}")

                z = (proj_margin + home_spread) / sigma
                home_prob = clamp_prob(normal_cdf(z))
                away_prob = clamp_prob(1.0 - home_prob)

                # Market-safe: favorite determined by sign of spread (negative = favorite)
                if home_spread < 0:
                    fav_team = "home"
                    fav_prob, dog_prob = home_prob, away_prob
                else:
                    fav_team = "away"
                    fav_prob, dog_prob = away_prob, home_prob

                # Fair odds
                fair_fav = 1.0 / fav_prob
                fair_dog = 1.0 / dog_prob

                # Acceptable odds: worse for bettor (lower decimal), preserve sign stability
                acc_fav = max(1.000001, fair_fav / JUICE)
                acc_dog = max(1.000001, fair_dog / JUICE)

                # Optional monotonic sanity (home_prob must increase as home_spread increases)
                if STRICT and last_home_spread is not None:
                    if home_spread > last_home_spread and home_prob + 1e-12 < last_home_prob:
                        raise AssertionError(f"{gid}: non-monotone ladder at {tag}")

                last_home_spread = home_spread
                last_home_prob = home_prob

                row.update({
                    f"home_spread_{tag}": home_spread,
                    f"away_spread_{tag}": away_spread,
                    f"fav_team_{tag}": fav_team,
                    f"fav_cover_prob_{tag}": round(fav_prob, 6),
                    f"dog_cover_prob_{tag}": round(dog_prob, 6),
                    f"fair_fav_dec_{tag}": round(fair_fav, 6),
                    f"fair_fav_amer_{tag}": dec_to_amer(fair_fav),
                    f"fair_dog_dec_{tag}": round(fair_dog, 6),
                    f"fair_dog_amer_{tag}": dec_to_amer(fair_dog),
                    f"acc_fav_dec_{tag}": round(acc_fav, 6),
                    f"acc_fav_amer_{tag}": dec_to_amer(acc_fav),
                    f"acc_dog_dec_{tag}": round(acc_dog, 6),
                    f"acc_dog_amer_{tag}": dec_to_amer(acc_dog),
                })

            # -------------------------
            # Soft consistency warnings (no failures)
            # -------------------------
            # Anchor sanity: p0 should be near 0.5 within rounding drift
            z0 = (proj_margin + model_home_spread) / sigma
            p0 = normal_cdf(z0)
            if abs(p0 - 0.5) > (normal_cdf(0.5 / sigma) - 0.5) + 1e-6:
                warn(f"{gid}: p0 unusually far from 0.5 (p0={p0:.4f}, margin={proj_margin:.2f}, spread={model_home_spread:.1f})")

            w.writerow(row)

if __name__ == "__main__":
    main()
