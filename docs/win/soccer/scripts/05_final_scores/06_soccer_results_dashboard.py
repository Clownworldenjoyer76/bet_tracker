#!/usr/bin/env python3
# docs/win/soccer/scripts/05_final_scores/06_soccer_results_dashboard.py
#
# Builds one self-contained Soccer Dashboard from the reporting artifacts
# already produced by:
#   03_soccer_results_reports.py
#   05_soccer_model_reports.py
#
# Inputs:
#   docs/win/soccer/05_final_scores/{league}_market_tally.csv
#   docs/win/soccer/05_final_scores/reports/{league}/...
#   docs/win/soccer/05_final_scores/model_evaluation/SOCCER_model_metrics.csv
#   docs/win/soccer/05_final_scores/model_evaluation/SOCCER_model_calibration.csv
#   docs/win/soccer/05_final_scores/model_evaluation/SOCCER_xg_metrics.csv
#
# Output:
#   frontend/soccer_dashboard.html
#
# Log:
#   docs/win/soccer/05_final_scores/errors/06_soccer_results_dashboard.txt

from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
import html
import json
import traceback

import pandas as pd


BASE = Path("docs/win/soccer/05_final_scores")
REPORT_DIR = BASE / "reports"
MODEL_DIR = BASE / "model_evaluation"
OUTPUT_FILE = Path("frontend/soccer_dashboard.html")
ERROR_DIR = BASE / "errors"
LOG_FILE = ERROR_DIR / "06_soccer_results_dashboard.txt"

ERROR_DIR.mkdir(parents=True, exist_ok=True)

LEAGUES = [
    ("mls", "MLS"),
    ("epl", "EPL"),
    ("laliga", "La Liga"),
    ("ligue1", "Ligue 1"),
    ("seriea", "Serie A"),
    ("bundesliga", "Bundesliga"),
]

MARKETS = [
    {
        "key": "match_odds",
        "display": "Match Odds",
        "folder": "match_odds",
        "file_prefix": "match_odds",
        "side_suffix": "home_draw_away",
        "dimensions": ["ev", "kelly", "month", "odds", "model_prob", "win_prob"],
    },
    {
        "key": "btts",
        "display": "BTTS",
        "folder": "btts",
        "file_prefix": "btts",
        "side_suffix": "yes_no",
        "dimensions": ["ev", "kelly", "month", "odds", "model_prob"],
    },
    {
        "key": "total25",
        "display": "Total 2.5",
        "folder": "total_25",
        "file_prefix": "total_25",
        "side_suffix": "over_under",
        "dimensions": ["ev", "kelly", "month", "odds", "model_prob"],
    },
    {
        "key": "total35",
        "display": "Total 3.5",
        "folder": "total_35",
        "file_prefix": "total_35",
        "side_suffix": "over_under",
        "dimensions": ["ev", "kelly", "month", "odds", "model_prob"],
    },
]

MARKET_LABELS = {
    "match_odds": "Match Odds",
    "btts": "BTTS",
    "total25": "Total 2.5",
    "total35": "Total 3.5",
}

