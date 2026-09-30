const BASE = 'https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/';
const BASE_DOCS = BASE + 'docs/';
let fraction = 1.0;
let selectedLeague = 'all';
let accountPreferenceCsrfToken = null;
let signedInKellyPreferences = false;
const allPicks = {
  cfb: [],
  nhl: [],
  mlb: [],
  mlb_lineups: [],
  nba: [],
  wnba: [],
  mls: [],
  epl: [],
  laliga: [],
  ligue1: [],
  seriea: [],
  bundesliga: [],
  ufc: [],
};

function toDateStr(v) { return v.replaceAll('-', '_'); }

function initDatePicker() {
  const d = new Date();
  const val = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  const el = document.getElementById('date-picker');
  if (!el.value) el.value = val;
  return el.value;
}

function applyFraction(value) {
  const parsed = parseFloat(value);
  const allowed = [1, 0.5, 0.25];

  if (!allowed.includes(parsed)) return false;

  fraction = parsed;
  document.querySelectorAll('.fraction-btns button').forEach(button => {
    button.classList.toggle(
      'active',
      parseFloat(button.dataset.frac) === parsed
    );
  });
  return true;
}

async function loadKellyAccountPreferences() {
  try {
    const response = await fetch('https://api.sportsmodelhub.com/api/account/preferences/', {
      credentials: 'include',
      headers: { 'Accept': 'application/json' }
    });

    if (!response.ok) return;

    const data = await response.json();
    if (!data.authenticated) return;

    signedInKellyPreferences = true;
    accountPreferenceCsrfToken = data.csrfToken || null;

    const bankrollInput = document.getElementById('bankroll');
    if (bankrollInput && data.bankroll !== null && data.bankroll !== undefined) {
      bankrollInput.value = data.bankroll;
    }

    if (data.kelly_fraction !== null && data.kelly_fraction !== undefined) {
      applyFraction(data.kelly_fraction);
    }

    render();
  } catch {
    // Anonymous/local behavior remains unchanged.
  }
}

async function saveKellyAccountPreferences(patch) {
  if (!signedInKellyPreferences || !accountPreferenceCsrfToken) return;

  try {
    const response = await fetch('https://api.sportsmodelhub.com/api/account/preferences/', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': accountPreferenceCsrfToken
      },
      body: JSON.stringify(patch)
    });

    if (!response.ok) return;

    const data = await response.json();
    if (data.csrfToken) {
      accountPreferenceCsrfToken = data.csrfToken;
    }
  } catch {
    // Keep the current calculator values if persistence is unavailable.
  }
}

document.querySelectorAll('.fraction-btns button').forEach(btn => {
  btn.addEventListener('click', () => {
    if (!applyFraction(btn.dataset.frac)) return;
    render();
    saveKellyAccountPreferences({ kelly_fraction: fraction });
  });
});

const bankrollInput = document.getElementById('bankroll');
bankrollInput.addEventListener('input', render);
bankrollInput.addEventListener('change', () => {
  const value = bankrollInput.value.trim();
  saveKellyAccountPreferences({
    bankroll: value === '' ? null : value
  });
});

document.getElementById('date-picker').addEventListener('change', loadAll);

document.getElementById('league-controls').addEventListener('click', event => {
  const pill = event.target.closest('.league-pill[data-league-key]');
  if (!pill || pill.disabled) return;

  selectedLeague = (pill.dataset.leagueKey || 'all').toLowerCase();

  document
    .querySelectorAll('#league-controls .league-pill[data-league-key]')
    .forEach(button => {
      button.classList.toggle(
        'active',
        (button.dataset.leagueKey || '').toLowerCase() === selectedLeague
      );
    });

  render();
});

function parseCSVLine(line) {
  const out = [];
  let cur = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];

    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (ch === ',' && !inQuotes) {
      out.push(cur.trim());
      cur = '';
      continue;
    }

    cur += ch;
  }

  out.push(cur.trim());
  return out;
}

function cleanCSVCell(v) {
  let s = String(v ?? '').trim();
  if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) s = s.slice(1, -1);
  return s.replaceAll('""', '"').trim();
}

