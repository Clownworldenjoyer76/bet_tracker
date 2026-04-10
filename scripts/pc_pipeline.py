#!/usr/bin/env python3
# local_pipeline.py

import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent

PIPELINE = [
    ("00_intake", "docs/win/soccer/scripts/00_intake/fetch_soccer_odds.py"),
    ("00_intake", "docs/win/soccer/scripts/00_intakeg/name_normalization.py"),
    ("00_intake", "docs/win/soccer/scripts/00_intake/soccer_drat.py"),
    ("00_intake", "docs/win/soccer/scripts/00_intake/soccer_cleaner.py"),
    ("00_intake", "docs/win/hockey/scripts/00_intake/odds_parse.py"),
    ("00_intake", "docs/win/hockey/scripts/00_intake/name_normalization.py"),
    ("00_intake", "docs/win/hockey/scripts/00_intake/hockey_drat_scraper.py"),
    ("00_intake", "docs/win/hockey/scripts/00_intake/transform_hockey.py"),
    ("00_intake", "docs/win/hockey/scripts/00_intake/name_normalization.py"),
    ("00_intake", "docs/win/baseball/scripts/00_intake/odds_parse.py"),
    ("00_intake", "docs/win/baseball/scripts/00_intake/name_normalization.py"),
    ("00_intake", "docs/win/baseball/scripts/00_intake/baseball_drat_scraper.py"),
    ("00_intake", "docs/win/baseball/scripts/00_intake/transform_baseball.py"),
    ("00_intake", "docs/win/baseball/scripts/00_intake/name_normalization.py"),
    ("00_intake", "docs/win/basketball/scripts/00_intake/basketball_odds_parse.py"),
    ("00_intake", "docs/win/basketball/scripts/00_intake/basketball_name_normalization.py"),
    ("00_intake", "docs/win/basketball/scripts/00_intake/basketball_drat_scraper.py"),
    ("00_intake", "docs/win/basketball/scripts/00_intake/transform_basketball.py"),
    ("00_intake", "docs/win/basketball/scripts/00_intake/basketball_name_normalization.py"),

    ("01_merge", "docs/win/soccer/scripts/01_merge/merge_intake.py"),
    ("01_merge", "docs/win/soccer/scripts/01_merge/build_juice_files.py"),
    ("01_merge", "docs/win/hockey/scripts/01_merge/merge_intake.py"),
    ("01_merge", "docs/win/hockey/scripts/01_merge/build_juice_files.py"),
    ("01_merge", "docs/win/baseball/scripts/01_merge/merge_intake.py"),
    ("01_merge", "docs/win/baseball/scripts/01_merge/build_juice_files.py"),
    ("01_merge", "docs/win/basketball/scripts/01_merge/merge_intake.py"),
    ("01_merge", "docs/win/basketball/scripts/01_merge/build_juice_files.py"),

    ("02_juice", "docs/win/soccer/scripts/02_juice/apply_juice.py"),
    ("02_juice", "docs/win/hockey/scripts/02_juice/apply_moneyline_juice.py"),
    ("02_juice", "docs/win/hockey/scripts/02_juice/apply_puck_line_juice.py"),
    ("02_juice", "docs/win/hockey/scripts/02_juice/apply_total_juice.py"),
    ("02_juice", "docs/win/baseball/scripts/02_juice/apply_moneyline_juice.py"),
    ("02_juice", "docs/win/baseball/scripts/02_juice/apply_run_line_juice.py"),
    ("02_juice", "docs/win/baseball/scripts/02_juice/apply_total_juice.py"),
    ("02_juice", "docs/win/basketball/scripts/02_juice/apply_moneyline_juice.py"),
    ("02_juice", "docs/win/basketball/scripts/02_juice/apply_spread_juice.py"),
    ("02_juice", "docs/win/basketball/scripts/02_juice/apply_total_juice.py"),

    ("03_edges", "docs/win/soccer/scripts/03_edges/build_edges.py"),
    ("03_edges", "docs/win/hockey/scripts/03_edges/compute_edges.py"),
    ("03_edges", "docs/win/hockey/scripts/03_edges/compute_ev_kelly.py"),
    ("03_edges", "docs/win/baseball/scripts/03_edges/compute_edges.py"),
    ("03_edges", "docs/win/baseball/scripts/03_edges/compute_ev_kelly.py"),
    ("03_edges", "docs/win/basketball/scripts/03_edges/compute_edges.py"),
    ("03_edges", "docs/win/basketball/scripts/03_edges/compute_ev_kelly.py"),

    ("04_select", "docs/win/soccer/scripts/04_select/select_bets.py"),
    ("04_select", "docs/win/hockey/scripts/04_select/select_bets.py"),
    ("04_select", "docs/win/baseball/scripts/04_select/select_bets.py"),
    ("04_select", "docs/win/basketball/scripts/04_select/select_bets.py"),

    ("05_final", "docs/win/final_scores/scripts/05_results/soccer/01_soccer_results_grade.py"),
    ("05_final", "docs/win/final_scores/scripts/05_results/soccer/02_soccer_results_analyze.py"),
    ("05_final", "docs/win/final_scores/scripts/05_results/soccer/03_soccer_results_reports.py"),
    ("05_final", "docs/win/final_scores/scripts/05_results/hockey/01_nhl_results_grade.py"),
    ("05_final", "docs/win/final_scores/scripts/05_results/hockey/02_nhl_results_analyze.py"),
    ("05_final", "docs/win/final_scores/scripts/05_results/hockey/03_nhl_results_reports.py"),
    ("05_final", "docs/win/final_scores/scripts/05_results/mlb/01_mlb_results_grade.py"),
    ("05_final", "docs/win/final_scores/scripts/05_results/mlb/02_mlb_results_analyze.py"),
    ("05_final", "docs/win/final_scores/scripts/05_results/mlb/03_mlb_results_reports.py"),
    ("05_final", "docs/win/final_scores/scripts/05_results/basketball/01_basketball_results_grade.py"),
    ("05_final", "docs/win/final_scores/scripts/05_results/basketball/02_basketball_results_analyze.py"),
    ("05_final", "docs/win/final_scores/scripts/05_results/basketball/03_basketball_results_reports.py"),
]


def print_header(title: str) -> None:
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def run_script(stage: str, script_rel: str, index: int, total: int) -> None:
    script_path = REPO_ROOT / script_rel

    print_header(f"[{index}/{total}] {stage} :: {script_rel}")

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    start = time.time()
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(REPO_ROOT),
        check=False,
    )
    elapsed = time.time() - start

    if result.returncode != 0:
        raise RuntimeError(
            f"Script failed with exit code {result.returncode}: {script_rel}"
        )

    print(f"SUCCESS :: {script_rel} :: {elapsed:.2f}s")


def main() -> int:
    total = len(PIPELINE)

    print_header("LOCAL PIPELINE START")

    overall_start = time.time()

    for index, (stage, script_rel) in enumerate(PIPELINE, start=1):
        run_script(stage, script_rel, index, total)

    overall_elapsed = time.time() - overall_start

    print_header("LOCAL PIPELINE COMPLETE")
    print(f"Ran {total} scripts successfully in {overall_elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print()
        print("PIPELINE FAILED")
        print(str(exc))
        raise SystemExit(1)
