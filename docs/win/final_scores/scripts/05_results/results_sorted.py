#!/usr/bin/env python3
# docs/win/final_scores/scripts/05_results/results_sorted.py

import os
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
}

OUTPUTS = {
    "NBA": Path("docs/win/final_scores/results/nba/graded/NBA_final_sorted.csv"),
    "NCAAB": Path("docs/win/final_scores/results/ncaab/graded/ncaab_final_sorted.csv"),
    "NHL": Path("docs/win/final_scores/results/nhl/graded/nhl_final_sorted.csv"),
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


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def normalize_result(df: pd.DataFrame) -> pd.DataFrame:
    if "bet_result" in df.columns:
        df["bet_result"] = df["bet_result"].astype(str).str.strip().str.title()
    return df


def add_market_col(df: pd.DataFrame, market_name: str) -> pd.DataFrame:
    if "market" not in df.columns:
        df["market"] = market_name
    else:
        df["market"] = df["market"].astype(str).replace("nan", "").str.strip()
        df.loc[df["market"] == "", "market"] = market_name
    return df


def edge_band_label(v: float) -> str:
    if pd.isna(v):
        return "NA"
    try:
        x = float(v)
    except Exception:
        return "NA"

    bands = [
        (0.00, 0.05),
        (0.05001, 0.10),
        (0.10001, 0.125),
        (0.12501, 0.15),
        (0.15001, 0.20),
        (0.20001, 0.30),
        (0.30001, 10.00),
    ]
    for lo, hi in bands:
        if lo <= x <= hi:
            return f"{lo:.5f}-{hi:.3f}"
    if x < 0:
        return "<0"
    return ">0.30001"


def summarize_wl(df: pd.DataFrame) -> tuple[int, int, int, int, float]:
    wins = int((df["bet_result"] == "Win").sum())
    losses = int((df["bet_result"] == "Loss").sum())
    pushes = int((df["bet_result"] == "Push").sum())
    total = wins + losses + pushes
    denom = wins + losses
    win_pct = float(wins / denom) if denom > 0 else 0.0
    return wins, losses, pushes, total, win_pct


def make_summary_table(df: pd.DataFrame, group_cols: list[str], label_cols: dict | None = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    tmp = df.copy()
    tmp = tmp[tmp["bet_result"].isin(["Win", "Loss", "Push"])].copy()
    if tmp.empty:
        return pd.DataFrame()

    grouped = tmp.groupby(group_cols, dropna=False)

    rows = []
    for keys, g in grouped:
        if not isinstance(keys, tuple):
            keys = (keys,)
        wins, losses, pushes, total, win_pct = summarize_wl(g)
        row = {col: keys[i] for i, col in enumerate(group_cols)}
        row.update({
            "Win": wins,
            "Loss": losses,
            "Push": pushes,
            "Total": total,
            "Win_Pct": round(win_pct, 4)
        })
        rows.append(row)

    out = pd.DataFrame(rows)
    if label_cols:
        out = out.rename(columns=label_cols)

    sort_cols = [c for c in group_cols if c in out.columns]
    if "Win_Pct" in out.columns:
        sort_cols2 = sort_cols + ["Win_Pct", "Total"]
        out = out.sort_values(
            sort_cols2,
            ascending=[True] * len(sort_cols) + [False, False],
            kind="mergesort"
        )
    else:
        out = out.sort_values(sort_cols, ascending=True, kind="mergesort")
    return out


def moneyline_line_band(v: float) -> str:
    if pd.isna(v):
        return "NA"
    try:
        x = float(v)
    except Exception:
        return "NA"

    if x < 0:
        hi = int((abs(x) // 10) * 10)
        lo = hi + 9
        return f"-{lo} to -{hi}"
    else:
        base = int((x // 25) * 25)
        top = base + 24
        return f"{base} to {top}"


def spread_line_band(v: float) -> str:
    if pd.isna(v):
        return "NA"
    try:
        x = float(v)
    except Exception:
        return "NA"

    import math
    band_start = math.floor(x)
    band_end = band_start + 0.9
    return f"{band_start:.1f} to {band_end:.1f}"


def total_line_band(v: float) -> str:
    if pd.isna(v):
        return "NA"
    try:
        x = float(v)
    except Exception:
        return "NA"
    base = int((x // 10) * 10)
    top = base + 9
    return f"{base}-{top}"


def prepare_edges(df: pd.DataFrame) -> pd.DataFrame:
    edge_cols = [
        "home_ml_edge_decimal",
        "away_ml_edge_decimal",
        "home_spread_edge_decimal",
        "away_spread_edge_decimal",
        "over_edge_decimal",
        "under_edge_decimal",
        "line",
    ]
    for c in edge_cols:
        if c in df.columns:
            df[c] = to_num(df[c])

    if "market_type" in df.columns:
        df["market_type"] = df["market_type"].astype(str).str.strip().str.lower()

    if "bet_side" in df.columns:
        df["bet_side"] = df["bet_side"].astype(str).str.strip().str.lower()

    return df


def nba_ncaab_summaries(df: pd.DataFrame, market_name: str) -> list[pd.DataFrame]:
    out = []
    df = df.copy()

    ml = df[df["market_type"] == "moneyline"].copy()
    if not ml.empty:
        def pick_edge(row):
            if row.get("bet_side") == "home":
                return row.get("home_ml_edge_decimal")
            if row.get("bet_side") == "away":
                return row.get("away_ml_edge_decimal")
            return pd.NA

        ml["edge_selected"] = ml.apply(pick_edge, axis=1)
        ml["edge_band"] = ml["edge_selected"].apply(edge_band_label)
        ml["line_band"] = ml["line"].apply(moneyline_line_band)

        t1 = make_summary_table(ml, ["market_type", "bet_side"])
        if not t1.empty:
            t1.insert(0, "section", f"{market_name} moneyline - bet_side overall")
            out.append(t1)

        t2 = make_summary_table(ml, ["market_type", "bet_side", "edge_band"])
        if not t2.empty:
            t2.insert(0, "section", f"{market_name} moneyline - edge bands (by side)")
            out.append(t2)

        t3 = make_summary_table(ml, ["market_type", "bet_side", "line_band"])
        if not t3.empty:
            t3.insert(0, "section", f"{market_name} moneyline - line bands (by side)")
            out.append(t3)

    sp = df[df["market_type"] == "spread"].copy()
    if not sp.empty:
        def pick_edge(row):
            if row.get("bet_side") == "home":
                return row.get("home_spread_edge_decimal")
            if row.get("bet_side") == "away":
                return row.get("away_spread_edge_decimal")
            return pd.NA

        sp["edge_selected"] = sp.apply(pick_edge, axis=1)
        sp["edge_band"] = sp["edge_selected"].apply(edge_band_label)
        sp["line_band"] = sp["line"].apply(spread_line_band)

        t1 = make_summary_table(sp, ["market_type", "bet_side"])
        if not t1.empty:
            t1.insert(0, "section", f"{market_name} spread - bet_side overall")
            out.append(t1)

        t2 = make_summary_table(sp, ["market_type", "bet_side", "edge_band"])
        if not t2.empty:
            t2.insert(0, "section", f"{market_name} spread - edge bands (by side)")
            out.append(t2)

        t3 = make_summary_table(sp, ["market_type", "bet_side", "line_band"])
        if not t3.empty:
            t3.insert(0, "section", f"{market_name} spread - line bands (by side)")
            out.append(t3)

    tot = df[df["market_type"] == "total"].copy()
    if not tot.empty:
        def pick_edge(row):
            if row.get("bet_side") == "over":
                return row.get("over_edge_decimal")
            if row.get("bet_side") == "under":
                return row.get("under_edge_decimal")
            return pd.NA

        tot["edge_selected"] = tot.apply(pick_edge, axis=1)
        tot["edge_band"] = tot["edge_selected"].apply(edge_band_label)
        tot["total_band"] = tot["line"].apply(total_line_band)

        t1 = make_summary_table(tot, ["market_type", "bet_side"])
        if not t1.empty:
            t1.insert(0, "section", f"{market_name} total - bet_side overall")
            out.append(t1)

        t2 = make_summary_table(tot, ["market_type", "bet_side", "edge_band"])
        if not t2.empty:
            t2.insert(0, "section", f"{market_name} total - edge bands (by side)")
            out.append(t2)

        t3 = make_summary_table(tot, ["market_type", "total_band", "bet_side"])
        if not t3.empty:
            t3.insert(0, "section", f"{market_name} total - total bands (over/under by band)")
            out.append(t3)

    return out


def nhl_summaries(df: pd.DataFrame, market_name: str) -> list[pd.DataFrame]:
    out = []
    df = df.copy()

    ml = df[df["market_type"] == "moneyline"].copy()
    if not ml.empty:
        t1 = make_summary_table(ml, ["market_type", "bet_side"])
        if not t1.empty:
            t1.insert(0, "section", f"{market_name} moneyline - bet_side overall")
            out.append(t1)

    pl = df[df["market_type"] == "puck_line"].copy()
    if not pl.empty:
        pl["line_side"] = pl.apply(
            lambda r: f"{r.get('line')} {str(r.get('bet_side', '')).lower().strip()}",
            axis=1
        )
        t1 = make_summary_table(pl, ["market_type", "line_side"])
        if not t1.empty:
            t1.insert(0, "section", f"{market_name} puck_line - line+side bands")
            out.append(t1)

    tot = df[df["market_type"] == "total"].copy()
    if not tot.empty:
        tot["line_side"] = tot.apply(
            lambda r: f"{r.get('line')} {str(r.get('bet_side', '')).lower().strip()}",
            axis=1
        )
        t1 = make_summary_table(tot, ["market_type", "line_side"])
        if not t1.empty:
            t1.insert(0, "section", f"{market_name} total - line+side bands")
            out.append(t1)

    return out


def build_sorted_output(df: pd.DataFrame, market_name: str) -> pd.DataFrame:
    df = normalize_result(df)
    df = prepare_edges(df)
    df = add_market_col(df, market_name)

    if market_name in ["NBA", "NCAAB"]:
        sections = nba_ncaab_summaries(df, market_name)
    else:
        sections = nhl_summaries(df, market_name)

    if not sections:
        return pd.DataFrame([{
            "section": f"{market_name}: no usable rows found",
            "Win": 0,
            "Loss": 0,
            "Push": 0,
            "Total": 0,
            "Win_Pct": 0.0
        }])

    all_cols = set()
    for s in sections:
        all_cols.update(s.columns.tolist())

    preferred = [
        "section",
        "market_type",
        "bet_side",
        "edge_band",
        "line_band",
        "total_band",
        "line_side",
        "Win",
        "Loss",
        "Push",
        "Total",
        "Win_Pct",
    ]
    cols = [c for c in preferred if c in all_cols] + [c for c in sorted(all_cols) if c not in preferred]

    normalized_sections = []
    for s in sections:
        tmp = s.copy()
        for c in cols:
            if c not in tmp.columns:
                tmp[c] = ""
        tmp = tmp[cols]
        normalized_sections.append(tmp)

    out = pd.concat(normalized_sections, ignore_index=True)
    return out


# =========================
# MAIN
# =========================

def main() -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("=== results_sorted.py log ===\n")

    for market_name, in_path in INPUTS.items():
        out_path = OUTPUTS[market_name]
        out_path.parent.mkdir(parents=True, exist_ok=True)

        df = safe_read(in_path)
        if df.empty:
            log(f"{market_name}: input empty or missing: {in_path}")
            pd.DataFrame([{
                "section": f"{market_name}: input empty or missing",
                "Win": 0,
                "Loss": 0,
                "Push": 0,
                "Total": 0,
                "Win_Pct": 0.0
            }]).to_csv(out_path, index=False)
            continue

        df = normalize_result(df)
        df = prepare_edges(df)
        df = add_market_col(df, market_name)

        # =========================
        # TRUE MARKET TALLY
        # =========================
        print(f"\n===== {market_name} TRUE MARKET TALLY =====")

        market_counts = df["market_type"].fillna("NA").value_counts(dropna=False).sort_index()
        print("\nBets by Market:")
        print(market_counts.to_string())

        market_side_counts = (
            df.groupby(["market_type", "bet_side"], dropna=False)
              .size()
              .sort_index()
        )
        print("\nBets by Market + Side:")
        print(market_side_counts.to_string())

        market_result_counts = (
            df.groupby(["market_type", "bet_result"], dropna=False)
              .size()
              .sort_index()
        )
        print("\nResults by Market:")
        print(market_result_counts.to_string())

        detailed_market_tally = (
            df.groupby(["market_type", "bet_side", "bet_result"], dropna=False)
              .size()
              .reset_index(name="count")
              .sort_values(["market_type", "bet_side", "bet_result"], kind="mergesort")
        )
        print("\nDetailed Market / Side / Result:")
        if detailed_market_tally.empty:
            print("No rows")
        else:
            print(detailed_market_tally.to_string(index=False))

        for mt in sorted(df["market_type"].dropna().astype(str).unique()):
            sub = df[df["market_type"] == mt].copy()
            wins = int((sub["bet_result"] == "Win").sum())
            losses = int((sub["bet_result"] == "Loss").sum())
            pushes = int((sub["bet_result"] == "Push").sum())
            graded = wins + losses
            win_pct = (wins / graded) if graded > 0 else 0.0

            print(f"\n{mt.upper()} SUMMARY")
            print(f"  Total bets : {len(sub)}")
            print(f"  Wins       : {wins}")
            print(f"  Losses     : {losses}")
            print(f"  Pushes     : {pushes}")
            print(f"  Win %      : {win_pct:.4f}")

        print(f"\nTotal Bets: {len(df)}")

        sorted_df = build_sorted_output(df, market_name)
        sorted_df.to_csv(out_path, index=False)
        log(f"{market_name}: wrote {out_path} ({len(sorted_df)} rows)")

    print("results_sorted.py complete.")


if __name__ == "__main__":
    main()
