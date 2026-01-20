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

  if (rows.length === 0) return [];

  const headers = rows[0].map(h =>
    (h ?? "").trim().replace(/^\uFEFF/, "")
  );

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

function setStatus(msg) {
  const el = document.getElementById("status");
  if (el) el.textContent = msg || "";
}

function safeGet(obj, key) {
  return obj && obj[key] != null ? obj[key].toString().trim() : "";
}

function format2(n) {
  const x = Number(n);
  return Number.isFinite(x) ? x.toFixed(2) : "";
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

/* ================= NHL (UNCHANGED) ================= */

async function loadNHLDaily(selectedDate) {
  setStatus("");
  document.getElementById("games").innerHTML = "";

  const [yyyy, mm, dd] = selectedDate.split("-");
  const d = `${yyyy}_${mm}_${dd}`;

  const mlUrl = `${RAW_BASE}/docs/win/edge/edge_nhl_${d}.csv`;
  const totalsUrl = `${RAW_BASE}/docs/win/nhl/edge_nhl_totals_${d}.csv`;

  let ml = [], totals = [];
  try {
    ml = parseCSV(await fetchText(mlUrl));
    totals = parseCSV(await fetchText(totalsUrl));
  } catch {
    setStatus("Failed to load NHL files.");
    return;
  }

  const totalsByGame = new Map();
  for (const r of totals) {
    if (!totalsByGame.has(r.game_id)) totalsByGame.set(r.game_id, r);
  }

  const games = new Map();
  const order = [];
  for (const r of ml) {
    if (!games.has(r.game_id)) {
      games.set(r.game_id, []);
      order.push(r.game_id);
    }
    games.get(r.game_id).push(r);
  }

  if (!order.length) {
    setStatus("No NHL games found for this date.");
    return;
  }

  renderNHLGames(order, games, totalsByGame);
}

function renderNHLGames(order, games, totalsByGame) {
  const container = document.getElementById("games");
  for (const gid of order) {
    const rows = games.get(gid);
    const a = rows[0];
    const b = rows[1];

    const t = totalsByGame.get(gid);

    const box = document.createElement("div");
    box.className = "game-box";

    box.innerHTML = `
      <div class="game-header">${escapeHtml(a.team)} at ${escapeHtml(a.opponent)}</div>
      <table class="game-grid">
        <thead>
          <tr>
            <th></th>
            <th>Win Probability</th>
            <th>Projected Goals</th>
            <th>Take ML at</th>
            <th>Take Over/Under at</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>${escapeHtml(a.team)}</strong></td>
            <td>${format2(a.win_probability)}</td>
            <td>${format2(a.goals)}</td>
            <td>${escapeHtml(a.acceptable_american_odds)}</td>
            <td>${t ? `${t.side} ${t.market_total}` : ""}</td>
          </tr>
          <tr>
            <td><strong>${escapeHtml(b.team)}</strong></td>
            <td>${format2(b.win_probability)}</td>
            <td>${format2(b.goals)}</td>
            <td>${escapeHtml(b.acceptable_american_odds)}</td>
            <td>${t ? t.acceptable_american_odds : ""}</td>
          </tr>
        </tbody>
      </table>
    `;
    container.appendChild(box);
  }
}

/* ================= SOCCER (FIXED) ================= */

async function loadSoccerDaily(selectedDate) {
  setStatus("");
  document.getElementById("games").innerHTML = "";

  const [yyyy, mm, dd] = selectedDate.split("-");
  const d = `${yyyy}_${mm}_${dd}`;

  const sidesUrl = `${RAW_BASE}/docs/win/edge/edge_soc_${d}.csv`;
  const totalsUrl = `${RAW_BASE}/docs/win/soc/edge_soc_totals_${d}.csv`;

  let sides = [], totals = [];
  try {
    sides = parseCSV(await fetchText(sidesUrl));
    totals = parseCSV(await fetchText(totalsUrl));
  } catch {
    setStatus("Failed to load soccer files.");
    return;
  }

  if (!sides.length) {
    setStatus("No soccer games found for this date.");
    return;
  }

  const totalsByGame = new Map();
  for (const r of totals) {
    if (!totalsByGame.has(r.game_id)) totalsByGame.set(r.game_id, r);
  }

  const games = new Map();
  const order = [];
  for (const r of sides) {
    if (!games.has(r.game_id)) {
      games.set(r.game_id, []);
      order.push(r.game_id);
    }
    games.get(r.game_id).push(r);
  }

  renderSoccerGames(order, games, totalsByGame);
}

function renderSoccerGames(order, games, totalsByGame) {
  const container = document.getElementById("games");

  for (const gid of order) {
    const rows = games.get(gid);
    if (rows.length < 2) continue;

    const a = rows[0];
    const b = rows[1];
    const t = totalsByGame.get(gid);

    const box = document.createElement("div");
    box.className = "game-box";

    box.innerHTML = `
      <div class="game-header">${escapeHtml(a.team)} vs ${escapeHtml(b.team)}</div>
      <table class="game-grid">
        <thead>
          <tr>
            <th></th>
            <th>Win Probability</th>
            <th>Projected Goals</th>
            <th>Take ML at</th>
            <th>Take Over/Under at</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>${escapeHtml(a.team)}</strong></td>
            <td>${format2(a.win_probability)}</td>
            <td>${format2(a.goals)}</td>
            <td>${escapeHtml(a.acceptable_american_odds)}</td>
            <td>${t ? `${t.side} ${t.market_total}` : ""}</td>
          </tr>
          <tr>
            <td><strong>${escapeHtml(b.team)}</strong></td>
            <td>${format2(b.win_probability)}</td>
            <td>${format2(b.goals)}</td>
            <td>${escapeHtml(b.acceptable_american_odds)}</td>
            <td>${t ? t.acceptable_american_odds : ""}</td>
          </tr>
        </tbody>
      </table>
    `;
    container.appendChild(box);
  }
}
