#!/usr/bin/env python3
# docs/win/soccer/scripts/00_parsing/drat.py

import sys
import re
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# =========================
# LOGGING
# =========================

ERROR_DIR = Path("docs/win/soccer/errors/00_intake")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "drat_log.txt"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

def log(msg: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

# =========================
# ARGS / INPUT
# =========================

USAGE = (
    "Usage:\n"
    "  drat.py <league> <market> <raw_text>\n"
    "  drat.py <league> <market> -            (read raw_text from stdin)\n"
    "  drat.py <league> <market> <path.txt>   (read raw_text from file)\n"
)

if len(sys.argv) < 3:
    raise ValueError(USAGE)

league_arg = sys.argv[1].strip()
market_input = sys.argv[2].strip()

# IMPORTANT:
# Passing multiline dumps via argv is fragile (spaces/newlines split arguments).
# We support:
# - stdin via "-"
# - file path
# - fallback: join remaining argv tokens
raw_text = ""
if len(sys.argv) >= 4:
    third = sys.argv[3]
    if third == "-":
        raw_text = sys.stdin.read()
        log("Read raw_text from stdin.")
    else:
        p = Path(third)
        if p.exists() and p.is_file():
            raw_text = p.read_text(encoding="utf-8", errors="replace")
            log(f"Read raw_text from file: {p}")
        else:
            # Fallback: join all remaining args (handles spaces if caller didn't quote correctly)
            raw_text = " ".join(sys.argv[3:])
            log("Read raw_text from joined argv tokens (fallback).")
else:
    # No raw_text arg provided; allow stdin as a last resort
    raw_text = sys.stdin.read()
    log("No raw_text arg; read from stdin as fallback.")

if not raw_text or not raw_text.strip():
    log("ERROR: raw_text is empty after ingestion.")
    raise ValueError("raw_text is empty. Provide stdin (-), a file path, or a properly quoted raw_text argument.")

log(f"raw_text_len={len(raw_text)} preview={raw_text[:120].replace(chr(10), ' | ')}")

# =========================
# MARKET MAP
# =========================

market_map = {
    "MLS": "mls",
    "EPL": "epl",
    "Ligue 1": "ligue1",
    "Serie A": "seriea",
    "La Liga": "laliga",
    "Bundesliga": "bundesliga",
}

market = market_map.get(market_input)
if not market:
    raise ValueError(f"Invalid soccer market: {market_input!r}")

# For output, you said league is always "soccer"
league = "soccer"

FIELDNAMES = [
    "league", "market", "match_date", "match_time",
    "home_team", "away_team",
    "home_prob", "draw_prob", "away_prob",
]

# =========================
# REGEX
# =========================

RE_DATE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
# Support:
#  - 9:00 AM / 09:00 AM / 9:00AM
#  - 14:45 (24h) just in case some dumps omit AM/PM
RE_TIME = re.compile(r"\b(\d{1,2}:\d{2})(?:\s*(AM|PM))?\b", re.IGNORECASE)
RE_PCT = re.compile(r"(\d+(?:\.\d+)?)%")

# =========================
# NORMALIZE LINES
# =========================

lines = []
for l in raw_text.splitlines():
    s = l.replace("−", "-").strip()
    if s:
        lines.append(s)

n = len(lines)
log(f"lines_count={n}")

# =========================
# PARSE
# =========================

rows_by_date = defaultdict(list)
dates_seen = set()

def next_idx_with_time(start_idx: int, max_lookahead: int = 5) -> int:
    """
    Find the next line index containing a time, within a limited lookahead.
    Returns index if found, else -1.
    """
    end = min(n, start_idx + max_lookahead)
    for j in range(start_idx, end):
        if RE_TIME.search(lines[j]):
            return j
    return -1

def strip_pct(text: str) -> str:
    return RE_PCT.sub("", text).strip()

i = 0
while i < n:
    dm = RE_DATE.search(lines[i])
    if not dm:
        i += 1
        continue

    mm, dd, yyyy = dm.groups()
    file_date = f"{yyyy}_{mm}_{dd}"
    dates_seen.add(file_date)

    # Look for time within next few lines (dump headers / noise can sometimes appear)
    t_idx = next_idx_with_time(i + 1, max_lookahead=6)
    if t_idx == -1:
        log(f"DATE found but no TIME near it: idx={i} line={lines[i]!r}")
        i += 1
        continue

    match_time = lines[t_idx].strip()

    # Teams should be the next two non-empty lines after the time line (we already removed empties)
    team_a_idx = t_idx + 1
    team_b_idx = t_idx + 2
    if team_b_idx >= n:
        break

    team_a = strip_pct(lines[team_a_idx])
    team_b = strip_pct(lines[team_b_idx])

    if not team_a or not team_b:
        log(f"Missing teams after date/time: date_idx={i} time_idx={t_idx} team_a={team_a!r} team_b={team_b!r}")
        i = team_b_idx + 1
        continue

    # Your existing assumption: Team A then Team B
    away_team = team_a
    home_team = team_b

    # Collect next 3 percentages from subsequent lines (starting after the 2 team lines)
    pct_vals = []
    j = team_b_idx + 1
    while j < n and len(pct_vals) < 3:
        found = RE_PCT.findall(lines[j])
        for v in found:
            try:
                pct_vals.append(float(v) / 100.0)
            except Exception:
                pass
            if len(pct_vals) == 3:
                break
        j += 1

    if len(pct_vals) != 3:
        log(
            f"Incomplete pct block: date={file_date} time={match_time!r} "
            f"away={away_team!r} home={home_team!r} pct_found={pct_vals}"
        )
        i = j
        continue

    # Per your instruction: Team A %, Team B %, Draw %
    away_prob = pct_vals[0]
    home_prob = pct_vals[1]
    draw_prob = pct_vals[2]

    rows_by_date[file_date].append({
        "league": league,
        "market": market,
        "match_date": file_date,
        "match_time": match_time,
        "home_team": home_team,
        "away_team": away_team,
        "home_prob": f"{home_prob:.6f}",
        "draw_prob": f"{draw_prob:.6f}",
        "away_prob": f"{away_prob:.6f}",
    })

    # Move pointer forward to continue scanning after the percentages block we just consumed
    i = j

# =========================
# WRITE OUTPUT(S)
# =========================

total_rows = sum(len(v) for v in rows_by_date.values())
log(f"dates_seen={sorted(dates_seen)} total_rows={total_rows}")

if total_rows == 0:
    raise ValueError("No rows parsed from raw_text (likely raw_text ingestion/quoting issue). See drat_log.txt for details.")

outdir = Path("docs/win/soccer/00_intake/predictions")
outdir.mkdir(parents=True, exist_ok=True)

# If multiple dates appear, write one file per date (safer and avoids silent mixing)
written = 0
for d in sorted(rows_by_date.keys()):
    outfile = outdir / f"soccer_{d}.csv"
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows_by_date[d])
    print(f"Wrote {outfile} ({len(rows_by_date[d])} rows)")
    written += 1

log(f"files_written={written}")
