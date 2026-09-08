#!/usr/bin/env python3
# docs/win/basketball/scripts/05_final_scores/04_basketball_results_dashboard.py
#
# Builds the Basketball master dashboard plus NBA, NCAAM, and WNBA dashboards.
# The master includes All, NBA, NCAAM, and WNBA league views.
#
# Inputs (per league nba, ncaam, wnba):
#   docs/win/basketball/05_final_scores/{league}_summary_grand_total.csv
#   docs/win/basketball/05_final_scores/{league}_summary_overall.csv
#   docs/win/basketball/05_final_scores/reports/{league}/{moneyline,spread,total,overview}/*.csv
#
# Outputs:
#   frontend/basketball_dashboard.html
#   frontend/nba_dashboard.html
#   frontend/ncaam_dashboard.html
#   frontend/wnba_dashboard.html
#
# Log:
#   docs/win/basketball/errors/05_final_scores/04_basketball_results_dashboard.txt
#
# No server required - open the file in a browser.

from datetime import datetime, UTC
from pathlib import Path
import html
import json
import traceback

import pandas as pd

LEAGUES = ["nba", "ncaam", "wnba"]
MARKETS = ["moneyline", "spread", "total"]

LEAGUE_DISPLAY = {
    "nba": "NBA",
    "ncaam": "NCAAM",
    "wnba": "WNBA",
    "all": "All",
}

BASE        = Path("docs/win/basketball/05_final_scores")
REPORT_DIR  = BASE / "reports"
HISTORICAL_ROOT = BASE / "seasons"
OUTPUT_FILE = Path("frontend/basketball_dashboard.html")
LEAGUE_OUTPUTS = {
    "nba": Path("frontend/nba_dashboard.html"),
    "ncaam": Path("frontend/ncaam_dashboard.html"),
    "wnba": Path("frontend/wnba_dashboard.html"),
}
LEAGUE_TITLES = {
    "nba": "NBA Analytics",
    "ncaam": "NCAAM Analytics",
    "wnba": "WNBA Analytics",
}
ERROR_DIR   = Path("docs/win/basketball/errors/05_final_scores")
LOG_FILE    = ERROR_DIR / "04_basketball_results_dashboard.txt"

ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOGGING
# =========================

RUN_STARTED = datetime.now(UTC)
WARNING_COUNT = 0
ERROR_COUNT = 0
INPUT_FILE_COUNT = 0
INPUT_ROW_COUNT = 0
OUTPUT_FILE_COUNT = 0
OUTPUT_ROW_COUNT = 0
INPUT_FILES_SEEN: set[str] = set()

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== 04_basketball_results_dashboard ===\n")
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



# =========================
# CSS
# =========================

CSS = """
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
  --table-border: #46515e;
}
* { box-sizing: border-box; }
html, body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  margin: 0;
  padding: 0;
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

.selector-bar {
  padding: 10px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--panel);
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}
.league-bar {
  position: sticky;
  top: 0;
  z-index: 10;
}
.selector-bar .lbl {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-right: 6px;
}
.league-btn, .season-btn {
  background: var(--panel-2);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 6px 14px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.league-btn.active, .season-btn.active {
  background: var(--accent);
  color: #0e1117;
  border-color: var(--accent);
  font-weight: 600;
}
main { padding: 18px 24px; max-width: 1500px; margin: 0 auto; }
.league-section { display: none; }
.league-section.active { display: block; }

h2 {
  font-size: 16px;
  margin: 24px 0 8px 0;
  color: var(--text);
  border-bottom: 1px solid var(--border);
  padding-bottom: 4px;
}
h3 {
  font-size: 13px;
  margin: 14px 0 6px 0;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin: 12px 0 4px 0;
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
  letter-spacing: 0.05em;
}
.kpi .value { font-size: 22px; margin-top: 4px; font-weight: 600; }
.kpi .value.good { color: var(--good); }
.kpi .value.bad { color: var(--bad); }

.tabs { display: flex; gap: 4px; margin: 16px 0 0 0; flex-wrap: wrap; }
.tab {
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 6px 12px;
  border-radius: 6px 6px 0 0;
  cursor: pointer;
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
.controls label { color: var(--muted); font-size: 12px; }
.controls select {
  background: var(--panel);
  color: var(--text);
  border: 1px solid var(--border);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 13px;
}

table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td {
  padding: 7px 9px;
  text-align: center;
  border: 1px solid var(--table-border);
  white-space: nowrap;
  vertical-align: middle;
}
th {
  color: var(--muted);
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.05em;
  cursor: pointer;
  user-select: none;
  position: sticky;
  top: 0;
  background: var(--panel-2);
}
th .arrow { opacity: 0.4; margin-left: 4px; }
th.sorted .arrow { opacity: 1; color: var(--accent); }
td.num { text-align: center; font-variant-numeric: tabular-nums; }

.pos { color: var(--good); }
.neg { color: var(--bad); }
.muted { color: var(--muted); }
.scroll {
  max-height: 60vh;
  overflow: auto;
  border: 1px solid var(--table-border);
  border-radius: 6px;
}

td.win-pct-strong {
  background: rgba(63,185,80,.24);
  color: #7ee787;
  font-weight: 700;
}
td.win-pct-green {
  background: rgba(63,185,80,.16);
  color: #56d364;
  font-weight: 600;
}
td.win-pct-light {
  background: rgba(63,185,80,.09);
  color: #8ddb8c;
  font-weight: 600;
}
td.win-pct-neutral {
  background: rgba(139,148,158,.09);
  color: #c9d1d9;
}
td.win-pct-red {
  background: rgba(248,81,73,.14);
  color: #ff7b72;
  font-weight: 600;
}
"""