function parseCSV(text) {
  const raw = String(text || '').replace(/^\uFEFF/, '').trim();
  if (!raw) return [];

  const lines = raw.split(/\r?\n/).filter(line => line.trim() !== '');
  if (lines.length < 2) return [];

  const headers = parseCSVLine(lines[0]).map(cleanCSVCell);

  return lines.slice(1).map(line => {
    const vals = parseCSVLine(line).map(cleanCSVCell);
    return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? '']));
  });
}

function resolveSelectFiles(configKey, dateStr) {
  const cfg = window.REPO_CONFIG && window.REPO_CONFIG[configKey];
  if (!cfg || !cfg.selectFiles) return [];

  const resolved = typeof cfg.selectFiles === 'function'
    ? cfg.selectFiles(dateStr)
    : cfg.selectFiles;

  if (Array.isArray(resolved)) return resolved.filter(Boolean);
  return resolved ? [resolved] : [];
}

function resolveSelectUrl(path) {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path;
  return path.startsWith('win/')
    ? BASE_DOCS + path
    : BASE + path.replace(/^\/+/, '');
}

async function loadConfigSelectedRows(configKey, dateStr) {
  const paths = resolveSelectFiles(configKey, dateStr);

  for (const path of paths) {
    try {
      const r = await fetch(resolveSelectUrl(path), { cache: 'no-store' });
      if (!r.ok) continue;
      return parseCSV(await r.text());
    } catch {}
  }

  return [];
}

function normalizeDateValue(value) {
  return String(value || '').trim().replaceAll('-', '_');
}

function rowMatchesConfig(row, configKey, cfg) {
  if (cfg.filterFn) {
    try {
      return cfg.filterFn(row, null, String(configKey).toUpperCase()) !== false;
    } catch {
      return true;
    }
  }

  if (cfg.leagueColumn) {
    return String(row[cfg.leagueColumn] || '').trim().toUpperCase() ===
      String(configKey).toUpperCase();
  }

  return true;
}

function prepareConfigRows(rows, configKey, dateStr) {
  const cfg = window.REPO_CONFIG && window.REPO_CONFIG[configKey];
  if (!cfg) return [];

  const normalize = cfg.normalizeRow
    ? row => cfg.normalizeRow(row)
    : row => row;

  const expanded = rows.flatMap(row => {
    const normalized = normalize(row);

    if (cfg.expandRows) {
      return cfg.expandRows(normalized);
    }

    return [normalized];
  });

  return expanded.filter(row => {
    if (!rowMatchesConfig(row, configKey, cfg)) return false;
    return normalizeDateValue(row.game_date) === dateStr;
  });
}

function americanToDecimal(odds) {
  const n = parseFloat(odds);
  if (isNaN(n) || n === 0) return null;
  return n > 0
    ? 1 + (n / 100)
    : 1 + (100 / Math.abs(n));
}

function calcKellyFromProbability(probability, americanOdds) {
  const p = parseFloat(probability);
  const decimal = americanToDecimal(americanOdds);

  if (isNaN(p) || !decimal || decimal <= 1) return null;

  const b = decimal - 1;
  const q = 1 - p;
  const k = ((b * p) - q) / b;

  return Math.max(0, Math.min(1, k));
}

function calcEvFromProbability(probability, americanOdds) {
  const p = parseFloat(probability);
  const decimal = americanToDecimal(americanOdds);

  if (isNaN(p) || !decimal) return null;
  return (p * decimal) - 1;
}

function firstNumeric(...values) {
  for (const value of values) {
    const n = parseFloat(value);
    if (!isNaN(n)) return n;
  }
  return null;
}

function getGenericOdds(row, sportKey) {
  if (sportKey === 'nba') {
    const nbaOdds = getNBAOdds(row);
    if (nbaOdds !== null && nbaOdds !== undefined && nbaOdds !== '') {
      return nbaOdds;
    }
  }

  return (
    row.bet_odds_american ||
    row.dk_odds_american ||
    row.american_odds ||
    row.take_odds ||
    ''
  );
}

function getGenericKelly(row, sportKey, odds) {
  const direct = firstNumeric(
    row.kelly,
    row.bet_kelly,
    row.bet_final_stake_pct,
    row.bet_stake_pct
  );

  if (direct !== null) return direct;

  if (sportKey === 'nba') {
    const nbaKelly = parseFloat(getNBAKelly(row));
    if (!isNaN(nbaKelly)) return nbaKelly;
  }

  const modelProb = firstNumeric(
    row.model_prob,
    row.bet_model_prob,
    row.bet_adjusted_model_prob
  );

  if (modelProb !== null) {
    return calcKellyFromProbability(modelProb, odds);
  }

  return null;
}

