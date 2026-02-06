import numpy as np
import pandas as pd
from itertools import combinations

# -----------------------------
# CONFIG
# -----------------------------
N_OLYMPICS = 50000
OUTPUT_PATH = "testing/olympics/top_lineups_k15.csv"
SEED = 42

TOP_15 = [
    "Germany","Norway","USA","Canada","Austria",
    "Netherlands","Japan","Sweden","Switzerland","China",
    "Italy","Finland","Slovenia","Kazakhstan","Croatia"
]

TIERS = {
    "Norway":1,"Canada":1,"Germany":1,"USA":1,
    "Netherlands":2,"Austria":2,"Sweden":2,"France":2,"Switzerland":2,
    "Japan":2,"Korea":2,"China":2,
    "Italy":3,"Finland":3,"Czechia":3,
    "Slovenia":4,"Belarus":4,"Great Britain":4,
    "Australia":5,"Poland":5,"Latvia":5,"Slovakia":5,"New Zealand":5,"Ukraine":5,"Hungary":5,
    "Belgium":6,"Spain":6,"Kazakhstan":6,"Croatia":6,"Liechtenstein":6,"Estonia":6
}

# Past 30 years medal counts
PAST30 = {
    "Germany":(99,97,61),
    "Norway":(83,59,56),
    "USA":(45,54,50),
    "Canada":(46,43,41),
    "Austria":(7,7,4),
    "Netherlands":(8,5,4),
    "Japan":(3,6,9),
    "Sweden":(8,5,5),
    "Switzerland":(12,7,10),
    "China":(9,4,2),
    "Italy":(2,7,8),
    "Finland":(2,2,4),
    "Slovenia":(2,3,2),
    "Kazakhstan":(1,3,4),
    "Croatia":(4,6,1)
}

GAMES_30Y = 8

# -----------------------------
# BUILD LAMBDAS
# -----------------------------
countries = TOP_15
C = len(countries)

lam_g = np.array([PAST30[c][0]/GAMES_30Y for c in countries])
lam_s = np.array([PAST30[c][1]/GAMES_30Y for c in countries])
lam_b = np.array([PAST30[c][2]/GAMES_30Y for c in countries])
tiers = np.array([TIERS[c] for c in countries])

# -----------------------------
# SIMULATE OLYMPICS
# -----------------------------
rng = np.random.default_rng(SEED)

G = rng.poisson(lam=lam_g, size=(N_OLYMPICS, C))
S = rng.poisson(lam=lam_s, size=(N_OLYMPICS, C))
B = rng.poisson(lam=lam_b, size=(N_OLYMPICS, C))

tot = G + S + B
bonus = (tot > 0) * (25 * (tiers / 2))

country_points = ((3*G + 2*S + B) * tiers) + bonus

# -----------------------------
# EVALUATE ALL LINEUPS
# -----------------------------
lineups = list(combinations(range(C), 6))
scores = np.zeros((len(lineups), N_OLYMPICS), dtype=np.float32)

for i, idxs in enumerate(lineups):
    scores[i] = country_points[:, idxs].sum(axis=1)

# -----------------------------
# METRICS
# -----------------------------
mean = scores.mean(axis=1)
median = np.median(scores, axis=1)
p90 = np.percentile(scores, 90, axis=1)
p99 = np.percentile(scores, 99, axis=1)

# win rate vs all other lineups
ranks = scores.argsort(axis=0)
winner = ranks[-1]
win_rate = np.bincount(winner, minlength=len(lineups)) / N_OLYMPICS

# -----------------------------
# OUTPUT
# -----------------------------
out = pd.DataFrame({
    "lineup": [",".join(countries[i] for i in l) for l in lineups],
    "expected_points": mean,
    "median": median,
    "p90": p90,
    "p99": p99,
    "win_rate": win_rate
})

out = out.sort_values("win_rate", ascending=False).reset_index(drop=True)
out.insert(0, "rank", np.arange(1, len(out)+1))

out.to_csv(OUTPUT_PATH, index=False)

print(f"Wrote {OUTPUT_PATH}")
print(out.head(10))
