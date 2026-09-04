import { esc, isPresent } from "./format.js";

let modal = null;
let modalContent = null;

export function initModal() {
  modal = document.getElementById("gt-modal");
  modalContent = document.getElementById("gt-modal-content");

  if (!modal) return;

  modal.addEventListener("click", event => {
    if (event.target === modal) {
      modal.classList.remove("open");
    }
  });
}

export function openGameModal(game) {
  if (!modal || !modalContent) return;

  const rows = (game.modal || [])
    .filter(([, value]) => isPresent(value))
    .map(([label, value]) => `
      <div class="gt-line-row">
        <span class="gt-line-label">${esc(label)}</span>
        <span class="gt-line-val">${esc(value)}</span>
      </div>
    `)
    .join("");

  modalContent.innerHTML = `
    <div class="gt-modal-header">
      <span class="gt-modal-league-tag">${esc(game.displayLeague)}</span>
      <span class="gt-modal-time">${esc([game.card?.date, game.card?.time].filter(Boolean).join(" · "))}</span>
    </div>

    <h2 class="gt-modal-title">${esc(game.title)}</h2>

    <div class="gt-modal-section-label">GAME DETAILS</div>
    <div class="gt-modal-lines">
      ${rows}
    </div>
  `;

  modal.classList.add("open");
}