function getGenericEv(row, sportKey, odds) {
  const direct = firstNumeric(
    row.ev,
    row.bet_ev,
    row.selected_ev
  );

  if (direct !== null) return direct;

  if (sportKey === 'nba') {
    const nbaEv = parseFloat(getNBAEV(row));
    if (!isNaN(nbaEv)) return nbaEv;
  }

  const modelProb = firstNumeric(
    row.model_prob,
    row.bet_model_prob,
    row.bet_adjusted_model_prob
  );

  if (modelProb !== null) {
    return calcEvFromProbability(modelProb, odds);
  }

  return null;
}

function buildConfigSideLabel(row, cfg) {
  if (cfg && typeof cfg.buildBetText === 'function') {
    try {
      return cfg.buildBetText(row, row);
    } catch {}
  }

  return buildSideLabel(row);
}

function processConfigPicks(rows, configKey, sportKey, dateStr) {
  const cfg = window.REPO_CONFIG && window.REPO_CONFIG[configKey];
  if (!cfg) return [];

  const prepared = prepareConfigRows(rows, configKey, dateStr);

  return prepared.map(row => {
    const odds = getGenericOdds(row, sportKey);
    const kelly = getGenericKelly(row, sportKey, odds);
    const ev = getGenericEv(row, sportKey, odds);

    if (kelly === null || isNaN(kelly) || kelly <= 0) return null;

    return {
      matchup: `${row.away_team || '—'} @ ${row.home_team || '—'}`,
      time: row.game_time || row.match_time || '',
      market_type: String(row.market_type || row.market || '').toLowerCase(),
      side: buildConfigSideLabel(row, cfg),
      odds: formatOdds(odds),
      ev,
      kelly,
    };
  }).filter(Boolean);
}

function formatOdds(val) {
  const n = parseFloat(val);
  if (isNaN(n)) return '—';
  return n > 0 ? `+${Math.round(n)}` : `${Math.round(n)}`;
}

