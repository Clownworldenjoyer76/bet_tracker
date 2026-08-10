(() => {

const dateInput    = document.getElementById("p-date");
const statusEl     = document.getElementById("status");
const gamesEl      = document.getElementById("games");
const modal        = document.getElementById("modal");
const modalContent = document.getElementById("modal-content");

if (!dateInput || !statusEl || !gamesEl) return;
if (!window.REPO_CONFIG) { statusEl.textContent = "Missing config."; return; }

// ─── Date ────────────────────────────────────────────────────────────────────

function todayLocal() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function toUnderscore(s) {
  return (s || "").trim().replaceAll("-", "_");
}

function normDate(v) {
  return toUnderscore(v || "");
}

// ─── CSV ─────────────────────────────────────────────────────────────────────

function cleanCSVCell(v) {
  let s = (v ?? "").trim();

  if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) {
    s = s.slice(1, -1);
  }

  return s.replaceAll('""', '"').trim();
}

function parseCSVLine(line) {
  const out = [];
  let cur = "";
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

    if (ch === "," && !inQuotes) {
      out.push(cur);
      cur = "";
      continue;
    }

    cur += ch;
  }

  out.push(cur);
  return out;
}

function parseCSV(text) {
  const raw = (text || "").replace(/^\uFEFF/, "").trim();
  if (!raw) return [];

  const lines = raw.split(/\r?\n/).filter(line => line.trim() !== "");
  if (lines.length < 2) return [];

  const headers = parseCSVLine(lines[0]).map(cleanCSVCell);

  return lines.slice(1).map(line => {
    const vals = parseCSVLine(line).map(cleanCSVCell);
    const obj = {};
    headers.forEach((h, i) => { obj[h] = vals[i] ?? ""; });
    return obj;
  });
}

async function fetchCSV(path) {
  try {
    const r = await fetch(path);
    if (!r.ok) return { ok: false, rows: [] };
    return { ok: true, rows: parseCSV(await r.text()), source: path };
  } catch {
    return { ok: false, rows: [] };
  }
}

function resolvePaths(value, dateFormatted) {
  if (!value) return [];

  const resolved = typeof value === "function"
    ? value(dateFormatted)
    : value;

  if (Array.isArray(resolved)) return resolved.filter(Boolean);
  if (resolved) return [resolved];
  return [];
}

// Try paths in order. First one that loads wins; the rest are skipped.
// This gives us "new path, fall back to old" semantics for league migrations
// without ever loading the same data twice.
// If every path fails, log the full list so the next silent breakage is visible.
async function fetchMultiCSV(paths) {
  const list = Array.isArray(paths) ? paths.filter(Boolean) : [];

  for (const p of list) {
    const res = await fetchCSV(p);
    if (res.ok) return { ok: true, rows: res.rows, source: p };
  }

  if (list.length) console.warn("[picks] No data file loaded. Tried:", list);
  return { ok: false, rows: [] };
}

// ─── Row Matching ─────────────────────────────────────────────────────────────

function rowMatchesLeague(row, cfg, target) {
  if (cfg.filterFn) return true;
  if (cfg.leagueColumn) return (row[cfg.leagueColumn] || "").trim().toUpperCase() === target;
  if (cfg.marketColumn) return (row[cfg.marketColumn] || "").trim().toUpperCase() === target;
  const league = (row.league || "").trim().toUpperCase();
  const market = (row.market || "").trim().toUpperCase();
  return league === target || market === target;
}

function filterRows(allRows, dateFormatted, leagueName, cfg) {
  const target = leagueName.toUpperCase();

  const leagueRows = allRows.filter(r => {
    if (cfg.filterFn) return cfg.filterFn(r, null, target);
    return rowMatchesLeague(r, cfg, target);
  });

  const dated = leagueRows.filter(r => normDate(r.game_date) === dateFormatted);
  if (dated.length > 0) return { rows: dated, stale: false, fromDate: dateFormatted };

  if (leagueRows.length === 0) return { rows: [], stale: false, fromDate: null };
  leagueRows.sort((a, b) => normDate(b.game_date).localeCompare(normDate(a.game_date)));
  const latestDate = normDate(leagueRows[0].game_date);
  const fallback = leagueRows.filter(r => normDate(r.game_date) === latestDate);
  return { rows: fallback, stale: true, fromDate: latestDate };
}

