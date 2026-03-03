#!/usr/bin/env python3

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LinearRegression

# =========================
# PATHS
# =========================

BASE = Path("bets/historic/NCAA MENS BASKETBALL")
RATINGS_DIR = BASE / "cbb"
GAMES_FILE = BASE / "games.csv"

HCA = 3.2  # temporary, will be indirectly calibrated

# =========================
# LOAD RATINGS
# =========================

ratings_list = []

for file in RATINGS_DIR.glob("*.csv"):
    df = pd.read_csv(file)
    season_digits = ''.join(filter(str.isdigit, file.name))
    season = int("20" + season_digits[-2:])
    df["season"] = season
    df.rename(columns={"TEAM": "team"}, inplace=True)
    ratings_list.append(df)

ratings = pd.concat(ratings_list, ignore_index=True)

# =========================
# LOAD GAMES
# =========================

games = pd.read_csv(GAMES_FILE)

# =========================
# MERGE RATINGS
# =========================

games = games.merge(
    ratings.add_prefix("home_"),
    left_on=["season", "home_team"],
    right_on=["home_season", "home_team"],
    how="left"
)

games = games.merge(
    ratings.add_prefix("away_"),
    left_on=["season", "away_team"],
    right_on=["away_season", "away_team"],
    how="left"
)

# Drop missing merges
games = games.dropna(subset=["home_ADJOE", "away_ADJOE"])

# =========================
# BUILD RAW PROJECTION
# =========================

games["raw_proj"] = (
    (games["home_ADJOE"] - games["away_ADJDE"])
    -
    (games["away_ADJOE"] - games["home_ADJDE"])
    + HCA
)

games["actual_margin"] = games["home_score"] - games["away_score"]

# =========================
# FIT MULTIPLIER
# =========================

X = games[["raw_proj"]].values
y = games["actual_margin"].values

model = LinearRegression(fit_intercept=False)
model.fit(X, y)

multiplier = model.coef_[0]

games["scaled_proj"] = games["raw_proj"] * multiplier

print("\n=== CALIBRATED MULTIPLIER ===")
print(multiplier)

# =========================
# RESIDUAL STD
# =========================

games["residual"] = games["actual_margin"] - games["scaled_proj"]
spread_std = games["residual"].std()

print("\n=== TRUE SPREAD STD ===")
print(spread_std)

# =========================
# EDGE CALCULATION
# =========================

games["edge"] = games["scaled_proj"] - games["closing_spread"]

print("\n=== THRESHOLD BACKTEST ===")

for t in np.arange(1, 6, 0.5):
    subset = games[np.abs(games["edge"]) >= t]
    if len(subset) < 200:
        continue
    
    correct = np.sign(subset["edge"]) == np.sign(
        subset["actual_margin"] - subset["closing_spread"]
    )
    
    win_rate = correct.mean()
    
    print(f"Edge ≥ {t:.1f}  |  Bets: {len(subset)}  |  Win%: {win_rate:.3f}")

print("\nDone.\n")