# =========================
# JS
# =========================

JS = """
let ACTIVE_SEASON = null;

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
function classForSigned(v) {
  if (v == null || isNaN(v)) return '';
  return Number(v) > 0 ? 'pos' : (Number(v) < 0 ? 'neg' : '');
}
function winPctClass(v) {
  if (v == null || isNaN(v)) return '';
  const pct = Number(v);
  if (pct >= 0.80) return 'win-pct-strong';
  if (pct >= 0.70) return 'win-pct-green';
  if (pct >= 0.60) return 'win-pct-light';
  if (pct >= 0.50) return 'win-pct-neutral';
  return 'win-pct-red';
}

function showTab(host, key) {
  host.querySelectorAll(':scope > .tabs .tab').forEach(el => {
    el.classList.toggle('active', el.dataset.key === key);
  });
  host.querySelectorAll(':scope > .tab-body > .tab-panel').forEach(el => {
    el.style.display = (el.dataset.key === key ? '' : 'none');
  });
}

function renderTable(data, columns, container) {
  if (!data || data.length === 0) {
    container.innerHTML = '<div class="muted">No rows.</div>';
    return;
  }

  const wrap = document.createElement('div');
  wrap.className = 'scroll';

  const tbl = document.createElement('table');
  const thead = document.createElement('thead');
  const trh = document.createElement('tr');
  let sortCol = null;
  let sortDir = 'desc';

  columns.forEach((c) => {
    const th = document.createElement('th');
    th.innerHTML = c.label + ' <span class="arrow">&#9662;</span>';
    th.onclick = () => {
      if (sortCol === c.key) sortDir = (sortDir === 'asc' ? 'desc' : 'asc');
      else {
        sortCol = c.key;
        sortDir = 'desc';
      }
      sortAndRender();
      thead.querySelectorAll('th').forEach(h => h.classList.remove('sorted'));
      th.classList.add('sorted');
    };
    trh.appendChild(th);
  });

  thead.appendChild(trh);
  const tbody = document.createElement('tbody');

  function sortAndRender() {
    const sorted = data.slice();

    if (sortCol) {
      sorted.sort((a, b) => {
        const av = a[sortCol];
        const bv = b[sortCol];
        if (av == null) return 1;
        if (bv == null) return -1;
        if (!isNaN(Number(av)) && !isNaN(Number(bv))) {
          return sortDir === 'asc'
            ? Number(av) - Number(bv)
            : Number(bv) - Number(av);
        }
        return sortDir === 'asc'
          ? String(av).localeCompare(String(bv))
          : String(bv).localeCompare(String(av));
      });
    }

    tbody.innerHTML = '';

    sorted.forEach(row => {
      const tr = document.createElement('tr');

      columns.forEach(c => {
        const td = document.createElement('td');
        const v = row[c.key];
        let cls = '';

        if (c.fmt === 'int') {
          td.classList.add('num');
          td.textContent = fmtInt(v);
        } else if (c.fmt === 'pct') {
          td.classList.add('num');
          td.textContent = fmtPct(v);
          if (String(c.key).toLowerCase() === 'win_pct') {
            const winClass = winPctClass(v);
            if (winClass) td.classList.add(winClass);
          }
          cls = c.color ? classForSigned(v) : '';
        } else if (c.fmt === 'num') {
          td.classList.add('num');
          td.textContent = fmtNum(v, c.decimals != null ? c.decimals : 2);
          cls = c.color ? classForSigned(v) : '';
        } else if (c.fmt === 'roi') {
          td.classList.add('num');
          td.textContent = fmtPct(v);
          cls = classForSigned(v);
        } else {
          td.textContent = (v == null ? '' : String(v));
        }

        if (cls) td.classList.add(cls);
        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });
  }

  sortAndRender();
  tbl.appendChild(thead);
  tbl.appendChild(tbody);
  wrap.appendChild(tbl);
  container.innerHTML = '';
  container.appendChild(wrap);
}

const STD_COLUMNS = [
  { key: 'bucket', label: 'Bucket' },
  { key: 'bets', label: 'Bets', fmt: 'int' },
  { key: 'wins', label: 'W', fmt: 'int' },
  { key: 'losses', label: 'L', fmt: 'int' },
  { key: 'pushes', label: 'P', fmt: 'int' },
  { key: 'win_pct', label: 'Win %', fmt: 'pct' },
  { key: 'units_flat', label: 'Units (flat)', fmt: 'num', decimals: 2, color: true },
  { key: 'roi_flat', label: 'ROI flat', fmt: 'roi' },
  { key: 'units_kelly', label: 'Units (Kelly)', fmt: 'num', decimals: 4, color: true },
  { key: 'roi_kelly', label: 'ROI Kelly', fmt: 'roi' },
  { key: 'avg_ev', label: 'Avg EV', fmt: 'pct' },
  { key: 'avg_edge_vs_market_pp', label: 'Avg edge (pp)', fmt: 'num', decimals: 2 },
  { key: 'avg_kelly_pct', label: 'Avg Kelly', fmt: 'pct' },
  { key: 'avg_model_prob', label: 'Avg model p', fmt: 'pct' },
  { key: 'avg_odds_american', label: 'Avg odds', fmt: 'num', decimals: 0 },
];

const STD_COLUMNS_WITH_SIDE = [
  { key: 'bucket', label: 'Side' },
  ...STD_COLUMNS.filter(c => c.key !== 'bucket'),
];

const QUALITY_COLUMNS = [
  { key: 'scope', label: 'Scope' },
  { key: 'market_type', label: 'Market' },
  { key: 'model_source', label: 'Model source' },
  { key: 'model_version', label: 'Model version' },
  { key: 'rows', label: 'Rows', fmt: 'int' },
  { key: 'probability_n', label: 'Prob N', fmt: 'int' },
  { key: 'brier_score', label: 'Brier', fmt: 'num', decimals: 4 },
  { key: 'log_loss', label: 'Log loss', fmt: 'num', decimals: 4 },
  { key: 'calibration_error', label: 'Calibration err', fmt: 'num', decimals: 4 },
  { key: 'margin_n', label: 'Margin N', fmt: 'int' },
  { key: 'margin_mae', label: 'Margin MAE', fmt: 'num', decimals: 3 },
  { key: 'margin_rmse', label: 'Margin RMSE', fmt: 'num', decimals: 3 },
  { key: 'total_n', label: 'Total N', fmt: 'int' },
  { key: 'total_mae', label: 'Total MAE', fmt: 'num', decimals: 3 },
  { key: 'total_rmse', label: 'Total RMSE', fmt: 'num', decimals: 3 },
  { key: 'clv_n', label: 'CLV N', fmt: 'int' },
  { key: 'avg_clv', label: 'Avg CLV', fmt: 'num', decimals: 3, color: true },
  { key: 'clv_units', label: 'CLV units' },
  { key: 'prob_disagreement_n', label: 'Prob dis N', fmt: 'int' },
  { key: 'avg_model_vs_market_prob_pp', label: 'Model-market p (pp)', fmt: 'num', decimals: 3, color: true },
  { key: 'mean_abs_model_vs_market_prob_pp', label: 'Abs p gap (pp)', fmt: 'num', decimals: 3 },
  { key: 'line_disagreement_n', label: 'Line dis N', fmt: 'int' },
  { key: 'avg_model_vs_market_line', label: 'Model-market line', fmt: 'num', decimals: 3, color: true },
  { key: 'mean_abs_model_vs_market_line', label: 'Abs line gap', fmt: 'num', decimals: 3 },
];

function buildQualityArea(section, data) {
  const area = section.querySelector('.quality-area');
  const rows = data.quality || [];

  if (!rows.length) {
    area.innerHTML = '<div class="muted">No model-quality rows available.</div>';
    return;
  }

  const values = (key) => [...new Set(
    rows
      .map(r => r[key])
      .filter(v =>
        v !== null &&
        v !== undefined &&
        String(v).trim() !== '' &&
        String(v).trim().toUpperCase() !== 'ALL'
      )
  )].sort();

  const markets = values('market_type');
  const sources = values('model_source');
  const versions = values('model_version');
  const scopes = values('scope');

  const optionHtml = (items) =>
    '<option value="ALL">All</option>' +
    items.map(v =>
      '<option value="' +
      String(v).replace(/"/g, '&quot;') +
      '">' + v + '</option>'
    ).join('');

  area.innerHTML =
    '<div class="controls">' +
      '<label>Scope: <select class="quality-scope">' + optionHtml(scopes) + '</select></label>' +
      '<label>Market: <select class="quality-market">' + optionHtml(markets) + '</select></label>' +
      '<label>Source: <select class="quality-source">' + optionHtml(sources) + '</select></label>' +
      '<label>Version: <select class="quality-version">' + optionHtml(versions) + '</select></label>' +
    '</div>' +
    '<div class="quality-table"></div>';

  const scopeSel = area.querySelector('.quality-scope');
  const marketSel = area.querySelector('.quality-market');
  const sourceSel = area.querySelector('.quality-source');
  const versionSel = area.querySelector('.quality-version');
  const table = area.querySelector('.quality-table');

  const refresh = () => {
    const filtered = rows.filter(r =>
      (scopeSel.value === 'ALL' || String(r.scope) === scopeSel.value) &&
      (marketSel.value === 'ALL' || String(r.market_type) === marketSel.value) &&
      (sourceSel.value === 'ALL' || String(r.model_source) === sourceSel.value) &&
      (versionSel.value === 'ALL' || String(r.model_version) === versionSel.value)
    );

    const columns = data.is_all
      ? [{ key: 'league', label: 'League' }, ...QUALITY_COLUMNS]
      : QUALITY_COLUMNS;

    renderTable(filtered, columns, table);
  };

  [scopeSel, marketSel, sourceSel, versionSel].forEach(el => {
    el.onchange = refresh;
  });

  refresh();
}

function selectLeague(lg) {
  document.querySelectorAll('.league-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.league === lg);
  });
  document.querySelectorAll('.league-section').forEach(s => {
    s.classList.toggle('active', s.dataset.league === lg);
  });

  const selectedButton = document.querySelector(
    '.league-btn[data-league="' + lg + '"]'
  );
  const display = selectedButton
    ? selectedButton.dataset.display
    : (lg === 'all' ? 'All' : String(lg).toUpperCase());

  const dashboardTitle = document.getElementById('dashboard-title');
  if (dashboardTitle) {
    dashboardTitle.textContent = display + ' Analytics';
  }

  try {
    localStorage.setItem('basketball_dash_league', lg);
  } catch (e) {}
}

function selectSeason(season) {
  if (!ALL_DATA[season]) return;

  ACTIVE_SEASON = season;

  document.querySelectorAll('.season-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.season === season);
  });

  const seasonData = ALL_DATA[season].leagues || {};
  Object.keys(seasonData).forEach(lg => {
    buildLeagueSection(lg, seasonData[lg]);
  });

  try {
    localStorage.setItem('basketball_dash_season', season);
  } catch (e) {}
}

function buildLeagueSection(lg, data) {
  const section = document.querySelector(
    '.league-section[data-league="' + lg + '"]'
  );
  if (!section) return;

  const gt = data.grand_total || {};

  const kpiHtml = (label, value, fmt) => {
    let disp = 'N/A';
    let cls = '';

    if (
      value !== null &&
      value !== undefined &&
      !(typeof value === 'number' && isNaN(value))
    ) {
      if (fmt === 'pct') {
        disp = (Number(value) * 100).toFixed(2) + '%';
        cls = Number(value) > 0 ? 'good' : (Number(value) < 0 ? 'bad' : '');
      } else if (fmt === 'int') {
        disp = Number(value).toLocaleString();
      } else if (fmt === 'signed') {
        disp = (Number(value) >= 0 ? '+' : '') + Number(value).toFixed(2);
        cls = Number(value) > 0 ? 'good' : (Number(value) < 0 ? 'bad' : '');
      } else {
        disp = String(value);
      }
    }

    return '<div class="kpi"><div class="label">' + label +
      '</div><div class="value ' + cls + '">' + disp + '</div></div>';
  };

  section.querySelector('.kpis').innerHTML = [
    kpiHtml('Bets', gt.bets, 'int'),
    kpiHtml('Wins', gt.wins, 'int'),
    kpiHtml('Losses', gt.losses, 'int'),
    kpiHtml('Pushes', gt.pushes, 'int'),
    kpiHtml('Win %', gt.win_pct, 'pct'),
    kpiHtml('Units (flat)', gt.units_flat, 'signed'),
    kpiHtml('ROI flat', gt.roi_flat, 'pct'),
    kpiHtml('Units (Kelly)', gt.units_kelly, 'signed'),
    kpiHtml('ROI Kelly', gt.roi_kelly, 'pct'),
  ].join('');

  let byMarketCols = [
    { key: 'market_type', label: 'Market' },
    { key: 'Win', label: 'W', fmt: 'int' },
    { key: 'Loss', label: 'L', fmt: 'int' },
    { key: 'Push', label: 'P', fmt: 'int' },
    { key: 'Total', label: 'Total', fmt: 'int' },
    { key: 'Win_Pct', label: 'Win %', fmt: 'pct' },
  ];

  if (data.is_all) {
    byMarketCols = [{ key: 'league', label: 'League' }, ...byMarketCols];
  }

  renderTable(
    data.by_market_summary || [],
    byMarketCols,
    section.querySelector('.by-market-summary')
  );

  buildQualityArea(section, data);

  ['moneyline', 'spread', 'total'].forEach(mt => {
    const wrap = section.querySelector('.panel-' + mt);
    const md = (data.markets && data.markets[mt]) || { by: {}, by_side: {} };

    const dimensions = Object.keys(md.by || {}).filter(dim =>
      ((md.by || {})[dim] || []).length ||
      ((md.by_side || {})[dim] || []).length
    );

    if (!dimensions.length) {
      wrap.innerHTML = '<div class="muted">No report rows available for this market.</div>';
      return;
    }

    wrap.innerHTML =
      '<div class="controls">' +
      '<label>Dimension: <select class="dim-select">' +
      dimensions.map(d =>
        '<option value="' + d + '">' + d.replaceAll('_', ' ') + '</option>'
      ).join('') +
      '</select></label>' +
      '<label>View: <select class="view-select">' +
      '<option value="overall">Overall</option>' +
      '<option value="side">Split by side</option>' +
      '</select></label>' +
      '</div>' +
      '<div class="market-table"></div>';

    const dimSel = wrap.querySelector('.dim-select');
    const viewSel = wrap.querySelector('.view-select');
    const tbl = wrap.querySelector('.market-table');

    function refresh() {
      const dim = dimSel.value;
      const sideView = viewSel.value === 'side';
      const rows = sideView
        ? ((md.by_side || {})[dim] || [])
        : ((md.by || {})[dim] || []);

      let cols = sideView ? STD_COLUMNS_WITH_SIDE : STD_COLUMNS;

      if (data.is_all) {
        cols = [{ key: 'league', label: 'League' }, ...cols];
      }

      renderTable(rows, cols, tbl);
    }

    dimSel.onchange = refresh;
    viewSel.onchange = refresh;
    refresh();
  });

  const marketArea = section.querySelector('.market-area');
  marketArea.querySelectorAll(':scope > .tabs .tab').forEach(t => {
    t.onclick = () => showTab(marketArea, t.dataset.key);
  });

  let overviewMarketCols = [
    { key: 'market_type', label: 'Market' },
    ...STD_COLUMNS.filter(c => c.key !== 'bucket'),
  ];

  let overviewSideCols = [
    { key: 'bucket', label: 'Side' },
    ...STD_COLUMNS.filter(c => c.key !== 'bucket'),
  ];

  let overviewDateCols = [
    { key: 'bucket', label: 'Date' },
    ...STD_COLUMNS.filter(c => c.key !== 'bucket'),
  ];

  if (data.is_all) {
    overviewMarketCols = [{ key: 'league', label: 'League' }, ...overviewMarketCols];
    overviewSideCols = [{ key: 'league', label: 'League' }, ...overviewSideCols];
    overviewDateCols = [{ key: 'league', label: 'League' }, ...overviewDateCols];
  }

  renderTable(
    (data.overview || {}).by_market || [],
    overviewMarketCols,
    section.querySelector('.overview-market')
  );

  renderTable(
    (data.overview || {}).by_side_group || [],
    overviewSideCols,
    section.querySelector('.overview-side')
  );

  renderTable(
    (data.overview || {}).by_date || [],
    overviewDateCols,
    section.querySelector('.overview-date')
  );

  const overviewArea = section.querySelector('.overview-area');
  overviewArea.querySelectorAll(':scope > .tabs .tab').forEach(t => {
    t.onclick = () => showTab(overviewArea, t.dataset.key);
  });
}
"""