// ─── Join Keys ────────────────────────────────────────────────────────────────

function makeKey(row, cfg) {
  if (cfg && cfg.joinKey) {
    return (row[cfg.joinKey] || "").trim();
  }
  return `${(row.game_date || "").trim()}|${(row.home_team || "").trim()}|${(row.away_team || "").trim()}`;
}

function buildMap(rows, cfg) {
  const map = {};
  rows.forEach(r => {
    const k = makeKey(r, cfg);
    if (k) map[k] = r;
  });
  return map;
}

function mergeRows(selectRows, predMap, bookMap, cfg) {
  return selectRows.map(sel => {
    const key  = makeKey(sel, cfg);
    const pred = predMap[key] || {};
    const book = bookMap[key] || {};
    // Layer pred → book → sel, but DON'T let an empty select value
    // overwrite a real value from book/pred. This happens when a select
    // row is for one market type (e.g. a total pick) and the moneyline /
    // spread columns on that same row are blank — without this guard we'd
    // wipe out the book file's real ML/spread odds during the merge.
    const merged = { ...pred, ...book };
    Object.keys(sel).forEach(k => {
      const v = sel[k];
      if (v !== "" && v !== null && v !== undefined) merged[k] = v;
    });
    merged.__key = key;
    if (!merged.game_time && pred.game_time) merged.game_time = pred.game_time;
    return merged;
  });
}

// ─── Bet Text ─────────────────────────────────────────────────────────────────

function formatLine(line) {
  const n = parseFloat(line);
  if (isNaN(n)) return line;
  return n > 0 ? "+" + n : String(n);
}

function cleanOdds(odds) {
  if (odds === null || odds === undefined || odds === "") return "";
  const n = parseFloat(odds);
  if (isNaN(n)) return String(odds);
  return n > 0 ? "+" + n : String(n);
}

function wrapOdds(odds) {
  const cleaned = cleanOdds(odds);
  return cleaned ? ` (${cleaned})` : "";
}

function buildBetText(p, r, cfg) {
  if (cfg.buildBetText) return cfg.buildBetText(p, r);

  const market = (p.market_type || "").toLowerCase();
  const side   = (p.bet_side    || "").toLowerCase();
  const line   = p.bet_line || p.line || "";
  const odds   = p.bet_odds_american || p.dk_odds_american || p.take_odds || "";

  let label = "";
  let american = odds;

  if (side === "home")  label = r.home_team || "Home";
  if (side === "away")  label = r.away_team || "Away";
  if (side === "over")  label = "Over";
  if (side === "under") label = "Under";

  if (["spread", "puck_line", "run_line"].includes(market)) {
    if (side === "home") american = p.bet_odds_american || p.dk_odds_american || p.take_odds || r.home_dk_spread_american || r.home_dk_puck_line_american || r.home_dk_run_line_american || odds;
    if (side === "away") american = p.bet_odds_american || p.dk_odds_american || p.take_odds || r.away_dk_spread_american || r.away_dk_puck_line_american || r.away_dk_run_line_american || odds;
    return `${label} ${formatLine(line)}${wrapOdds(american)}`.trim();
  }

  if (market === "total") {
    if (side === "over")  american = p.bet_odds_american || p.dk_odds_american || p.take_odds || r.dk_total_over_american  || odds;
    if (side === "under") american = p.bet_odds_american || p.dk_odds_american || p.take_odds || r.dk_total_under_american || odds;
    return `${label} ${formatLine(line)}${wrapOdds(american)}`.trim();
  }

  if (market === "moneyline") {
    if (side === "home") american = p.bet_odds_american || p.dk_odds_american || p.take_odds || r.home_dk_moneyline_american || odds;
    if (side === "away") american = p.bet_odds_american || p.dk_odds_american || p.take_odds || r.away_dk_moneyline_american || odds;
    return `${label}${wrapOdds(american)}`.trim();
  }

  return `${side} ${formatLine(line)} ${cleanOdds(odds)}`.trim();
}

// ─── Edge / EV / Kelly ────────────────────────────────────────────────────────

// Centralized accessors so column-name drift doesn't silently zero these out
// in one place but not another. Order matters: prefer the per-pick fields the
// select files actually write today, then fall back to legacy names.
function getEv(p)    { return parseFloat(p.ev    || p.bet_ev    || p.selected_ev || 0); }
function getKelly(p) { return parseFloat(p.kelly || p.bet_kelly || 0); }

