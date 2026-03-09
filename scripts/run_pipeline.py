import subprocess
import sys
from datetime import datetime
from pathlib import Path

# -----------------------
# Paths
# -----------------------

LOG_DIR = Path("docs/win/errors")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "pipeline_log.txt"

# overwrite log every run
log = open(LOG_FILE, "w", encoding="utf-8")


def write_log(message):
    print(message)
    log.write(message + "\n")


write_log(f"\nPipeline Run: {datetime.now()}\n")

# -----------------------
# Pipeline definition
# -----------------------

pipeline = [

    # -----------------------
    # 01 MERGE
    # -----------------------

    ["python", "docs/win/soccer/scripts/01_merge/merge_intake.py"],
    ["python", "docs/win/soccer/scripts/01_merge/market_model.py"],   # NEW STEP

    ["python", "docs/win/hockey/scripts/01_merge/merge_intake.py"],
    ["python", "docs/win/basketball/scripts/01_merge/merge_intake.py"],

    ["python", "docs/win/hockey/scripts/01_merge/build_juice_files.py"],
    ["python", "docs/win/basketball/scripts/01_merge/build_juice_files.py"],

    # -----------------------
    # 02 APPLY JUICE
    # -----------------------

    ["python", "docs/win/soccer/scripts/02_juice/apply_juice.py"],

    ["python", "docs/win/hockey/scripts/02_juice/apply_moneyline_juice.py"],
    ["python", "docs/win/hockey/scripts/02_juice/apply_total_juice.py"],
    ["python", "docs/win/hockey/scripts/02_juice/apply_puck_line_juice.py"],

    ["python", "docs/win/basketball/scripts/02_juice/apply_moneyline_juice.py"],
    ["python", "docs/win/basketball/scripts/02_juice/apply_spread_juice.py"],
    ["python", "docs/win/basketball/scripts/02_juice/apply_total_juice.py"],

    # -----------------------
    # 03 EDGES
    # -----------------------

    ["python", "docs/win/soccer/scripts/03_edges/compute_edges.py"],
    ["python", "docs/win/hockey/scripts/03_edges/compute_edges.py"],
    ["python", "docs/win/basketball/scripts/03_edges/compute_edges.py"],

    # -----------------------
    # 04 SELECT
    # -----------------------

    ["python", "docs/win/soccer/scripts/04_select/select_bets.py"],
    ["python", "docs/win/hockey/scripts/04_select/select_bets.py"],
    ["python", "docs/win/basketball/scripts/04_select/select_bets.py"],
    ["python", "docs/win/basketball/scripts/04_select/combine_trim_basketball.py"],

    # -----------------------
    # 05 RESULTS
    # -----------------------

    ["python", "docs/win/final_scores/scripts/05_results/name_normalization.py"],
    ["python", "docs/win/final_scores/scripts/05_results/results.py"],
    ["python", "docs/win/final_scores/scripts/05_results/generate_summary.py"],
    ["python", "docs/win/final_scores/scripts/05_results/results_sorted.py"],
]

# -----------------------
# Execute pipeline
# -----------------------

failures = 0

for step in pipeline:

    script = step[1]

    try:
        subprocess.run(step, check=True)
        write_log(f"✅ {script}")

    except subprocess.CalledProcessError as e:
        failures += 1
        write_log(f"❌ {script}")
        write_log(f"   ERROR: {str(e)}")

write_log("\nPipeline complete")

if failures:
    write_log(f"\n❌ FAILURES: {failures}")
else:
    write_log("\n✅ ALL SCRIPTS SUCCESSFUL")

log.close()
