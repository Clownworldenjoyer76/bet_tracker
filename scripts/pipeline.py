# scripts/pipeline.py

import subprocess
import sys
from datetime import datetime
from pathlib import Path

# -----------------------
# Paths & Setup
# -----------------------

LOG_DIR = Path("docs/win/errors")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "pipeline_log.txt"

log = open(LOG_FILE, "w", encoding="utf-8")

current_date_str = datetime.now().strftime("%Y_%m_%d")


def write_log(message):
    print(message)
    log.write(message + "\n")


write_log(f"\nPipeline Run: {datetime.now()}\n")

# -----------------------
# Pipeline definition
# -----------------------

pipeline = [

    # --------------------------------
    # 01 MERGE
    # --------------------------------

    # Soccer
   # ["python", "docs/win/soccer/scripts/01_merge/merge_intake.py"],
    #["python", "docs/win/soccer/scripts/01_merge/build_juice_files.py"],


    # Hockey + Basketball
    ["python", "docs/win/hockey/scripts/01_merge/merge_intake.py"],
    ["python", "docs/win/basketball/scripts/01_merge/merge_intake.py"],

    ["python", "docs/win/hockey/scripts/01_merge/build_juice_files.py"],
    ["python", "docs/win/basketball/scripts/01_merge/build_juice_files.py"],

    # Baseball
    ["python", "docs/win/baseball/scripts/01_merge/merge_intake.py"],
    ["python", "docs/win/baseball/scripts/01_merge/build_juice_files.py"],


    # --------------------------------
    # 02 APPLY JUICE
    # --------------------------------

    # Soccer
    ## ["python", "docs/win/soccer/scripts/02_juice/apply_juice.py"],

    # Hockey
    ["python", "docs/win/hockey/scripts/02_juice/apply_moneyline_juice.py"],
    ["python", "docs/win/hockey/scripts/02_juice/apply_total_juice.py"],
    ["python", "docs/win/hockey/scripts/02_juice/apply_puck_line_juice.py"],

    # Basketball
    ["python", "docs/win/basketball/scripts/02_juice/apply_moneyline_juice.py"],
    ["python", "docs/win/basketball/scripts/02_juice/apply_spread_juice.py"],
    ["python", "docs/win/basketball/scripts/02_juice/apply_total_juice.py"],

    # Baseball
    ["python", "docs/win/baseball/scripts/02_juice/apply_moneyline_juice.py"],
    ["python", "docs/win/baseball/scripts/02_juice/apply_run_line_juice.py"],
    ["python", "docs/win/baseball/scripts/02_juice/apply_total_juice.py"],


    # --------------------------------
    # 03 EDGES
    # --------------------------------

    # Soccer / Hockey / Basketball
  #  ["python", "docs/win/soccer/scripts/03_edges/compute_edges.py"],
  #  ["python", "docs/win/hockey/scripts/03_edges/compute_edges.py"],
 #   ["python", "docs/win/basketball/scripts/03_edges/compute_edges.py"],

    # Baseball
    ["python", "docs/win/baseball/scripts/03_edges/compute_edges.py"],

    # EV + Kelly
    ["python", "docs/win/hockey/scripts/03_edges/compute_ev_kelly.py"],
    ["python", "docs/win/basketball/scripts/03_edges/compute_ev_kelly.py"],
    ["python", "docs/win/baseball/scripts/03_edges/compute_ev_kelly.py"],


    # --------------------------------
    # 04 SELECT
    # --------------------------------

  #  ["python", "docs/win/soccer/scripts/04_select/select_bets.py"],
    ["python", "docs/win/hockey/scripts/04_select/select_bets.py"],
    ["python", "docs/win/basketball/scripts/04_select/select_bets.py"],
    ["python", "docs/win/baseball/scripts/04_select/select_bets.py"],


    # --------------------------------
    # 05 RESULTS
    # --------------------------------

    ["python", "docs/win/final_scores/scripts/05_results/name_normalization.py"],

    # Basketball
    ["python", "docs/win/final_scores/scripts/05_results/basketball/01_basketball_results_grade.py"],
    ["python", "docs/win/final_scores/scripts/05_results/basketball/02_basketball_results_analyze.py"],
    ["python", "docs/win/final_scores/scripts/05_results/basketball/03_basketball_results_reports.py"],

    # NHL
    ["python", "docs/win/final_scores/scripts/05_results/hockey/01_nhl_results_grade.py"],
    ["python", "docs/win/final_scores/scripts/05_results/hockey/02_nhl_results_analyze.py"],
    ["python", "docs/win/final_scores/scripts/05_results/hockey/03_nhl_results_reports.py"],

    # Soccer
  #  ["python", "docs/win/final_scores/scripts/05_results/soccer/01_soccer_results_grade.py"],
  #  ["python", "docs/win/final_scores/scripts/05_results/soccer/02_soccer_results_analyze.py"],
  #  ["python", "docs/win/final_scores/scripts/05_results/soccer/03_soccer_results_reports.py"],

    # MLB
    ["python", "docs/win/final_scores/scripts/05_results/mlb/01_mlb_results_grade.py"],
    ["python", "docs/win/final_scores/scripts/05_results/mlb/02_mlb_results_analyze.py"],
    ["python", "docs/win/final_scores/scripts/05_results/mlb/03_mlb_results_reports.py"],
]

# -----------------------
# Execute pipeline
# -----------------------

failures = 0

try:
    for step in pipeline:

        script = step[1]

        try:
            subprocess.run(step, check=True)
            write_log(f"✅ {script}")

        except subprocess.CalledProcessError as e:
            failures += 1
            write_log(f"❌ {script}")
            write_log(f"    ERROR: {str(e)}")

    write_log("\nPipeline complete")

    if failures:
        write_log(f"\n❌ FAILURES: {failures}")
    else:
        write_log("\n✅ ALL SCRIPTS SUCCESSFUL")

finally:
    log.close()

if failures:
    sys.exit(1)
