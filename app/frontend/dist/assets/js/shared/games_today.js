(() => {

const dateInput    = document.getElementById("gt-date");
const statusEl     = document.getElementById("gt-status");
const gamesEl      = document.getElementById("gt-games");
const modal        = document.getElementById("gt-modal");
const modalContent = document.getElementById("gt-modal-content");

if (!dateInput || !statusEl || !gamesEl) return;
if (!window.REPO_CONFIG) { statusEl.textContent = "Missing config."; return; }

// ─── Date ────────────────────────────────────────────────────────────────────

function todayLocal() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
}

function toUnderscore(s) {
  return (s || "").trim().replaceAll("-", "_");
}

function normDate(v) {
  return toUnderscore(v || "");
}

// ─── CSV ─────────────────────────────────────────────────────────────────────

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map(h => h.trim());
  return lines.slice(1).map(line => {
    const vals = line.split(",");
    const obj = {};
    headers.forEach((h, i) => { obj[h] = (vals[i] ?? "").trim(); });
    return obj;
  });
}

async function fetchCSV(path) {
  try {
    const r = await fetch(path);
    if (!r.ok) return { ok: false, rows: [] };
    return { ok: true, rows: parseCSV(await r.text()) };
  } catch {
    return { ok: false, rows: [] };
  }
}

// ─── Join Key ─────────────────────────────────────────────────────────────────

function makeKey(row, cfg) {
  if (cfg && cfg.joinKey) return (row[cfg.joinKey] || "").trim();
  return `${(row.game_date||"").trim()}|${(row.home_team||"").trim()}|${(row.away_team||"").trim()}`;
}

function buildMap(rows, cfg) {
  const map = {};
  rows.forEach(r => { const k = makeKey(r, cfg); if (k) map[k] = r; });
  return map;
}

// ─── Filter by date ───────────────────────────────────────────────────────────

function filterByDate(rows, dateFormatted) {
  return rows.filter(r => normDate(r.game_date) === dateFormatted);
}

// ─── Time Sort ────────────────────────────────────────────────────────────────

function parseTime(t) {
  if (!t) return 9999;
  const m = t.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (!m) return 9999;
  let h = parseInt(m[1], 10);
  const min = parseInt(m[2], 10);
  if (m[3].toUpperCase() === "PM" && h !== 12) h += 12;
  if (m[3].toUpperCase() === "AM" && h === 12) h = 0;
  return h * 60 + min;
}

// ─── Formatting helpers ───────────────────────────────────────────────────────

function fmt(v, fallback = "—") {
  return (v && v.trim && v.trim() !== "") ? v.trim() : fallback;
}

function fmtOdds(v) {
  const n = parseFloat(v);
  if (isNaN(n)) return "—";
  return (n > 0 ? "+" : "") + n;
}

function fmtLine(v) {
  const n = parseFloat(v);
  if (isNaN(n)) return v || "—";
  return n > 0 ? "+" + n : String(n);
}

function fmtProj(v) {
  const n = parseFloat(v);
  return isNaN(n) ? "—" : n.toFixed(1);
}

function fmtProb(v) {
  const n = parseFloat(v);
  return isNaN(n) ? "—" : (n * 100).toFixed(1) + "%";
}

// ─── Spread label per sport ───────────────────────────────────────────────────

function spreadLabel(cfg) {
  if (cfg.isHockey)   return "PUCK LINE";
  if (cfg.isBaseball) return "RUN LINE";
  return "SPREAD";
}

function getSpreadCols(cfg) {
  if (cfg.isHockey)   return { away: "away_puck_line",  home: "home_puck_line",  awayOdds: "away_dk_puck_line_american",  homeOdds: "home_dk_puck_line_american"  };
  if (cfg.isBaseball) return { away: "away_run_line",   home: "home_run_line",   awayOdds: "away_dk_run_line_american",   homeOdds: "home_dk_run_line_american"   };
  return                     { away: "away_spread",     home: "home_spread",     awayOdds: "away_dk_spread_american",     homeOdds: "home_dk_spread_american"     };
}

function getProjCols(cfg) {
  if (cfg.isHockey)   return { away: "away_projected_goals",  home: "home_projected_goals",  total: "total_projected_goals"  };
  if (cfg.isBaseball) return { away: "away_projected_runs",   home: "home_projected_runs",   total: "total_projected_runs"   };
  return                     { away: "away_projected_points", home: "home_projected_points", total: "total_projected_points" };
}

// ─── Modal ────────────────────────────────────────────────────────────────────

function openModal(html) {
  if (!modalContent || !modal) return;
  modalContent.innerHTML = html;
  modal.classList.add("open");
}

