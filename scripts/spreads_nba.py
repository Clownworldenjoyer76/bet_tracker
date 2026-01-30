#!/usr/bin/env python3

import csv
import math
from pathlib import Path

# ============================================================
# Paths
# ============================================================
TOTALS_DIR = Path("docs/win/nba")
EDGE_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/nba/spreads")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Model constants
# ============================================================
LEAGUE_STD = 7.2
JUICE = 1.047619
EPS = 1e-6

# Spread ladder offsets (points relative to model line)
SPREAD_OFFSETS = [-4.0, -2.0, 0.0, 2.0, 4.0]

# ============================================================
# Helpers
# ============================================================
def round_to_half_no_whole(x: float) -> float:
    """
    Round to nearest half-point, forbid whole numbers.
    """
    r = round(x * 2) / 2
    if r.is_integer():
        return r + 0.5 if r >= 0 else r - 0.5
    return r

def force_half(x: float) -> float:
    """
    Force any number onto a .5 grid.
    """
    return round_to_half_no_whole(x)

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def clamp_prob(p: float) -> float:
    return max(EPS, min(1.0 - EPS, p))

def dec_to_amer(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))

# ============================================================
# Linear interpolation between ladder points
# ============================================================
def interpolate_prob(spreads, probs, target_spread):
    """
    Linear interpolation of cover probability at target_spread.
    Assumes spreads are sorted.
    """
    if target_spread <= spreads[0]:
        return probs[0]
    if target_spread >= spreads[-1]:
        return probs[-1]

    for i in range(len(spreads) - 1):
        s0, s1 = spreads[i], spreads[i + 1]
        if s0 <= target_spread <= s1:
            p0, p1 = probs[i], probs[i + 1]
            w = (target_spread - s0) / (s1 - s0)
            return p0 + w * (p1 - p0)

    raise RuntimeError("Interpolation failure")

# ============================================================
# Main
# ============================================================
def main():
    totals_file = sorted(TOTALS_DIR.glob("edge_nba_totals_*.csv"))[-1]
    with totals_file.open(newline="", encoding="utf-8") as f:
        totals = list(csv.DictReader(f))

    if not totals:
        raise RuntimeError("Totals file empty")

    mm, dd, yyyy = totals[0]["date"].split("/")
    out_path = OUTPUT_DIR / f"edge_nba_spreads_ladder_{yyyy}_{mm.zfill(2)}_{dd.zfill(2)}.csv"

    edge_file = sorted(EDGE_DIR.glob("edge_nba_*.csv"))[-1]
    edge_by_game = {}
    with edge_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            edge_by_game.setdefault(r["game_id"], []).append(r)

    # ============================================================
    # Build schema dynamically
    # ============================================================
    fields = [
        "game_id","date","time","away_team","home_team","league",
        "away_team_proj_pts","home_team_proj_pts",
        "proj_margin","sigma",
        "model_home_spread","model_away_spread",
        "away_ml_prob","home_ml_prob"
    ]

    for k in SPREAD_OFFSETS:
        tag = f"m{abs(int(k))}" if k < 0 else f"p{int(k)}"
        fields += [
            f"home_spread_{tag}",
            f"away_spread_{tag}",
            f"home_cover_prob_{tag}",
            f"away_cover_prob_{tag}",
            f"fair_home_dec_{tag}",
            f"fair_home_amer_{tag}",
            f"fair_away_dec_{tag}",
            f"fair_away_amer_{tag}",
            f"acc_home_dec_{tag}",
            f"acc_home_amer_{tag}",
            f"acc_away_dec_{tag}",
            f"acc_away_amer_{tag}",
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

            if rows[0]["team"] == away:
                a, h = rows
            else:
                h, a = rows

            away_pts = float(a["points"])
            home_pts = float(h["points"])
            away_ml = float(a["win_probability"])
            home_ml = float(h["win_probability"])

            # ====================================================
            # Projection anchor (used ONCE)
            # ====================================================
            proj_margin = home_pts - away_pts
            sigma = LEAGUE_STD

            model_home_spread = force_half(-proj_margin)
            model_away_spread = -model_home_spread

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

            # ====================================================
            # Spread ladder
            # ====================================================
            ladder_spreads = []
            ladder_probs = []

            for k in SPREAD_OFFSETS:
                home_spread = force_half(model_home_spread + k)
                away_spread = -home_spread

                z = (proj_margin + home_spread) / sigma
                home_prob = clamp_prob(normal_cdf(z))
                away_prob = clamp_prob(1.0 - home_prob)

                ladder_spreads.append(home_spread)
                ladder_probs.append(home_prob)

                fair_home_dec = 1.0 / home_prob
                fair_away_dec = 1.0 / away_prob
                acc_home_dec = fair_home_dec * JUICE
                acc_away_dec = fair_away_dec * JUICE

                tag = f"m{abs(int(k))}" if k < 0 else f"p{int(k)}"

                row.update({
                    f"home_spread_{tag}": home_spread,
                    f"away_spread_{tag}": away_spread,
                    f"home_cover_prob_{tag}": round(home_prob, 6),
                    f"away_cover_prob_{tag}": round(away_prob, 6),
                    f"fair_home_dec_{tag}": round(fair_home_dec, 6),
                    f"fair_home_amer_{tag}": dec_to_amer(fair_home_dec),
                    f"fair_away_dec_{tag}": round(fair_away_dec, 6),
                    f"fair_away_amer_{tag}": dec_to_amer(fair_away_dec),
                    f"acc_home_dec_{tag}": round(acc_home_dec, 6),
                    f"acc_home_amer_{tag}": dec_to_amer(acc_home_dec),
                    f"acc_away_dec_{tag}": round(acc_away_dec, 6),
                    f"acc_away_amer_{tag}": dec_to_amer(acc_away_dec),
                })

            # ====================================================
            # Example interpolation (market-ready)
            # ====================================================
            # Example: evaluate probability at model_home_spread + 1.5
            # target_spread = force_half(model_home_spread + 1.5)
            # interp_prob = interpolate_prob(ladder_spreads, ladder_probs, target_spread)

            w.writerow(row)

if __name__ == "__main__":
    main()