function extractEdge(p) {
  // Select files write a per-pick edge for the chosen side; that's the
  // single source of truth. Fall back to ev only if it isn't present.
  if (p.edge !== undefined && p.edge !== "") {
    return parseFloat(p.edge);
  }
  if (p.bet_edge_vs_market !== undefined && p.bet_edge_vs_market !== "") {
    return parseFloat(p.bet_edge_vs_market);
  }
  return parseFloat(p.ev || p.selected_ev || 0);
}

function statDecimals(cfg, fallback) {
  const n = parseInt(cfg && cfg.statDecimals, 10);
  return Number.isFinite(n) ? n : fallback;
}

function formatPercentValue(n, decimals, signed) {
  const v = parseFloat(n);
  if (isNaN(v)) return "—";
  const prefix = signed && v >= 0 ? "+" : "";
  return `${prefix}${(v * 100).toFixed(decimals)}%`;
}

function edgeDots(edge, cfg) {
  const filled = edge >= 0.15 ? 5 : edge >= 0.10 ? 4 : edge >= 0.07 ? 3 : edge >= 0.04 ? 2 : edge >= 0.001 ? 1 : 0;
  const cls    = ["e0","e1","e2","e3","e4","e5"][filled];
  const dots   = "●".repeat(filled) + "○".repeat(5 - filled);
  const dec    = statDecimals(cfg, 1);
  return `<span class="edge-dots ${cls}" title="Edge ${(edge*100).toFixed(dec)}%">${dots}</span>`;
}

// ─── Time Sort ────────────────────────────────────────────────────────────────

function parseTime(t) {
  if (!t) return 9999;

  const s = String(t).trim();

  const ampm = s.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (ampm) {
    let h = parseInt(ampm[1], 10);
    const min = parseInt(ampm[2], 10);
    if (ampm[3].toUpperCase() === "PM" && h !== 12) h += 12;
    if (ampm[3].toUpperCase() === "AM" && h === 12) h = 0;
    return h * 60 + min;
  }

  const military = s.match(/^(\d{1,2}):(\d{2})/);
  if (military) {
    const h = parseInt(military[1], 10);
    const min = parseInt(military[2], 10);
    if (!isNaN(h) && !isNaN(min)) return h * 60 + min;
  }

  return 9999;
}

// ─── Modal ────────────────────────────────────────────────────────────────────

function openModal(html) {
  if (!modalContent || !modal) return;
  modalContent.innerHTML = html;
  modal.classList.add("open");
}

