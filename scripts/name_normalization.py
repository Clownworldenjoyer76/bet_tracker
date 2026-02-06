#scripts/name_normalization.py
#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import traceback

# =========================
# PATHS
# =========================

MANUAL_DIR = Path("docs/win/manual")
DUMP_DIR = Path("docs/win/dump/csvs/cleaned")

MAP_PATH = Path("mappings/team_map.csv")

NO_MAP_DIR = Path("mappings/need_map")
NO_MAP_PATH = NO_MAP_DIR / "no_map.csv"

ERROR_DIR = Path("docs/win/errors")
ERROR_LOG = ERROR_DIR / "name_normalization.txt"

NO_MAP_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# MAIN
# =========================

def main():
    try:
        map_df = pd.read_csv(MAP_PATH, dtype=str)

        # Build lookup structures
        # team_map: league -> {dk_team: canonical_team}
        # canonical_sets: league -> set(canonical_team)
        team_map = {}
        canonical_sets = {}

        for _, row in map_df.iterrows():
            lg = row["league"].strip()
            dk = row["dk_team"].strip()
            can = row["canonical_team"].strip()

            team_map.setdefault(lg, {})[dk] = can
            canonical_sets.setdefault(lg, set()).add(can)

        # store (team, league)
        unmapped = set()

        # ==================================================
        # 1️⃣ MANUAL FILES (LOGIC UNCHANGED)
        # ==================================================

        for file_path in MANUAL_DIR.glob("*.csv"):
            df = pd.read_csv(file_path, dtype=str)

            if "league" not in df.columns:
                continue

            for col in ("team", "opponent"):
                if col not in df.columns:
                    continue

                def replace(val, lg):
                    if pd.isna(val):
                        return val

                    base_lg = lg.split("_")[0]

                    # already canonical
                    if val in canonical_sets.get(base_lg, set()):
                        return val

                    # dk_team -> canonical_team
                    if val in team_map.get(base_lg, {}):
                        return team_map[base_lg][val]

                    # no match
                    unmapped.add((val, base_lg))
                    return val

                df[col] = [
                    replace(v, lg) for v, lg in zip(df[col], df["league"])
                ]

            df.to_csv(file_path, index=False)

        # ==================================================
        # 2️⃣ DUMP FILES (SAME MATCHING LOGIC)
        # ==================================================

        for file_path in DUMP_DIR.glob("*.csv"):
            # filename: league_YYYY_MM_DD.csv
            parts = file_path.stem.split("_")
            if len(parts) < 4:
                continue

            base_lg = parts[0]

            df = pd.read_csv(file_path, dtype=str)

            for col in ("home_team", "away_team"):
                if col not in df.columns:
                    continue

                def replace_dump(val):
                    if pd.isna(val):
                        return val

                    # already canonical
                    if val in canonical_sets.get(base_lg, set()):
                        return val

                    # dk_team -> canonical_team
                    if val in team_map.get(base_lg, {}):
                        return team_map[base_lg][val]

                    # no match
                    unmapped.add((val, base_lg))
                    return val

                df[col] = df[col].apply(replace_dump)

            df.to_csv(file_path, index=False)

        # ==================================================
        # 3️⃣ WRITE UNMAPPED (TEAM + LEAGUE)
        # ==================================================

        if unmapped:
            pd.DataFrame(
                sorted(unmapped),
                columns=["team", "league"]
            ).to_csv(
                NO_MAP_PATH, index=False
            )

    except Exception as e:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(str(e) + "\n")
            f.write(traceback.format_exc())
            f.write("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    main()