# =========================
# DATA LOADING
# =========================

def df_to_records(df: pd.DataFrame) -> list:
    if df.empty:
        return []
    df = df.copy()
    df = df.where(pd.notna(df), None)
    return df.to_dict(orient="records")


def safe_read(path: Path, *, required: bool = False) -> pd.DataFrame:
    if not path.exists():
        log_input(path, 0, exists=False)
        if required:
            warn(f"Required dashboard input missing: {path}")
        else:
            log("INFO", f"Optional dashboard input missing: {path}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(path)
        log_input(path, len(df), exists=True)
        return df
    except Exception as exc:
        log_input(path, 0, exists=True)
        warn(f"Unable to read dashboard input {path}: {type(exc).__name__}: {exc}")
        return pd.DataFrame()


def first_row_dict(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    rec = df.iloc[0].to_dict()
    return {
        k: (None if (isinstance(v, float) and pd.isna(v)) else v)
        for k, v in rec.items()
    }


def side_group_records(df: pd.DataFrame) -> list[dict]:
    records = df_to_records(df)

    for row in records:
        current = row.get("bucket")
        if current not in (None, ""):
            continue

        for candidate in ("side_group", "side", "SIDE", "variable"):
            value = row.get(candidate)
            if value not in (None, ""):
                row["bucket"] = value
                break

    return records


def season_display_name(name: str) -> str:
    return name.replace("_", "-").strip()


def discover_seasons() -> list[tuple[str, str, Path]]:
    seasons = [("current", "Current", BASE)]

    if HISTORICAL_ROOT.exists():
        historical = sorted(
            [path for path in HISTORICAL_ROOT.iterdir() if path.is_dir()],
            key=lambda path: path.name,
            reverse=True,
        )
        for path in historical:
            seasons.append((path.name, season_display_name(path.name), path))

    return seasons


def collect_league_data(league: str, base_root: Path = BASE) -> dict:
    report_dir = base_root / "reports"

    data = {
        "league": league.upper(),
        "display": LEAGUE_DISPLAY[league],
        "grand_total": first_row_dict(
            safe_read(
                base_root / f"{league}_summary_grand_total.csv",
                required=(base_root == BASE),
            )
        ),
        "by_market_summary": df_to_records(
            safe_read(
                base_root / f"{league}_summary_overall.csv",
                required=(base_root == BASE),
            )
        ),
        "quality": df_to_records(
            safe_read(
                report_dir / league / "quality" / f"{league}_model_quality_all.csv"
            )
        ),
        "overview": {
            "by_market": df_to_records(
                safe_read(
                    report_dir / league / "overview" / f"{league}_summary_by_market.csv"
                )
            ),
            "by_side_group": side_group_records(
                safe_read(
                    report_dir / league / "overview" / f"{league}_summary_by_side_group.csv"
                )
            ),
            "by_date": df_to_records(
                safe_read(
                    report_dir / league / "overview" / f"{league}_summary_by_date.csv"
                )
            ),
        },
        "markets": {},
    }

    for mt in MARKETS:
        mt_dir = report_dir / league / mt
        market_data = {"by": {}, "by_side": {}}

        for label in (
            "ev",
            "kelly",
            "odds",
            "win_prob",
            "edge_vs_market",
            "dow",
            "month",
        ):
            no_side = mt_dir / f"{league}_{mt}_by_{label}.csv"
            with_side_sfx = "over_under" if mt == "total" else "home_away"
            with_side = (
                mt_dir
                / f"{league}_{mt}_by_{label}_{with_side_sfx}_summary.csv"
            )
            market_data["by"][label] = df_to_records(safe_read(no_side))
            market_data["by_side"][label] = side_group_records(safe_read(with_side))

        if mt in ("spread", "total"):
            with_side_sfx = "over_under" if mt == "total" else "home_away"
            market_data["by"]["side"] = df_to_records(
                safe_read(mt_dir / f"{league}_{mt}_by_side.csv")
            )
            market_data["by_side"]["side"] = side_group_records(
                safe_read(
                    mt_dir
                    / f"{league}_{mt}_by_side_{with_side_sfx}_summary.csv"
                )
            )

        if mt == "total":
            market_data["by"]["total_range"] = df_to_records(
                safe_read(mt_dir / f"{league}_{mt}_by_total_range.csv")
            )
            market_data["by_side"]["total_range"] = side_group_records(
                safe_read(
                    mt_dir
                    / f"{league}_{mt}_by_total_range_over_under_summary.csv"
                )
            )

        data["markets"][mt] = market_data

    return data


def _rows_with_league(rows: list[dict], league: str) -> list[dict]:
    display = LEAGUE_DISPLAY[league]
    return [{"league": display, **row} for row in rows]


def collect_all_data(league_payloads: dict[str, dict]) -> dict:
    grand_rows = [
        payload.get("grand_total") or {}
        for payload in league_payloads.values()
        if payload.get("grand_total")
    ]

    def num(row: dict, key: str) -> float:
        try:
            value = row.get(key)
            if value is None or pd.isna(value):
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    bets = int(sum(num(row, "bets") for row in grand_rows))
    wins = int(sum(num(row, "wins") for row in grand_rows))
    losses = int(sum(num(row, "losses") for row in grand_rows))
    pushes = int(sum(num(row, "pushes") for row in grand_rows))
    total = wins + losses + pushes
    units_flat = sum(num(row, "units_flat") for row in grand_rows)
    units_kelly = sum(num(row, "units_kelly") for row in grand_rows)

    grand_total = {
        "league": "ALL",
        "bets": bets,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "total": total,
        "win_pct": wins / (wins + losses) if (wins + losses) else None,
        "units_flat": units_flat if grand_rows else None,
        "roi_flat": units_flat / bets if bets else None,
        "units_kelly": units_kelly if grand_rows else None,
        "roi_kelly": None,
    }

    by_market_summary = []
    quality = []
    overview = {
        "by_market": [],
        "by_side_group": [],
        "by_date": [],
    }
    markets = {
        market: {"by": {}, "by_side": {}}
        for market in MARKETS
    }

    for league, payload in league_payloads.items():
        by_market_summary.extend(
            _rows_with_league(payload.get("by_market_summary") or [], league)
        )
        quality.extend(
            _rows_with_league(payload.get("quality") or [], league)
        )

        source_overview = payload.get("overview") or {}
        for key in overview:
            overview[key].extend(
                _rows_with_league(source_overview.get(key) or [], league)
            )

        for market in MARKETS:
            source_market = (payload.get("markets") or {}).get(
                market,
                {"by": {}, "by_side": {}},
            )

            for view in ("by", "by_side"):
                for dimension, rows in (source_market.get(view) or {}).items():
                    markets[market][view].setdefault(dimension, [])
                    markets[market][view][dimension].extend(
                        _rows_with_league(rows or [], league)
                    )

    return {
        "league": "ALL",
        "display": "All",
        "is_all": True,
        "grand_total": grand_total,
        "by_market_summary": by_market_summary,
        "quality": quality,
        "overview": overview,
        "markets": markets,
    }


# =========================
# HTML BUILD
# =========================

def league_section_html(league: str, display: str) -> str:
    return f"""
<section class="league-section" data-league="{html.escape(league)}">
  <h2>{html.escape(display)} Analytics</h2>
  <div class="kpis"></div>

  <h2>By Market</h2>
  <div class="by-market-summary"></div>

  <h2>Model Quality</h2>
  <div class="quality-area"></div>

  <h2>Per Market Drilldown</h2>
  <div class="market-area">
    <div class="tabs">
      <div class="tab active" data-key="moneyline">Moneyline</div>
      <div class="tab" data-key="spread">Spread</div>
      <div class="tab" data-key="total">Total</div>
    </div>
    <div class="tab-body">
      <div class="tab-panel panel-moneyline" data-key="moneyline"></div>
      <div class="tab-panel panel-spread" data-key="spread" style="display:none"></div>
      <div class="tab-panel panel-total" data-key="total" style="display:none"></div>
    </div>
  </div>

  <h2>Overview</h2>
  <div class="overview-area">
    <div class="tabs">
      <div class="tab active" data-key="market">By market</div>
      <div class="tab" data-key="side">By side group</div>
      <div class="tab" data-key="date">By date</div>
    </div>
    <div class="tab-body">
      <div class="tab-panel overview-market" data-key="market"></div>
      <div class="tab-panel overview-side" data-key="side" style="display:none"></div>
      <div class="tab-panel overview-date" data-key="date" style="display:none"></div>
    </div>
  </div>
</section>
"""


def build_dashboard(
    league_defs: list[str] | None = None,
    *,
    include_all: bool = False,
) -> str:
    league_defs = list(LEAGUES if league_defs is None else league_defs)
    season_defs = discover_seasons()

    all_payloads: dict[str, dict] = {}

    for season_key, season_label, season_root in season_defs:
        league_payloads = {
            league: collect_league_data(league, season_root)
            for league in league_defs
        }

        page_payloads = dict(league_payloads)
        if include_all:
            page_payloads = {
                "all": collect_all_data(league_payloads),
                **league_payloads,
            }

        all_payloads[season_key] = {
            "label": season_label,
            "leagues": page_payloads,
        }

    payload_json = json.dumps(all_payloads, default=str)

    nav_leagues = (
        [("all", "All")]
        if include_all
        else []
    ) + [
        (league, LEAGUE_DISPLAY[league])
        for league in league_defs
    ]

    league_buttons = "\n".join(
        f'<button class="league-btn{" active" if i == 0 else ""}" '
        f'data-league="{html.escape(league)}" '
        f'data-display="{html.escape(display)}" '
        f'onclick="selectLeague(\'{html.escape(league)}\')">'
        f'{html.escape(display)}</button>'
        for i, (league, display) in enumerate(nav_leagues)
    )

    sections = "\n".join(
        league_section_html(league, display)
        for league, display in nav_leagues
    )

    season_buttons = "\n".join(
        f'<button class="season-btn{" active" if i == 0 else ""}" '
        f'data-season="{html.escape(season_key)}" '
        f'onclick="selectSeason(\'{html.escape(season_key)}\')">'
        f'{html.escape(season_label)}</button>'
        for i, (season_key, season_label, _) in enumerate(season_defs)
    )

    season_bar_style = (
        ' style="display:none"'
        if len(season_defs) <= 1
        else ""
    )

    first_season = season_defs[0][0]
    first_league = nav_leagues[0][0]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Basketball Analytics</title>
<link rel="stylesheet" href="assets/css/matstheme.css">
<style>{CSS}</style>
</head>
<body>
<div id="nav-placeholder"></div>

<header>
  <h1 id="dashboard-title">Basketball Analytics</h1>
</header>

<div class="selector-bar season-bar"{season_bar_style}>
  <span class="lbl">Season:</span>
  {season_buttons}
</div>

<div class="selector-bar league-bar">
  <span class="lbl">League:</span>
  {league_buttons}
</div>

<main>
{sections}
</main>

<script src="assets/js/shared/nav.js"></script>
<script>
{JS}

const ALL_DATA = {payload_json};

document.addEventListener('DOMContentLoaded', () => {{
  let initialSeason = '{html.escape(first_season)}';
  try {{
    const storedSeason = localStorage.getItem('basketball_dash_season');
    if (storedSeason && ALL_DATA[storedSeason]) initialSeason = storedSeason;
  }} catch (e) {{}}

  selectSeason(initialSeason);

  let initialLeague = '{html.escape(first_league)}';
  try {{
    const storedLeague = localStorage.getItem('basketball_dash_league');
    if (
      storedLeague &&
      ALL_DATA[initialSeason] &&
      ALL_DATA[initialSeason].leagues &&
      ALL_DATA[initialSeason].leagues[storedLeague]
    ) {{
      initialLeague = storedLeague;
    }}
  }} catch (e) {{}}

  selectLeague(initialLeague);
}});
</script>
</body>
</html>"""


def run() -> None:
    # ANALYTICS_MULTI_OUTPUT
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    outputs: list[tuple[Path, str]] = []

    master_page = build_dashboard(LEAGUES, include_all=True)
    outputs.append((OUTPUT_FILE, master_page))

    for league in LEAGUES:
        page = build_dashboard([league], include_all=False)
        title = LEAGUE_TITLES[league]
        page = (
            page
            .replace(
                "<title>Basketball Analytics</title>",
                f"<title>{title}</title>",
                1,
            )
            .replace(
                '<h1 id="dashboard-title">Basketball Analytics</h1>',
                f'<h1 id="dashboard-title">{title}</h1>',
                1,
            )
            .replace(
                "</style>",
                "\n.league-bar{display:none!important}\n</style>",
                1,
            )
        )
        outputs.append((LEAGUE_OUTPUTS[league], page))

    for output_path, page in outputs:
        output_path.write_text(page, encoding="utf-8")
        rows = page.count("\n") + 1
        bytes_written = len(page.encode("utf-8"))
        log_output(output_path, rows, bytes_written)
        log("INFO", f"dashboard -> {output_path}")


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
