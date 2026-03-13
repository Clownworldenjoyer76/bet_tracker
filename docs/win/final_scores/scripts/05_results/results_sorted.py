#!/usr/bin/env python3
# docs/win/final_scores/scripts/05_results/results_sorted.py

from pathlib import Path
from datetime import datetime
import pandas as pd


# =========================
# PATHS
# =========================

INPUTS = {
    "NBA": Path("docs/win/final_scores/results/nba/graded/NBA_final.csv"),
    "NCAAB": Path("docs/win/final_scores/results/ncaab/graded/NCAAB_final.csv"),
    "NHL": Path("docs/win/final_scores/results/nhl/graded/NHL_final.csv"),
    "SOCCER": Path("docs/win/final_scores/results/soccer/graded/SOCCER_final.csv"),
}

OUTPUTS = {
    "NBA": Path("docs/win/final_scores/results/nba/graded/NBA_final_sorted.csv"),
    "NCAAB": Path("docs/win/final_scores/results/ncaab/graded/ncaab_final_sorted.csv"),
    "NHL": Path("docs/win/final_scores/results/nhl/graded/nhl_final_sorted.csv"),
    "SOCCER": Path("docs/win/final_scores/results/soccer/graded/soccer_final_sorted.csv"),
}

MARKET_TALLY_INPUTS = {
    "NBA": Path("docs/win/final_scores/results/nba/graded/NBA_final_sorted.csv"),
    "NCAAB": Path("docs/win/final_scores/results/ncaab/graded/ncaab_final_sorted.csv"),
    "NHL": Path("docs/win/final_scores/results/nhl/graded/nhl_final_sorted.csv"),
    "SOCCER": Path("docs/win/final_scores/results/soccer/graded/soccer_final_sorted.csv"),
}

MARKET_TALLY_OUTPUTS = {
    "NBA": Path("docs/win/final_scores/results/market_tally_NBA.csv"),
    "NCAAB": Path("docs/win/final_scores/results/market_tally_NCAAB.csv"),
    "NHL": Path("docs/win/final_scores/results/market_tally_NHL.csv"),
    "SOCCER": Path("docs/win/final_scores/results/market_tally_SOCCER.csv"),
}

DEEP_DIR = Path("docs/win/final_scores/deep_market_breakdowns")

DEEP_OUTPUTS = {
    "NBA": {
        "band": DEEP_DIR / "NBA_band_by_band_summary.csv",
        "edge": DEEP_DIR / "NBA_edge_by_edge_summary.csv",
    },
    "NCAAB": {
        "band": DEEP_DIR / "NCAAB_band_by_band_summary.csv",
        "edge": DEEP_DIR / "NCAAB_edge_by_edge_summary.csv",
    },
    "NHL": {
        "band": DEEP_DIR / "NHL_band_by_band_summary.csv",
        "edge": DEEP_DIR / "NHL_edge_by_edge_summary.csv",
    },
    "SOCCER": {
        "band": DEEP_DIR / "SOCCER_band_by_band_summary.csv",
        "edge": DEEP_DIR / "SOCCER_edge_by_edge_summary.csv",
    },
}

ERROR_LOG = Path("docs/win/final_scores/errors/results_sorted_errors.txt")


# =========================
# HELPERS
# =========================

def log(msg: str) -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def safe_read(path: Path) -> pd.DataFrame:
    try:
        if not path.exists():
            log(f"Missing input: {path}")
            return pd.DataFrame()

        df = pd.read_csv(path)

        if df is None or df.empty:
            return pd.DataFrame()

        return df

    except Exception as e:
        log(f"ERROR reading {path}: {e}")
        return pd.DataFrame()


def normalize_result(df: pd.DataFrame) -> pd.DataFrame:
    if "bet_result" in df.columns:
        df["bet_result"] = df["bet_result"].astype(str).str.strip().str.title()
    return df


def summarize_wl(df: pd.DataFrame):
    wins = int((df["bet_result"] == "Win").sum())
    losses = int((df["bet_result"] == "Loss").sum())
    pushes = int((df["bet_result"] == "Push").sum())

    total = wins + losses + pushes
    denom = wins + losses
    win_pct = float(wins / denom) if denom > 0 else 0.0

    return wins, losses, pushes, total, win_pct


def first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        real = lower_map.get(candidate.lower())
        if real is not None:
            return real
    return None


def get_edge_column(df: pd.DataFrame) -> str | None:
    candidates = [
        "edge",
        "edge_pct",
        "edge_percent",
        "model_edge",
        "proj_edge",
        "edge_value",
        "ev_edge",
    ]
    return first_existing_column(df, candidates)


