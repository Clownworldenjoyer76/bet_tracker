import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import xgboost as xgb
import pickle
import warnings
warnings.filterwarnings("ignore")

df = pd.read_parquet("ufc_features.parquet")
df = df.sort_values("match_date").reset_index(drop=True)

# Separate originals
df["fight_key"] = df.apply(lambda r: "_".join(sorted([r["fighter_1"], r["fighter_2"]])) + "_" + str(r["match_date"].date()), axis=1)
df["is_mirror"] = df.duplicated(subset="fight_key", keep="first")
original = df[~df["is_mirror"]].copy()

FEATURES = [
    "implied_prob_f1",
    "f1_win_rate_all", "f1_win_rate_last5", "f1_streak", "f1_experience",
    "f1_days_since_last", "f1_sos", "f1_age", "f1_reach", "f1_height",
    "f2_win_rate_all", "f2_win_rate_last5", "f2_streak", "f2_experience",
    "f2_days_since_last", "f2_sos", "f2_age", "f2_reach", "f2_height",
    "diff_win_rate_all", "diff_win_rate_last5", "diff_streak", "diff_experience",
    "diff_days_since_last", "diff_sos", "diff_age", "diff_reach", "diff_height",
]
TARGET = "result"

train = original[original["match_date"] < "2025-01-01"].copy()
test  = original[original["match_date"] >= "2025-01-01"].copy()
train = train.dropna(subset=["implied_prob_f1"])
test  = test.dropna(subset=["implied_prob_f1"])

median_fill = train[FEATURES].median()
X_train = train[FEATURES].fillna(median_fill)
y_train = train[TARGET]
X_test  = test[FEATURES].fillna(median_fill)
y_test  = test[TARGET]

# --- Recency weights: exponential decay, half-life 365 days ---
cutoff = pd.Timestamp("2025-01-01")
days_before_cutoff = (cutoff - train["match_date"]).dt.days
sample_weights = np.exp(-days_before_cutoff * np.log(2) / 365)
sample_weights = sample_weights / sample_weights.sum() * len(sample_weights)

print(f"Train: {len(X_train)} fights | Test: {len(X_test)} fights")
print(f"Weight range: {sample_weights.min():.3f} to {sample_weights.max():.3f}")

# --- Baseline ---
print("\n--- BASELINE: Implied Probability Only ---")
lr_base = LogisticRegression()
lr_base.fit(train[["implied_prob_f1"]].fillna(0.5), y_train)
base_preds = lr_base.predict_proba(test[["implied_prob_f1"]].fillna(0.5))[:, 1]
base_brier = brier_score_loss(y_test, base_preds)
base_logloss = log_loss(y_test, base_preds)
print(f"Brier Score: {base_brier:.4f}")
print(f"Log Loss:    {base_logloss:.4f}")

# --- Logistic Regression with recency weights ---
print("\n--- LOGISTIC REGRESSION (recency weighted) ---")
lr_pipe = Pipeline([("scaler", StandardScaler()), ("lr", LogisticRegression(max_iter=1000, C=0.1))])
lr_pipe.fit(X_train, y_train, lr__sample_weight=sample_weights.values)
lr_preds = lr_pipe.predict_proba(X_test)[:, 1]
lr_brier = brier_score_loss(y_test, lr_preds)
lr_logloss = log_loss(y_test, lr_preds)
print(f"Brier Score: {lr_brier:.4f}  (baseline: {base_brier:.4f})")
print(f"Log Loss:    {lr_logloss:.4f}  (baseline: {base_logloss:.4f})")

# --- XGBoost with recency weights ---
print("\n--- XGBOOST (recency weighted) with TimeSeriesSplit CV ---")
tscv = TimeSeriesSplit(n_splits=5)
cv_brier, cv_logloss = [], []

for fold, (tr_idx, val_idx) in enumerate(tscv.split(X_train)):
    fold_weights = sample_weights.values[tr_idx]
    model = xgb.XGBClassifier(
        n_estimators=300, max_depth=3, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
        eval_metric="logloss", random_state=42, verbosity=0
    )
    model.fit(X_train.iloc[tr_idx], y_train.iloc[tr_idx], sample_weight=fold_weights)
    preds = model.predict_proba(X_train.iloc[val_idx])[:, 1]
    cv_brier.append(brier_score_loss(y_train.iloc[val_idx], preds))
    cv_logloss.append(log_loss(y_train.iloc[val_idx], preds))
    print(f"  Fold {fold+1}: Brier={cv_brier[-1]:.4f}  LogLoss={cv_logloss[-1]:.4f}")

print(f"\nCV Mean Brier:   {np.mean(cv_brier):.4f} (+/- {np.std(cv_brier):.4f})")
print(f"CV Mean LogLoss: {np.mean(cv_logloss):.4f} (+/- {np.std(cv_logloss):.4f})")