RUN_STARTED = datetime.now(UTC)
WARNING_COUNT = 0
ERROR_COUNT = 0
INPUT_FILE_COUNT = 0
INPUT_ROW_COUNT = 0
OUTPUT_FILE_COUNT = 0
OUTPUT_ROW_COUNT = 0
INPUT_FILES_SEEN: set[str] = set()

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== 06_soccer_results_dashboard ===\n")
    f.write(f"START_TIMESTAMP_UTC: {RUN_STARTED.isoformat()}\n")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def log(level: str, message: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{_now()} | {level} | {message}\n")


def warn(message: str) -> None:
    global WARNING_COUNT
    WARNING_COUNT += 1
    log("WARNING", message)


def error(message: str) -> None:
    global ERROR_COUNT
    ERROR_COUNT += 1
    log("ERROR", message)


def log_input(path: Path, rows: int, exists: bool) -> None:
    global INPUT_FILE_COUNT, INPUT_ROW_COUNT
    key = str(path)
    if key in INPUT_FILES_SEEN:
        return
    INPUT_FILES_SEEN.add(key)
    INPUT_FILE_COUNT += 1
    INPUT_ROW_COUNT += rows
    log("INFO", f"INPUT | file={path} | exists={int(exists)} | rows={rows}")


def log_output(path: Path, rows: int, bytes_written: int) -> None:
    global OUTPUT_FILE_COUNT, OUTPUT_ROW_COUNT
    OUTPUT_FILE_COUNT += 1
    OUTPUT_ROW_COUNT += rows
    log("INFO", f"OUTPUT | file={path} | rows={rows} | bytes={bytes_written}")


def finish(status: str) -> None:
    ended = datetime.now(UTC)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"INPUT_SUMMARY | files={INPUT_FILE_COUNT} | rows={INPUT_ROW_COUNT}\n")
        f.write(f"OUTPUT_SUMMARY | files={OUTPUT_FILE_COUNT} | rows={OUTPUT_ROW_COUNT}\n")
        f.write(f"WARNING_COUNT: {WARNING_COUNT}\n")
        f.write(f"ERROR_COUNT: {ERROR_COUNT}\n")
        f.write(f"END_TIMESTAMP_UTC: {ended.isoformat()}\n")
        f.write(f"STATUS: {status}\n")


