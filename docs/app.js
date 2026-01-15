// docs/app.js
const GH_OWNER = "Clownworldenjoyer76";
const GH_REPO = "bet_tracker";
const GH_BRANCH = "main";
const RAW_BASE = `https://raw.githubusercontent.com/${GH_OWNER}/${GH_REPO}/${GH_BRANCH}`;

/**
 * Robust CSV parser:
 * - supports quoted fields
 * - supports commas inside quotes
 * - supports CRLF
 */
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

  // last field
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
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
    return res.text();
  });
}

function setStatus(msg) {
  const el = document.getElementById("status");
  if (!el) return;
  el.textContent = msg || "";
}

/**
 * NHL loader:
 * - Uses filename date (derived from picker YYYY-MM-DD) to construct:
 *   docs/win/edge/edge_nhl_YYYY_MM_DD.csv
 *   docs/win/nhl/edge_nhl_totals_YYYY_MM_DD.csv
 * - Groups games by game_id in the order they appear in edge_nhl file
 * - Renders one game box per game_id
 * - Leaves blanks if data missing
 * - Rounds win_probability and goals to 2 decimals
 */
async function loadNHLDaily(selectedDateYYYYMMDD) {
  setStatus("");

  const gamesEl = document.getElementById("games");
  if (gamesEl) gamesEl.innerHTML = "";

  // Convert YYYY-MM-DD -> YYYY_MM_DD
  const parts = (selectedDateYYYYMMDD || "").split("-");
  if (parts.length !== 3) {
    setStatus("Invalid date selected.");
    return;
  }
  const yyyy = parts[0];
  const mm = parts[1];
  const dd = parts[2];
  const fileDate = `${yyyy}_${mm}_${dd}`;

  const mlUrl = `${RAW_BASE}/docs/win/edge/edge_nhl_${fileDate}.csv`;
  const totalsUrl = `${RAW_BASE}/docs/win/nhl/edge_nhl_totals_${fileDate}.csv`;

  let mlRows = [];
  let totalsRows = [];

  try {
    const [mlText, totalsText] = await Promise.all([
      fetchText(mlUrl).catch(() => ""),       // render blanks if missing
      fetchText(totalsUrl).catch(() => "")
    ]);

    mlRows = mlText ? parseCSV(mlText) : [];
    totalsRows = totalsText ? parseCSV(totalsText) : [];
  } catch (e) {
    setStatus("Failed to load NHL files.");
    return;
  }

  // Index totals by game_id (one row per game, per your spec)
  const totalsByGameId = new Map();
  for (const r of totalsRows) {
    const gid = (r.game_id || "").trim();
    if (!gid) continue;
    if (!totalsByGameId.has(gid)) totalsByGameId.set(gid, r);
  }

  // Group ML rows by game_id in file order
  const gameOrder = [];
  const mlByGameId = new Map();

  for (const r of mlRows) {
    const gid = (r.game_id || "").trim();
    if (!gid) continue;

    if (!mlByGameId.has(gid)) {
      mlByGameId.set(gid, []);
      gameOrder.push(gid);
    }
    mlByGameId.get(gid).push(r);
  }

  if (gameOrder.length === 0) {
    setStatus("No NHL games found for this date.");
    return;
  }

  renderNHLGames(gameOrder, mlByGameId, totalsByGameId);
}

function format2(n) {
  const x = Number(n);
  if (!Number.isFinite(x)) return "";
  return x.toFixed(2);
}

function safeGet(obj, key) {
  if (!obj) return "";
  const v = obj[key];
  return (v ?? "").toString().trim();
}

function renderNHLGames(gameOrder, mlByGameId, totalsByGameId) {
  const container = document.getElementById("games");
  if (!container) return;

  container.innerHTML = "";

  for (const gid of gameOrder) {
    const rows = mlByGameId.get(gid) || [];
    const first = rows[0] || null;

    // Header requires: "team at opponent" derived from ML edge file first occurrence
    const headerTeam = safeGet(first, "team");
    const headerOpp = safeGet(first, "opponent");
    const headerText = (headerTeam && headerOpp) ? `${headerTeam} at ${headerOpp}` : "";

    // Team row is first row encountered for that game_id
    const teamName = headerTeam || "";
    const teamWinProb = first ? format2(safeGet(first, "win_probability")) : "";
    const teamGoals = first ? format2(safeGet(first, "goals")) : "";
    const teamAcceptML = first ? safeGet(first, "acceptable_american_odds") : "";

    // Opponent row should match on (opponent + game_id) as requested.
    // We locate the row where team == first.opponent. If not found, fallback to second row if present.
    let oppRow = null;
    if (first && headerOpp) {
      for (const r of rows) {
        if (safeGet(r, "team") === headerOpp) {
          oppRow = r;
          break;
        }
      }
    }
    if (!oppRow && rows.length >= 2) oppRow = rows[1] || null;

    const oppName = headerOpp || (oppRow ? safeGet(oppRow, "team") : "");
    const oppWinProb = oppRow ? format2(safeGet(oppRow, "win_probability")) : "";
    const oppGoals = oppRow ? format2(safeGet(oppRow, "goals")) : "";
    const oppAcceptML = oppRow ? safeGet(oppRow, "acceptable_american_odds") : "";

    // Totals row (one per game)
    const totals = totalsByGameId.get(gid) || null;
    const totalsSide = totals ? safeGet(totals, "side") : "";
    const totalsMarket = totals ? safeGet(totals, "market_total") : "";
    const totalsAccept = totals ? safeGet(totals, "acceptable_american_odds") : "";

    const takeOUForTeamLine = (totalsSide || totalsMarket) ? `${totalsSide} ${totalsMarket}`.trim() : "";

    const box = document.createElement("div");
    box.className = "game-box";

    const h = document.createElement("div");
    h.className = "game-header";
    h.textContent = headerText || `Game ID: ${gid}`;
    box.appendChild(h);

    const table = document.createElement("table");
    table.className = "game-grid";

    table.innerHTML = `
      <thead>
        <tr>
          <th class="cell-muted"></th>
          <th>Win Probability</th>
          <th>Projected Goals</th>
          <th>Take ML at</th>
          <th>Take Over/Under at</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>${escapeHtml(teamName)}</strong></td>
          <td>${escapeHtml(teamWinProb)}</td>
          <td>${escapeHtml(teamGoals)}</td>
          <td>${escapeHtml(teamAcceptML)}</td>
          <td>${escapeHtml(takeOUForTeamLine)}</td>
        </tr>
        <tr>
          <td><strong>${escapeHtml(oppName)}</strong></td>
          <td>${escapeHtml(oppWinProb)}</td>
          <td>${escapeHtml(oppGoals)}</td>
          <td>${escapeHtml(oppAcceptML)}</td>
          <td>${escapeHtml(totalsAccept)}</td>
        </tr>
      </tbody>
    `;

    box.appendChild(table);
    container.appendChild(box);
  }
}

function escapeHtml(str) {
  return (str ?? "").toString()
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/* Existing functions you already had can remain below if needed.
   Keeping them here would be redundant; NHL page uses loadNHLDaily().
*/
