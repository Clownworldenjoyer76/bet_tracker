const GH_OWNER = "Clownworldenjoyer76";
const GH_REPO = "bet_tracker";
const GH_BRANCH = "main";
const RAW_BASE = `https://raw.githubusercontent.com/${GH_OWNER}/${GH_REPO}/${GH_BRANCH}`;

/* ======================================================== NCAAB ======================================================== */

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
    if (statusEl) statusEl.textContent = "No NCAAB ML file found.";
    return;
  }

  try { spreads = parseCSV(await fetchText(spreadsUrl)); } catch {}
  try { totals = parseCSV(await fetchText(totalsUrl)); } catch {}
  try { dkRows = parseCSV(await fetchText(dkUrl)); } catch {}

  if (!mlRows.length) {
    if (statusEl) statusEl.textContent = "No NCAAB games found.";
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

  renderNCAABGames(
    mlRows,
    spreadsByGame,
    totalsByGame,
    timeByGame,
    d
  );
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
      window.location.href = `ncaab-game.html?date=${d}&game_id=${g.game_id}`;

    box.innerHTML = `
      <div class="game-header">
        ${escapeHtml(g.away_team)} @ ${escapeHtml(g.home_team)}
        ${gameTime ? ` — ${escapeHtml(gameTime)}` : ""}
      </div>

      <div class="game-subheader">
        Projected Total: ${format2(g.game_projected_points)}
      </div>

      <table class="game-grid large-grid">
        <thead>
          <tr>
            <th></th>
            <th>Win %</th>
            <th>Proj Pts</th>
            <th>Fair ML</th>
            <th>Accept ML</th>
            <th>DK ML</th>
            <th>Spread</th>
            <th>Spread Accept</th>
            <th>Handle %</th>
            <th>Bets %</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>${escapeHtml(g.away_team)}</strong></td>
            <td>${formatPct(g.away_team_moneyline_win_prob)}</td>
            <td>${format2(g.away_team_projected_points)}</td>
            <td>${escapeHtml(g.away_ml_fair_american_odds)}</td>
            <td>${escapeHtml(g.away_ml_acceptable_american_odds)}</td>
            <td>${escapeHtml(g.dk_away_odds)}</td>
            <td>${escapeHtml(spreads.away_spread || "")}</td>
            <td>${escapeHtml(spreads.away_spread_acceptable_american_odds || "")}</td>
            <td>${format2(g.away_handle_pct)}</td>
            <td>${format2(g.away_bets_pct)}</td>
          </tr>

          <tr>
            <td><strong>${escapeHtml(g.home_team)}</strong></td>
            <td>${formatPct(g.home_team_moneyline_win_prob)}</td>
            <td>${format2(g.home_team_projected_points)}</td>
            <td>${escapeHtml(g.home_ml_fair_american_odds)}</td>
            <td>${escapeHtml(g.home_ml_acceptable_american_odds)}</td>
            <td>${escapeHtml(g.dk_home_odds)}</td>
            <td>${escapeHtml(spreads.home_spread || "")}</td>
            <td>${escapeHtml(spreads.home_spread_acceptable_american_odds || "")}</td>
            <td>${format2(g.home_handle_pct)}</td>
            <td>${format2(g.home_bets_pct)}</td>
          </tr>
        </tbody>
      </table>

      <div class="totals-section">
        <table class="game-grid large-grid">
          <thead>
            <tr>
              <th>Total</th>
              <th>Over %</th>
              <th>Under %</th>
              <th>Over Accept</th>
              <th>Under Accept</th>
              <th>DK Over</th>
              <th>DK Under</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>${escapeHtml(totals.total || "")}</td>
              <td>${formatPct(totals.over_probability)}</td>
              <td>${formatPct(totals.under_probability)}</td>
              <td>${escapeHtml(totals.over_acceptable_american_odds || "")}</td>
              <td>${escapeHtml(totals.under_acceptable_american_odds || "")}</td>
              <td>${escapeHtml(totals.dk_over_odds || "")}</td>
              <td>${escapeHtml(totals.dk_under_odds || "")}</td>
            </tr>
          </tbody>
        </table>
      </div>
    `;

    container.appendChild(box);
  });
}
