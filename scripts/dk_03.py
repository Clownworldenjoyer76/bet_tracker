#scripts/dk_03.py
#!/usr/bin/env python3

import csv
from pathlib import Path
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/manual/cleaned")
OUTPUT_DIR = Path("docs/win/manual/normalized")
ERROR_DIR = Path("docs/win/errors")

ERROR_LOG = ERROR_DIR / "dk_03.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# ERROR LOGGING
# =========================

def log_error(msg: str):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# =========================
# CORE LOGIC
# =========================

def process_file(path: Path):
    try:
        parts = path.stem.split("_")
        if len(parts) < 4:
            raise ValueError(f"Invalid filename: {path.name}")

        _, league, market, *_ = parts

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return

        out_rows = []
        i = 0

        while i < len(rows):

            # ======================
            # MONEYLINE / SPREADS
            # ======================
            if market in ("moneyline", "spreads"):
                away = rows[i]
                home = rows[i + 1]
                i += 2

                out = {
                    "date": away["date"],
                    "time": away["time"],
                    "league": away["league"],
                    "game_id": away["game_id"],
                    "away_team": away["team"],
                    "home_team": home["team"],
                    "away_handle_pct": away.get("handle_pct"),
                    "home_handle_pct": home.get("handle_pct"),
                    "away_bets_pct": away.get("bets_pct"),
                    "home_bets_pct": home.get("bets_pct"),
                }

                if market == "moneyline":
                    out.update({
                        "away_odds": away["odds"],
                        "home_odds": home["odds"],
                        "away_decimal_odds": away["decimal_odds"],
                        "home_decimal_odds": home["decimal_odds"],
                    })

                else:  # spreads
                    out.update({
                        "away_spread": away["spread"],
                        "home_spread": home["spread"],
                        "away_odds": away["odds"],
                        "home_odds": home["odds"],
                        "away_decimal_odds": away["decimal_odds"],
                        "home_decimal_odds": home["decimal_odds"],
                    })

                out_rows.append(out)

            # ======================
            # TOTALS
            # ======================
            elif market == "totals":
                r1, r2, r3, r4 = rows[i:i+4]
                i += 4

                over_row = next(r for r in (r1, r2, r3, r4) if r["side"].lower() == "over")
                under_row = next(r for r in (r1, r2, r3, r4) if r["side"].lower() == "under")

                out = {
                    "date": r1["date"],
                    "time": r1["time"],
                    "league": r1["league"],
                    "game_id": r1["game_id"],
                    "away_team": r1["team"],
                    "home_team": r3["team"],
                    "away_handle_pct": r1.get("handle_pct"),
                    "home_handle_pct": r3.get("handle_pct"),
                    "away_bets_pct": r1.get("bets_pct"),
                    "home_bets_pct": r3.get("bets_pct"),
                    "total": over_row["total"],
                    "over_odds": over_row["odds"],
                    "under_odds": under_row["odds"],
                    "over_decimal_odds": over_row["decimal_odds"],
                    "under_decimal_odds": under_row["decimal_odds"],
                }

                out_rows.append(out)

            else:
                raise ValueError(f"Unknown market: {market}")

        # ======================
        # WRITE OUTPUT
        # ======================

        out_path = OUTPUT_DIR / path.name
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_rows[0].keys())
            writer.writeheader()
            writer.writerows(out_rows)

    except Exception as e:
        log_error(f"FILE: {path}")
        log_error(str(e))
        log_error(traceback.format_exc())
        log_error("-" * 80)

# =========================
# MAIN
# =========================

def main():
    for path in INPUT_DIR.glob("dk_*_*.csv"):
        process_file(path)

if __name__ == "__main__":
    main()
