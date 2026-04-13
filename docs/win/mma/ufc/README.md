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

### 6. `build_features.py`
Engineers all model features from the clean fight data and fighter attributes. All rolling stats are computed strictly from data before each fight date to prevent data leakage. Produces mirror rows (each fight from both fighters' perspectives) to remove position bias. Key features include:

- Rolling win rate (all-time and last 5 fights)
- Win/loss streak, experience, days since last fight
- Strength of schedule (average opponent win rate)
- Sportsbook implied probability (vig-removed)
- Fighter age at fight date
- Physical differentials: reach, height, age
- Career record at time of fight
- SLpM, SApM, takedown accuracy/defense differentials

**Input:** `data/processed/ufc_master_clean.parquet`, `data/processed/fighter_attributes.json`
**Output:** `data/processed/ufc_features.parquet`

```powershell
python scripts/build_features.py
```

---

### 7. `train_model_weighted.py`
Trains and evaluates the prediction model. Uses a time-based train/test split (train on fights before 2025, test on 2025 onward). Applies exponential recency weighting (half-life 365 days) so recent fights count more than older ones. Compares logistic regression baseline vs XGBoost. Evaluates using Brier score, log loss, and ROI simulation at multiple edge thresholds using fractional Kelly sizing.

**Input:** `data/processed/ufc_features.parquet`
**Output:** `data/processed/ufc_model.pkl`, `data/processed/test_predictions.csv`

```powershell
python scripts/train_model_weighted.py
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

**Kelly criterion:** Stake = `(p * (odds + 1) - 1) / odds`. Use 25% of full Kelly to reduce variance.

---

## Data Sources

- **Fight results & odds:** 434 CSV files (one per event, 2020–2026)
- **Fighter attributes & stats:** [ufcstats.com](http://ufcstats.com)

---

## Current Model Performance (as of last run)

| Model | Brier Score | Log Loss |
|---|---|---|
| Baseline (implied prob only) | 0.1979 | 0.5796 |
| Logistic Regression (all features) | 0.2000 | 0.5845 |
| XGBoost (recency weighted) | 0.2128 | 0.6198 |

ROI simulation at 3% edge threshold: ~-13% (648 test fights, 2025–2026)

---

## Next Steps

- Rebuild `ufc_features.parquet` with new career record and strike/TD features
- Retrain model with expanded feature set
- Build live prediction pipeline for upcoming cards
