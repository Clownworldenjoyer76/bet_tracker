#!/usr/bin/env python3
"""
simulate_pool_winprob.py

Compute win probability for a given 6-country lineup in a 2000-player pool,
using 10,000 simulated Olympics and your scoring rules.

Model:
- Country medal counts ~ Poisson(lambda) for Gold/Silver/Bronze
- Lambdas from "past 30 years" / 8 Olympics; fallback to all-time per-games averages
- Points = (3G + 2S + 1B) * tier + first-medal-bonus(if any medal)
- first-medal-bonus = 25*(tier/2)

Pool:
- 1 lineup = "you"
- 1999 opponent lineups sampled once (players keep same picks for the Games)
- For each simulated Olympics: compute all scores and determine winner
- Tie-handling: random tie-break among all top scorers -> expected win share

Outputs:
- strict win probability (you strictly beat everyone)
- expected win share (random tie-break among ties)
"""

import argparse
import math
import numpy as np
import pandas as pd
from itertools import combinations

# -----------------------------
# Inputs (from your message)
# -----------------------------
TIERS = {
    "Norway": 1, "Canada": 1, "Germany": 1, "USA": 1,
    "Netherlands": 2, "Austria": 2, "Sweden": 2, "France": 2, "Switzerland": 2,
    "Japan": 2, "Korea": 2, "China": 2,
    "Italy": 3, "Finland": 3, "Czechia": 3,
    "Slovenia": 4, "Belarus": 4, "Great Britain": 4,
    "Australia": 5, "Poland": 5, "Latvia": 5, "Slovakia": 5, "New Zealand": 5, "Ukraine": 5, "Hungary": 5,
    "Belgium": 6, "Spain": 6, "Kazakhstan": 6, "Croatia": 6, "Liechtenstein": 6, "Estonia": 6
}

ALL_TIME = pd.DataFrame([
    ("Norway", 24, 148, 133, 124),
    ("USA", 24, 114, 121, 95),
    ("Germany", 28, 162, 155, 118),
    ("Canada", 24, 77, 72, 76),
    ("Austria", 24, 71, 88, 91),
    ("Sweden", 24, 65, 51, 60),
    ("Switzerland", 24, 63, 47, 57),
    ("Netherlands", 22, 53, 49, 45),
    ("Finland", 24, 45, 65, 65),
    ("Italy", 24, 42, 43, 56),
    ("France", 24, 41, 42, 55),
    ("Korea", 28, 33, 31, 17),
    ("China", 12, 22, 32, 23),
    ("Japan", 22, 17, 28, 31),
    ("Great Britain", 24, 12, 5, 17),
    ("Czechia", 24, 12, 19, 27),
    ("Belarus", 8, 8, 7, 5),
    ("Poland", 24, 7, 7, 9),
    ("Australia", 20, 6, 7, 6),
    ("Slovenia", 9, 4, 8, 12),
    ("Croatia", 9, 4, 6, 1),
    ("Slovakia", 8, 4, 4, 2),
    ("Estonia", 11, 4, 2, 2),
    ("Ukraine", 8, 3, 2, 4),
    ("Hungary", 24, 2, 2, 6),
    ("Liechtenstein", 20, 2, 2, 6),
    ("Belgium", 22, 2, 2, 4),
    ("New Zealand", 17, 2, 2, 2),
    ("Latvia", 12, 1, 3, 6),
    ("Kazakhstan", 8, 1, 3, 4),
    ("Spain", 21, 1, 1, 3),
], columns=["Country", "No_Games", "Gold", "Silver", "Bronze"])

PAST30 = pd.DataFrame([
    ("Australia", 1, 2, 1),
    ("Austria", 7, 7, 4),
    ("Belarus", 0, 2, 0),
    ("Belgium", 1, 0, 1),
    ("Canada", 46, 43, 41),
    ("China", 9, 4, 2),
    ("Czechia", 1, 0, 1),
    ("Estonia", 0, 0, 1),
    ("Finland", 2, 2, 4),
    ("France", 5, 7, 2),
    ("Germany", 99, 97, 61),
    ("Great Britain", 1, 1, 0),
    ("Hungary", 1, 0, 2),
    ("Italy", 2, 7, 8),
    ("Japan", 3, 6, 9),
    ("Korea", 2, 5, 2),
    ("Latvia", 0, 0, 1),
    ("Netherlands", 8, 5, 4),
    ("New Zealand", 2, 1, 0),
    ("Norway", 83, 59, 56),
    ("Poland", 0, 0, 1),
    ("Slovakia", 1, 0, 1),
    ("Slovenia", 2, 3, 2),
    ("Spain", 0, 1, 0),
    ("Sweden", 8, 5, 5),
    ("Switzerland", 5, 5, 5),
    ("Switzerland", 7, 2, 5),  # duplicated in your paste; must aggregate
    ("Ukraine", 0, 1, 0),
    ("USA", 45, 54, 50),
], columns=["Country", "Gold", "Silver", "Bronze"]).groupby("Country", as_index=False)[["Gold","Silver","Bronze"]].sum()

