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

/* ================= SOCCER (UPDATED) ================= */

async function loadSoccerDaily(selectedDate) {
  setStatus("");
  document.getElementById("games").innerHTML = "";

  const [yyyy, mm, dd] = selectedDate.split("-");
  const d = `${yyyy}_${mm}_${dd}`;

  const url = `${RAW_BASE}/docs/win/final/final_soc_${d}.csv`;

  let rows = [];
  try {
    rows = parseCSV(await fetchText(url));
  } catch {
    setStatus("Failed to load soccer file.");
    return;
  }

  if (!rows.length) {
    setStatus("No soccer games found for this date.");
    return;
  }

  const games = new Map();
  const order = [];

  for (const r of rows) {
    if (!games.has(r.game_id)) {
      games.set(r.game_id, []);
      order.push(r.game_id);
    }
    games.get(r.game_id).push(r);
  }

  renderSoccerGames(order, games);
}

function renderSoccerGames(order, games) {
  const container = document.getElementById("games");

  for (const gid of order) {
    const rows = games.get(gid);

    const winRows = rows.filter(r => r.bet_type === "win");
    const drawRow = rows.find(r => r.bet_type === "draw");

    if (winRows.length !== 2) continue;

    const a = winRows[0];
    const b = winRows[1];

    const box = document.createElement("div");
    box.className = "game-box";

    box.innerHTML = `
      <div class="game-header">${escapeHtml(a.team)} vs ${escapeHtml(b.team)}</div>
      <table class="game-grid">
        <thead>
          <tr>
            <th></th>
            <th>Probability</th>
            <th>Projected Goals</th>
            <th>Take ML at</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>${escapeHtml(a.team)}</strong></td>
            <td>${format2(a.win_probability)}</td>
            <td>${format2(a.goals)}</td>
            <td>${escapeHtml(a.personally_acceptable_american_odds)}</td>
          </tr>
          <tr>
            <td><strong>${escapeHtml(b.team)}</strong></td>
            <td>${format2(b.win_probability)}</td>
            <td>${format2(b.goals)}</td>
            <td>${escapeHtml(b.personally_acceptable_american_odds)}</td>
          </tr>
          ${drawRow ? `
          <tr class="draw-row">
            <td><strong>DRAW</strong></td>
            <td>${format2(drawRow.draw_probability)}</td>
            <td></td>
            <td>${escapeHtml(drawRow.personally_acceptable_american_odds)}</td>
          </tr>` : ""}
        </tbody>
      </table>
    `;

    container.appendChild(box);
  }
}
