#!/usr/bin/env python3

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LinearRegression
from scipy.stats import norm

# =========================
# PATHS
# =========================

BASE = Path("bets/historic/NCAA MENS BASKETBALL")
RATINGS_DIR = BASE / "cbb"
GAMES_FILE = BASE / "games.csv"

SUMMARY_CSV = BASE / "calibration_summary.csv"
SUMMARY_XLSX = BASE / "calibration_summary.xlsx"

HCA = 3.2

# =========================
# LOAD RATINGS
# =========================

ratings_list = []

for file in RATINGS_DIR.glob("*.csv"):
    df = pd.read_csv(file)

    season_digits = ''.join(filter(str.isdigit, file.name))
    if season_digits:
        season = int("20" + season_digits[-2:])
    else:
        season = None

    df["season"] = season
    df.rename(columns={"TEAM": "team", "Team": "team"}, inplace=True)

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

# =========================
# RESIDUAL STD
# =========================

games["residual"] = games["actual_margin"] - games["scaled_proj"]
spread_std = games["residual"].std()

# =========================
# EDGE TESTING
# =========================

games["edge"] = games["scaled_proj"] - games["closing_spread"]

threshold_results = []

for t in np.arange(1, 6.5, 0.5):
    subset = games[np.abs(games["edge"]) >= t]
    if len(subset) < 200:
        continue

    correct = np.sign(subset["edge"]) == np.sign(
        subset["actual_margin"] - subset["closing_spread"]
    )

    win_rate = correct.mean()

    threshold_results.append({
        "edge_threshold": round(t, 2),
        "bets": len(subset),
        "win_rate": round(win_rate, 4)
    })

threshold_df = pd.DataFrame(threshold_results)

summary_df = pd.DataFrame([{
    "multiplier": round(multiplier, 6),
    "spread_std": round(spread_std, 6),
    "total_games_used": len(games)
}])

# =========================
# SAVE TO REPO
# =========================

summary_df.to_csv(SUMMARY_CSV, index=False)

with pd.ExcelWriter(SUMMARY_XLSX) as writer:
    summary_df.to_excel(writer, sheet_name="model_constants", index=False)
    threshold_df.to_excel(writer, sheet_name="threshold_backtest", index=False)

print("Calibration complete.")
print("Files written to repo:")
print(SUMMARY_CSV)
print(SUMMARY_XLSX)