def safe_read(path: Path, *, required: bool = False) -> pd.DataFrame:
    if not path.exists():
        log_input(path, 0, False)
        if required:
            warn(f"Required dashboard input missing: {path}")
        else:
            log("INFO", f"Optional dashboard input missing: {path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(path)
        log_input(path, len(df), True)
        return df
    except Exception as exc:
        log_input(path, 0, True)
        warn(f"Unable to read dashboard input {path}: {type(exc).__name__}: {exc}")
        return pd.DataFrame()


def json_safe_value(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def df_to_records(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    records = []
    for row in df.to_dict(orient="records"):
        records.append({k: json_safe_value(v) for k, v in row.items()})
    return records


def aggregate_tally(tally: pd.DataFrame) -> tuple[dict, list[dict]]:
    if tally.empty:
        return {}, []

    work = tally.copy()
    for col in ["Win", "Loss", "Push", "Total", "Sample_Count"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0)

    wins = int(work["Win"].sum()) if "Win" in work.columns else 0
    losses = int(work["Loss"].sum()) if "Loss" in work.columns else 0
    pushes = int(work["Push"].sum()) if "Push" in work.columns else 0
    total = wins + losses + pushes
    win_pct = wins / (wins + losses) if (wins + losses) else None

    headline = {
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "total": total,
        "win_pct": win_pct,
    }

    by_market = []
    if "market" in work.columns:
        for market, part in work.groupby("market", dropna=False):
            w = int(part["Win"].sum()) if "Win" in part.columns else 0
            l = int(part["Loss"].sum()) if "Loss" in part.columns else 0
            p = int(part["Push"].sum()) if "Push" in part.columns else 0
            t = w + l + p
            by_market.append(
                {
                    "market": str(market),
                    "market_display": MARKET_LABELS.get(str(market), str(market)),
                    "Win": w,
                    "Loss": l,
                    "Push": p,
                    "Total": t,
                    "Sample_Count": t,
                    "Win_Pct": (w / (w + l)) if (w + l) else None,
                }
            )

    return headline, by_market


def load_model_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metrics = safe_read(MODEL_DIR / "SOCCER_model_metrics.csv")
    calibration = safe_read(MODEL_DIR / "SOCCER_model_calibration.csv")
    xg = safe_read(MODEL_DIR / "SOCCER_xg_metrics.csv")
    return metrics, calibration, xg


def filter_league_rows(df: pd.DataFrame, league: str) -> pd.DataFrame:
    if df.empty or "league" not in df.columns:
        return pd.DataFrame()
    scope_mask = (
        df["scope"].astype(str).str.strip().str.lower().eq("league")
        if "scope" in df.columns
        else pd.Series(True, index=df.index)
    )
    league_mask = df["league"].astype(str).str.strip().str.lower().eq(league)
    return df.loc[scope_mask & league_mask].copy()


def collect_league_data(
    league: str,
    display: str,
    model_metrics: pd.DataFrame,
    calibration: pd.DataFrame,
    xg_metrics: pd.DataFrame,
) -> dict:
    tally = safe_read(BASE / f"{league}_market_tally.csv", required=True)
    headline, by_market = aggregate_tally(tally)

    data = {
        "league": league,
        "display": display,
        "headline": headline,
        "tally": df_to_records(tally),
        "by_market": by_market,
        "model_metrics": df_to_records(filter_league_rows(model_metrics, league)),
        "calibration": df_to_records(filter_league_rows(calibration, league)),
        "xg_metrics": df_to_records(filter_league_rows(xg_metrics, league)),
        "markets": {},
    }

    for spec in MARKETS:
        market_dir = REPORT_DIR / league / spec["folder"]
        market_data = {
            "display": spec["display"],
            "by": {},
            "by_side": {},
        }

        for dim in spec["dimensions"]:
            base_name = f"{league}_{spec['file_prefix']}_by_{dim}"
            overall = market_dir / f"{base_name}.csv"
            by_side = market_dir / f"{base_name}_{spec['side_suffix']}_summary.csv"

            overall_df = safe_read(overall)
            side_df = safe_read(by_side)

            if not overall_df.empty or not side_df.empty:
                market_data["by"][dim] = df_to_records(overall_df)
                market_data["by_side"][dim] = df_to_records(side_df)

        data["markets"][spec["key"]] = market_data

    return data


CSS = r"""
:root {
  --bg: #0e1117;
  --panel: #161b22;
  --panel-2: #1c232c;
  --text: #e6edf3;
  --muted: #8b949e;
  --accent: #58a6ff;
  --good: #3fb950;
  --bad: #f85149;
  --border: #30363d;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
header {
  padding: 18px 24px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 12px;
}
header h1 { margin: 0; font-size: 20px; }
header .ts { color: var(--muted); font-size: 12px; }
.league-bar {
  padding: 10px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--panel);
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 10;
}
.league-bar .lbl {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-right: 6px;
}
.league-btn, .tab {
  background: var(--panel-2);
  border: 1px solid var(--border);
  color: var(--text);
  cursor: pointer;
}
.league-btn {
  padding: 6px 14px;
  border-radius: 4px;
  font-size: 13px;
}
.league-btn.active {
  background: var(--accent);
  color: #0e1117;
  border-color: var(--accent);
  font-weight: 600;
}
main {
  padding: 18px 24px;
  max-width: 1500px;
  margin: 0 auto;
}
.league-section { display: none; }
.league-section.active { display: block; }
h2 {
  font-size: 16px;
  margin: 24px 0 8px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 4px;
}
.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin: 12px 0 4px;
}
.kpi {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
}
.kpi .label {
  color: var(--muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .05em;
}
.kpi .value {
  font-size: 22px;
  margin-top: 4px;
  font-weight: 600;
}
.good { color: var(--good); }
.bad { color: var(--bad); }
.tabs {
  display: flex;
  gap: 4px;
  margin: 16px 0 0;
  flex-wrap: wrap;
}
.tab {
  padding: 6px 12px;
  border-radius: 6px 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}
.tab.active {
  background: var(--panel-2);
  color: var(--text);
  border-bottom-color: var(--panel-2);
}
.tab-body {
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-top: none;
  padding: 14px;
  border-radius: 0 6px 6px 6px;
}
.controls {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 10px;
}
.controls label {
  color: var(--muted);
  font-size: 12px;
}
.controls select {
  background: var(--panel);
  color: var(--text);
  border: 1px solid var(--border);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th, td {
  padding: 6px 8px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
th {
  color: var(--muted);
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: .05em;
  cursor: pointer;
  user-select: none;
  position: sticky;
  top: 0;
  background: var(--panel-2);
}
td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.scroll {
  max-height: 60vh;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 6px;
}
.muted { color: var(--muted); }
footer {
  color: var(--muted);
  font-size: 11px;
  padding: 16px 24px;
}
"""

JS = r"""
function fmtPct(v) {
  if (v == null || isNaN(v)) return '';
  return (Number(v) * 100).toFixed(2) + '%';
}
function fmtNum(v, d) {
  if (v == null || isNaN(v)) return '';
  return Number(v).toFixed(d);
}
function fmtInt(v) {
  if (v == null || isNaN(v)) return '';
  return Number(v).toLocaleString();
}
function signedClass(v) {
  if (v == null || isNaN(v)) return '';
  return Number(v) > 0 ? 'good' : (Number(v) < 0 ? 'bad' : '');
}

function showTab(host, key) {
  host.querySelectorAll(':scope > .tabs .tab').forEach(el => {
    el.classList.toggle('active', el.dataset.key === key);
  });
  host.querySelectorAll(':scope > .tab-body > .tab-panel').forEach(el => {
    el.style.display = el.dataset.key === key ? '' : 'none';
  });
}

function renderTable(data, columns, container) {
  if (!data || data.length === 0) {
    container.innerHTML = '<div class="muted">No rows available.</div>';
    return;
  }

  const wrap = document.createElement('div');
  wrap.className = 'scroll';
  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  const tbody = document.createElement('tbody');

  let sortCol = null;
  let sortDir = 'desc';

  columns.forEach(col => {
    const th = document.createElement('th');
    th.textContent = col.label;
    th.onclick = () => {
      if (sortCol === col.key) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
      else {
        sortCol = col.key;
        sortDir = 'desc';
      }
      drawRows();
    };
    headRow.appendChild(th);
  });

  thead.appendChild(headRow);

  function drawRows() {
    const rows = data.slice();
    if (sortCol) {
      rows.sort((a, b) => {
        const av = a[sortCol];
        const bv = b[sortCol];
        if (av == null) return 1;
        if (bv == null) return -1;
        if (!isNaN(Number(av)) && !isNaN(Number(bv))) {
          return sortDir === 'asc' ? Number(av) - Number(bv) : Number(bv) - Number(av);
        }
        return sortDir === 'asc'
          ? String(av).localeCompare(String(bv))
          : String(bv).localeCompare(String(av));
      });
    }

    tbody.innerHTML = '';
    rows.forEach(row => {
      const tr = document.createElement('tr');
      columns.forEach(col => {
        const td = document.createElement('td');
        const v = row[col.key];

        if (col.fmt === 'int') {
          td.classList.add('num');
          td.textContent = fmtInt(v);
        } else if (col.fmt === 'pct') {
          td.classList.add('num');
          td.textContent = fmtPct(v);
        } else if (col.fmt === 'num') {
          td.classList.add('num');
          td.textContent = fmtNum(v, col.decimals == null ? 3 : col.decimals);
          if (col.signed) {
            const cls = signedClass(v);
            if (cls) td.classList.add(cls);
          }
        } else {
          td.textContent = v == null ? '' : String(v);
        }

        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  drawRows();
  table.appendChild(thead);
  table.appendChild(tbody);
  wrap.appendChild(table);
  container.innerHTML = '';
  container.appendChild(wrap);
}

const RESULT_COLUMNS = [
  { key: 'bucket', label: 'Bucket' },
  { key: 'Win', label: 'W', fmt: 'int' },
  { key: 'Loss', label: 'L', fmt: 'int' },
  { key: 'Push', label: 'P', fmt: 'int' },
  { key: 'Total', label: 'Total', fmt: 'int' },
  { key: 'Sample_Count', label: 'Sample', fmt: 'int' },
  { key: 'Win_Pct', label: 'Win %', fmt: 'pct' },
];

const RESULT_SIDE_COLUMNS = [
  { key: 'side', label: 'Side' },
  ...RESULT_COLUMNS,
];

const MODEL_COLUMNS = [
  { key: 'model', label: 'Model' },
  { key: 'sample_count', label: 'Sample', fmt: 'int' },
  { key: 'brier_score', label: 'Brier', fmt: 'num', decimals: 4 },
  { key: 'log_loss', label: 'Log Loss', fmt: 'num', decimals: 4 },
  { key: 'rps', label: 'RPS', fmt: 'num', decimals: 4 },
];

const XG_COLUMNS = [
  { key: 'sample_count', label: 'Sample', fmt: 'int' },
  { key: 'home_xg_mae', label: 'Home xG MAE', fmt: 'num', decimals: 3 },
  { key: 'home_xg_rmse', label: 'Home xG RMSE', fmt: 'num', decimals: 3 },
  { key: 'home_xg_bias', label: 'Home xG Bias', fmt: 'num', decimals: 3, signed: true },
  { key: 'away_xg_mae', label: 'Away xG MAE', fmt: 'num', decimals: 3 },
  { key: 'away_xg_rmse', label: 'Away xG RMSE', fmt: 'num', decimals: 3 },
  { key: 'away_xg_bias', label: 'Away xG Bias', fmt: 'num', decimals: 3, signed: true },
  { key: 'total_xg_mae', label: 'Total xG MAE', fmt: 'num', decimals: 3 },
  { key: 'total_xg_rmse', label: 'Total xG RMSE', fmt: 'num', decimals: 3 },
  { key: 'total_xg_bias', label: 'Total xG Bias', fmt: 'num', decimals: 3, signed: true },
];

const CAL_COLUMNS = [
  { key: 'model', label: 'Model' },
  { key: 'outcome', label: 'Outcome' },
  { key: 'bucket', label: 'Bucket' },
  { key: 'sample_count', label: 'Sample', fmt: 'int' },
  { key: 'mean_predicted_probability', label: 'Mean Pred', fmt: 'pct' },
  { key: 'observed_rate', label: 'Observed', fmt: 'pct' },
  { key: 'calibration_gap', label: 'Gap', fmt: 'num', decimals: 4, signed: true },
];

function selectLeague(league) {
  document.querySelectorAll('.league-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.league === league);
  });
  document.querySelectorAll('.league-section').forEach(section => {
    section.classList.toggle('active', section.dataset.league === league);
  });
  try {
    localStorage.setItem('soccer_dash_league', league);
  } catch (e) {}
}

function buildModelArea(section, data) {
  const host = section.querySelector('.model-area');

  renderTable(
    data.model_metrics || [],
    MODEL_COLUMNS,
    host.querySelector('.model-core')
  );

  renderTable(
    data.xg_metrics || [],
    XG_COLUMNS,
    host.querySelector('.model-xg')
  );

  const calibrationRows = data.calibration || [];
  const calibrationHost = host.querySelector('.model-calibration');

  if (!calibrationRows.length) {
    calibrationHost.innerHTML = '<div class="muted">No calibration rows available.</div>';
  } else {
    const models = [...new Set(calibrationRows.map(r => r.model).filter(Boolean))].sort();
    const outcomes = [...new Set(calibrationRows.map(r => r.outcome).filter(Boolean))].sort();

    calibrationHost.innerHTML =
      '<div class="controls">' +
        '<label>Model: <select class="cal-model"><option value="ALL">All</option>' +
          models.map(v => '<option value="' + v + '">' + v + '</option>').join('') +
        '</select></label>' +
        '<label>Outcome: <select class="cal-outcome"><option value="ALL">All</option>' +
          outcomes.map(v => '<option value="' + v + '">' + v + '</option>').join('') +
        '</select></label>' +
      '</div>' +
      '<div class="cal-table"></div>';

    const modelSel = calibrationHost.querySelector('.cal-model');
    const outcomeSel = calibrationHost.querySelector('.cal-outcome');
    const tableHost = calibrationHost.querySelector('.cal-table');

    const refreshCalibration = () => {
      const filtered = calibrationRows.filter(row =>
        (modelSel.value === 'ALL' || String(row.model) === modelSel.value) &&
        (outcomeSel.value === 'ALL' || String(row.outcome) === outcomeSel.value)
      );
      renderTable(filtered, CAL_COLUMNS, tableHost);
    };

    modelSel.onchange = refreshCalibration;
    outcomeSel.onchange = refreshCalibration;
    refreshCalibration();
  }

  host.querySelectorAll(':scope > .tabs .tab').forEach(tab => {
    tab.onclick = () => showTab(host, tab.dataset.key);
  });
}

function buildMarketArea(section, data) {
  const host = section.querySelector('.market-area');

  Object.entries(data.markets || {}).forEach(([key, market]) => {
    const panel = host.querySelector('.panel-' + key);
    if (!panel) return;

    const dimensions = Object.keys(market.by || {});
    if (!dimensions.length) {
      panel.innerHTML = '<div class="muted">No report rows available for this market.</div>';
      return;
    }

    panel.innerHTML =
      '<div class="controls">' +
        '<label>Dimension: <select class="dim-select">' +
          dimensions.map(dim => '<option value="' + dim + '">' + dim + '</option>').join('') +
        '</select></label>' +
        '<label>View: <select class="view-select">' +
          '<option value="overall">Overall</option>' +
          '<option value="side">Split by side</option>' +
        '</select></label>' +
      '</div>' +
      '<div class="market-table"></div>';

    const dimSel = panel.querySelector('.dim-select');
    const viewSel = panel.querySelector('.view-select');
    const tableHost = panel.querySelector('.market-table');

    const refresh = () => {
      const dim = dimSel.value;
      const sideView = viewSel.value === 'side';
      const rows = sideView
        ? ((market.by_side || {})[dim] || [])
        : ((market.by || {})[dim] || []);
      renderTable(
        rows,
        sideView ? RESULT_SIDE_COLUMNS : RESULT_COLUMNS,
        tableHost
      );
    };

    dimSel.onchange = refresh;
    viewSel.onchange = refresh;
    refresh();
  });

  host.querySelectorAll(':scope > .tabs .tab').forEach(tab => {
    tab.onclick = () => showTab(host, tab.dataset.key);
  });
}

function buildLeagueSection(league, data) {
  const section = document.querySelector(
    '.league-section[data-league="' + league + '"]'
  );
  if (!section) return;

  const h = data.headline || {};
  const kpi = (label, value, fmt) => {
    let display = '—';
    if (value != null && !(typeof value === 'number' && isNaN(value))) {
      if (fmt === 'pct') display = fmtPct(value);
      else if (fmt === 'int') display = fmtInt(value);
      else display = String(value);
    }
    return '<div class="kpi"><div class="label">' + label +
      '</div><div class="value">' + display + '</div></div>';
  };

  section.querySelector('.kpis').innerHTML = [
    kpi('Bets', h.total, 'int'),
    kpi('Wins', h.wins, 'int'),
    kpi('Losses', h.losses, 'int'),
    kpi('Pushes', h.pushes, 'int'),
    kpi('Win %', h.win_pct, 'pct'),
  ].join('');

  renderTable(
    data.by_market || [],
    [
      { key: 'market_display', label: 'Market' },
      { key: 'Win', label: 'W', fmt: 'int' },
      { key: 'Loss', label: 'L', fmt: 'int' },
      { key: 'Push', label: 'P', fmt: 'int' },
      { key: 'Total', label: 'Total', fmt: 'int' },
      { key: 'Win_Pct', label: 'Win %', fmt: 'pct' },
    ],
    section.querySelector('.by-market')
  );

  renderTable(
    data.tally || [],
    [
      { key: 'market', label: 'Market' },
      { key: 'market_type', label: 'Side' },
      { key: 'Win', label: 'W', fmt: 'int' },
      { key: 'Loss', label: 'L', fmt: 'int' },
      { key: 'Push', label: 'P', fmt: 'int' },
      { key: 'Total', label: 'Total', fmt: 'int' },
      { key: 'Win_Pct', label: 'Win %', fmt: 'pct' },
    ],
    section.querySelector('.side-tally')
  );

  buildModelArea(section, data);
  buildMarketArea(section, data);
}
"""


def league_section_html(league: str, display: str) -> str:
    market_tabs = "\n".join(
        f'<button class="tab{" active" if i == 0 else ""}" data-key="{spec["key"]}">{html.escape(spec["display"])}</button>'
        for i, spec in enumerate(MARKETS)
    )
    market_panels = "\n".join(
        f'<div class="tab-panel panel-{spec["key"]}" data-key="{spec["key"]}"'
        f'{" style=\"display:none\"" if i else ""}></div>'
        for i, spec in enumerate(MARKETS)
    )

    return f"""
<section class="league-section" data-league="{league}">
  <h2>{html.escape(display)} — Headline</h2>
  <div class="kpis"></div>

  <h2>By Market</h2>
  <div class="by-market"></div>

  <h2>By Market + Side</h2>
  <div class="side-tally"></div>

  <h2>Model Quality</h2>
  <div class="model-area">
    <div class="tabs">
      <button class="tab active" data-key="core">Core Metrics</button>
      <button class="tab" data-key="xg">xG Metrics</button>
      <button class="tab" data-key="calibration">Calibration</button>
    </div>
    <div class="tab-body">
      <div class="tab-panel model-core" data-key="core"></div>
      <div class="tab-panel model-xg" data-key="xg" style="display:none"></div>
      <div class="tab-panel model-calibration" data-key="calibration" style="display:none"></div>
    </div>
  </div>

  <h2>Per Market Drilldown</h2>
  <div class="market-area">
    <div class="tabs">
      {market_tabs}
    </div>
    <div class="tab-body">
      {market_panels}
    </div>
  </div>
</section>
"""


def build_dashboard() -> str:
    ts = datetime.now(UTC).isoformat(timespec="seconds")
    metrics, calibration, xg = load_model_tables()

    payloads = {
        league: collect_league_data(
            league,
            display,
            metrics,
            calibration,
            xg,
        )
        for league, display in LEAGUES
    }

    payload_json = json.dumps(payloads, ensure_ascii=False, default=str)

    league_buttons = "\n".join(
        f'<button class="league-btn{" active" if i == 0 else ""}" '
        f'data-league="{league}" onclick="selectLeague(\'{league}\')">{html.escape(display)}</button>'
        for i, (league, display) in enumerate(LEAGUES)
    )

    sections = "\n".join(
        league_section_html(league, display)
        for league, display in LEAGUES
    )

    first_league = LEAGUES[0][0]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Soccer Dashboard</title>
<style>
{CSS}
.league-section[data-league="{first_league}"] {{ display: block; }}
</style>
</head>
<body>
<header>
  <h1>Soccer Dashboard</h1>
  <span class="ts">Built {html.escape(ts)} UTC</span>
</header>

<div class="league-bar">
  <span class="lbl">League:</span>
  {league_buttons}
</div>

<main>
{sections}
</main>

<footer>
  Click column headers to sort. Built from CSVs in
  <code>{html.escape(str(BASE))}</code>.
</footer>

<script>
{JS}

const ALL_DATA = {payload_json};

document.addEventListener('DOMContentLoaded', () => {{
  Object.keys(ALL_DATA).forEach(league => {{
    buildLeagueSection(league, ALL_DATA[league]);
  }});

  let initial = '{first_league}';
  try {{
    const stored = localStorage.getItem('soccer_dash_league');
    if (stored && ALL_DATA[stored]) initial = stored;
  }} catch (e) {{}}

  selectLeague(initial);
}});
</script>
</body>
</html>
"""


def run() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    page = build_dashboard()
    OUTPUT_FILE.write_text(page, encoding="utf-8")

    rows = page.count("\n") + 1
    bytes_written = len(page.encode("utf-8"))
    log_output(OUTPUT_FILE, rows, bytes_written)
    log("INFO", f"dashboard -> {OUTPUT_FILE}")


def main() -> None:
    status = "FAILED"
    try:
        run()
        status = "SUCCESS"
    except Exception as exc:
        error(f"Unhandled exception: {type(exc).__name__}: {exc}")
        trace = traceback.format_exc()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(trace)
            if not trace.endswith("\n"):
                f.write("\n")
        raise
    finally:
        finish(status)


if __name__ == "__main__":
    main()
