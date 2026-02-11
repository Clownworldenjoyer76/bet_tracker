import pandas as pd
from pathlib import Path
import re

INPUT_DIR = Path("bets/historic/juice_files")
OUTPUT_DIR = INPUT_DIR / "tables"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- helpers ----------------

def american_to_prob(amer: float) -> float:
    if amer == 0:
        raise ValueError("American odds cannot be 0")
    if amer < 0:
        return (-amer) / ((-amer) + 100.0)
    return 100.0 / (amer + 100.0)

def parse_band_range(band: str):
    s = str(band).strip()
    m = re.match(
        r"^\s*([+-]?\d+(?:\.\d+)?)\s*to\s*([+-]?\d+(?:\.\d+)?)\s*$",
        s,
        re.IGNORECASE,
    )
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))

def drop_unknown_bands(df: pd.DataFrame) -> pd.DataFrame:
    if "band" in df.columns:
        return df[df["band"].astype(str).str.lower() != "unknown"].copy()
    return df.copy()

# ---------------- builders ----------------

def juice_from_prob_dec(df: pd.DataFrame) -> pd.DataFrame:
    if not {"prob_dec", "wins", "bets"}.issubset(df.columns):
        raise ValueError("Expected columns prob_dec,wins,bets")

    BIN_SIZE = 0.05
    df = df.copy()
    df["prob_bin_min"] = (df["prob_dec"] // BIN_SIZE) * BIN_SIZE
    df["prob_bin_max"] = df["prob_bin_min"] + BIN_SIZE

    g = (
        df.groupby(["prob_bin_min", "prob_bin_max"], as_index=False)
          .agg(bets=("bets", "sum"),
               wins=("wins", "sum"),
               avg_prob=("prob_dec", "mean"))
    )
    g["actual_win_pct"] = g["wins"] / g["bets"]
    g = g[g["actual_win_pct"] > 0]

    g["extra_juice"] = (g["avg_prob"] / g["actual_win_pct"]) - 1
    return g[["prob_bin_min", "prob_bin_max", "extra_juice"]].sort_values("prob_bin_min")

def juice_from_american_band(df: pd.DataFrame, keep_cols):
    needed = {"band", "wins", "bets"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Expected columns {needed}")

    out = drop_unknown_bands(df)
    lows, highs, p_models = [], [], []

    for b in out["band"].astype(str).tolist():
        lo, hi = parse_band_range(b)
        if lo is None:
            continue
        lows.append(lo)
        highs.append(hi)
        mid = (lo + hi) / 2.0
        p_models.append(american_to_prob(mid))

    if not p_models:
        return pd.DataFrame(columns=["band", "band_min", "band_max"] + keep_cols + ["extra_juice"])

    out = out.iloc[:len(p_models)].copy()
    out["band_min"] = lows
    out["band_max"] = highs
    out["p_model"] = p_models

    out["q_actual"] = out["wins"] / out["bets"]
    out = out[out["q_actual"] > 0]

    out["extra_juice"] = (out["p_model"] / out["q_actual"]) - 1
    cols = ["band", "band_min", "band_max"] + keep_cols + ["extra_juice"]
    return out[cols].sort_values(keep_cols + ["band_min"] if keep_cols else ["band_min"])

def juice_from_spread_band(df: pd.DataFrame, keep_cols):
    needed = {"band", "wins", "decisions"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Expected columns {needed}")

    out = drop_unknown_bands(df)
    lows, highs = [], []

    for b in out["band"].astype(str).tolist():
        lo, hi = parse_band_range(b)
        if lo is None:
            continue
        lows.append(lo)
        highs.append(hi)

    if not lows:
        return pd.DataFrame(columns=["band", "band_min", "band_max"] + keep_cols + ["extra_juice"])

    out = out.iloc[:len(lows)].copy()
    out["band_min"] = lows
    out["band_max"] = highs

    out["q_actual"] = out["wins"] / out["decisions"]
    out = out[out["q_actual"] > 0]

    out["p_model"] = 0.5
    out["extra_juice"] = (out["p_model"] / out["q_actual"]) - 1
    cols = ["band", "band_min", "band_max"] + keep_cols + ["extra_juice"]
    return out[cols].sort_values(keep_cols + ["band_min"] if keep_cols else ["band_min"])

def juice_from_totals_band(df: pd.DataFrame, keep_cols):
    needed = {"band", "wins", "bets"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Expected columns {needed}")

    out = drop_unknown_bands(df)
    lows, highs = [], []

    for b in out["band"].astype(str).tolist():
        lo, hi = parse_band_range(b)
        if lo is None:
            continue
        lows.append(lo)
        highs.append(hi)

    if not lows:
        return pd.DataFrame(columns=["band", "band_min", "band_max"] + keep_cols + ["extra_juice"])

    out = out.iloc[:len(lows)].copy()
    out["band_min"] = lows
    out["band_max"] = highs

    out["q_actual"] = out["wins"] / out["bets"]
    out = out[out["q_actual"] > 0]

    out["p_model"] = 0.5
    out["extra_juice"] = (out["p_model"] / out["q_actual"]) - 1
    cols = ["band", "band_min", "band_max"] + keep_cols + ["extra_juice"]
    return out[cols].sort_values(keep_cols + ["band_min"] if keep_cols else ["band_min"])

def juice_from_ncaab_spreads(df: pd.DataFrame) -> pd.DataFrame:
    needed = {"spread", "covers", "no_covers"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Expected columns {needed}")

    out = df.copy()
    out["decisions"] = out["covers"] + out["no_covers"]
    out = out[out["decisions"] > 0]

    out["q_actual"] = out["covers"] / out["decisions"]
    out["p_model"] = 0.5
    out["extra_juice"] = (out["p_model"] / out["q_actual"]) - 1
    return out[["spread", "extra_juice"]].sort_values("spread")

def juice_from_ncaab_ou(df: pd.DataFrame) -> pd.DataFrame:
    needed = {"over_under", "overs", "unders"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Expected columns {needed}")

    out = df.copy()
    out["decisions"] = out["overs"] + out["unders"]
    out = out[out["decisions"] > 0]

    rows = []
    for _, r in out.iterrows():
        q_over = r["overs"] / r["decisions"]
        q_under = r["unders"] / r["decisions"]
        rows.append({"over_under": r["over_under"], "side": "over", "extra_juice": (0.5 / q_over) - 1})
        rows.append({"over_under": r["over_under"], "side": "under", "extra_juice": (0.5 / q_under) - 1})

    res = pd.DataFrame(rows)
    try:
        res["line_num"] = pd.to_numeric(res["over_under"])
        res = res.sort_values(["line_num", "side"]).drop(columns=["line_num"])
    except Exception:
        res = res.sort_values(["over_under", "side"])
    return res

# ---------------- dispatcher ----------------

def generate_for_file(path: Path) -> pd.DataFrame:
    name = path.stem
    parts = name.split("_")
    if len(parts) != 2:
        raise ValueError(f"Bad filename: {path.name}")

    league, market = parts
    df = pd.read_csv(path)

    if league == "ncaab" and market == "ml":
        return juice_from_prob_dec(df)
    if league == "ncaab" and market == "spreads":
        return juice_from_ncaab_spreads(df)
    if league == "ncaab" and market in {"ou", "totals"}:
        return juice_from_ncaab_ou(df)

    if market == "ml":
        keep = [c for c in ["fav_ud", "venue"] if c in df.columns]
        return juice_from_american_band(df, keep_cols=keep)
    if market == "spreads":
        keep = [c for c in ["fav_ud", "venue"] if c in df.columns]
        return juice_from_spread_band(df, keep_cols=keep)
    if market == "totals":
        keep = [c for c in ["side"] if c in df.columns]
        return juice_from_totals_band(df, keep_cols=keep)

    raise ValueError(f"Unhandled file: {path.name}")

def main():
    files = sorted(INPUT_DIR.glob("*.csv"))
    if not files:
        raise SystemExit(f"No CSVs found in {INPUT_DIR}")

    for f in files:
        table = generate_for_file(f)
        out_path = OUTPUT_DIR / f"{f.stem}_juice.csv"
        table.to_csv(out_path, index=False)
        print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
