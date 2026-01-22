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

function mlClassFromProb(p) {
  const x = Number(p);
  if (!Number.isFinite(x)) return "";
  if (x > 0.65) return "ml-green";
  if (x > 0.50) return "ml-orange";
  return "ml-pink";
}

/* ================= NCAAB ================= */

async function loadNCAABDaily(selectedDate) {
  setStatus("");
  document.getElementById("games").innerHTML = "";

  const [yyyy, mm, dd] = selectedDate.split("-");
  const d = `${yyyy}_${mm}_${dd}`;

  const url = `${RAW_BASE}/docs/win/final/final_ncaab_${d}.csv`;

  let rows = [];
  try {
    rows = parseCSV(await fetchText(url));
  } catch {
    setStatus("No NCAAB file found for this date.");
    return;
  }

  if (!rows.length) {
    setStatus("No NCAAB games found for this date.");
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

  renderNCAABGames(order, games);
}

function renderNCAABGames(order, games) {
  const container = document.getElementById("games");

  for (const gid of order) {
    const rows = games.get(gid);
    if (rows.length !== 2) continue;

    const a = rows[0];
    const b = rows[1];

    const box = document.createElement("div");
    box.className = "game-box";

    box.innerHTML = `
      <div class="game-header">
        ${escapeHtml(a.team)} vs ${escapeHtml(b.team)}
        <span class="cell-muted"> — ${escapeHtml(a.time)}</span>
      </div>
      <table class="game-grid">
        <thead>
          <tr>
            <th></th>
            <th>Win Probability</th>
            <th>Projected Pts</th>
            <th>Total</th>
            <th>Take ML at</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>${escapeHtml(a.team)}</strong></td>
            <td>${formatPct(a.win_probability)}</td>
            <td>${format2(a.points)}</td>
            <td>${escapeHtml(a.best_ou)}</td>
            <td class="${mlClassFromProb(a.win_probability)}">
              ${escapeHtml(a.personally_acceptable_american_odds)}
            </td>
          </tr>
          <tr>
            <td><strong>${escapeHtml(b.team)}</strong></td>
            <td>${formatPct(b.win_probability)}</td>
            <td>${format2(b.points)}</td>
            <td>${escapeHtml(b.best_ou)}</td>
            <td class="${mlClassFromProb(b.win_probability)}">
              ${escapeHtml(b.personally_acceptable_american_odds)}
            </td>
          </tr>
        </tbody>
      </table>
    `;

    container.appendChild(box);
  }
}