function buildModalHtml(g, cfg) {
  const proj   = getProjCols(cfg);
  const spread = getSpreadCols(cfg);

  const pitcherRow = cfg.isBaseball && (g.home_pitcher || g.away_pitcher) ? `
    <div class="gt-modal-pitchers">
      <span class="gt-pitcher-label">SP</span>
      <span>${fmt(g.away_pitcher)}</span>
      <span class="gt-pitcher-vs">vs</span>
      <span>${fmt(g.home_pitcher)}</span>
    </div>` : "";

  const awayLine = fmtLine(g[spread.away]);
  const homeLine = fmtLine(g[spread.home]);

  return `
    <div class="gt-modal-header">
      <span class="gt-modal-league-tag">${cfg.displayName}</span>
      <span class="gt-modal-time">${fmt(g.game_time)}</span>
    </div>
    <h2 class="gt-modal-title">
      ${fmt(g.away_team)} <span class="gt-modal-at">@</span> ${fmt(g.home_team)}
    </h2>
    ${pitcherRow}

    <div class="gt-modal-section-label">PROJECTIONS</div>
    <div class="gt-modal-proj">
      <div class="gt-proj-row">
        <span class="gt-proj-team">${fmt(g.away_team)}</span>
        <span class="gt-proj-val">${fmtProj(g[proj.away])}</span>
        <span class="gt-proj-prob">${fmtProb(g.away_prob)}</span>
      </div>
      <div class="gt-proj-row">
        <span class="gt-proj-team">${fmt(g.home_team)}</span>
        <span class="gt-proj-val">${fmtProj(g[proj.home])}</span>
        <span class="gt-proj-prob">${fmtProb(g.home_prob)}</span>
      </div>
      <div class="gt-proj-total">Projected Total: <strong>${fmtProj(g[proj.total])}</strong></div>
    </div>

    <div class="gt-modal-section-label">LINES</div>
    <div class="gt-modal-lines">
      <div class="gt-line-row">
        <span class="gt-line-label">ML</span>
        <span class="gt-line-team">${fmt(g.away_team)}</span>
        <span class="gt-line-odds ${parseFloat(g.away_dk_moneyline_american) > 0 ? "plus" : ""}">${fmtOdds(g.away_dk_moneyline_american)}</span>
        <span class="gt-line-team">${fmt(g.home_team)}</span>
        <span class="gt-line-odds ${parseFloat(g.home_dk_moneyline_american) > 0 ? "plus" : ""}">${fmtOdds(g.home_dk_moneyline_american)}</span>
      </div>
      <div class="gt-line-row">
        <span class="gt-line-label">${spreadLabel(cfg)}</span>
        <span class="gt-line-team">${fmt(g.away_team)}</span>
        <span class="gt-line-val">${awayLine} <span class="gt-line-odds">${fmtOdds(g[spread.awayOdds])}</span></span>
        <span class="gt-line-team">${fmt(g.home_team)}</span>
        <span class="gt-line-val">${homeLine} <span class="gt-line-odds">${fmtOdds(g[spread.homeOdds])}</span></span>
      </div>
      <div class="gt-line-row gt-total-row">
        <span class="gt-line-label">TOTAL</span>
        <span class="gt-total-num">${fmt(g.total)}</span>
        <span>O <span class="gt-line-odds ${parseFloat(g.dk_total_over_american) > 0 ? "plus" : ""}">${fmtOdds(g.dk_total_over_american)}</span></span>
        <span>U <span class="gt-line-odds ${parseFloat(g.dk_total_under_american) > 0 ? "plus" : ""}">${fmtOdds(g.dk_total_under_american)}</span></span>
      </div>
    </div>`;
}

// ─── Game Card ────────────────────────────────────────────────────────────────