GAMES_30Y = 8


# -----------------------------
# Scoring
# -----------------------------
def first_bonus(tier: int) -> float:
    return 25.0 * (tier / 2.0)


def build_lambdas(countries: list[str]) -> pd.DataFrame:
    fb = ALL_TIME.copy()
    fb["lam_g"] = fb["Gold"] / fb["No_Games"]
    fb["lam_s"] = fb["Silver"] / fb["No_Games"]
    fb["lam_b"] = fb["Bronze"] / fb["No_Games"]
    fb = fb[["Country","lam_g","lam_s","lam_b"]]

    lam = pd.DataFrame({"Country": countries}).merge(PAST30, on="Country", how="left").merge(fb, on="Country", how="left", suffixes=("","_fb"))

    lam["lam_g"] = np.where(lam["Gold"].notna(), lam["Gold"]/GAMES_30Y, lam["lam_g"])
    lam["lam_s"] = np.where(lam["Silver"].notna(), lam["Silver"]/GAMES_30Y, lam["lam_s"])
    lam["lam_b"] = np.where(lam["Bronze"].notna(), lam["Bronze"]/GAMES_30Y, lam["lam_b"])
    lam[["lam_g","lam_s","lam_b"]] = lam[["lam_g","lam_s","lam_b"]].fillna(0.0)
    lam["tier"] = lam["Country"].map(TIERS).astype(int)
    return lam


