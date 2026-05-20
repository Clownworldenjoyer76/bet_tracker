import { esc, isPresent } from "./format.js";
import { openGameModal } from "./modal.js";

function labelForSpread(game) {
  if (game.sport === "baseball") return "RUN LINE";
  if (game.sport === "hockey") return "PUCK LINE";
  if (game.sport === "soccer") return "";
  if (game.sport === "mma") return "";
  return "SPREAD";
}

function lineHtml(label, value) {
  if (!isPresent(label) || !isPresent(value)) return "";

  return `
    <div class="gt-card-line-row">
      <span class="gt-card-line-label">${esc(label)}</span>
      <span class="gt-card-line-val">${esc(value)}</span>
    </div>
  `;
}

function arrayLineHtml(label, values) {
  const clean = (values || []).filter(isPresent);
  if (!isPresent(label) || !clean.length) return "";

  return `
    <div class="gt-card-line-row">
      <span class="gt-card-line-label">${esc(label)}</span>
      <span class="gt-card-line-val">${clean.map(esc).join(" / ")}</span>
    </div>
  `;
}

export function buildFilters(results) {
  const container = document.getElementById("gt-filters");
  if (!container) return;

  container.innerHTML = "";

  const makePill = (text, league) => {
    const pill = document.createElement("div");
    pill.className = `filter-pill${league === "all" ? " active" : ""}`;
    pill.textContent = text;
    pill.dataset.league = league;
    return pill;
  };

  container.appendChild(makePill("All", "all"));

  results.forEach(result => {
    container.appendChild(makePill(result.displayName, result.league));
  });

  container.onclick = event => {
    const pill = event.target.closest(".filter-pill");
    if (!pill) return;

    container.querySelectorAll(".filter-pill").forEach(item => {
      item.classList.remove("active");
    });

    pill.classList.add("active");

    const selected = pill.dataset.league;

    document.querySelectorAll(".gt-league-section").forEach(section => {
      section.style.display = selected === "all" || section.dataset.league === selected ? "" : "none";
    });
  };
}

export function buildGameCard(game) {
  const card = document.createElement("div");
  card.className = "gt-card";

  const c = game.card || {};
  const spreadLabel = labelForSpread(game);

  card.innerHTML = `
    <div class="gt-card-top">
      <span class="gt-card-time">${esc([c.date, c.time].filter(Boolean).join(" · "))}</span>
      <span class="gt-card-league">${esc(game.displayLeague)}</span>
    </div>

    <div class="gt-card-matchup">
      <div class="gt-card-team-row">
        <span class="gt-card-team away">${esc(c.away || "")}</span>
      </div>
      <div class="gt-card-team-row">
        <span class="gt-card-team home">${esc(c.home || "")}</span>
      </div>
    </div>

    <div class="gt-card-divider"></div>

    <div class="gt-card-lines">
      ${arrayLineHtml("ML", c.moneyline)}
      ${arrayLineHtml(spreadLabel, c.spread)}
      ${lineHtml("TOTAL", c.total)}
    </div>

    ${isPresent(c.projection) ? `
      <div class="gt-card-divider"></div>
      <div class="gt-card-proj">
        <span class="gt-card-proj-label">PROJ</span>
        <span class="gt-card-proj-val">${esc(c.projection)}</span>
      </div>
    ` : ""}
  `;

  card.addEventListener("click", () => openGameModal(game));

  return card;
}

export function renderResults(results, dateStr) {
  const gamesEl = document.getElementById("gt-games");
  const statusEl = document.getElementById("gt-status");

  if (!gamesEl || !statusEl) return;

  gamesEl.innerHTML = "";

  buildFilters(results);

  let totalGames = 0;

  results.forEach(result => {
    const section = document.createElement("section");
    section.className = "gt-league-section";
    section.dataset.league = result.league;

    const header = document.createElement("div");
    header.className = "gt-league-header";
    header.textContent = result.displayName;
    section.appendChild(header);

    const grid = document.createElement("div");
    grid.className = "gt-league-games";

    if (!result.games || result.games.length === 0) {
      grid.innerHTML = `<div class="gt-col-state empty">No games</div>`;
    } else {
      result.games.forEach(game => {
        grid.appendChild(buildGameCard(game));
      });

      totalGames += result.games.length;
    }

    section.appendChild(grid);
    gamesEl.appendChild(section);
  });

  if (totalGames === 0) {
    gamesEl.innerHTML = `<div class="gt-empty-state">NO GAMES FOR THIS DATE</div>`;
  }

  statusEl.textContent = `${totalGames} game${totalGames === 1 ? "" : "s"} · ${dateStr}`;
  statusEl.className = "status";
}
