from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path("bets/historic")
OUT_DIR = DATA_DIR / "spreads"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# League-specific spread bands
SPREAD_BANDS = {
    "nba": [
        (0, 1), (1.5, 3), (3.5, 5), (5.5, 7),
        (7.5, 10), (10.5, 15), (15.5, 100),
    ],
    "nfl": [
        (0, 1), (1.5, 3), (3.5, 6),
        (6.5, 10), (10.5, 14), (14.5, 100),
    ],
    # NHL / MLB are puck line / run line
    "nhl": [(1, 1.5)],
    "mlb": [(1, 1.5)],
}


def spread_to_band(val, league):
    for lo, hi in SPREAD_BANDS[league]:
        if lo <= abs(val) <= hi:
            return f"{lo} to {hi}"
    return None  # important: no "unknown"


def ats_profit(win, odds=-110):
    if win:
        return 100 / abs(odds)
    return -1.0


def process_file(path: Path):
    league = path.stem.split("_")[0]

    if league not in SPREAD_BANDS:
        print(f"[SKIP] {path.name}: unknown league")
        return

    df = pd.read_csv(path)

    required = {
        "home_final", "away_final",
        "home_close_spread", "away_close_spread",
    }

    if not required.issubset(df.columns):
        print(f"[SKIP] {path.name}: missing spread columns")
        return

    # numeric coercion
    for c in required:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=required)

    rows = []

    for _, r in df.iterrows():
        home_margin = r.home_final + r.home_close_spread - r.away_final
        away_margin = r.away_final + r.away_close_spread - r.home_final

        home_push = home_margin == 0
        away_push = away_margin == 0

        home_win = home_margin > 0
        away_win = away_margin > 0

        home_fav = r.home_close_spread < r.away_close_spread
        away_fav = r.away_close_spread < r.home_close_spread

        rows.append({
            "spread": r.home_close_spread,
            "win": home_win,
            "push": home_push,
            "fav_ud": "favorite" if home_fav else "underdog",
            "venue": "home",
        })

        rows.append({
            "spread": r.away_close_spread,
            "win": away_win,
            "push": away_push,
            "fav_ud": "favorite" if away_fav else "underdog",
            "venue": "away",
        })

    sides = pd.DataFrame(rows)

    # ---- LEAGUE GUARDS ----
    if league in {"nhl", "mlb"}:
        # Only keep true puck/run line games (±1.5)
        sides = sides[sides["spread"].abs() == 1.5]

    sides["band"] = sides["spread"].apply(lambda x: spread_to_band(x, league))

    # Drop anything outside defined bands
    sides = sides.dropna(subset=["band"])

    sides["profit"] = sides.apply(
        lambda r: 0.0 if r.push else ats_profit(r.win),
        axis=1,
    )

    summary = (
        sides
        .groupby(["band", "fav_ud", "venue"], dropna=False)
        .agg(
            bets=("win", "count"),
            wins=("win", "sum"),
            pushes=("push", "sum"),
            profit=("profit", "sum"),
        )
        .reset_index()
    )

    summary["decisions"] = summary["bets"] - summary["pushes"]
    summary = summary[summary["decisions"] > 0]

    summary["win_pct"] = (
        summary["wins"] / summary["decisions"]
    ).round(4)

    summary["roi"] = (
        summary["profit"] / summary["decisions"]
    ).round(4)

    # Clear naming
    suffix = (
        "spread_bands"
        if league in {"nba", "nfl"}
        else "puck_runline_bands"
    )

    out_path = OUT_DIR / f"{league}_{suffix}.csv"
    summary.to_csv(out_path, index=False)

    print(f"[OK] wrote {out_path} ({len(summary)} rows)")


def main():
    for path in DATA_DIR.glob("*_data.csv"):
        try:
            process_file(path)
        except Exception as e:
            print(f"[ERROR] {path.name}: {e}")


if __name__ == "__main__":
    main()
