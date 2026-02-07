import pandas as pd
import glob
from pathlib import Path
from scipy.stats import poisson

# =========================
# CONSTANTS
# =========================

CLEANED_DIR = Path("docs/win/dump/csvs/cleaned")
NORMALIZED_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/nhl/totals")
EDGE = 0.05  # 5% edge

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def to_american(decimal_odds):
    if pd.isna(decimal_odds) or decimal_odds <= 1:
        return ""
    if decimal_odds >= 2.0:
        return f"+{int((decimal_odds - 1) * 100)}"
    return f"-{int(100 / (decimal_odds - 1))}"

# =========================
# CORE
# =========================

def process_totals():
    projection_files = glob.glob(str(CLEANED_DIR / "nhl_*.csv"))

    for proj_path in projection_files:
        date_suffix = "_".join(Path(proj_path).stem.split("_")[1:])
        dk_path = NORMALIZED_DIR / f"dk_nhl_totals_{date_suffix}.csv"

        if not dk_path.exists():
            continue

        df_proj = pd.read_csv(proj_path)
        df_dk = pd.read_csv(dk_path)

        # ✅ Merge on game_id (single source of truth)
        merged = pd.merge(
            df_proj,
            df_dk,
            on="game_id",
            how="inner",
            suffixes=("", "_dk")
        )

        if merged.empty:
            continue

        # =========================
        # POISSON CALCULATIONS
        # =========================

        merged["under_probability"] = merged.apply(
            lambda x: poisson.cdf(x["total"] - 0.5, x["game_projected_goals"]),
            axis=1
        )

        merged["over_probability"] = 1 - merged["under_probability"]

        merged["over_acceptable_decimal_odds"] = (1 / merged["over_probability"]) * (1 + EDGE)
        merged["under_acceptable_decimal_odds"] = (1 / merged["under_probability"]) * (1 + EDGE)

        merged["over_acceptable_american_odds"] = merged["over_acceptable_decimal_odds"].apply(to_american)
        merged["under_acceptable_american_odds"] = merged["under_acceptable_decimal_odds"].apply(to_american)

        # =========================
        # OUTPUT
        # =========================

        cols = [
            "game_id", "date", "time", "away_team", "home_team",
            "away_team_projected_goals", "home_team_projected_goals",
            "over_handle_pct", "over_bets_pct", "under_handle_pct", "under_bets_pct",
            "game_projected_goals", "over_odds", "under_odds", "total",
            "over_probability", "under_probability",
            "over_acceptable_decimal_odds", "over_acceptable_american_odds",
            "under_acceptable_decimal_odds", "under_acceptable_american_odds",
        ]

        output_df = merged[cols].copy()
        output_df.insert(1, "league", "nhl_ou")

        out_path = OUTPUT_DIR / f"ou_nhl_{date_suffix}.csv"
        output_df.to_csv(out_path, index=False)
        print(f"Saved: {out_path}")

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    process_totals()