def get_edge_band_column(df: pd.DataFrame) -> str | None:
    candidates = [
        "edge_band",
        "edge_bucket",
        "band",
        "edge_range",
        "edge_group",
    ]
    return first_existing_column(df, candidates)


def build_edge_band_from_numeric(df: pd.DataFrame, edge_col: str) -> pd.Series:
    edge_num = pd.to_numeric(df[edge_col], errors="coerce")

    bins = [
        float("-inf"),
        0.5,
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        4.0,
        5.0,
        7.5,
        10.0,
        float("inf"),
    ]

    labels = [
        "<=0.5",
        "0.5_to_1.0",
        "1.0_to_1.5",
        "1.5_to_2.0",
        "2.0_to_2.5",
        "2.5_to_3.0",
        "3.0_to_4.0",
        "4.0_to_5.0",
        "5.0_to_7.5",
        "7.5_to_10.0",
        "10.0_plus",
    ]

    return pd.cut(edge_num, bins=bins, labels=labels, include_lowest=True, right=True).astype("string")


def prepare_deep_columns(df: pd.DataFrame, market_name: str) -> pd.DataFrame:
    df = df.copy()
    df = normalize_result(df)

    edge_col = get_edge_column(df)
    band_col = get_edge_band_column(df)

    if edge_col is not None:
        df["_edge_numeric"] = pd.to_numeric(df[edge_col], errors="coerce")
        df["_edge_value"] = df["_edge_numeric"].round(4)
    else:
        df["_edge_numeric"] = pd.NA
        df["_edge_value"] = pd.NA

    if band_col is not None:
        df["_edge_band"] = df[band_col].astype(str).str.strip()
    elif edge_col is not None:
        df["_edge_band"] = build_edge_band_from_numeric(df, edge_col)
    else:
        df["_edge_band"] = pd.NA

    if "market_type" not in df.columns:
        df["market_type"] = "unknown"

    if market_name == "SOCCER":
        if "league" in df.columns:
            df["_deep_extra"] = df["league"].astype(str).str.strip()
            df["_deep_extra_name"] = "league"
        else:
            df["_deep_extra"] = pd.NA
            df["_deep_extra_name"] = pd.NA
    else:
        df["_deep_extra"] = pd.NA
        df["_deep_extra_name"] = pd.NA

    return df


# =========================
# SUMMARY BUILDERS
# =========================

def generic_summary(df: pd.DataFrame, market_name: str):
    rows = []

    for m in sorted(df["market_type"].dropna().astype(str).unique()):
        sub = df[df["market_type"].astype(str) == m]

        wins, losses, pushes, total, win_pct = summarize_wl(sub)

        rows.append({
            "market": market_name,
            "market_type": m,
            "Win": wins,
            "Loss": losses,
            "Push": pushes,
            "Total": total,
            "Win_Pct": round(win_pct, 4)
        })

    return pd.DataFrame(rows)


def soccer_summary(df: pd.DataFrame):
    rows = []

    for m in ["result", "total"]:
        sub = df[df["market_type"] == m]

        wins, losses, pushes, total, win_pct = summarize_wl(sub)

        rows.append({
            "market": "SOCCER",
            "market_type": m,
            "Win": wins,
            "Loss": losses,
            "Push": pushes,
            "Total": total,
            "Win_Pct": round(win_pct, 4)
        })

    return pd.DataFrame(rows)


# =========================
# DEEP ANALYTICS
# =========================

def build_group_summary(
    df: pd.DataFrame,
    market_name: str,
    grouping_cols: list[str],
    value_name_map: dict[str, str] | None = None
) -> pd.DataFrame:
    rows = []

    work = df.copy()

    for col in grouping_cols:
        if col not in work.columns:
            return pd.DataFrame()

    work = work.dropna(subset=grouping_cols, how="any")

    if work.empty:
        return pd.DataFrame()

    grouped = work.groupby(grouping_cols, dropna=False, sort=True)

    for keys, sub in grouped:
        if not isinstance(keys, tuple):
            keys = (keys,)

        wins, losses, pushes, total, win_pct = summarize_wl(sub)

        row = {
            "market": market_name,
            "Win": wins,
            "Loss": losses,
            "Push": pushes,
            "Total": total,
            "Win_Pct": round(win_pct, 4),
        }

        for idx, col in enumerate(grouping_cols):
            out_col = value_name_map[col] if value_name_map and col in value_name_map else col
            row[out_col] = keys[idx]

        rows.append(row)

    out = pd.DataFrame(rows)

    preferred_order = (
        ["market"]
        + [value_name_map.get(c, c) if value_name_map else c for c in grouping_cols]
        + ["Win", "Loss", "Push", "Total", "Win_Pct"]
    )

    existing_cols = [c for c in preferred_order if c in out.columns]
    remaining_cols = [c for c in out.columns if c not in existing_cols]

    return out[existing_cols + remaining_cols]


