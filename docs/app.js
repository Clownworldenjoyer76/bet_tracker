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

  const headers = rows[0].map(h => (h ?? "").trim());
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

function fetchText(url) {
  return fetch(url).then(res => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
  });
}

function setStatus(msg) {
  const el = document.getElementById("status");
  if (el) el.textContent = msg || "";
}

function format2(n) {
  const x = Number(n);
  return Number.isFinite(x) ? x.toFixed(2) : "";
}

function safeGet(obj, key) {
  return (obj && obj[key]) ? obj[key].toString().trim() : "";
}

function escapeHtml(str) {
  return (str ?? "").toString()
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/* ================= SOCCER LOADER ================= */

async function loadSoccerDaily(selectedDate) {
  setStatus("");
  const gamesEl = document.getElementById("games");
  if (gamesEl) gamesEl.innerHTML = "";

  const parts = (selectedDate || "").split("-");
  if (parts.length !== 3) {
    setStatus("Invalid date selected.");
    return;
  }

  const yyyy = parts[0];
  const mm = parts[1];
  const dd = parts[2];

  const sidesUrl =
    `${RAW_BASE}/docs/win/edge/edge_soc_${yyyy}-${mm}-${dd}.csv`;

  const totalsUrl =
    `${RAW_BASE}/docs/win/soc/edge_soc_totals_${yyyy}_${mm}_${dd}.csv`;

  let sides = [];
  let totals = [];

  try {
    const [sidesText, totalsText] = await Promise.all([
      fetchText(sidesUrl).catch(() => ""),
      fetchText(totalsUrl).catch(() => "")
    ]);
    sides = sidesText ? parseCSV(sidesText) : [];
    totals = totalsText ? parseCSV(totalsText) : [];
  } catch {
    setStatus("Failed to load soccer files.");
    return;
  }

  if (sides.length === 0) {
    setStatus("No soccer games found for this date.");
    return;
  }

  const sidesByGame = new Map();
  const gameOrder = [];

  for (const r of sides) {
    const gid = safeGet(r, "game_id");
    if (!gid) continue;
    if (!sidesByGame.has(gid)) {
      sidesByGame.set(gid, []);
      gameOrder.push(gid);
    }
    sidesByGame.get(gid).push(r);
  }

  const totalsByGame = new Map();
  for (const r of totals) {
    const gid = safeGet(r, "game_id");
    if (!gid) continue;
    if (!totalsByGame.has(gid)) totalsByGame.set(gid, []);
    totalsByGame.get(gid).push(r);
  }

  renderSoccerGames(gameOrder, sidesByGame, totalsByGame);
}

function renderSoccerGames(gameOrder, sidesByGame, totalsByGame) {
  const container = document.getElementById("games");
  if (!container) return;

  for (const gid of gameOrder) {
    const sideRows = sidesByGame.get(gid) || [];
    if (sideRows.length < 2) continue;

    const a = sideRows[0];
    const b = sideRows[1];

    const header =
      `${safeGet(a, "team")} vs ${safeGet(b, "team")}`;

    const totals = totalsByGame.get(gid) || [];

    const box = document.createElement("div");
    box.className = "game-box";

    const h = document.createElement("div");
    h.className = "game-header";
    h.textContent = header;
    box.appendChild(h);

    const table = document.createElement("table");
    table.className = "game-grid";

    let totalsHtml = "";
    for (const t of totals) {
      totalsHtml += `<div>${escapeHtml(
        `${safeGet(t, "side")} ${safeGet(t, "market_total")} @ ${safeGet(t, "acceptable_american_odds")}`
      )}</div>`;
    }

    table.innerHTML = `
      <thead>
        <tr>
          <th>Team</th>
          <th>Win %</th>
          <th>Take ML At</th>
          <th>Totals</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>${escapeHtml(safeGet(a, "team"))}</strong></td>
          <td>${format2(safeGet(a, "win_probability"))}</td>
          <td>${escapeHtml(safeGet(a, "acceptable_american_odds"))}</td>
          <td rowspan="2">${totalsHtml || ""}</td>
        </tr>
        <tr>
          <td><strong>${escapeHtml(safeGet(b, "team"))}</strong></td>
          <td>${format2(safeGet(b, "win_probability"))}</td>
          <td>${escapeHtml(safeGet(b, "acceptable_american_odds"))}</td>
        </tr>
      </tbody>
    `;

    box.appendChild(table);
    container.appendChild(box);
  }
}
