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

  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  if (rows.length === 0) return [];

  // Handle potential BOM on first header
  const headers = rows[0].map((h, idx) => {
    const t = (h ?? "").trim();
    if (idx === 0) return t.replace(/^\uFEFF/, "");
    return t;
  });

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
  if (!el) return;
  el.textContent = msg || "";
}

function safeGet(obj, key) {
  if (!obj) return "";
  const v = obj[key];
  return (v ?? "").toString().trim();
}

function format2(n) {
  const x = Number(n);
  if (!Number.isFinite(x)) return "";
  return x.toFixed(2);
}

function escapeHtml(str) {
  return (str ?? "").toString()
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/**
 * Fetch text, returning { ok, status, text, url }.
 * Never throws.
 */
async function fetchTextResult(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) {
      return { ok: false, status: res.status, text: "", url };
    }
    const text = await res.text();
    return { ok: true, status: res.status, text, url };
  } catch {
    return { ok: false, status: 0, text: "", url };
  }
}

/**
 * Try a list of URLs in order. Return the first that succeeds.
 * Returns { ok, status, text, url, tried: [...] }.
 */
async function fetchFirstOk(urls) {
  const tried = [];
  for (const url of urls) {
    const r = await fetchTextResult(url);
    tried.push({ url: r.url, ok: r.ok, status: r.status });
    if (r.ok && r.text) return { ok: true, status: r.status, text: r.text, url: r.url, tried };
    if (r.ok && !r.text) {
      // File exists but empty; still treat as "ok" but empty
      return { ok: true, status: r.status, text: r.text, url: r.url, tried };
    }
  }
  return { ok: false, status: 0, text: "", url: "", tried };
}

