# UFC Fight Prediction Model

A machine learning pipeline to predict UFC fight outcomes and identify betting edges against sportsbook implied probabilities.

---

## Project Structure

```
ufc-model/
├── data/
│   ├── raw/          # Original CSV files (one per event date, 434 files)
│   └── processed/    # Generated data files (parquet, json, pkl, csv)
├── scripts/          # All Python scripts
├── .gitignore
└── README.md
```

---

## Setup

```powershell
pip install pandas pyarrow requests beautifulsoup4 scikit-learn xgboost
```

---

## Scripts — Run in This Order

### 1. `parse_ufc_files.py`
Reads all CSV files from `data/raw/`, standardizes fighter names and dates, validates for duplicates and missing results, and saves a consolidated dataset.

**Input:** `data/raw/*.csv`
**Output:** `data/processed/ufc_master.parquet`

```powershell
python scripts/parse_ufc_files.py
```

---

### 2. `fix_fighter_names.py`
Generates a template JSON file listing all unique fighter names that need manual correction review.

**Input:** `data/processed/ufc_master.parquet`
**Output:** `name_corrections_template.json` (review before next step)

```powershell
python scripts/fix_fighter_names.py
```

---

### 3. `apply_corrections.py`
Applies name corrections from `name_corrections.json` to fix mangled fighter names caused by multi-word last names being split incorrectly in source files.

**Input:** `data/processed/ufc_master.parquet`, `name_corrections.json`
**Output:** `data/processed/ufc_master_clean.parquet`

```powershell
python scripts/apply_corrections.py
```

---

### 4. `scrape_fighter_stats.py`
Scrapes ufcstats.com for all fighters in the dataset. Pulls height, weight, reach, stance, DOB, career record (wins/losses), significant strikes landed per minute (SLpM), strikes absorbed per minute (SApM), takedown accuracy, and takedown defense. Runs at ~1.5 second delay per fighter to avoid being blocked. Takes approximately 45 minutes for ~1,168 fighters.

**Input:** `data/processed/ufc_master_clean.parquet`
**Output:** `data/processed/fighter_attributes.json`

```powershell
python scripts/scrape_fighter_stats.py
```

---

### 5. `fix_unmatched_fighters.py`
Handles fighters whose names didn't match the ufcstats index due to capitalization differences (e.g. "McGregor" vs "Mcgregor") or alternate name formats (e.g. "Ian Garry" vs "Ian Machado Garry"). Uses a manual mapping dictionary to resolve ~42 additional fighters.

**Input:** `data/processed/fighter_attributes.json`
**Output:** `data/processed/fighter_attributes.json` (updated in place)

```powershell
python scripts/fix_unmatched_fighters.py
```

---

### 6. `scrape_historical_stats.py`
Scrapes each fighter's full fight-by-fight history from ufcstats.com. For every fight in the dataset, computes cumulative stats (career record, SLpM, strike accuracy, takedown accuracy) up to but not including that fight date — preventing data leakage. Takes approximately 35–40 minutes for ~1,167 fighters.

**Input:** `data/processed/ufc_master_clean.parquet`
**Output:** `data/processed/fighter_history.json`, `data/processed/fighter_historical_stats.parquet`

```powershell
python scripts/scrape_historical_stats.py
```

---

### 7. `build_features.py`
Engineers all model features from the clean fight data, fighter attributes, and time-gated historical stats. All rolling stats are computed strictly from data before each fight date to prevent data leakage. Produces mirror rows (each fight from both fighters' perspectives) to remove position bias. Key features include:

- Rolling win rate (all-time and last 5 fights, from dataset)
- Win/loss streak, experience, days since last fight
- Strength of schedule (average opponent win rate)
- Sportsbook implied probability (vig-removed)
- Fighter age at fight date
- Physical differentials: reach, height, age
- Time-gated career record (wins, losses, win rate) from ufcstats fight history
- Time-gated SLpM, strike accuracy, takedown accuracy differentials

**Input:** `data/processed/ufc_master_clean.parquet`, `data/processed/fighter_attributes.json`, `data/processed/fighter_historical_stats.parquet`
**Output:** `data/processed/ufc_features.parquet`

```powershell
python scripts/build_features.py
```

---

### 8. `train_model_weighted.py`
Trains and evaluates the prediction model. Uses a time-based train/test split (train on fights before 2025, test on 2025 onward). Applies exponential recency weighting (half-life 365 days) so recent fights count more than older ones. Compares logistic regression baseline vs XGBoost. Evaluates using Brier score, log loss, and ROI simulation at multiple edge thresholds.

**Input:** `data/processed/ufc_features.parquet`
**Output:** `data/processed/ufc_model.pkl`, `data/processed/test_predictions.csv`

```powershell
python scripts/train_model_weighted.py
```

---

### 9. `evaluate_roi.py`
Loads the saved model and runs a detailed ROI simulation on the test set, broken out by all fighters, underdogs only, and favorites only. Uses capped fractional Kelly staking (25% Kelly, max 10% of bankroll per bet).

**Input:** `data/processed/ufc_features.parquet`, `data/processed/ufc_model.pkl`
**Output:** `data/processed/test_predictions.csv` (updated)

```powershell
python scripts/evaluate_roi.py
```

---

## Key Concepts

**Edge:** `model_probability - sportsbook_implied_probability`. Only bet when edge exceeds a threshold (3–10%).

**Implied probability from moneyline:**
- Positive line (underdog): `100 / (line + 100)`
- Negative line (favorite): `|line| / (|line| + 100)`
- Both normalized to remove the vig so they sum to 1.

**Recency weighting:** Fights from 2020–2021 are lower quality signal as fighters' styles and records evolve. Exponential decay with 365-day half-life downweights older fights.

**Brier score:** Lower is better. Measures calibration of predicted probabilities. Baseline (sportsbook implied prob only) is ~0.198.

**Calibration:** When the model predicts 70%, fighters win ~70% of the time. Confirmed across all probability buckets on 648 test fights.

**Kelly criterion:** Stake = `(p * (odds + 1) - 1) / odds`. Use 25% of full Kelly, capped at 10% of bankroll per bet to reduce variance.

**Data leakage prevention:** All historical stats (career record, SLpM, strike accuracy, TD accuracy) are computed from fight-by-fight history strictly before each fight date. Static career stats from ufcstats were confirmed to cause leakage and were replaced with time-gated equivalents.

---

## Data Sources

- **Fight results & odds:** 434 CSV files (one per event, 2020–2026), 2,876 fights total
- **Fighter attributes & stats:** [ufcstats.com](http://ufcstats.com), 1,168 fighters scraped

---

## Current Model Performance

| Model | Brier Score | Log Loss |
|---|---|---|
| Baseline (implied prob only) | 0.1979 | 0.5796 |
| Logistic Regression (recency weighted) | 0.1828 | 0.5488 |
| XGBoost (recency weighted) | 0.1796 | 0.5411 |

**Test set:** 648 fights, January 2025 – April 2026

**Calibration (XGBoost on test set):**

| Model Probability | Actual Win Rate | Count |
|---|---|---|
| 0–40% | 23% | 270 |
| 40–50% | 51% | 51 |
| 50–60% | 59% | 46 |
| 60–70% | 64% | 56 |
| 70–80% | 76% | 58 |
| 80–90% | 81% | 89 |
| 90–100% | 88% | 78 |

**Top features:** `diff_h_career_wr`, `implied_prob_f1`, `diff_win_rate_all`, `diff_h_str_acc`

---

## Next Steps

- Phase 6: Edge detection and backtesting
- Phase 7: Live prediction pipeline for upcoming cards