def simulate_olympics_points(lam: pd.DataFrame, n_olympics: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    C = lam.shape[0]
    tier = lam["tier"].to_numpy(dtype=np.int16)

    G = rng.poisson(lam=lam["lam_g"].to_numpy(), size=(n_olympics, C))
    S = rng.poisson(lam=lam["lam_s"].to_numpy(), size=(n_olympics, C))
    B = rng.poisson(lam=lam["lam_b"].to_numpy(), size=(n_olympics, C))

    tot = G + S + B
    bonus = (tot > 0) * (25.0 * (tier / 2.0))
    pts = ((3*G + 2*S + 1*B) * tier) + bonus
    return pts.astype(np.float32)


def precompute_all_combos(C: int, k: int = 6) -> np.ndarray:
    # 31 choose 6 = 736,281 -> ~9MB as int16 (safe)
    combos = np.fromiter((i for comb in combinations(range(C), k) for i in comb), dtype=np.int16)
    return combos.reshape(-1, k)


def sample_opponents(n_combos: int, n_opp: int, model: str, combo_weights: np.ndarray | None, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if model == "uniform":
        return rng.integers(0, n_combos, size=n_opp, dtype=np.int32)
    if model in ("ev_biased", "tier_biased"):
        if combo_weights is None:
            raise ValueError("combo_weights required for biased models")
        return rng.choice(n_combos, size=n_opp, replace=True, p=combo_weights).astype(np.int32)
    raise ValueError(f"Unknown model: {model}")


def pool_win_probability(
    country_points: np.ndarray,
    my_idx: np.ndarray,
    combos: np.ndarray,
    opp_combo_idx: np.ndarray,
    chunk_players: int = 500
) -> tuple[float, float]:
    """
    Returns:
    - strict win probability (my_score > max_opp)
    - expected win share (random tiebreak among top scores)
    """
    N, C = country_points.shape
    my_scores = country_points[:, my_idx].sum(axis=1)

    opp_lineups = combos[opp_combo_idx]  # (OPP,6)
    OPP = opp_lineups.shape[0]

    max_opp = np.full(N, -1e18, dtype=np.float32)
    cnt_at_max = np.zeros(N, dtype=np.int16)

    # compute max opponent score per Olympics in chunks
    for start in range(0, OPP, chunk_players):
        end = min(OPP, start + chunk_players)
        ch = opp_lineups[start:end]  # (k,6)

        # allocate once and do in-place adds (fast)
        scores = country_points[:, ch[:, 0]].copy()
        scores += country_points[:, ch[:, 1]]
        scores += country_points[:, ch[:, 2]]
        scores += country_points[:, ch[:, 3]]
        scores += country_points[:, ch[:, 4]]
        scores += country_points[:, ch[:, 5]]

        ch_max = scores.max(axis=1)
        better = ch_max > max_opp
        equal = ch_max == max_opp

        if np.any(better):
            max_opp[better] = ch_max[better]
            cnt_at_max[better] = (scores[better] == ch_max[better, None]).sum(axis=1).astype(np.int16)
        if np.any(equal):
            cnt_at_max[equal] = (cnt_at_max[equal] + (scores[equal] == max_opp[equal, None]).sum(axis=1).astype(np.int16))

    strict_win = float((my_scores > max_opp).mean())

    ties = (my_scores == max_opp)
    win_share = np.where(my_scores > max_opp, 1.0, np.where(ties, 1.0/(1.0 + cnt_at_max.astype(np.float32)), 0.0)).mean()
    return strict_win, float(win_share)


def build_combo_weights(lam: pd.DataFrame, points: np.ndarray, combos: np.ndarray, model: str) -> np.ndarray:
    """
    Approximate opponent combo popularity:
    - ev_biased: product of per-country EV shares
    - tier_biased: product of per-country tier-popularity weights
    """
    if model == "ev_biased":
        ev = points.mean(axis=0).astype(np.float64)
        p = ev / ev.sum()
        w = np.prod(p[combos], axis=1)
        w = w / w.sum()
        return w.astype(np.float64)

    if model == "tier_biased":
        tier = lam["tier"].to_numpy()
        # adjustable knobs: heavier weight to Tier 1/2
        base = {1:4.0, 2:2.5, 3:1.8, 4:1.2, 5:1.0, 6:0.9}
        p = np.array([base[int(t)] for t in tier], dtype=np.float64)
        p = p / p.sum()
        w = np.prod(p[combos], axis=1)
        w = w / w.sum()
        return w.astype(np.float64)

    raise ValueError("Unknown model for weights")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--players", type=int, default=2000)
    ap.add_argument("--olympics", type=int, default=10000)
    ap.add_argument("--seed_olympics", type=int, default=42)
    ap.add_argument("--seed_pool", type=int, default=123)
    ap.add_argument("--opponent_model", choices=["uniform", "ev_biased", "tier_biased"], default="uniform")
    ap.add_argument("--lineup", type=str, default="Germany,Norway,USA,Canada,Kazakhstan,Croatia")
    args = ap.parse_args()

    countries = sorted(TIERS.keys())
    idx = {c:i for i,c in enumerate(countries)}

    lineup = [x.strip() for x in args.lineup.split(",")]
    if len(lineup) != 6 or len(set(lineup)) != 6:
        raise SystemExit("Lineup must contain exactly 6 unique countries.")
    for c in lineup:
        if c not in idx:
            raise SystemExit(f"Unknown country in lineup: {c}")

    lam = build_lambdas(countries)
    pts = simulate_olympics_points(lam, args.olympics, args.seed_olympics)

    combos = precompute_all_combos(len(countries), 6)

    combo_weights = None
    if args.opponent_model in ("ev_biased", "tier_biased"):
        combo_weights = build_combo_weights(lam, pts, combos, args.opponent_model)

    opp = args.players - 1
    opp_combo_idx = sample_opponents(combos.shape[0], opp, args.opponent_model, combo_weights, args.seed_pool)

    my_idx = np.array([idx[c] for c in lineup], dtype=np.int16)

    strict, share = pool_win_probability(pts, my_idx, combos, opp_combo_idx, chunk_players=500)

    print("=== Pool Win Probability ===")
    print(f"Players: {args.players} (opponents={opp})")
    print(f"Olympics simulated: {args.olympics}")
    print(f"Opponent model: {args.opponent_model}")
    print(f"My lineup: {', '.join(lineup)}")
    print(f"Strict win probability: {strict:.6f}")
    print(f"Expected win share (random tiebreak): {share:.6f}")


if __name__ == "__main__":
    main()
