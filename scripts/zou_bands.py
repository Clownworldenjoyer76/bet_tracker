from pathlib import Path
import pandas as pd

DATA_DIR = Path("bets/historic")
OUT_DIR = DATA_DIR / "totals"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------
# League-specific total bands
# -------------------------
TOTAL_BANDS = {
    "nba": [
        (0, 204.5),
        (205, 214.5),
        (215, 224.5),
        (225, 234.5),
        (235, 244.5),
        (245, 1000),
    ],
    "nfl": [
        (0, 40.5),
        (41, 44.5),
        (45, 48.5),
        (49, 52.5),
        (53, 1000),
    ],
    "nhl": [
        (0, 4.5),
        (5, 5.5),
        (6, 6.5),
        (7, 100),
    ],
    "mlb": [
        (0, 7),
        (7.5, 8),
        (8.5, 9),
        (9.5, 100),
    ],
}

DEFAULT_ODDS = -110


def odds_profit(win: bool, odds: int = DEFAULT_ODDS) -> float:
    if not win:
        return -1.0
    if odds < 0:
        return 100 / abs(odds)
    return odds / 100


def band_label(low, high):
    return f"{low} to {high}"


def assign_band(total, bands):
    for low, high in bands:
        if low <= total <= high:
            return band_label(low, high)
    return "unknown"


def process_league(path: Path, league: str):
    df = pd.read_csv(path)

    required = {
        "home_final",
        "away_final",
        "close_over_under",
    }

    if not required.issubset(df.columns):
        print(f"[SKIP] {path.name}: missing required columns")
        return

    # numeric safety
    df["home_final"] = pd.to_numeric(df["home_final"], errors="coerce")
    df["away_final"] = pd.to_numeric(df["away_final"], errors="coerce")
    df["close_over_under"] = pd.to_numeric(df["close_over_under"], errors="coerce")

    df = df.dropna(subset=["home_final", "away_final", "close_over_under"])

    df["final_total"] = df["home_final"] + df["away_final"]

    # remove pushes
    df = df[df["final_total"] != df["close_over_under"]]

    df["band"] = df["close_over_under"].apply(
        lambda x: assign_band(x, TOTAL_BANDS[league])
    )

    records = []

    for side in ["over", "under"]:
        tmp = df.copy()

        if side == "over":
            tmp["win"] = tmp["final_total"] > tmp["close_over_under"]
        else:
            tmp["win"] = tmp["final_total"] < tmp["close_over_under"]

        tmp["profit"] = tmp["win"].apply(lambda w: odds_profit(w))

        grouped = (
            tmp.groupby("band")
            .agg(
                bets=("win", "count"),
                wins=("win", "sum"),
                profit=("profit", "sum"),
            )
            .reset_index()
        )

        grouped["side"] = side
        records.append(grouped)

    out = pd.concat(records, ignore_index=True)

    out["win_pct"] = (out["wins"] / out["bets"]).round(4)
    out["roi"] = (out["profit"] / out["bets"]).round(4)

    out = out[
        ["band", "side", "bets", "wins", "profit", "win_pct", "roi"]
    ].sort_values(["band", "side"])

    out_path = OUT_DIR / f"{league}_totals_bands.csv"
    out.to_csv(out_path, index=False)

    print(f"[OK] wrote {out_path} ({len(out)} rows)")


def main():
    leagues = ["nba", "nfl", "nhl", "mlb"]

    for league in leagues:
        path = DATA_DIR / f"{league}_data.csv"
        if not path.exists():
            print(f"[WARN] missing {path.name}")
            continue

        try:
            process_league(path, league)
        except Exception as e:
            print(f"[ERROR] {league}: {e}")


if __name__ == "__main__":
    main()