function buildGameCard(g, cfg) {
  const proj   = getProjCols(cfg);
  const spread = getSpreadCols(cfg);

  const pitcherLine = cfg.isBaseball && (g.away_pitcher || g.home_pitcher)
    ? `<div class="gt-card-pitchers">${fmt(g.away_pitcher, "TBD")} vs ${fmt(g.home_pitcher, "TBD")}</div>`
    : "";

  const awayML   = fmtOdds(g.away_dk_moneyline_american);
  const homeML   = fmtOdds(g.home_dk_moneyline_american);
  const awayLine = fmtLine(g[spread.away]);
  const homeLine = fmtLine(g[spread.home]);
  const awayLineOdds = fmtOdds(g[spread.awayOdds]);
  const homeLineOdds = fmtOdds(g[spread.homeOdds]);
  const total    = fmt(g.total);
  const overOdds = fmtOdds(g.dk_total_over_american);
  const underOdds= fmtOdds(g.dk_total_under_american);

  const projAway  = fmtProj(g[proj.away]);
  const projHome  = fmtProj(g[proj.home]);
  const projTotal = fmtProj(g[proj.total]);

  const card = document.createElement("div");
  card.className = "gt-card";

  card.innerHTML = `
    <div class="gt-card-top">
      <span class="gt-card-time">${fmt(g.game_time)}</span>
      <span class="gt-card-league">${cfg.displayName}</span>
    </div>

    <div class="gt-card-matchup">
      <div class="gt-card-team-row">
        <span class="gt-card-team away">${fmt(g.away_team)}</span>
        <span class="gt-card-ml ${parseFloat(g.away_dk_moneyline_american) > 0 ? "plus" : ""}">${awayML}</span>
      </div>
      <div class="gt-card-team-row">
        <span class="gt-card-team home">${fmt(g.home_team)}</span>
        <span class="gt-card-ml ${parseFloat(g.home_dk_moneyline_american) > 0 ? "plus" : ""}">${homeML}</span>
      </div>
    </div>

    ${pitcherLine}

    <div class="gt-card-divider"></div>

    <div class="gt-card-lines">
      <div class="gt-card-line-row">
        <span class="gt-card-line-label">${spreadLabel(cfg)}</span>
        <span class="gt-card-line-val">${awayLine} <span class="gt-card-line-odds">${awayLineOdds}</span></span>
        <span class="gt-card-line-sep">/</span>
        <span class="gt-card-line-val">${homeLine} <span class="gt-card-line-odds">${homeLineOdds}</span></span>
      </div>
      <div class="gt-card-line-row">
        <span class="gt-card-line-label">TOTAL</span>
        <span class="gt-card-line-val">${total} &nbsp;O ${overOdds} / U ${underOdds}</span>
      </div>
    </div>

    <div class="gt-card-divider"></div>

    <div class="gt-card-proj">
      <span class="gt-card-proj-label">PROJ</span>
      <span class="gt-card-proj-val">${projAway} – ${projHome}</span>
      <span class="gt-card-proj-total">· ${projTotal}</span>
    </div>`;

  card.addEventListener("click", () => openModal(buildModalHtml(g, cfg)));
  return card;
}

// ─── League Loader ────────────────────────────────────────────────────────────

async function loadLeague(league, dateFormatted) {
  const cfg = REPO_CONFIG[league];
  if (!cfg) return { league, error: "No config" };

  const [predRes, bookRes] = await Promise.all([
    fetchCSV(cfg.predFile(dateFormatted)),
    fetchCSV(cfg.bookFile(dateFormatted)),
  ]);

  if (!predRes.ok && !bookRes.ok) return { league, cfg, error: "Files not found", games: [] };

  // Filter pred rows to selected date
  const predRows = filterByDate(predRes.rows, dateFormatted);
  if (predRows.length === 0) return { league, cfg, games: [] };

  // Build book map and merge into pred rows
  const bookMap = buildMap(bookRes.rows, cfg);

  const games = predRows.map(p => {
    const key  = makeKey(p, cfg);
    const book = bookMap[key] || {};
    return { ...book, ...p }; // pred wins on conflicts (has game_time for MLB)
  });

  // Sort by time
  games.sort((a, b) => parseTime(a.game_time) - parseTime(b.game_time));

  return { league, cfg, games };
}

// ─── Render Column ────────────────────────────────────────────────────────────

function renderColumn(result) {
  const col = document.createElement("div");
  col.className = "gt-league-column";
  col.dataset.league = result.league;

  const hdr = document.createElement("div");
  hdr.className = "gt-league-header";
  hdr.textContent = result.league;
  col.appendChild(hdr);

  if (result.error) {
    col.innerHTML += `<div class="gt-col-state error">⚠ ${result.error}</div>`;
    return { col, count: 0 };
  }

  if (!result.games || result.games.length === 0) {
    col.innerHTML += `<div class="gt-col-state empty">No games</div>`;
    return { col, count: 0 };
  }

  result.games.forEach(g => {
    col.appendChild(buildGameCard(g, result.cfg));
  });

  return { col, count: result.games.length };
}

// ─── Filter Pills ─────────────────────────────────────────────────────────────

function buildFilters(leagues) {
  const container = document.getElementById("gt-filters");
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
  leagues.forEach(l => container.appendChild(makeP(l, l)));

  container.addEventListener("click", e => {
    const pill = e.target.closest(".filter-pill");
    if (!pill) return;
    container.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
    pill.classList.add("active");
    const sel = pill.dataset.league;
    document.querySelectorAll(".gt-league-column").forEach(col => {
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

  const leagues = REPO_CONFIG.leagues || [];
  buildFilters(leagues);

  const results = await Promise.all(leagues.map(l => loadLeague(l, dateFormatted)));

  let totalGames = 0;
  results.forEach(result => {
    const { col, count } = renderColumn(result);
    gamesEl.appendChild(col);
    totalGames += count;
  });

  if (totalGames === 0) {
    gamesEl.innerHTML = '<div class="gt-empty-state">NO GAMES FOR THIS DATE</div>';
  }

  statusEl.textContent = `${totalGames} game${totalGames !== 1 ? "s" : ""} · ${dateStr}`;
  statusEl.className   = "status";
}

init();

})();