def create_band_by_band_summary(df: pd.DataFrame, market_name: str) -> pd.DataFrame:
    work = prepare_deep_columns(df, market_name)

    group_cols = ["market_type", "_edge_band"]
    name_map = {"_edge_band": "edge_band"}

    if market_name == "SOCCER" and "_deep_extra" in work.columns and work["_deep_extra"].notna().any():
        group_cols = ["market_type", "_deep_extra", "_edge_band"]
        name_map["_deep_extra"] = "league"

    out = build_group_summary(work, market_name, group_cols, name_map)

    if out.empty:
        log(f"{market_name}: skipped band-by-band summary (no usable edge band data)")
        return out

    return out.sort_values(by=[c for c in out.columns if c in ["market_type", "league", "edge_band"]]).reset_index(drop=True)


def create_edge_by_edge_summary(df: pd.DataFrame, market_name: str) -> pd.DataFrame:
    work = prepare_deep_columns(df, market_name)

    if "_edge_value" not in work.columns or work["_edge_value"].isna().all():
        log(f"{market_name}: skipped edge-by-edge summary (no usable edge column found)")
        return pd.DataFrame()

    group_cols = ["market_type", "_edge_value"]
    name_map = {"_edge_value": "edge"}

    if market_name == "SOCCER" and "_deep_extra" in work.columns and work["_deep_extra"].notna().any():
        group_cols = ["market_type", "_deep_extra", "_edge_value"]
        name_map["_deep_extra"] = "league"

    out = build_group_summary(work, market_name, group_cols, name_map)

    if out.empty:
        log(f"{market_name}: skipped edge-by-edge summary (grouped output empty)")
        return out

    sort_cols = [c for c in ["market_type", "league", "edge"] if c in out.columns]
    return out.sort_values(by=sort_cols).reset_index(drop=True)


def write_deep_outputs(df: pd.DataFrame, market_name: str) -> None:
    DEEP_DIR.mkdir(parents=True, exist_ok=True)

    band_df = create_band_by_band_summary(df, market_name)
    edge_df = create_edge_by_edge_summary(df, market_name)

    if not band_df.empty:
        band_path = DEEP_OUTPUTS[market_name]["band"]
        band_df.to_csv(band_path, index=False)
        log(f"{market_name}: wrote band-by-band summary {band_path}")

    if not edge_df.empty:
        edge_path = DEEP_OUTPUTS[market_name]["edge"]
        edge_df.to_csv(edge_path, index=False)
        log(f"{market_name}: wrote edge-by-edge summary {edge_path}")


# =========================
# BUILD SORTED OUTPUT
# =========================

def build_sorted_output(df: pd.DataFrame, market_name: str):
    df = normalize_result(df)

    if market_name == "SOCCER":
        summary = soccer_summary(df)
    else:
        summary = generic_summary(df, market_name)

    return summary


# =========================
# MARKET TALLY
# =========================

def create_market_tally_file(market_name: str, in_path: Path, out_path: Path):
    df = safe_read(in_path)

    if df.empty:
        log(f"{market_name}: Input empty {in_path}")
        return

    df = normalize_result(df)

    rows = []

    if market_name in ["NBA", "NCAAB"]:
        markets = ["moneyline", "spread", "total"]
    elif market_name == "NHL":
        markets = ["moneyline", "puck_line", "total"]
    else:
        markets = ["result", "total"]

    for m in markets:
        sub = df[df["market_type"] == m]

        wins, losses, pushes, total, win_pct = summarize_wl(sub)

        rows.append({
            "market": market_name,
            "market_type": m,
            "Win": wins,
            "Loss": losses,
            "Push": pushes,
            "Total": total,
            "Win_Pct": round(win_pct, 4)
        })

    out = pd.DataFrame(rows)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)

    log(f"{market_name}: wrote tally {out_path}")


def create_all_market_tally_files():
    for m, path in MARKET_TALLY_INPUTS.items():
        create_market_tally_file(
            m,
            path,
            MARKET_TALLY_OUTPUTS[m]
        )


# =========================
# MAIN
# =========================

def main():
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)

    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("=== results_sorted.py log ===\n")

    for market_name, in_path in INPUTS.items():
        df = safe_read(in_path)

        if df.empty:
            log(f"{market_name}: input empty")
            continue

        # Existing output stays unchanged
        out_df = build_sorted_output(df, market_name)

        out_path = OUTPUTS[market_name]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(out_path, index=False)

        log(f"{market_name}: wrote sorted file {out_path}")

        # Added deep analytics
        write_deep_outputs(df, market_name)

    create_all_market_tally_files()

    print("results_sorted.py complete.")


if __name__ == "__main__":
    main()