function buildModalHtml(r, picks, cfg) {
  // Soccer: simpler modal — no projections / spreads / totals exist for these markets.
  if (cfg.isSoccer) {
    const picksHtml = picks.map(p => {
      const betText = buildBetText(p, r, cfg);
      const ev      = getEv(p);
      const kelly   = getKelly(p);
      const edge    = extractEdge(p);
      const dec     = statDecimals(cfg, 2);
      return `
        <div class="modal-pick-row">
          <div class="modal-bet">${betText}</div>
          <div class="modal-pick-stats">
            <span class="modal-ev ${ev >= 0 ? "pos" : "neg"}">${formatPercentValue(ev, dec, true)} EV</span>
            <span class="modal-kelly">Kelly ${formatPercentValue(kelly, dec, false)}</span>
            ${edgeDots(edge, cfg)}
          </div>
        </div>`;
    }).join("");

    return `
      <div class="modal-header">
        <span class="modal-league-tag">${cfg.displayName}</span>
        <span class="modal-game-time">${r.game_time || ""}</span>
      </div>
      <h2 class="modal-title">${r.home_team || "—"} <span class="modal-at">vs</span> ${r.away_team || "—"}</h2>
      <div class="modal-picks-section">
        <div class="modal-picks-label">PICKS</div>
        <div class="modal-picks">${picksHtml}</div>
      </div>`;
  }

  const isHockey   = !!cfg.isHockey;
  const isBaseball = !!cfg.isBaseball;

  const projAway  = isHockey ? r.away_projected_goals : isBaseball ? r.away_projected_runs  : r.away_projected_points;
  const projHome  = isHockey ? r.home_projected_goals : isBaseball ? r.home_projected_runs  : r.home_projected_points;
  const projTotal = isHockey ? r.total_projected_goals: isBaseball ? r.total_projected_runs : r.total_projected_points;

  const spreadKey  = isHockey ? "puck_line" : isBaseball ? "run_line" : "spread";
  const spreadAway = r[`away_${spreadKey}`]              || r.away_spread || "—";
  const spreadHome = r[`home_${spreadKey}`]              || r.home_spread || "—";
  const spreadAwayOdds = r[`away_dk_${spreadKey}_american`] || r.away_dk_spread_american || "—";
  const spreadHomeOdds = r[`home_dk_${spreadKey}_american`] || r.home_dk_spread_american || "—";

  const pitcherRow = isBaseball && (r.away_pitcher || r.home_pitcher)
    ? `<div class="modal-pitchers">
        <span class="modal-pitcher-label">SP</span>
        ${r.away_pitcher || "?"} <span class="modal-pitcher-vs">vs</span> ${r.home_pitcher || "?"}
       </div>`
    : "";

  const picksHtml = picks.map(p => {
    const betText = buildBetText(p, r, cfg);
    const ev      = getEv(p);
    const kelly   = getKelly(p);
    const edge    = extractEdge(p);
    const dec     = statDecimals(cfg, 2);
    return `
      <div class="modal-pick-row">
        <div class="modal-bet">${betText}</div>
        <div class="modal-pick-stats">
          <span class="modal-ev ${ev >= 0 ? "pos" : "neg"}">${formatPercentValue(ev, dec, true)} EV</span>
          <span class="modal-kelly">Kelly ${formatPercentValue(kelly, dec, false)}</span>
          ${edgeDots(edge, cfg)}
        </div>
      </div>`;
  }).join("");

  return `
    <div class="modal-header">
      <span class="modal-league-tag">${cfg.displayName}</span>
      <span class="modal-game-time">${r.game_time || ""}</span>
    </div>
    <h2 class="modal-title">${r.away_team || "—"} <span class="modal-at">@</span> ${r.home_team || "—"}</h2>
    ${pitcherRow}
    <div class="modal-proj">
      <span>Proj ${r.away_team || "Away"}: <strong>${projAway || "—"}</strong></span>
      <span>Proj ${r.home_team || "Home"}: <strong>${projHome || "—"}</strong></span>
      <span>Total: <strong>${projTotal || "—"}</strong></span>
    </div>
    <div class="modal-lines">
      <div class="modal-line-row"><span class="line-label">ML</span><span>${r.away_dk_moneyline_american || "—"} / ${r.home_dk_moneyline_american || "—"}</span></div>
      <div class="modal-line-row"><span class="line-label">${spreadKey.replace("_"," ").toUpperCase()}</span><span>${spreadAway} (${spreadAwayOdds}) / ${spreadHome} (${spreadHomeOdds})</span></div>
      <div class="modal-line-row"><span class="line-label">TOTAL</span><span>${r.total || "—"} &nbsp; O ${r.dk_total_over_american || "—"} / U ${r.dk_total_under_american || "—"}</span></div>
    </div>
    <div class="modal-picks-section">
      <div class="modal-picks-label">PICKS</div>
      <div class="modal-picks">${picksHtml}</div>
    </div>`;
}

// ─── Card ─────────────────────────────────────────────────────────────────────

function buildCard(p, r, cfg) {
  const card     = document.createElement("div");
  card.className = "pick-card";

  const betText    = buildBetText(p, r, cfg);
  const edge       = extractEdge(p);
  const ev         = getEv(p);
  const isBaseball = !!cfg.isBaseball;
  const dec        = statDecimals(cfg, 1);

  const pitcherLine = isBaseball && (r.away_pitcher || r.home_pitcher)
    ? `<div class="card-pitchers">${r.away_pitcher || "?"} vs ${r.home_pitcher || "?"}</div>`
    : "";

  // MLB-only: warn when lineup info isn't yet available for this game.
  // Pick still renders normally; this just flags reduced confidence.
  const lowConf = isBaseball && (p.low_confidence === "1" || p.low_confidence === 1);
  const warningBar = lowConf
    ? `<div class="card-warning">Lineups not available yet</div>`
    : "";

  card.innerHTML = `
    ${warningBar}
    <div class="card-top">
      <span class="card-time">${r.game_time || "—"}</span>
      <span class="card-league-tag">${cfg.displayName}</span>
    </div>
    <div class="card-matchup">
      <span class="card-team">${r.away_team || "—"}</span>
      <span class="card-at">@</span>
      <span class="card-team">${r.home_team || "—"}</span>
    </div>
    ${pitcherLine}
    <div class="card-bet">${betText}</div>
    <div class="card-footer">
      <span class="card-ev ${ev >= 0 ? "pos" : "neg"}">${formatPercentValue(ev, dec, true)}</span>
      ${edgeDots(edge, cfg)}
    </div>`;

  return card;
}

