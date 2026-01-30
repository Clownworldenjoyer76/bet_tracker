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
JUICE = 1.047619  # acceptable_dec = fair_dec / JUICE  (worse price for bettor)
EPS = 1e-6
SPREAD_OFFSETS = [-4.0, -2.0, 0.0, 2.0, 4.0]

STRICT = os.getenv("STRICT_VALIDATE", "0") == "1"

# =========================
# Helpers
# =========================
def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def clamp_prob(p: float) -> float:
    return max(EPS, min(1.0 - EPS, p))

def dec_to_amer(d: float) -> int:
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))

def is_half_point(x: float) -> bool:
    return abs((abs(x) % 1.0) - 0.5) < 1e-9

def snap_to_half_point(x: float) -> float:
    """
    Snap to the nearest value ending in .5 (…,-1.5,-0.5,0.5,1.5,…).
    Guarantees |snap - x| <= 0.5.
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
    # tie: deterministic
    return c1

def matchup_sigma(base_sigma: float, proj_total: float) -> float:
    """
    Add minimal, deterministic game-level variance to avoid probability ladder clustering.
    Scales sigma with projected total (higher-scoring games -> higher variance).
    """
    # Typical NBA total ~230. Keep the scaling mild.
    scale = math.sqrt(max(0.80, min(1.25, proj_total / 230.0)))
    return base_sigma * scale

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

            # Map edge rows to away/home reliably
            if rows[0].get("team") == away:
                a, h = rows
            elif rows[1].get("team") == away:
                a, h = rows[1], rows[0]
            else:
                continue

            away_pts = float(a["points"])
            home_pts = float(h["points"])
            away_ml = float(a["win_probability"])
            home_ml = float(h["win_probability"])

            proj_margin = home_pts - away_pts
            proj_total = home_pts + away_pts
            sigma = matchup_sigma(LEAGUE_STD, proj_total)

            # -------------------------
            # Option-B anchor:
            # 1) build anchor from -proj_margin on .5 grid
            # 2) use a "margin_used" that is exactly centered on that anchor so p0 is ~0.50 by construction
            # -------------------------
            model_home_spread = snap_to_half_point(-proj_margin)
            model_away_spread = -model_home_spread

            # Use centered margin for spread probabilities (prevents p0 drift due to snapping)
            margin_used = -model_home_spread  # ensures (margin_used + model_home_spread) == 0

            if STRICT:
                if not is_half_point(model_home_spread):
                    raise AssertionError(f"{gid}: model_home_spread not .5 -> {model_home_spread}")
                if abs((margin_used + model_home_spread)) > 1e-12:
                    raise AssertionError(f"{gid}: margin centering failed")
                if sigma <= 0:
                    raise AssertionError(f"{gid}: non-positive sigma")

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
                "sigma": round(sigma, 6),
                "model_home_spread": model_home_spread,
                "model_away_spread": model_away_spread,
                "away_ml_prob": round(away_ml, 6),
                "home_ml_prob": round(home_ml, 6),
            }

            # -------------------------
            # Ladder (offsets preserve .5 because anchor ends in .5 and offsets are integers)
            # -------------------------
            last_home_spread = None
            last_home_prob = None

            for k in SPREAD_OFFSETS:
                tag = f"m{abs(int(k))}" if k < 0 else f"p{int(k)}"

                home_spread = model_home_spread + k
                away_spread = -home_spread

                if STRICT and not is_half_point(home_spread):
                    raise AssertionError(f"{gid}: home_spread_{tag} not .5 -> {home_spread}")

                # Probability home covers home_spread: P(M + spread > 0), where M = home-away margin
                z = (margin_used + home_spread) / sigma
                home_cover = clamp_prob(normal_cdf(z))
                away_cover = clamp_prob(1.0 - home_cover)

                # Favorite is the side with negative spread (always true unless spread == 0, which cannot happen here)
                if home_spread < 0:
                    fav_team = "home"
                    fav_prob, dog_prob = home_cover, away_cover
                else:
                    fav_team = "away"
                    fav_prob, dog_prob = away_cover, home_cover

                # Fair odds
                fair_fav = 1.0 / fav_prob
                fair_dog = 1.0 / dog_prob

                # Acceptable odds: always worse for bettor than fair (lower decimal)
                acc_fav = max(1.000001, fair_fav / JUICE)
                acc_dog = max(1.000001, fair_dog / JUICE)

                # Optional monotonic check (home_cover must increase as home_spread increases)
                if STRICT and last_home_spread is not None:
                    if home_spread > last_home_spread and home_cover + 1e-12 < last_home_prob:
                        raise AssertionError(f"{gid}: non-monotone ladder at {tag}")

                last_home_spread = home_spread
                last_home_prob = home_cover

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

            # Soft warning: ML vs p0 spread favorite probability disagreement (informational only)
            # (Does not change outputs; just flags potential upstream modeling inconsistency.)
            try:
                p0_tag = "p0"
                fav_team_p0 = row.get(f"fav_team_{p0_tag}")
                fav_prob_p0 = float(row.get(f"fav_cover_prob_{p0_tag}"))
                if fav_team_p0 == "home":
                    ml_fav = home_ml
                else:
                    ml_fav = away_ml
                if abs(ml_fav - 0.5) > 0.25 and abs(fav_prob_p0 - 0.5) < 0.03:
                    warn(f"{gid}: large ML edge with near-coinflip spread p0 (ml_fav={ml_fav:.3f}, p0_fav_cover={fav_prob_p0:.3f})")
            except Exception:
                pass

            w.writerow(row)

if __name__ == "__main__":
    main()