function formatDollar(n) {
  return '$' + n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function formatPct(n) { return (n * 100).toFixed(1) + '%'; }

function getNBAKelly(row) {
  const mt = (row.market_type || '').toLowerCase();
  const side = (row.bet_side || '').toLowerCase();
  if (mt === 'spread') return side === 'home' ? row.home_spread_kelly : row.away_spread_kelly;
  if (mt === 'moneyline') return side === 'home' ? row.home_ml_kelly : row.away_ml_kelly;
  if (mt === 'total') return side === 'over' ? row.over_kelly : row.under_kelly;
  return null;
}

function getNBAEV(row) {
  const mt = (row.market_type || '').toLowerCase();
  const side = (row.bet_side || '').toLowerCase();
  if (mt === 'spread') return side === 'home' ? row.home_spread_ev : row.away_spread_ev;
  if (mt === 'moneyline') return side === 'home' ? row.home_ml_ev : row.away_ml_ev;
  if (mt === 'total') return side === 'over' ? row.over_ev : row.under_ev;
  return row.selected_ev;
}

function getNBAOdds(row) {
  const mt = (row.market_type || '').toLowerCase();
  const side = (row.bet_side || '').toLowerCase();
  if (mt === 'spread') return side === 'home' ? row.home_dk_spread_american : row.away_dk_spread_american;
  if (mt === 'moneyline') return side === 'home' ? row.home_dk_moneyline_american : row.away_dk_moneyline_american;
  if (mt === 'total') return side === 'over' ? row.dk_total_over_american : row.dk_total_under_american;
  return null;
}

function buildSideLabel(row) {
  const mt = (row.market_type || '').toLowerCase();
  const side = (row.bet_side || '').toLowerCase();
  const line = parseFloat(row.line);
  if (mt === 'total') return `${side.toUpperCase()} ${row.line || ''}`;
  if (['spread','puck_line','run_line'].includes(mt)) {
    const team = side === 'home' ? row.home_team : row.away_team;
    const lineStr = !isNaN(line) ? ` ${line > 0 ? '+' : ''}${line}` : '';
    return `${team}${lineStr}`;
  }
  if (mt === 'moneyline') return side === 'home' ? row.home_team : row.away_team;
  return side;
}

function processPicks(rows, sport, dateStr) {
  return rows.filter(row => (row.game_date || '').trim() === dateStr).map(row => {
    let kelly, ev, odds;
    if (sport === 'nba') {
      kelly = parseFloat(getNBAKelly(row));
      ev = parseFloat(getNBAEV(row));
      odds = getNBAOdds(row);
    } else {
      kelly = parseFloat(row.kelly);
      ev = parseFloat(row.ev);
      odds = row.dk_odds_american;
    }
    if (isNaN(kelly) || kelly <= 0) return null;
    return {
      matchup: `${row.away_team} @ ${row.home_team}`,
      time: row.game_time || '',
      market_type: (row.market_type || '').toLowerCase(),
      side: buildSideLabel(row),
      odds: formatOdds(odds),
      ev: isNaN(ev) ? null : ev,
      kelly,
    };
  }).filter(Boolean);
}

// ─── UFC: Find nearest event ───────────────────────────────────────────────
async function findUFCEventDate() {
  const today = new Date();
  const candidates = [];
  for (let offset = -30; offset <= 30; offset++) {
    const d = new Date(today);
    d.setDate(today.getDate() + offset);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    candidates.push({ date: `${y}_${m}_${day}`, offset: Math.abs(offset) });
  }
  const results = await Promise.all(
    candidates.map(async ({ date, offset }) => {
      const url = `${BASE_DOCS}win/mma/ufc/03_select/${date}_ufc_select.csv`;
      try {
        const r = await fetch(url, { method: 'HEAD' });
        return r.ok ? { date, offset } : null;
      } catch { return null; }
    })
  );
  const valid = results.filter(Boolean).sort((a, b) => a.offset - b.offset);
  return valid.length ? valid[0].date : null;
}

async function loadUFCPicks() {
  const eventDate = await findUFCEventDate();
  const el = document.getElementById('kelly-ufc-event');
  if (!eventDate) {
    if (el) el.textContent = 'No event';
    return [];
  }
  if (el) el.textContent = eventDate.replaceAll('_', '-');

  try {
    const url = `${BASE_DOCS}win/mma/ufc/03_select/${eventDate}_ufc_select.csv`;
    const r = await fetch(url);
    if (!r.ok) return [];
    const rows = parseCSV(await r.text());
    return rows.map(row => {
      const kelly = parseFloat(row.kelly || 0);
      const ev = parseFloat(row.ev || 0);
      if (isNaN(kelly) || kelly <= 0) return null;
      return {
        matchup: `${row.fighter} vs ${row.opponent}`,
        time: '',
        market_type: 'ufc',
        side: `${row.fighter} ${row.moneyline || ''}`,
        odds: row.moneyline || '—',
        ev: isNaN(ev) ? null : ev,
        kelly,
        isUFC: true,
      };
    }).filter(Boolean);
  } catch { return []; }
}

function render() {
  const bankroll = parseFloat(document.getElementById('bankroll').value) || 0;
  const container = document.getElementById('picks-container');
  const allSports = [
    { key: 'cfb', label: 'COLLEGE FOOTBALL' },
    { key: 'nhl', label: 'NHL' },
    { key: 'mlb', label: 'MLB' },
    { key: 'mlb_lineups', label: 'MLB · WITH LINEUPS' },
    { key: 'nba', label: 'NBA' },
    { key: 'wnba', label: 'WNBA' },
    { key: 'mls', label: 'MLS' },
    { key: 'epl', label: 'EPL' },
    { key: 'laliga', label: 'LA LIGA' },
    { key: 'ligue1', label: 'LIGUE 1' },
    { key: 'seriea', label: 'SERIE A' },
    { key: 'bundesliga', label: 'BUNDESLIGA' },
    { key: 'ufc', label: 'UFC' },
  ];

  const sports = selectedLeague === 'all'
    ? allSports
    : allSports.filter(s => s.key === selectedLeague);

  let totalPicks = 0, totalBet = 0, html = '';
  const allPicksList = sports.flatMap(s => allPicks[s.key]);
  const totalKelly = allPicksList.reduce((sum, p) => sum + p.kelly * fraction, 0);
  const scale = totalKelly > 1.0 ? 1.0 / totalKelly : 1.0;

  for (const { key, label } of sports) {
    const picks = allPicks[key];
    totalPicks += picks.length;

    html += `<div class="sport-section">
      <div class="sport-section-header">
        <span class="sport-section-title ${key}">${label}</span>
        <span class="pick-count">${picks.length} PICK${picks.length !== 1 ? 'S' : ''}</span>
      </div>`;

    if (picks.length === 0) {
      html += `<div class="no-picks">No picks${key === 'ufc' ? ' for upcoming event' : ' for this date'}</div>`;
    } else {
      html += `<div class="picks-grid">`;
      for (const p of picks) {
        const betAmt = bankroll > 0 ? bankroll * p.kelly * fraction * scale : 0;
        totalBet += betAmt;
        const amountHtml = bankroll > 0
          ? `<span class="pick-amount">${formatDollar(betAmt)}</span>`
          : `<span class="pick-amount zero">enter bankroll</span>`;

        html += `<div class="pick-card">
          <div class="pick-card-top">
            <span class="pick-market-tag ${p.market_type}">${p.market_type.replace('_',' ')}</span>
            <span class="pick-odds">${p.odds}</span>
          </div>
          <div class="pick-matchup">${p.matchup}${p.time ? ' · ' + p.time : ''}</div>
          <div class="pick-bet">${p.side}</div>
          <div class="pick-footer">
            <span class="pick-ev">EV ${p.ev !== null ? formatPct(p.ev) : '—'}</span>
            <span class="pick-kelly">K ${formatPct(p.kelly)}</span>
            ${amountHtml}
          </div>
        </div>`;
      }
      html += `</div>`;
    }
    html += `</div>`;
  }

  container.innerHTML = html;
  document.getElementById('total-picks').textContent = totalPicks || '—';
  document.getElementById('total-bet').textContent = bankroll > 0 && totalBet > 0 ? formatDollar(totalBet) : '—';
  document.getElementById('total-pct').textContent = bankroll > 0 && totalBet > 0 ? formatPct(totalBet / bankroll) : '—';
}

async function loadAll() {
  const date = toDateStr(initDatePicker());

  const configuredFeeds = [
    { sport: 'cfb',         configKey: 'CFB' },
    { sport: 'nhl',         configKey: 'NHL' },
    { sport: 'mlb',         configKey: 'MLB' },
    { sport: 'mlb_lineups', configKey: 'MLB_LINEUPS' },
    { sport: 'nba',         configKey: 'NBA' },
    { sport: 'wnba',        configKey: 'WNBA' },
    { sport: 'mls',         configKey: 'MLS' },
    { sport: 'epl',         configKey: 'EPL' },
    { sport: 'laliga',      configKey: 'LALIGA' },
    { sport: 'ligue1',      configKey: 'LIGUE1' },
    { sport: 'seriea',      configKey: 'SERIEA' },
    { sport: 'bundesliga',  configKey: 'BUNDESLIGA' },
  ];

  await Promise.all([
    ...configuredFeeds.map(async ({ sport, configKey }) => {
      try {
        const cfg = window.REPO_CONFIG && window.REPO_CONFIG[configKey];

        if (!cfg || cfg.enabled === false) {
          allPicks[sport] = [];
          return;
        }

        const rows = await loadConfigSelectedRows(configKey, date);
        allPicks[sport] = processConfigPicks(
          rows,
          configKey,
          sport === 'mlb_lineups' ? 'mlb' : sport,
          date
        );
      } catch {
        allPicks[sport] = [];
      }
    }),
    loadUFCPicks().then(picks => { allPicks.ufc = picks; }),
  ]);

  render();
}

loadKellyAccountPreferences();
loadAll();

/* KELLY ACCESSIBILITY POLISH 2026-09-29 */
(() => {
  const group = document.querySelector('.fraction-btns');
  if (!group || group.dataset.a11yEnhanced === 'true') return;

  group.dataset.a11yEnhanced = 'true';

  function syncPressedState() {
    group.querySelectorAll('button[data-frac]').forEach(button => {
      button.setAttribute(
        'aria-pressed',
        button.classList.contains('active') ? 'true' : 'false'
      );
    });
  }

  group.addEventListener('click', () => {
    requestAnimationFrame(syncPressedState);
  });

  new MutationObserver(syncPressedState).observe(group, {
    subtree: true,
    attributes: true,
    attributeFilter: ['class']
  });

  syncPressedState();
})();
