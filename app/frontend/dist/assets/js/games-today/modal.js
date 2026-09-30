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

/* GAME MODAL ACCESSIBILITY POLISH 2026-09-29 */
(() => {
  const dialog = document.getElementById('gt-modal');
  if (!dialog || dialog.dataset.a11yEnhanced === 'true') return;

  dialog.dataset.a11yEnhanced = 'true';

  let returnFocus = null;
  let wasOpen = dialog.classList.contains('open');

  function focusableItems() {
    return Array.from(dialog.querySelectorAll(
      'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'
    )).filter(el => !el.hidden && el.getClientRects().length);
  }

  function syncDialogState() {
    const open = dialog.classList.contains('open');
    dialog.setAttribute('aria-hidden', open ? 'false' : 'true');

    if (open === wasOpen) return;

    if (open) {
      returnFocus = document.activeElement;

      requestAnimationFrame(() => {
        const items = focusableItems();
        if (items.length) items[0].focus();
      });
    } else if (returnFocus && document.contains(returnFocus)) {
      const target = returnFocus;
      returnFocus = null;
      requestAnimationFrame(() => target.focus());
    }

    wasOpen = open;
  }

  dialog.addEventListener('keydown', event => {
    if (!dialog.classList.contains('open')) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      dialog.classList.remove('open');
      return;
    }

    if (event.key !== 'Tab') return;

    const items = focusableItems();
    if (!items.length) {
      event.preventDefault();
      return;
    }

    const first = items[0];
    const last = items[items.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  new MutationObserver(syncDialogState).observe(dialog, {
    attributes: true,
    attributeFilter: ['class']
  });

  syncDialogState();
})();