/* ====================== NHL (UNCHANGED) ====================== */

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
      fetchTextResult(mlUrl).then(r => r.ok ? r.text : ""),
      fetchTextResult(totalsUrl).then(r => r.ok ? r.text : "")
    ]);

    mlRows = mlText ? parseCSV(mlText) : [];
    totalsRows = totalsText ? parseCSV(totalsText) : [];
  } catch {
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

function renderNHLGames(gameOrder, mlByGameId, totalsByGameId) {
  const container = document.getElementById("games");
  if (!container) return;

  container.innerHTML = "";

  for (const gid of gameOrder) {
    const rows = mlByGameId.get(gid) || [];
    const first = rows[0] || null;

    const headerTeam = safeGet(first, "team");
    const headerOpp = safeGet(first, "opponent");
    const headerText = (headerTeam && headerOpp) ? `${headerTeam} at ${headerOpp}` : "";

    const teamName = headerTeam || "";
    const teamWinProb = first ? format2(safeGet(first, "win_probability")) : "";
    const teamGoals = first ? format2(safeGet(first, "goals")) : "";
    const teamAcceptML = first ? safeGet(first, "acceptable_american_odds") : "";

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

/* ====================== SOCCER (FIXED + DIAGNOSTICS) ====================== */

/**
 * Soccer loader:
 * - Tries BOTH file naming conventions for sides + totals:
 *   sides:  docs/win/edge/edge_soc_YYYY_MM_DD.csv  OR edge_soc_YYYY-MM-DD.csv
 *   totals: docs/win/soc/edge_soc_totals_YYYY_MM_DD.csv OR edge_soc_totals_YYYY-MM-DD.csv
 * - Groups by game_id in file order (from sides file)
 * - Renders games even if totals missing
 */
async function loadSoccerDaily(selectedDateYYYYMMDD) {
  setStatus("");

  const gamesEl = document.getElementById("games");
  if (gamesEl) gamesEl.innerHTML = "";

  const parts = (selectedDateYYYYMMDD || "").split("-");
  if (parts.length !== 3) {
    setStatus("Invalid date selected.");
    return;
  }

  const yyyy = parts[0];
  const mm = parts[1];
  const dd = parts[2];

  const fileDateUnderscore = `${yyyy}_${mm}_${dd}`;
  const fileDateHyphen = `${yyyy}-${mm}-${dd}`;

  const sidesUrls = [
    `${RAW_BASE}/docs/win/edge/edge_soc_${fileDateUnderscore}.csv`,
    `${RAW_BASE}/docs/win/edge/edge_soc_${fileDateHyphen}.csv`
  ];

  const totalsUrls = [
    `${RAW_BASE}/docs/win/soc/edge_soc_totals_${fileDateUnderscore}.csv`,
    `${RAW_BASE}/docs/win/soc/edge_soc_totals_${fileDateHyphen}.csv`
  ];

  const [sidesFetch, totalsFetch] = await Promise.all([
    fetchFirstOk(sidesUrls),
    fetchFirstOk(totalsUrls)
  ]);

  const sidesText = sidesFetch.ok ? sidesFetch.text : "";
  const totalsText = totalsFetch.ok ? totalsFetch.text : "";

  const sides = sidesText ? parseCSV(sidesText) : [];
  const totals = totalsText ? parseCSV(totalsText) : [];

  if (sides.length === 0) {
    const triedLines = sidesFetch.tried
      .map(t => `- ${t.url} (${t.ok ? "OK" : "HTTP " + t.status})`)
      .join("\n");
    setStatus(
      "No soccer games found for this date. Sides file not loaded.\nTried:\n" + triedLines
    );
    return;
  }

  // Group sides by game_id in file order
  const gameOrder = [];
  const sidesByGameId = new Map();
  for (const r of sides) {
    const gid = safeGet(r, "game_id");
    if (!gid) continue;

    if (!sidesByGameId.has(gid)) {
      sidesByGameId.set(gid, []);
      gameOrder.push(gid);
    }
    sidesByGameId.get(gid).push(r);
  }

  if (gameOrder.length === 0) {
    setStatus("Soccer sides file loaded, but no game_id rows found.");
    return;
  }

  // Index totals by game_id (can be multiple rows per game)
  const totalsByGameId = new Map();
  for (const r of totals) {
    const gid = safeGet(r, "game_id");
    if (!gid) continue;
    if (!totalsByGameId.has(gid)) totalsByGameId.set(gid, []);
    totalsByGameId.get(gid).push(r);
  }

  // If totals missing, say so once (but still render sides)
  if (!totalsFetch.ok || totals.length === 0) {
    const triedLines = totalsFetch.tried
      .map(t => `- ${t.url} (${t.ok ? "OK" : "HTTP " + t.status})`)
      .join("\n");
    setStatus(
      "Soccer sides loaded. Totals not loaded for this date.\nTried:\n" + triedLines
    );
  }

  renderSoccerGames(gameOrder, sidesByGameId, totalsByGameId);
}

function renderSoccerGames(gameOrder, sidesByGameId, totalsByGameId) {
  const container = document.getElementById("games");
  if (!container) return;

  container.innerHTML = "";

  for (const gid of gameOrder) {
    const rows = sidesByGameId.get(gid) || [];
    if (rows.length === 0) continue;

    // Your sides file has: team + opponent
    const first = rows[0] || null;
    const teamA = safeGet(first, "team");
    const teamB = safeGet(first, "opponent");

    const headerText = (teamA && teamB) ? `${teamA} vs ${teamB}` : `Game ID: ${gid}`;

    // For display: try to get the opposing row (team == opponent)
    let oppRow = null;
    if (teamB) {
      for (const r of rows) {
        if (safeGet(r, "team") === teamB) {
          oppRow = r;
          break;
        }
      }
    }

    const teamARow = first;
    const teamBRow = oppRow || (rows.length >= 2 ? rows[1] : null);

    const aName = teamARow ? safeGet(teamARow, "team") : "";
    const aProb = teamARow ? format2(safeGet(teamARow, "win_probability")) : "";
    const aAccept = teamARow ? safeGet(teamARow, "acceptable_american_odds") : "";

    const bName = teamBRow ? safeGet(teamBRow, "team") : "";
    const bProb = teamBRow ? format2(safeGet(teamBRow, "win_probability")) : "";
    const bAccept = teamBRow ? safeGet(teamBRow, "acceptable_american_odds") : "";

    const totalsRows = totalsByGameId.get(gid) || [];

    let totalsHtml = "";
    for (const t of totalsRows) {
      const side = safeGet(t, "side");
      const mt = safeGet(t, "market_total");
      const acc = safeGet(t, "acceptable_american_odds");
      const line = [side, mt].filter(Boolean).join(" ");
      totalsHtml += `<div>${escapeHtml(`${line} @ ${acc}`.trim())}</div>`;
    }

    const box = document.createElement("div");
    box.className = "game-box";

    const h = document.createElement("div");
    h.className = "game-header";
    h.textContent = headerText;
    box.appendChild(h);

    const table = document.createElement("table");
    table.className = "game-grid";

    table.innerHTML = `
      <thead>
        <tr>
          <th>Team</th>
          <th>Win Probability</th>
          <th>Take ML at</th>
          <th>Totals</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>${escapeHtml(aName)}</strong></td>
          <td>${escapeHtml(aProb)}</td>
          <td>${escapeHtml(aAccept)}</td>
          <td rowspan="2">${totalsHtml}</td>
        </tr>
        <tr>
          <td><strong>${escapeHtml(bName)}</strong></td>
          <td>${escapeHtml(bProb)}</td>
          <td>${escapeHtml(bAccept)}</td>
        </tr>
      </tbody>
    `;

    box.appendChild(table);
    container.appendChild(box);
  }
}