# --- Final XGBoost ---
print("\n--- FINAL XGBOOST: Full train -> test ---")
xgb_model = xgb.XGBClassifier(
    n_estimators=300, max_depth=3, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
    eval_metric="logloss", random_state=42, verbosity=0
)
xgb_model.fit(X_train, y_train, sample_weight=sample_weights.values)
xgb_preds = xgb_model.predict_proba(X_test)[:, 1]
xgb_brier = brier_score_loss(y_test, xgb_preds)
xgb_logloss = log_loss(y_test, xgb_preds)
print(f"Brier Score: {xgb_brier:.4f}  (baseline: {base_brier:.4f})")
print(f"Log Loss:    {xgb_logloss:.4f}  (baseline: {base_logloss:.4f})")

best_preds = xgb_preds if xgb_brier < lr_brier else lr_preds
best_name = "XGBoost" if xgb_brier < lr_brier else "Logistic Regression"
print(f"\nBest model: {best_name}")

# --- ROI Simulation ---
def simulate_roi(test_df, preds, threshold, kelly_fraction=0.25):
    df_sim = test_df.copy().reset_index(drop=True)
    df_sim["model_prob"] = preds
    df_sim["edge"] = df_sim["model_prob"] - df_sim["implied_prob_f1"]
    bets = df_sim[df_sim["edge"] > threshold].copy()
    if len(bets) == 0:
        return None, 0, 0
    bankroll = 1000.0
    profits = []
    for _, row in bets.iterrows():
        p = row["model_prob"]
        try:
            ml = float(str(row["moneyline_f1"]).replace("+", ""))
            odds = ml / 100 if ml > 0 else 100 / abs(ml)
        except:
            continue
        kelly = (p * (odds + 1) - 1) / odds
        stake = max(0, kelly * kelly_fraction * bankroll)
        profit = stake * odds if row["result"] == 1 else -stake
        bankroll += profit
        profits.append(profit)
    roi = (bankroll - 1000) / 1000 * 100
    win_rate = sum(1 for p in profits if p > 0) / len(profits) * 100 if profits else 0
    return roi, len(bets), win_rate

print("\n--- ROI SIMULATION (ALL FIGHTERS) ---")
print(f"\n{'Threshold':>10} {'Bets':>6} {'Win%':>7} {'ROI':>8}")
print("-" * 35)
for threshold in [0.03, 0.05, 0.07, 0.10]:
    roi, n_bets, win_rate = simulate_roi(test, best_preds, threshold)
    if roi is not None:
        print(f"{threshold:>10.0%} {n_bets:>6} {win_rate:>6.1f}% {roi:>7.1f}%")
    else:
        print(f"{threshold:>10.0%} {'0':>6} {'N/A':>7} {'N/A':>8}")

print("\n--- ROI SIMULATION (UNDERDOGS ONLY, implied_prob < 0.5) ---")
mask = test["implied_prob_f1"].values < 0.5
test_dogs = test[mask].copy().reset_index(drop=True)
if best_name == "XGBoost":
    dog_preds = xgb_model.predict_proba(X_test[mask])[:, 1]
else:
    dog_preds = lr_pipe.predict_proba(X_test[mask])[:, 1]
print(f"Underdog fights in test: {len(test_dogs)}")
print(f"\n{'Threshold':>10} {'Bets':>6} {'Win%':>7} {'ROI':>8}")
print("-" * 35)
for threshold in [0.03, 0.05, 0.07, 0.10]:
    roi, n_bets, win_rate = simulate_roi(test_dogs, dog_preds, threshold)
    if roi is not None:
        print(f"{threshold:>10.0%} {n_bets:>6} {win_rate:>6.1f}% {roi:>7.1f}%")
    else:
        print(f"{threshold:>10.0%} {'0':>6} {'N/A':>7} {'N/A':>8}")

# --- Feature Importance ---
print("\n--- FEATURE IMPORTANCE (top 10) ---")
importance = pd.Series(xgb_model.feature_importances_, index=FEATURES)
print(importance.sort_values(ascending=False).head(10).to_string())

# --- Save ---
with open("ufc_model.pkl", "wb") as f:
    pickle.dump({"xgb": xgb_model, "lr": lr_pipe, "median_fill": median_fill, "best": best_name}, f)

test = test.reset_index(drop=True)
test["model_prob"] = best_preds
test["edge"] = test["model_prob"] - test["implied_prob_f1"]
test[["match_date","fighter_1","fighter_2","result","implied_prob_f1","model_prob","edge"]].to_csv("test_predictions.csv", index=False)
print("\nSaved: ufc_model.pkl, test_predictions.csv")
