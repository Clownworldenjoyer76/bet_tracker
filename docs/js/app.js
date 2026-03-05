(() => {
  const dateInput = document.getElementById("p-date");
  const leagueSelect = document.getElementById("league-filter");
  const statusEl = document.getElementById("status");
  const gamesEl = document.getElementById("games");

  if (!dateInput || !leagueSelect || !statusEl || !gamesEl) return;
  if (!window.REPO_CONFIG) {
    statusEl.textContent = "Missing config.";
    return;
  }

  init();

  function init() {
    leagueSelect.innerHTML = "";
    (REPO_CONFIG.leagues || []).forEach(l => {
      const opt = document.createElement("option");
      opt.value = l;
      opt.textContent = l;
      leagueSelect.appendChild(opt);
    });

    dateInput.value = new Date().toLocaleDateString("en-CA");

    dateInput.addEventListener("change", loadPage);
    leagueSelect.addEventListener("change", loadPage);

    loadPage();
  }

  async function loadPage() {
    const date = (dateInput.value || "").replaceAll("-", "_");
    const league = leagueSelect.value;

    statusEl.textContent = "Loading...";
    gamesEl.innerHTML = "";

    const cfg = REPO_CONFIG[league];
    if (!cfg) {
      statusEl.textContent = "No config found.";
      return;
    }

    const selectFiles = cfg.selectFiles(date) || [];
    const predFile = cfg.predFile(date);
    const bookFile = cfg.bookFile(date);

    try {
      const selectRows = await fetchMultiple(selectFiles);
      const predRows = await fetchCSV(predFile);
      const bookRows = await fetchCSV(bookFile);

      const predMap = buildGameMap(predRows);
      const bookMap = buildGameMap(bookRows);

      const merged = selectRows.map(sel => {
        const key = makeKeyFromRow(sel);
        const pred = predMap[key] || {};
        const book = bookMap[key] || {};
        return { ...sel, ...pred, ...book, __key: key };
      });

      const grouped = {};
      merged.forEach(r => {
        if (!grouped[r.__key]) grouped[r.__key] = [];
        grouped[r.__key].push(r);
      });

      const sortedGameKeys = Object.keys(grouped).sort((a, b) => {
        return parseTime(grouped[a][0].game_time) - parseTime(grouped[b][0].game_time);
      });

      renderGames(grouped, sortedGameKeys, league, cfg);

      statusEl.textContent = merged.length + " picks found";
    } catch {
      statusEl.textContent = "No data found.";
    }
  }

  function parseTime(t) {
    if (!t) return 0;
    const m = String(t).match(/(\d+):(\d+)\s*(AM|PM)/i);
    if (!m) return 0;
    let h = parseInt(m[1], 10);
    const min = parseInt(m[2], 10);
    const p = m[3].toUpperCase();
    if (p === "PM" && h !== 12) h += 12;
    if (p === "AM" && h === 12) h = 0;
    return h * 60 + min;
  }

  async function fetchMultiple(paths) {
    let rows = [];
    for (const p of paths) {
      const r = await fetch(p);
      if (!r.ok) continue;
      const txt = await r.text();
      rows = rows.concat(parseCSV(txt));
    }
    return rows;
  }

  async function fetchCSV(path) {
    const r = await fetch(path);
    if (!r.ok) return [];
    const txt = await r.text();
    return parseCSV(txt);
  }

  function parseCSV(text) {
    const raw = (text ?? "").trim();
    if (!raw) return [];
    const lines = raw.split(/\r?\n/);
    if (lines.length < 2) return [];
    const headers = lines[0].split(",").map(h => h.trim());
    return lines.slice(1).map(line => {
      const values = line.split(",");
      const obj = {};
      headers.forEach((h, i) => (obj[h] = (values[i] ?? "")));
      return obj;
    });
  }

  function buildGameMap(rows) {
    const map = {};
    rows.forEach(r => {
      const key = makeKeyFromRow(r);
      map[key] = r;
    });
    return map;
  }

  function makeKeyFromRow(r) {
    const gameDate = (r.game_date || "").trim();
    const homeTeam = (r.home_team || "").trim();
    const awayTeam = (r.away_team || "").trim();
    return gameDate + "|" + homeTeam + "|" + awayTeam;
  }

  function formatMarket(market) {
    if (!market) return "-";
    return String(market)
      .toLowerCase()
      .replaceAll("_", " ")
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  function formatLine(line, market) {
    if (line === "" || line == null) return "-";
    let num = parseFloat(line);
    if (isNaN(num)) return String(line);

    if (market && String(market).toLowerCase().includes("total")) {
      return num.toString();
    }
    if (num > 0) return "+" + num;
    return num.toString();
  }

  function renderGames(grouped, gameKeys, league, cfg) {
    gamesEl.innerHTML = "";

    gameKeys.forEach(key => {
      const picks = grouped[key];
      const r = picks[0] || {};
      const isHockey = !!cfg.isHockey;

      const projAway = isHockey ? r.away_projected_goals : r.away_projected_points;
      const projHome = isHockey ? r.home_projected_goals : r.home_projected_points;
      const projTotal = isHockey ? r.total_projected_goals : r.total_projected_points;

      const spreadAway = isHockey ? r.away_puck_line : r.away_spread;
      const spreadHome = isHockey ? r.home_puck_line : r.home_spread;

      const spreadAwayOdds = isHockey ? r.away_dk_puck_line_american : r.away_dk_spread_american;
      const spreadHomeOdds = isHockey ? r.home_dk_puck_line_american : r.home_dk_spread_american;

      let picksHtml = "";

      picks.forEach(p => {
        let market = "";
        let line = p.line;
        let odds = "-";
        let edge = "-";

        if (p.take_bet) {
          market = p.take_bet;
          odds = p.take_odds || "-";
          edge = p.take_bet_edge_pct
            ? (parseFloat(p.take_bet_edge_pct) * 100).toFixed(2) + "%"
            : "-";
        } else {
          market = (p.market_type || "") + " " + (p.bet_side || "");

          if (p.bet_side === "home") edge = p.home_edge_decimal;
          if (p.bet_side === "away") edge = p.away_edge_decimal;
          if (p.bet_side === "over") edge = p.over_edge_decimal;
          if (p.bet_side === "under") edge = p.under_edge_decimal;

          if (edge !== "" && edge != null && !isNaN(parseFloat(edge))) {
            edge = (parseFloat(edge) * 100).toFixed(2) + "%";
          } else {
            edge = "-";
          }
        }

        const formattedMarket = formatMarket(market);
        const formattedLine = formatLine(line, market);

        picksHtml += `
          <div class="pick-block">
            <div class="game-market">${formattedMarket}</div>
            <div class="game-line">${formattedLine}</div>
            <div class="game-odds">Odds: ${odds}</div>
            <div class="game-edge">Edge: ${edge}</div>
          </div>
        `;
      });

      const card = document.createElement("div");
      card.className = "game-card";

      card.innerHTML = `
        <div class="game-time">${r.game_time || "-"}</div>
        <div class="game-matchup">${r.away_team || "-"} @ ${r.home_team || "-"}</div>

        <div class="game-proj">
          Proj: ${projAway || "-"} - ${projHome || "-"}
          (Total: ${projTotal || "-"})
        </div>

        <div class="game-book">
          ML: ${r.away_dk_moneyline_american || "-"} / ${r.home_dk_moneyline_american || "-"}
          <br>
          Line: ${spreadAway || "-"} (${spreadAwayOdds || "-"})
          / ${spreadHome || "-"} (${spreadHomeOdds || "-"})
          <br>
          Total: ${r.total || "-"} (O ${r.dk_total_over_american || "-"} / U ${r.dk_total_under_american || "-"})
        </div>

        <hr style="margin:10px 0; opacity:.2">

        ${picksHtml}
      `;

      gamesEl.appendChild(card);
    });
  }
})();
