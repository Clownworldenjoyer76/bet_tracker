#!/usr/bin/env python3
# scripts/email_alert_workflow_failures.py

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


ALERT_FILE = Path("alert_body.txt")
LOOKBACK_HOURS = 12

WORKFLOW_FILES_TO_CHECK = {
    "intake_basketball.yml",
    "intake_mlb.yml",
    "intake_nhl.yml",
    "intake_soccer.yml",
    "manual_soccer_pred.yml",
    "manual_soccer_scores.yml",
    "mlb_lineup_scraper.yml",
    "odds_basketball_nba.yml",
    "odds_basketball_wnba.yml",
    "odds_mlb.yml",
    "odds_nhl.yml",
    "odds_soccer_epl_mls.yml",
    "odds_soccer_lig1_laliga.yml",
    "odds_soccer_seriea_bund.yml",
    "pipeline_basketball.yml",
    "pipeline_mlb.yml",
    "pipeline_nhl.yml",
    "pipeline_soccer.yml",
    "pipeline_ufc.yml",
    "pipeline_ufc_2.yml",
    "ufc_manual_final.yml",
    "_00_manual_data.yml",
}

FAILURE_CONCLUSIONS = {
    "failure",
    "timed_out",
    "action_required",
    "cancelled",
}


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def github_api_get(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "workflow-failure-alert-checker",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_workflow_path(path_value: str) -> str:
    """
    GitHub usually returns workflow paths like:
      .github/workflows/intake_mlb.yml

    This function returns only:
      intake_mlb.yml
    """
    return Path(path_value).name.strip()


def fetch_recent_workflow_runs(
    repo: str,
    token: str,
    created_since: datetime,
    max_pages: int = 5,
) -> list[dict]:
    created_filter = urllib.parse.quote(
        f">={created_since.isoformat().replace('+00:00', 'Z')}"
    )

    all_runs: list[dict] = []

    for page in range(1, max_pages + 1):
        url = (
            f"https://api.github.com/repos/{repo}/actions/runs"
            f"?per_page=100"
            f"&page={page}"
            f"&created={created_filter}"
        )

        payload = github_api_get(url, token)
        runs = payload.get("workflow_runs", [])

        if not runs:
            break

        all_runs.extend(runs)

    return all_runs


def is_target_workflow(run: dict) -> bool:
    workflow_path = normalize_workflow_path(str(run.get("path") or ""))
    return workflow_path in WORKFLOW_FILES_TO_CHECK


def is_failed_run(run: dict) -> bool:
    conclusion = str(run.get("conclusion") or "").strip().lower()
    return conclusion in FAILURE_CONCLUSIONS


def build_alert_body(
    repo: str,
    failed_runs: list[dict],
    created_since: datetime,
) -> str:
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines = [
        "GitHub workflow failure alert triggered.",
        "",
        f"Repository: {repo}",
        f"Checked at UTC: {checked_at}",
        f"Lookback window: previous {LOOKBACK_HOURS} hours",
        f"Window start UTC: {created_since.isoformat(timespec='seconds')}",
        "",
        f"Failed runs found: {len(failed_runs)}",
        "",
    ]

    for index, run in enumerate(failed_runs, start=1):
        workflow_name = run.get("name") or "UNKNOWN"
        workflow_file = normalize_workflow_path(str(run.get("path") or "UNKNOWN"))
        conclusion = run.get("conclusion") or "UNKNOWN"
        status = run.get("status") or "UNKNOWN"
        event = run.get("event") or "UNKNOWN"
        branch = run.get("head_branch") or "UNKNOWN"
        run_number = run.get("run_number") or "UNKNOWN"
        created_at = run.get("created_at") or "UNKNOWN"
        updated_at = run.get("updated_at") or "UNKNOWN"
        html_url = run.get("html_url") or "UNKNOWN"

        lines.extend(
            [
                "-" * 72,
                f"Failure #{index}",
                "",
                f"Workflow name: {workflow_name}",
                f"Workflow file: {workflow_file}",
                f"Conclusion: {conclusion}",
                f"Status: {status}",
                f"Event: {event}",
                f"Branch: {branch}",
                f"Run number: {run_number}",
                f"Created at: {created_at}",
                f"Updated at: {updated_at}",
                f"Run URL: {html_url}",
                "",
            ]
        )

    lines.extend(
        [
            "-" * 72,
            "",
            "Workflows checked:",
        ]
    )

    for workflow_file in sorted(WORKFLOW_FILES_TO_CHECK):
        lines.append(f"- {workflow_file}")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    if ALERT_FILE.exists():
        ALERT_FILE.unlink()

    repo = required_env("GITHUB_REPOSITORY")
    token = required_env("GITHUB_TOKEN")

    created_since = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    runs = fetch_recent_workflow_runs(
        repo=repo,
        token=token,
        created_since=created_since,
    )

    failed_runs = [
        run
        for run in runs
        if is_target_workflow(run) and is_failed_run(run)
    ]

    failed_runs.sort(
        key=lambda r: str(r.get("created_at") or ""),
        reverse=True,
    )

    if not failed_runs:
        print(f"No failed workflow runs found in previous {LOOKBACK_HOURS} hours.")
        return 0

    body = build_alert_body(
        repo=repo,
        failed_runs=failed_runs,
        created_since=created_since,
    )

    ALERT_FILE.write_text(body, encoding="utf-8")

    print(f"FAILED WORKFLOW RUNS FOUND: {len(failed_runs)}")
    print(f"WROTE {ALERT_FILE}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        raise
