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

  for (const c of text.replace(/\r/g, "").split("")) {
    if (c === '"' && inQuotes) {
      inQuotes = false;
      continue;
    }
    if (c === '"' && !inQuotes) {
      inQuotes = true;
      continue;
    }
    if (c === "," && !inQuotes) {
      row.push(field.trim());
      field = "";
      continue;
    }
    if (c === "\n" && !inQuotes) {
      row.push(field.trim());
      rows.push(row);
      row = [];
      field = "";
      continue;
    }
    field += c;
  }
  if (field || row.length) {
    row.push(field.trim());
    rows.push(row);
  }

  const headers = rows.shift();
  return rows.map(r => {
    const o = {};
    headers.forEach((h, i) => o[h] = r[i] ?? "");
    return o;
  });
}

function formatPct(n) {
  const x = Number(n);
  return Number.isFinite(x) ? `${(x * 100).toFixed(2)}%` : "";
}

function format2(n) {
  const x = Number(n);
  return Number.isFinite(x) ? x.toFixed(2) : "";
}

function mlClassFromProb(p) {
  const x = Number(p);
  if (x > 0.65) return "ml-green";
  if (x > 0.5) return "ml-orange";
  return "ml-pink";
}

/* ================= NHL ================= */

async function loadNHLDaily(date) {
  document.getElementById("games").innerHTML = "";
  const d = date.replaceAll("-", "_");

  const spreadsUrl = `${RAW_BASE}/docs/win/nhl/spreads/nhl_spreads_${d}.csv`;
  const edgeUrl = `${RAW_BASE}/docs/win/edge/edge_nhl_${d}.csv`;

  let spreads, edge;

  try {
    spreads = parseCSV(await fetch(spreadsUrl).then(r => r.text()));
    edge = parseCSV(await fetch(edgeUrl).then(r => r.text()));
  } catch {
    document.getElementById("status").textContent = "Failed to load NHL files.";
    return;
  }

  const edgeByTeam = new Map();
  edge.forEach(r => edgeByTeam.set(r.team, r.acceptable_american_odds));

  const games = new Map();
  spreads.forEach(r => {
    if (!games.has(r.game_id)) games.set(r.game_id, []);
    games.get(r.game_id).push(r);
  });

  for (const rows of games.values()) {
    if (rows.length !== 2) continue;

    const away = rows.find(r => r.side === "away");
    const home = rows.find(r => r.side === "home");

    const box = document.createElement("div");
    box.className = "game-box";

    box.innerHTML = `
      <div class="game-header">
        ${away.away_team} vs ${home.home_team} — ${away.time}
      </div>

      <table class="game-grid">
        <thead>
          <tr>
            <th></th>
            <th>Win Probability</th>
            <th>Projected Goals</th>
            <th>Take O/U at</th>
            <th>Take ML at</th>
            <th>Take +1.5</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>${away.away_team}</strong></td>
            <td>${formatPct(away.away_win_prob)}</td>
            <td>${format2(away.away_goals)}</td>
            <td>${away.market_total}</td>
            <td class="${mlClassFromProb(away.away_win_prob)}">
              ${edgeByTeam.get(away.away_team) || ""}
            </td>
            <td>${away.away_win_prob < home.home_win_prob ? away.puck_line_acceptable_amer : ""}</td>
          </tr>

          <tr>
            <td><strong>${home.home_team}</strong></td>
            <td>${formatPct(home.home_win_prob)}</td>
            <td>${format2(home.home_goals)}</td>
            <td>${home.side}</td>
            <td class="${mlClassFromProb(home.home_win_prob)}">
              ${edgeByTeam.get(home.home_team) || ""}
            </td>
            <td>${home.home_win_prob < away.away_win_prob ? home.puck_line_acceptable_amer : ""}</td>
          </tr>

          <tr class="draw-row">
            <td><strong>Over/Under</strong></td>
            <td></td>
            <td></td>
            <td>${away.ou_prob}</td>
            <td></td>
            <td></td>
          </tr>
        </tbody>
      </table>
    `;

    document.getElementById("games").appendChild(box);
  }
}
