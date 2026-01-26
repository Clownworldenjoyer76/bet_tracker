from pathlib import Path
import pandas as pd

IN_PATH = Path("bets/historic/nhl_data.csv")
OUT_PATH = Path("bets/historic/nhl_normalized.csv")


def main():
    df = pd.read_csv(IN_PATH)

    # Explicit coercion (this is the key NHL fix)
    df["home_final"] = pd.to_numeric(df["home_final"], errors="coerce")
    df["away_final"] = pd.to_numeric(df["away_final"], errors="coerce")

    # Drop any rows that failed coercion
    bad = df[df["home_final"].isna() | df["away_final"].isna()]
    if not bad.empty:
        print(f"[WARN] dropping {len(bad)} rows with invalid scores")

    df = df.dropna(subset=["home_final", "away_final"])

    rows = []

    for _, r in df.iterrows():
        # home side
        rows.append(
            {
                "league": "nhl",
                "season": int(r["season"]),
                "date": int(r["date"]),
                "team": r["home_team"],
                "opponent": r["away_team"],
                "side": "home",
                "team_score": int(r["home_final"]),
                "opp_score": int(r["away_final"]),
                "close_ml": int(r["home_close_ml"]),
                "close_spread": float(r["home_close_spread"]),
                "close_total": float(r["close_over_under"]),
            }
        )

        # away side
        rows.append(
            {
                "league": "nhl",
                "season": int(r["season"]),
                "date": int(r["date"]),
                "team": r["away_team"],
                "opponent": r["home_team"],
                "side": "away",
                "team_score": int(r["away_final"]),
                "opp_score": int(r["home_final"]),
                "close_ml": int(r["away_close_ml"]),
                "close_spread": float(r["away_close_spread"]),
                "close_total": float(r["close_over_under"]),
            }
        )

    out = pd.DataFrame(rows)

    # derived fields
    out["win"] = out["team_score"] > out["opp_score"]
    out["margin"] = out["team_score"] - out["opp_score"]

    out.to_csv(OUT_PATH, index=False)

    print(f"[OK] wrote {OUT_PATH} ({len(out)} rows)")


if __name__ == "__main__":
    main()