// ─── UFC: Find Nearest Event ──────────────────────────────────────────────────

const BASE_RAW = "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/docs/";
const UFC_MANIFEST_PATH = "win/mma/ufc/03_select/_index.json";

function ymdToFileDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}_${m}_${day}`;
}

async function findUFCEventDate() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayStr = ymdToFileDate(today);

  // 1) Preferred path: read the manifest. No probing, no console noise.
  //    Schema: ["YYYY_MM_DD", ...]
  try {
    const r = await fetch(UFC_MANIFEST_PATH, { cache: "no-store" });
    if (r.ok) {
      const dates = await r.json();
      if (Array.isArray(dates) && dates.length) {
        const sorted  = [...dates].sort();
        const upcoming = sorted.find(d => d >= todayStr);
        if (upcoming) return upcoming;
        // Nothing upcoming — show the most recent past event so the page
        // isn't empty between fight cards.
        return sorted[sorted.length - 1];
      }
    }
  } catch { /* fall through to probe */ }

  // 2) Fallback: small probe (today + 7 days) so the console shows at most
  //    7 misses instead of 31 if the manifest is missing.
  const candidates = [];
  for (let offset = 0; offset <= 7; offset++) {
    const d = new Date(today);
    d.setDate(today.getDate() + offset);
    candidates.push({ date: ymdToFileDate(d), offset });
  }

  const results = await Promise.all(
    candidates.map(async ({ date, offset }) => {
      const url = `${BASE_RAW}win/mma/ufc/03_select/${date}_ufc_select.csv`;
      try {
        const r = await fetch(url, { method: "HEAD" });
        return r.ok ? { date, offset } : null;
      } catch {
        return null;
      }
    })
  );

  const valid = results.filter(Boolean).sort((a, b) => a.offset - b.offset);
  return valid.length ? valid[0].date : null;
}

// ─── UFC: Build Card ──────────────────────────────────────────────────────────

function buildUFCCard(row) {
  const card = document.createElement("div");
  card.className = "pick-card";

  const fighter  = row.fighter  || "—";
  const opponent = row.opponent || "—";
  const ml       = row.moneyline || "—";
  const ev       = parseFloat(row.ev || 0);
  const edge     = parseFloat(row.edge || 0);

  card.innerHTML = `
    <div class="card-top">
      <span class="card-time">MMA</span>
      <span class="card-league-tag">UFC</span>
    </div>
    <div class="card-matchup">
      <span class="card-team">${fighter}</span>
      <span class="card-at">vs</span>
      <span class="card-team">${opponent}</span>
    </div>
    <div class="card-bet">${fighter} ${ml}</div>
    <div class="card-footer">
      <span class="card-ev ${ev >= 0 ? "pos" : "neg"}">${formatPercentValue(ev, 1, true)}</span>
      ${edgeDots(edge)}
    </div>`;

  card.addEventListener("click", () => openModal(buildUFCModalHtml(row)));
  return card;
}

// ─── UFC: Build Modal ─────────────────────────────────────────────────────────

function buildUFCModalHtml(row) {
  const fighter     = row.fighter      || "—";
  const opponent    = row.opponent     || "—";
  const ml          = row.moneyline    || "—";
  const impliedProb = parseFloat(row.implied_prob || 0);
  const modelProb   = parseFloat(row.model_prob   || 0);
  const edge        = parseFloat(row.edge         || 0);
  const ev          = parseFloat(row.ev           || 0);
  const kelly       = parseFloat(row.kelly        || 0);

  const fmt = (n, dec = 1) => isNaN(n) ? "—" : (n * 100).toFixed(dec) + "%";

  return `
    <div class="modal-header">
      <span class="modal-league-tag">UFC</span>
      <span class="modal-game-time">${row.match_date ? row.match_date.replaceAll("_", "-") : ""}</span>
    </div>
    <h2 class="modal-title">${fighter} <span class="modal-at">vs</span> ${opponent}</h2>
    <div class="modal-proj">
      <span>Moneyline: <strong>${ml}</strong></span>
      <span>Implied: <strong>${fmt(impliedProb)}</strong></span>
      <span>Model: <strong>${fmt(modelProb)}</strong></span>
    </div>
    <div class="modal-picks-section">
      <div class="modal-picks-label">EDGE ANALYSIS</div>
      <div class="modal-picks">
        <div class="modal-pick-row">
          <div class="modal-bet">${fighter} to Win</div>
          <div class="modal-pick-stats">
            <span class="modal-ev ${ev >= 0 ? "pos" : "neg"}">${formatPercentValue(ev, 2, true)} EV</span>
            <span class="modal-kelly">Kelly ${formatPercentValue(kelly, 2, false)}</span>
            <span class="modal-kelly">Edge ${formatPercentValue(edge, 2, false)}</span>
            ${edgeDots(edge)}
          </div>
        </div>
      </div>
    </div>`;
}

// ─── UFC: Load ────────────────────────────────────────────────────────────────

async function loadUFC() {
  const cfg = REPO_CONFIG["UFC"];
  const eventDate = await findUFCEventDate();

  // Update event selector if present
  const ufcSelector = document.getElementById("ufc-event-selector");
  if (ufcSelector) {
    if (eventDate) {
      ufcSelector.textContent = eventDate.replaceAll("_", "-");
    } else {
      ufcSelector.textContent = "No upcoming event";
    }
  }

  if (!eventDate) return { league: "UFC", cfg, picks: 0, error: "No event found" };

  const url = `${BASE_RAW}win/mma/ufc/03_select/${eventDate}_ufc_select.csv`;
  const res = await fetchCSV(url);

  if (!res.ok || res.rows.length === 0) return { league: "UFC", cfg, picks: 0 };

  return { league: "UFC", cfg, eventDate, rows: res.rows, picks: res.rows.length };
}

// ─── UFC: Render Column ───────────────────────────────────────────────────────

function renderUFCColumn(result) {
  const col = document.createElement("div");
  col.className = "league-column";
  col.dataset.league = "UFC";

  const hdr = document.createElement("div");
  hdr.className = "league-header";
  hdr.textContent = "UFC";
  col.appendChild(hdr);

  if (result.error || !result.rows || result.rows.length === 0) {
    col.innerHTML += `<div class="col-state empty">No UFC Picks</div>`;
    return { col, count: 0 };
  }

  const grid = document.createElement("div");
  grid.className = "league-cards";

  result.rows.forEach(row => {
    grid.appendChild(buildUFCCard(row));
  });

  col.appendChild(grid);
  return { col, count: result.rows.length };
}

// ─── League Loader ────────────────────────────────────────────────────────────

async function loadLeague(league, dateFormatted) {
  const cfg = REPO_CONFIG[league];
  if (!cfg) return { league, error: "No config" };

  // UFC uses its own loader
  if (cfg.isUFC) return loadUFC();

  const emptyRes = Promise.resolve({ ok: false, rows: [] });

  const selectPaths = resolvePaths(cfg.selectFiles, dateFormatted);
  const predPaths   = resolvePaths(cfg.predFile, dateFormatted);
  const bookPaths   = resolvePaths(cfg.bookFile, dateFormatted);

  const [selectRes, predRes, bookRes] = await Promise.all([
    fetchMultiCSV(selectPaths),
    predPaths.length ? fetchMultiCSV(predPaths) : emptyRes,
    bookPaths.length ? fetchMultiCSV(bookPaths) : emptyRes,
  ]);

  if (!selectRes.ok) return { league, cfg, error: "File not found", picks: 0 };

  // Allow leagues with non-canonical column names (e.g. soccer's match_date)
  // to remap into the standard shape before any other logic touches the rows.
  const normalize = cfg.normalizeRow ? (r) => cfg.normalizeRow(r) : (r) => r;
  const normalizedSelect = selectRes.rows.map(normalize);

  const { rows: selectRows, stale, fromDate } = filterRows(normalizedSelect, dateFormatted, league, cfg);
  if (selectRows.length === 0) return { league, cfg, picks: 0, stale, fromDate };

  const predMap = buildMap(predRes.rows, cfg);
  const bookMap = buildMap(bookRes.rows, cfg);
  const merged  = mergeRows(selectRows, predMap, bookMap, cfg);

  const grouped = {};
  merged.forEach(r => {
    if (!grouped[r.__key]) grouped[r.__key] = [];
    grouped[r.__key].push(r);
  });

  const keys = Object.keys(grouped).sort((a, b) =>
    parseTime(grouped[a][0].game_time) - parseTime(grouped[b][0].game_time)
  );

  return { league, cfg, keys, grouped, stale, fromDate, picks: merged.length };
}

// ─── Render Column ────────────────────────────────────────────────────────────

function renderColumn(result) {
  // UFC uses its own renderer
  if (result.league === "UFC") return renderUFCColumn(result);

  const col = document.createElement("div");
  col.className = "league-column";
  col.dataset.league = result.league;

  const hdr = document.createElement("div");
  hdr.className = "league-header";

  if (result.error) {
    hdr.textContent = (result.cfg && result.cfg.displayName) || result.league;
    col.appendChild(hdr);
    col.innerHTML += `<div class="col-state empty">No Picks Today</div>`;
    return { col, count: 0 };
  }

  hdr.innerHTML = (result.cfg && result.cfg.displayName) || result.league;
  col.appendChild(hdr);

  if (result.stale || !result.keys || result.keys.length === 0) {
    col.innerHTML += `<div class="col-state empty">No Picks Today</div>`;
    return { col, count: 0 };
  }

  let count = 0;
  result.keys.forEach(key => {
    const picks = result.grouped[key];
    const r     = picks[0];
    picks.forEach(p => {
      const card = buildCard(p, r, result.cfg);
      card.addEventListener("click", () => openModal(buildModalHtml(r, picks, result.cfg)));
      col.appendChild(card);
      count++;
    });
  });

  return { col, count };
}

// ─── Filter Pills ─────────────────────────────────────────────────────────────

function buildFilters(leagues) {
  const container = document.getElementById("league-filters");
  if (!container) return;
  container.innerHTML = "";

  const makeP = (text, league) => {
    const p = document.createElement("div");
    p.className = "filter-pill" + (league === "all" ? " active" : "");
    p.textContent = text;
    p.dataset.league = league;
    return p;
  };

  container.appendChild(makeP("All", "all"));
  leagues.forEach(l => {
    const cfg = REPO_CONFIG[l];
    container.appendChild(makeP((cfg && cfg.displayName) || l, l));
  });

  container.addEventListener("click", e => {
    const pill = e.target.closest(".filter-pill");
    if (!pill) return;
    container.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
    pill.classList.add("active");
    const sel = pill.dataset.league;
    document.querySelectorAll(".league-column").forEach(col => {
      col.style.display = (sel === "all" || col.dataset.league === sel) ? "" : "none";
    });
  });
}

// ─── Main ─────────────────────────────────────────────────────────────────────

function init() {
  dateInput.value = todayLocal();
  dateInput.addEventListener("change", loadPage);

  if (modal) {
    modal.addEventListener("click", e => {
      if (e.target === modal) modal.classList.remove("open");
    });
  }

  loadPage();
}

async function loadPage() {
  const dateStr       = dateInput.value || "";
  const dateFormatted = toUnderscore(dateStr);

  statusEl.textContent = "Loading…";
  statusEl.className   = "status loading";
  gamesEl.innerHTML    = "";

  // Honor `enabled: false` on a league config so it disappears from the page
  // (header + filter pill + data load) without deleting its config block.
  const leagues = (REPO_CONFIG.leagues || []).filter(l => {
    const cfg = REPO_CONFIG[l];
    return cfg && cfg.enabled !== false;
  });
  buildFilters(leagues);

  const results = await Promise.all(leagues.map(l => loadLeague(l, dateFormatted)));

  let totalPicks = 0;
  results.forEach(result => {
    const { col, count } = renderColumn(result);
    gamesEl.appendChild(col);
    totalPicks += count;
  });

  if (totalPicks === 0) {
    gamesEl.innerHTML = '<div class="empty-state">NO PICKS FOR THIS DATE</div>';
  }

  statusEl.textContent = `${totalPicks} pick${totalPicks !== 1 ? "s" : ""} · ${dateStr}`;
  statusEl.className   = "status";
}

init();

})();
