import { loadAllLeagues } from "./loaders.js";
import { renderResults } from "./render.js";
import { initModal } from "./modal.js";

const dateInput = document.getElementById("gt-date");
const statusEl = document.getElementById("gt-status");
const gamesEl = document.getElementById("gt-games");

function todayLocal() {
  const date = new Date();

  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

async function loadPage() {
  if (!dateInput || !statusEl || !gamesEl) return;

  const dateStr = dateInput.value || todayLocal();

  statusEl.textContent = "Loading…";
  statusEl.className = "status loading";
  gamesEl.innerHTML = "";

  try {
    const results = await loadAllLeagues(dateStr);
    renderResults(results, dateStr);
  } catch (error) {
    console.error(error);

    statusEl.textContent = "Error loading games.";
    statusEl.className = "status";
    gamesEl.innerHTML = `<div class="gt-empty-state">ERROR LOADING GAMES</div>`;
  }
}

function init() {
  if (!dateInput || !statusEl || !gamesEl) return;

  if (!window.REPO_CONFIG) {
    statusEl.textContent = "Missing config.";
    return;
  }

  dateInput.value = todayLocal();
  dateInput.addEventListener("change", loadPage);

  initModal();
  loadPage();
}

init();
