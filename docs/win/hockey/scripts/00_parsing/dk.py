# docs/win/hockey/scripts/00_parsing/dk.py
#!/usr/bin/env python3

import sys
import re
import csv
from pathlib import Path
from datetime import datetime, timedelta

# =========================
# PATHS / LOGGING
# =========================

ERROR_DIR = Path("docs/win/hockey/errors/00_intake")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "dk_log.txt"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

def log(msg: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")

# =========================
# ARGS
# =========================

if len(sys.argv) < 4:
    raise SystemExit("Usage: dk.py <league> <market> <dump.txt>")

league_input = sys.argv[1].strip()
market_input = sys.argv[2].strip()
dump_path = Path(sys.argv[3])

if not dump_path.exists():
    raise FileNotFoundError(f"dump file not found: {dump_path}")

raw_text = dump_path.read_text(encoding="utf-8", errors="replace")

league = "hockey"

market_map = {
    "NHL": "NHL",
}

market = market_map.get(market_input)
if not market:
    raise ValueError(f"Invalid hockey market: {market_input}")

FIELDNAMES = [
    "league",
    "market",
    "game_date",
    "game_time",
    "home_team",
    "away_team",
    "away_puck_line",
    "home_puck_line",
    "total",
    "away_dk_puck_line_american",
    "home_dk_puck_line_american",
    "dk_total_over_american",
    "dk_total_under_american",
    "away_dk_moneyline_american",
    "home_dk_moneyline_american",
]

# =========================
# HELPERS
# =========================

MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

RE_DATE_HEADER = re.compile(
    r"^(?:MON|TUE|WED|THU|FRI|SAT|SUN)\s+"
    r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2})",
    re.IGNORECASE
)

RE_DATE_INLINE = re.compile(
    r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2})",
    re.IGNORECASE
)

RE_TIME = re.compile(r"\b(\d{1,2}:\d{2}\s*[AP]M)\b", re.IGNORECASE)

RE_ODDS = re.compile(r"^[+\-−]\d+$")  # includes unicode minus
RE_SPREAD = re.compile(r"^[+\-]\d+(?:\.\d+)?$")  # +1.5 / -1.5
RE_TOTAL_NUM = re.compile(r"^\d+(?:\.\d+)?$")     # 5.5

def clean_line(s: str) -> str:
    return s.strip()

def is_logo_line(s: str) -> bool:
    return s.lower().endswith("-logo")

def normalize_odds(s: str) -> str:
    return s.replace("−", "-").strip()

def parse_game_date(lines: list[str]) -> str:
    """
    Priority:
      - line containing TODAY -> today
      - line containing TOMORROW -> today+1
      - header like 'WED FEB 25th' (uses system year)
      - fallback: today
    """
    today = datetime.today()

    for raw in lines[:15]:
        u = raw.strip().upper()
        if not u:
            continue
        if "TODAY" in u:
            return today.strftime("%Y_%m_%d")
        if "TOMORROW" in u:
            return (today + timedelta(days=1)).strftime("%Y_%m_%d")

        m = RE_DATE_HEADER.match(u)
        if m:
            mon = MONTH_MAP[m.group(1)[:3].upper()]
            day = int(m.group(2))
            dt = datetime(today.year, mon, day)
            return dt.strftime("%Y_%m_%d")

    # fallback
    return today.strftime("%Y_%m_%d")

def extract_time(lines: list[str]) -> str:
    for raw in lines:
        m = RE_TIME.search(raw)
        if m:
            return m.group(1).upper().replace("  ", " ").strip()
    return ""

def extract_teams(lines: list[str]) -> tuple[str, str]:
    """
    Pattern:
      [away_logo] (optional)
      away_team
      at
      [home_logo] (optional)
      home_team
    """
    # remove empty and normalize
    cleaned = [clean_line(x) for x in lines if clean_line(x)]
    # locate "at"
    try:
        at_i = next(i for i, x in enumerate(cleaned) if x.lower() == "at")
    except StopIteration:
        raise ValueError("Missing 'at' delimiter")

    # away_team: nearest non-logo line before "at"
    away_team = ""
    for j in range(at_i - 1, -1, -1):
        if not is_logo_line(cleaned[j]) and cleaned[j].lower() not in ("puck line", "total", "moneyline"):
            away_team = cleaned[j]
            break
    if not away_team:
        raise ValueError("Could not determine away_team")

    # home_team: first non-logo line after "at"
    home_team = ""
    for j in range(at_i + 1, len(cleaned)):
        if not is_logo_line(cleaned[j]) and cleaned[j].lower() not in ("puck line", "total", "moneyline"):
            home_team = cleaned[j]
            break
    if not home_team:
        raise ValueError("Could not determine home_team")

    return away_team, home_team

