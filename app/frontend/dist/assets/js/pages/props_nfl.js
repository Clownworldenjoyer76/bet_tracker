    const RAW_ROOT =
      "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main";

    const AVAILABLE_SEASONS = [2026];
    const AVAILABLE_WEEKS = Array.from({ length: 18 }, (_, i) => i + 1);

    const PROP_TYPES = [
      {
        key: "passing",
        label: "Passing Yards",
        path: "passing",
        suffix: "passing",
        line: "actual_prop_total_passing_yards",
        projection: "prop_engine_passing_yards",
        low: "prop_engine_passing_yards_low",
        high: "prop_engine_passing_yards_high"
      },
      {
        key: "rushing",
        label: "Rushing Yards",
        path: "rushing",
        suffix: "rushing",
        line: "actual_prop_total_rushing_yards",
        projection: "prop_engine_rushing_yards",
        low: "prop_engine_rushing_yards_low",
        high: "prop_engine_rushing_yards_high"
      },
      {
        key: "receiving",
        label: "Receiving Yards",
        path: "receiving",
        suffix: "receiving",
        line: "actual_prop_total_receiving_yards",
        projection: "prop_engine_receiving_yards",
        low: "prop_engine_receiving_yards_low",
        high: "prop_engine_receiving_yards_high"
      },
      {
        key: "kicking",
        label: "Kicking Points",
        path: "kicking",
        suffix: "kicking",
        line: "actual_prop_total_kicking_points",
        projection: "prop_engine_kicking_points",
        low: "prop_engine_kicking_points_low",
        high: "prop_engine_kicking_points_high"
      },
      {
        key: "defense",
        label: "Tackles",
        path: "defense",
        suffix: "defense",
        line: "actual_prop_total_tackles",
        projection: "prop_engine_tackles",
        low: "prop_engine_tackles_low",
        high: "prop_engine_tackles_high"
      },
      {
        key: "pass_rush",
        label: "Passing/Rushing Yards",
        path: "combo/pass_rush_yds",
        suffix: "pass_rush_yds",
        line: "actual_prop_total_passing_plus_rushing_yards",
        projection: "prop_engine_pr",
        low: "prop_engine_pr_low",
        high: "prop_engine_pr_high"
      },
      {
        key: "rec_rush",
        label: "Rushing/Receiving Yards",
        path: "combo/rec_rush_yds",
        suffix: "rec_rush_yds",
        line: "actual_prop_total_rushing_plus_receiving_yards",
        projection: "prop_engine_rr",
        low: "prop_engine_rr_low",
        high: "prop_engine_rr_high"
      }
    ];

    const state = {
      season: 2026,
      week: 1,
      schedule: [],
      props: [],
      selectedProp: null,
      selectedGame: null
    };

    function parseCsv(text) {
      const rows = [];
      let row = [];
      let field = "";
      let quoted = false;

      for (let i = 0; i < text.length; i++) {
        const ch = text[i];

        if (quoted) {
          if (ch === '"') {
            if (text[i + 1] === '"') {
              field += '"';
              i++;
            } else {
              quoted = false;
            }
          } else {
            field += ch;
          }
        } else {
          if (ch === '"') {
            quoted = true;
          } else if (ch === ",") {
            row.push(field);
            field = "";
          } else if (ch === "\n") {
            row.push(field.replace(/\r$/, ""));
            rows.push(row);
            row = [];
            field = "";
          } else {
            field += ch;
          }
        }
      }

      if (field.length || row.length) {
        row.push(field.replace(/\r$/, ""));
        rows.push(row);
      }

      if (!rows.length) return [];

      const headers = rows[0].map(h => h.trim());

      return rows
        .slice(1)
        .filter(r => r.some(v => String(v).trim() !== ""))
        .map(r => {
          const obj = {};
          headers.forEach((h, index) => {
            obj[h] = r[index] ?? "";
          });
          return obj;
        });
    }

    async function fetchCsv(url) {
      const response = await fetch(url, { cache: "no-store" });

      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }

      return parseCsv(await response.text());
    }

    function stage2Url(season, week, config) {
      return (
        `${RAW_ROOT}/docs/win/football/prop_engine/prop_picks_final/` +
        `${season}/stage_2/week_${week}/${config.path}/` +
        `week_${week}_${config.suffix}.csv`
      );
    }

    function scheduleUrl(week) {
      return (
        `${RAW_ROOT}/docs/win/football/nfl/00_intake/schedule/weekly/` +
        `week_${week}_NFL_weekly_schedule.csv`
      );
    }

    function numeric(value) {
      const n = Number(value);
      return Number.isFinite(n) ? n : null;
    }

    function formatProb(value) {
      const n = numeric(value);
      return n === null ? "" : n.toFixed(4);
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function gameLabel(gameId) {
      const game = state.schedule.find(
        g => String(g.game_id) === String(gameId)
      );

      if (!game) return String(gameId);

      return `${game.away_team} @ ${game.home_team}`;
    }

    function renderSeasonSelect() {
      const select = document.getElementById("seasonSelect");
      select.innerHTML = "";

      AVAILABLE_SEASONS.forEach(season => {
        const option = document.createElement("option");
        option.value = String(season);
        option.textContent = String(season);
        option.selected = season === state.season;
        select.appendChild(option);
      });
    }

    function renderWeekSelect() {
      const select = document.getElementById("weekSelect");
      select.innerHTML = "";

      AVAILABLE_WEEKS.forEach(week => {
        const option = document.createElement("option");
        option.value = String(week);
        option.textContent = `Week ${week}`;
        option.selected = week === state.week;
        select.appendChild(option);
      });
    }

    function renderPropButtons() {
      const container = document.getElementById("propButtons");
      container.innerHTML = "";

      const gameFilteredRows = state.props.filter(row => {
        if (row.pick === "no_bet") return false;
        if (!state.selectedGame) return true;
        return String(row.game_id) === state.selectedGame;
      });

      const allButton = document.createElement("button");
      allButton.textContent = `All Prop Types (${gameFilteredRows.length})`;
      allButton.classList.toggle("active", state.selectedProp === null);
      allButton.onclick = () => {
        state.selectedProp = null;
        renderPropButtons();
        renderResults();
      };
      container.appendChild(allButton);

      PROP_TYPES.forEach(config => {
        const count = gameFilteredRows.filter(
          row => row.prop_type === config.key
        ).length;

        const button = document.createElement("button");
        button.textContent = `${config.label} (${count})`;
        button.classList.toggle(
          "active",
          state.selectedProp === config.key
        );

        button.onclick = () => {
          state.selectedProp = config.key;
          renderPropButtons();
          renderResults();
        };

        container.appendChild(button);
      });
    }

    function renderGameButtons() {
      const container = document.getElementById("gameButtons");
      container.innerHTML = "";

      const allGamesCount = state.props.filter(
        row => row.pick !== "no_bet"
      ).length;

      const allGamesButton = document.createElement("button");
      allGamesButton.className = "game-button";
      allGamesButton.classList.toggle(
        "active",
        state.selectedGame === null
      );

      const allGamesTeams = document.createElement("span");
      allGamesTeams.className = "teams";
      allGamesTeams.textContent = "All Games";

      const allGamesMeta = document.createElement("span");
      allGamesMeta.className = "meta";
      allGamesMeta.textContent = `${allGamesCount} picks`;

      allGamesButton.appendChild(allGamesTeams);
      allGamesButton.appendChild(allGamesMeta);

      allGamesButton.onclick = () => {
        state.selectedGame = null;
        renderPropButtons();
        renderGameButtons();
        renderResults();
      };

      container.appendChild(allGamesButton);

      state.schedule.forEach(game => {
        const gameId = String(game.game_id);
        const count = state.props.filter(
          row =>
            String(row.game_id) === gameId &&
            row.pick !== "no_bet"
        ).length;

        const button = document.createElement("button");
        button.className = "game-button";
        button.classList.toggle(
          "active",
          state.selectedGame === gameId
        );

        const teams = document.createElement("span");
        teams.className = "teams";
        teams.textContent = `${game.away_team} @ ${game.home_team}`;

        const meta = document.createElement("span");
        meta.className = "meta";
        meta.textContent = `${game.game_date || ""} • ${count} picks`;

        button.appendChild(teams);
        button.appendChild(meta);

        button.onclick = () => {
          state.selectedGame = gameId;
          state.selectedProp = null;
          renderPropButtons();
          renderGameButtons();
          renderResults();
        };

        container.appendChild(button);
      });
    }

    function renderResults() {
      const target = document.getElementById("results");
      const title = document.getElementById("resultsTitle");
      const count = document.getElementById("resultCount");

      let rows = state.props.filter(row => row.pick !== "no_bet");

      if (state.selectedGame) {
        rows = rows.filter(
          row => String(row.game_id) === state.selectedGame
        );
      }

      let selectedPropConfig = null;
      if (state.selectedProp) {
        selectedPropConfig = PROP_TYPES.find(
          p => p.key === state.selectedProp
        );

        rows = rows.filter(
          row => row.prop_type === state.selectedProp
        );
      }

      if (state.selectedGame && selectedPropConfig) {
        title.textContent = `${gameLabel(state.selectedGame)} · ${selectedPropConfig.label}`;
      } else if (state.selectedGame) {
        title.textContent = gameLabel(state.selectedGame);
      } else if (selectedPropConfig) {
        title.textContent = selectedPropConfig.label;
      } else {
        title.textContent = "Picks";
      }

      rows.sort(
        (a, b) =>
          (numeric(b.pick_prob) ?? -1) -
          (numeric(a.pick_prob) ?? -1)
      );

      count.textContent = `${rows.length} picks`;

      if (!rows.length) {
        target.innerHTML =
          '<div class="empty">No qualifying picks.</div>';
        return;
      }

      const cards = rows.map(row => {
        const config = PROP_TYPES.find(
          p => p.key === row.prop_type
        );

        const pickClass =
          row.pick === "over" ? "pick-over" : "pick-under";

        return `
          <article class="pick-card-nfl">
            <div class="pick-card-head">
              <div>
                <div class="pick-player">${escapeHtml(row.player_name)}</div>
                <div class="pick-prop">${escapeHtml(config?.label || row.prop_type)}</div>
                <div class="pick-game">${escapeHtml(gameLabel(row.game_id))}</div>
              </div>
              <div class="pick-choice ${pickClass}">${escapeHtml(row.pick)}</div>
            </div>
            <div class="pick-metrics">
              <div class="pick-metric">
                <div class="pick-metric-label">Sportsbook Line</div>
                <div class="pick-metric-value">${escapeHtml(row[config.line])}</div>
              </div>
              <div class="pick-metric">
                <div class="pick-metric-label">Pick Prob</div>
                <div class="pick-metric-value prob">${escapeHtml(formatProb(row.pick_prob))}</div>
              </div>
              <div class="pick-metric">
                <div class="pick-metric-label">Over Prob</div>
                <div class="pick-metric-value">${escapeHtml(formatProb(row.over_prob))}</div>
              </div>
              <div class="pick-metric">
                <div class="pick-metric-label">Under Prob</div>
                <div class="pick-metric-value">${escapeHtml(formatProb(row.under_prob))}</div>
              </div>
              <div class="pick-metric">
                <div class="pick-metric-label">Projection</div>
                <div class="pick-metric-value">${escapeHtml(row[config.projection])}</div>
              </div>
              <div class="pick-metric">
                <div class="pick-metric-label">Low</div>
                <div class="pick-metric-value">${escapeHtml(row[config.low])}</div>
              </div>
              <div class="pick-metric">
                <div class="pick-metric-label">High</div>
                <div class="pick-metric-value">${escapeHtml(row[config.high])}</div>
              </div>
            </div>
          </article>
        `;
      }).join("");

      target.innerHTML = `<div class="pick-grid">${cards}</div>`;
    }

    async function loadWeek() {
      const status = document.getElementById("status");

      status.textContent =
        `Loading ${state.season} Week ${state.week}...`;

      state.schedule = [];
      state.props = [];

      const schedulePromise = fetchCsv(scheduleUrl(state.week))
        .catch(() => []);

      const propPromises = PROP_TYPES.map(async config => {
        try {
          const rows = await fetchCsv(
            stage2Url(state.season, state.week, config)
          );

          return rows.map(row => ({
            ...row,
            prop_type: config.key
          }));
        } catch (_) {
          return [];
        }
      });

      const [schedule, propGroups] = await Promise.all([
        schedulePromise,
        Promise.all(propPromises)
      ]);

      state.schedule = schedule.filter(
        row =>
          !row.season ||
          String(row.season) === String(state.season)
      );

      state.props = propGroups.flat();

      renderPropButtons();
      renderGameButtons();
      renderResults();

      if (!state.schedule.length && !state.props.length) {
        status.textContent =
          `No data found for ${state.season} Week ${state.week}.`;
      } else {
        status.textContent =
          `${state.season} Week ${state.week}`;
      }
    }

    async function init() {
      renderSeasonSelect();
      renderWeekSelect();

      document.getElementById("seasonSelect").addEventListener("change", async event => {
        state.season = Number(event.target.value);
        state.selectedProp = null;
        state.selectedGame = null;
        await loadWeek();
      });

      document.getElementById("weekSelect").addEventListener("change", async event => {
        state.week = Number(event.target.value);
        state.selectedProp = null;
        state.selectedGame = null;
        await loadWeek();
      });

      await loadWeek();
    }

    init();
  
