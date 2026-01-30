#!/usr/bin/env python3

import csv
import math
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
JUICE = 1.047619
EPS = 1e-6
SPREAD_OFFSETS = [-4.0, -2.0, 0.0, 2.0, 4.0]

# With "no whole numbers" adjustment, rounding can drift up to 0.75 pts from proj_margin.
MAX_ANCHOR_DRIFT = 0.75
DRIFT_EPS = 1e-9

# =========================
# Helpers
# =========================
def round_to_half_no_whole(x: float) -> float:
    """
    Round to nearest 0.5, but if result is an integer, force to +/-0.5 away from zero.
    This can introduce up to 0.75 points of drift vs x (worst-case).
    """
    r = round(x * 2) / 2
    if r.is_integer():
        return r + 0.5 if r >= 0 else r - 0.5
    return r

def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def clamp_prob(p: float) -> float:
    return max(EPS, min(1.0 - EPS, p))

def dec_to_amer(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))

def is_half_point(x: float) -> bool:
    # True if x ends with .5 (including negative values)
    return abs((abs(x) % 1.0) - 0.5) < 1e-9

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

            if rows[0]["team"] == away:
                a, h = rows
            else:
                h, a = rows

            away_pts = float(a["points"])
            home_pts = float(h["points"])
            away_ml = float(a["win_probability"])
            home_ml = float(h["win_probability"])

            proj_margin = home_pts - away_pts
            sigma = LEAGUE_STD

            # =========================
            # Option B anchor (correct)
            # =========================
            model_home_spread = -round_to_half_no_whole(proj_margin)
            model_away_spread = -model_home_spread

            # Anchor drift must be explainable solely by rounding + "no whole" rule.
            drift = abs(proj_margin + model_home_spread)
            assert drift <= MAX_ANCHOR_DRIFT + DRIFT_EPS, (
                f"Anchor drift too large for {gid}: drift={drift:.6f}, "
                f"proj_margin={proj_margin:.6f}, model_home_spread={model_home_spread:.6f}"
            )

            # All spreads must be half-points
            assert is_half_point(model_home_spread), f"Anchor not .5 for {gid}: {model_home_spread}"
            assert is_half_point(model_away_spread), f"Anchor not .5 for {gid}: {model_away_spread}"

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

            # =========================
            # Spread ladder
            # =========================
            for k in SPREAD_OFFSETS:
                tag = f"m{abs(int(k))}" if k < 0 else f"p{int(k)}"

                home_spread = round_to_half_no_whole(model_home_spread + k)
                away_spread = -home_spread

                assert is_half_point(home_spread), f"home_spread_{tag} not .5 for {gid}: {home_spread}"
                assert is_half_point(away_spread), f"away_spread_{tag} not .5 for {gid}: {away_spread}"

                z = (proj_margin + home_spread) / sigma
                home_prob = clamp_prob(normal_cdf(z))
                away_prob = clamp_prob(1.0 - home_prob)

                # Market-safe: always report favorite vs dog
                if home_spread < 0:
                    fav_team = "home"
                    fav_prob, dog_prob = home_prob, away_prob
                else:
                    fav_team = "away"
                    fav_prob, dog_prob = away_prob, home_prob

                fair_fav = 1.0 / fav_prob
                fair_dog = 1.0 / dog_prob
                acc_fav = fair_fav * JUICE
                acc_dog = fair_dog * JUICE

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

            w.writerow(row)

if __name__ == "__main__":
    main()
