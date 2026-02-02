import pandas as pd
from pathlib import Path
import re

INPUT_DIR = Path("bets/historic/juice_files")
OUTPUT_DIR = INPUT_DIR / "tables"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --------- helpers ----------

def american_to_prob(amer: float) -> float:
    """Implied probability from American odds."""
    if amer == 0:
        raise ValueError("American odds cannot be 0")
    if amer < 0:
        return (-amer) / ((-amer) + 100.0)
    return 100.0 / (amer + 100.0)

def parse_band_range(band: str):
    """
    Parses strings like:
      '-119 to -110', '0 to 4.5', '205 to 214.5', '245 to 1000'
    Returns (low, high) floats or (None, None) if not parseable.
    """
    s = str(band).strip()
    m = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)\s*to\s*([+-]?\d+(?:\.\d+)?)\s*$", s, re.IGNORECASE)
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))

def safe_div(a, b):
    return a / b if b != 0 else None

# --------- juice builders (schema-specific, based on what exists) ----------

def juice_from_prob_dec(df: pd.DataFrame) -> pd.DataFrame:
    # expects: prob_dec, wins, bets (like ncaab_ml.csv)
    if not {"prob_dec", "wins", "bets"}.issubset(df.columns):
        raise ValueError("Expected columns prob_dec,wins,bets")

    # Bin already exists implicitly by exact prob_dec rows; build bins by 0.05
    BIN_SIZE = 0.05
    df = df.copy()
    df["prob_bin_min"] = (df["prob_dec"] // BIN_SIZE) * BIN_SIZE
    df["prob_bin_max"] = df["prob_bin_min"] + BIN_SIZE

    g = df.groupby(["prob_bin_min", "prob_bin_max"], as_index=False).agg(
        bets=("bets", "sum"),
        wins=("wins", "sum"),
        avg_prob=("prob_dec", "mean"),
    )
    g["actual_win_pct"] = g["wins"] / g["bets"]
    g["extra_juice"] = (g["avg_prob"] / g["actual_win_pct"]) - 1
    return g[["prob_bin_min", "prob_bin_max", "extra_juice"]].sort_values(["prob_bin_min"])

def juice_from_american_band(df: pd.DataFrame, keep_cols) -> pd.DataFrame:
    """
    NBA/NHL ML files:
      band = american odds range; wins/bets exist.
    We compute model 'p' as implied prob from MIDPOINT American odds of the band,
    then extra_juice = p/q - 1 where q = wins/bets.
    """
    needed = {"band", "wins", "bets"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Expected columns {needed}")

    out = df.copy()
    lows, highs = [], []
    p_models = []

    for b in out["band"].astype(str).tolist():
        lo, hi = parse_band_range(b)
        if lo is None:
            raise ValueError(f"Unparseable band: {b}")
        lows.append(lo); highs.append(hi)
        mid = (lo + hi) / 2.0
        p_models.append(american_to_prob(mid))

    out["band_min"] = lows
    out["band_max"] = highs
    out["p_model"] = p_models

    out["q_actual"] = out["wins"] / out["bets"]
    out["extra_juice"] = (out["p_model"] / out["q_actual"]) - 1

    cols = ["band", "band_min", "band_max"] + keep_cols + ["extra_juice"]
    return out[cols].sort_values(keep_cols + ["band_min"] if keep_cols else ["band_min"])

def juice_from_spread_band(df: pd.DataFrame, keep_cols) -> pd.DataFrame:
    """
    NBA/NHL spreads:
      band = spread magnitude range; wins/bets/decisions exist
    There is no model probability in file, so p_model is defined as 0.5 on decisions.
    q_actual = wins/decisions (pushes excluded).
    extra_juice = 0.5/q - 1
    """
    needed = {"band", "wins", "decisions"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Expected columns {needed}")

    out = df.copy()
    lows, highs = [], []
    for b in out["band"].astype(str).tolist():
        lo, hi = parse_band_range(b)
        if lo is None:
            raise ValueError(f"Unparseable band: {b}")
        lows.append(lo); highs.append(hi)

    out["band_min"] = lows
    out["band_max"] = highs

    out["q_actual"] = out["wins"] / out["decisions"]
    out["p_model"] = 0.5
    out["extra_juice"] = (out["p_model"] / out["q_actual"]) - 1

    cols = ["band", "band_min", "band_max"] + keep_cols + ["extra_juice"]
    return out[cols].sort_values(keep_cols + ["band_min"] if keep_cols else ["band_min"])

def juice_from_totals_band(df: pd.DataFrame, keep_cols) -> pd.DataFrame:
    """
    NBA/NHL totals:
      band = total range, side exists, wins/bets exist.
    No model probability in file, so p_model is defined as 0.5.
    q_actual = wins/bets for that side in that band.
    extra_juice = 0.5/q - 1
    """
    needed = {"band", "wins", "bets"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Expected columns {needed}")

    out = df.copy()
    lows, highs = [], []
    for b in out["band"].astype(str).tolist():
        lo, hi = parse_band_range(b)
        if lo is None:
            raise ValueError(f"Unparseable band: {b}")
        lows.append(lo); highs.append(hi)

    out["band_min"] = lows
    out["band_max"] = highs

    out["q_actual"] = out["wins"] / out["bets"]
    out["p_model"] = 0.5
    out["extra_juice"] = (out["p_model"] / out["q_actual"]) - 1

    cols = ["band", "band_min", "band_max"] + keep_cols + ["extra_juice"]
    return out[cols].sort_values(keep_cols + ["band_min"] if keep_cols else ["band_min"])

def juice_from_ncaab_spreads(df: pd.DataFrame) -> pd.DataFrame:
    """
    ncaab_spreads.csv:
      spread, covers, no_covers, pushes
    p_model defined as 0.5
    q_actual = covers / (covers + no_covers)
    extra_juice = 0.5/q - 1
    """
    needed = {"spread", "covers", "no_covers"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Expected columns {needed}")

    out = df.copy()
    out["decisions"] = out["covers"] + out["no_covers"]
    out["q_actual"] = out["covers"] / out["decisions"]
    out["p_model"] = 0.5
    out["extra_juice"] = (out["p_model"] / out["q_actual"]) - 1

    return out[["spread", "extra_juice"]].sort_values("spread")

def juice_from_ncaab_ou(df: pd.DataFrame) -> pd.DataFrame:
    """
    ncaab_ou.csv:
      over_under, overs, unders, pushes
    Produces two-sided juice by line: 'over' and 'under'
    p_model defined as 0.5
    q_over  = overs/(overs+unders)
    q_under = unders/(overs+unders)
    extra_juice = 0.5/q - 1
    """
    needed = {"over_under", "overs", "unders"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Expected columns {needed}")

    out = df.copy()
    out["decisions"] = out["overs"] + out["unders"]

    rows = []
    for _, r in out.iterrows():
        line = r["over_under"]
        dec = r["decisions"]
        if dec == 0:
            continue
        q_over = r["overs"] / dec
        q_under = r["unders"] / dec

        rows.append({"over_under": line, "side": "over", "extra_juice": (0.5 / q_over) - 1})
        rows.append({"over_under": line, "side": "under", "extra_juice": (0.5 / q_under) - 1})

    res = pd.DataFrame(rows)
    # keep numeric ordering if possible
    try:
        res["line_num"] = pd.to_numeric(res["over_under"])
        res = res.sort_values(["line_num", "side"]).drop(columns=["line_num"])
    except Exception:
        res = res.sort_values(["over_under", "side"])
    return res

# --------- dispatcher based ONLY on observed filename + observed columns ----------

def generate_for_file(path: Path) -> pd.DataFrame:
    name = path.stem  # e.g., nba_ml
    parts = name.split("_")
    if len(parts) != 2:
        raise ValueError(f"Bad filename: {path.name} (expected league_market.csv)")

    league, market = parts
    df = pd.read_csv(path)

    if league == "ncaab" and market == "ml":
        return juice_from_prob_dec(df)

    if league == "ncaab" and market == "spreads":
        return juice_from_ncaab_spreads(df)

    # your NCAAB totals file is named ncaab_ou.csv (not ncaab_totals.csv)
    if league == "ncaab" and market in {"ou", "totals"}:
        return juice_from_ncaab_ou(df)

    # NBA/NHL ML
    if market == "ml":
        keep = [c for c in ["fav_ud", "venue"] if c in df.columns]
        return juice_from_american_band(df, keep_cols=keep)

    # NBA/NHL spreads
    if market == "spreads":
        keep = [c for c in ["fav_ud", "venue"] if c in df.columns]
        return juice_from_spread_band(df, keep_cols=keep)

    # NBA/NHL totals
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
