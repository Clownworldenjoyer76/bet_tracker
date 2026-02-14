const GH_OWNER = "Clownworldenjoyer76";
const GH_REPO = "bet_tracker";
const GH_BRANCH = "main";
const RAW_BASE = `https://raw.githubusercontent.com/${GH_OWNER}/${GH_REPO}/${GH_BRANCH}`;

/* ================= CSV PARSER ================= */

function parseCSV(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  const s = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    const next = s[i + 1];

    if (c === '"' && inQuotes && next === '"') {
      field += '"';
      i++;
      continue;
    }

    if (c === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (!inQuotes && c === ",") {
      row.push(field);
      field = "";
      continue;
    }

    if (!inQuotes && c === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
      continue;
    }

    field += c;
  }

  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  if (!rows.length) return [];

  const headers = rows[0].map(h => (h ?? "").trim().replace(/^\uFEFF/, ""));
  const objects = [];

  for (let r = 1; r < rows.length; r++) {
    const values = rows[r];
    if (values.length === 1 && values[0].trim() === "") continue;

    const obj = {};
    for (let c = 0; c < headers.length; c++) {
      obj[headers[c]] = (values[c] ?? "").trim();
    }
    objects.push(obj);
  }

  return objects;
}

/* ================= HELPERS ================= */

function format2(n) {
  const x = Number(n);
  return Number.isFinite(x) ? x.toFixed(2) : "";
}

function formatPct(n) {
  const x = Number(n);
  return Number.isFinite(x) ? `${(x * 100).toFixed(2)}%` : "";
}

function escapeHtml(str) {
  return (str ?? "").toString()
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchText(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

function timeToMinutes(t) {
  if (!t) return 0;
  const m = t.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (!m) return 0;

  let h = Number(m[1]);
  const min = Number(m[2]);
  const ap = m[3].toUpperCase();

  if (ap === "PM" && h !== 12) h += 12;
  if (ap === "AM" && h === 12) h = 0;

  return h * 60 + min;
}

/* ================= NCAAB ================= */

async function loadNCAABDaily(selectedDate) {

  const statusEl = document.getElementById("status");
  const gamesEl = document.getElementById("games");

  if (statusEl) statusEl.textContent = "";
  if (gamesEl) gamesEl.innerHTML = "";

  const [yyyy, mm, dd] = selectedDate.split("-");
  const d = `${yyyy}_${mm}_${dd}`;

  const mlUrl =
    `${RAW_BASE}/docs/win/final/step_2/ncaab/ml/juice_ncaab_ml_${d}.csv`;

  const spreadsUrl =
    `${RAW_BASE}/docs/win/final/step_2/ncaab/spreads/juice_ncaab_spreads_${d}.csv`;

  const totalsUrl =
    `${RAW_BASE}/docs/win/final/step_2/ncaab/totals/juice_ncaab_totals_${d}.csv`;

  const dkUrl =
    `${RAW_BASE}/docs/win/manual/normalized/dk_ncaab_moneyline_${d}.csv`;

  let mlRows = [];
  let spreads = [];
  let totals = [];
  let dkRows = [];

  try {
    mlRows = parseCSV(await fetchText(mlUrl));
  } catch {
    statusEl.textContent = "No NCAAB ML file found.";
    return;
  }

  try { spreads = parseCSV(await fetchText(spreadsUrl)); } catch {}
  try { totals = parseCSV(await fetchText(totalsUrl)); } catch {}
  try { dkRows = parseCSV(await fetchText(dkUrl)); } catch {}

  if (!mlRows.length) {
    statusEl.textContent = "No NCAAB games found.";
    return;
  }

  const spreadsByGame = new Map();
  spreads.forEach(s => spreadsByGame.set(s.game_id, s));

  const totalsByGame = new Map();
  totals.forEach(t => totalsByGame.set(t.game_id, t));

  const timeByGame = new Map();
  dkRows.forEach(r => {
    if (r.game_id && r.time) {
      timeByGame.set(r.game_id.trim(), r.time.trim());
    }
  });

  mlRows.sort((a, b) =>
    timeToMinutes(timeByGame.get(a.game_id)) -
    timeToMinutes(timeByGame.get(b.game_id))
  );

  renderNCAABGames(mlRows, spreadsByGame, totalsByGame, timeByGame, d);
}

function renderNCAABGames(
  mlRows,
  spreadsByGame,
  totalsByGame,
  timeByGame,
  d
) {

  const container = document.getElementById("games");

  mlRows.forEach(g => {

    const spreads = spreadsByGame.get(g.game_id) || {};
    const totals = totalsByGame.get(g.game_id) || {};
    const gameTime = timeByGame.get(g.game_id);

    const box = document.createElement("div");
    box.className = "game-box";
    box.style.cursor = "pointer";
    box.onclick = () =>
      window.location.href =
        `ncaab-game.html?date=${d}&game_id=${g.game_id}`;

    box.innerHTML = `
      <div class="game-header">
        ${escapeHtml(g.away_team)} @ ${escapeHtml(g.home_team)}
        ${gameTime ? ` — ${escapeHtml(gameTime)}` : ""}
      </div>

      <div class="game-subheader">
        Projected Total: ${format2(g.game_projected_points)}
      </div>
    `;

    container.appendChild(box);
  });
}