def parse_numbers(lines: list[str]) -> dict:
    """
    Expected NHL ordering within a block (after teams):
      away_puck_line
      away_puck_line_odds
      O
      total
      over_odds
      away_moneyline
      home_puck_line
      home_puck_line_odds
      U
      total (repeat) [ignored]
      under_odds
      home_moneyline
    """
    cleaned = [clean_line(x) for x in lines if clean_line(x)]
    tokens = []

    # keep only the relevant tokens and keep order
    for x in cleaned:
        xl = x.strip()
        if xl.upper() in ("O", "U"):
            tokens.append(xl.upper())
            continue
        if RE_SPREAD.match(xl):
            tokens.append(xl)
            continue
        if RE_TOTAL_NUM.match(xl):
            tokens.append(xl)
            continue
        if RE_ODDS.match(normalize_odds(xl)):
            tokens.append(normalize_odds(xl))
            continue

    out = {
        "away_puck_line": "",
        "home_puck_line": "",
        "total": "",
        "away_dk_puck_line_american": "",
        "home_dk_puck_line_american": "",
        "dk_total_over_american": "",
        "dk_total_under_american": "",
        "away_dk_moneyline_american": "",
        "home_dk_moneyline_american": "",
    }

    i = 0
    # away puck line + odds
    if i < len(tokens) and RE_SPREAD.match(tokens[i]):
        out["away_puck_line"] = tokens[i]; i += 1
    if i < len(tokens) and RE_ODDS.match(tokens[i]):
        out["away_dk_puck_line_american"] = tokens[i]; i += 1

    # over total + odds
    if i < len(tokens) and tokens[i] == "O":
        i += 1
    if i < len(tokens) and RE_TOTAL_NUM.match(tokens[i]):
        out["total"] = tokens[i]; i += 1
    if i < len(tokens) and RE_ODDS.match(tokens[i]):
        out["dk_total_over_american"] = tokens[i]; i += 1

    # away moneyline odds
    if i < len(tokens) and RE_ODDS.match(tokens[i]):
        out["away_dk_moneyline_american"] = tokens[i]; i += 1

    # home puck line + odds
    if i < len(tokens) and RE_SPREAD.match(tokens[i]):
        out["home_puck_line"] = tokens[i]; i += 1
    if i < len(tokens) and RE_ODDS.match(tokens[i]):
        out["home_dk_puck_line_american"] = tokens[i]; i += 1

    # under total + odds
    if i < len(tokens) and tokens[i] == "U":
        i += 1
    # possible repeated total number; ignore if present
    if i < len(tokens) and RE_TOTAL_NUM.match(tokens[i]):
        i += 1
    if i < len(tokens) and RE_ODDS.match(tokens[i]):
        out["dk_total_under_american"] = tokens[i]; i += 1

    # home moneyline odds
    if i < len(tokens) and RE_ODDS.match(tokens[i]):
        out["home_dk_moneyline_american"] = tokens[i]; i += 1

    return out

# =========================
# PARSE
# =========================

blocks = raw_text.split("More Bets")
rows = []
errors = 0

for block in blocks:
    lines = [clean_line(l) for l in block.splitlines() if clean_line(l)]
    if not lines:
        continue

    # must contain "at" and at least 2 team names
    if not any(l.lower() == "at" for l in lines):
        continue

    try:
        game_date = parse_game_date(lines)
        game_time = extract_time(lines)
        away_team, home_team = extract_teams(lines)
        nums = parse_numbers(lines)

        # minimal validation (must at least have teams + date)
        if not away_team or not home_team or not game_date:
            raise ValueError("Missing required fields")

        rows.append({
            "league": league,
            "market": market,
            "game_date": game_date,
            "game_time": game_time,
            "home_team": home_team,
            "away_team": away_team,
            **nums,
        })

    except Exception as e:
        log(f"ERROR parsing block: {e}")
        errors += 1

if not rows:
    log("SUMMARY: wrote 0 rows")
    sys.exit()

# file per date (use date of first parsed row)
file_date = rows[0]["game_date"]

output_dir = Path("docs/win/hockey/00_intake/sportsbook")
output_dir.mkdir(parents=True, exist_ok=True)
outfile = output_dir / f"hockey_{file_date}.csv"

# =========================
# LOAD + SELF-DEDUP EXISTING
# =========================

existing_rows = {}

if outfile.exists():
    with open(outfile, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames == FIELDNAMES:
            for row in reader:
                if all(k in row for k in FIELDNAMES):
                    key = (row["game_date"], row["market"], row["home_team"], row["away_team"])
                    existing_rows[key] = row
        else:
            log("WARNING: Invalid header detected. Rebuilding clean.")

# =========================
# UPSERT
# =========================

for new_row in rows:
    key = (new_row["game_date"], new_row["market"], new_row["home_team"], new_row["away_team"])
    existing_rows[key] = new_row

temp_file = outfile.with_suffix(".tmp")
with open(temp_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    for r in existing_rows.values():
        writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

temp_file.replace(outfile)

log(f"SUMMARY: upserted {len(rows)} rows, {errors} errors")
print(f"Wrote {outfile} ({len(rows)} rows processed)")
