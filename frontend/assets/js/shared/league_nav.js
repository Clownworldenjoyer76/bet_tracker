(() => {
  "use strict";

  const PAGE = (location.pathname.split("/").pop() || "")
    .replace(/\.html$/i, "")
    .toLowerCase();

  const TARGET_PAGES = new Set([
    "teams",
    "players",
    "standings"
  ]);

  if (!TARGET_PAGES.has(PAGE)) return;

  const GROUPS = [
    {
      key: "football",
      label: "Football",
      leagues: [
        { key: "nfl", label: "NFL" },
        { key: "cfb", label: "College Football" },
        { key: "cfl", label: "CFL" }
      ]
    },
    {
      key: "basketball",
      label: "Basketball",
      leagues: [
        { key: "nba", label: "NBA" },
        { key: "ncaam", label: "College Basketball" },
        { key: "wnba", label: "WNBA" }
      ]
    },
    {
      key: "soccer",
      label: "Soccer",
      leagues: [
        { key: "mls", label: "MLS" },
        { key: "epl", label: "EPL" },
        { key: "laliga", label: "La Liga" },
        { key: "ligue1", label: "Ligue 1" },
        { key: "seriea", label: "Serie A" },
        { key: "bundesliga", label: "Bundesliga" }
      ]
    }
  ];

  const DIRECT = [
    { key: "nhl", label: "NHL", after: "football" },
    { key: "mlb", label: "MLB", after: "nhl" },
    { key: "ufc", label: "UFC", after: "soccer" }
  ];

  let host = null;
  let classObserver = null;
  let hostObserver = null;
  let transforming = false;

  function injectStyles() {
    if (document.getElementById("shared-league-nav-style")) return;

    const style = document.createElement("style");
    style.id = "shared-league-nav-style";
    style.textContent = `
      #league-controls.shared-league-nav-host {
        display: flex !important;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        width: 100%;
        position: relative;
        z-index: 20;
      }

      #league-controls .shared-league-nav-main {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }

      #league-controls .shared-league-nav-aux {
        margin-left: auto;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }

      #league-controls .control-group {
        position: relative;
        display: inline-flex;
        align-items: center;
      }

      #league-controls .league-pill,
      #league-controls .group-pill,
      #league-controls .submenu-pill {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.08em;
        padding: 4px 12px;
        border: 1px solid var(--border-soft);
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
        transition: all 0.15s;
        text-transform: uppercase;
        line-height: 1.2;
        white-space: nowrap;
      }

      #league-controls .league-pill:hover,
      #league-controls .group-pill:hover,
      #league-controls .submenu-pill:hover {
        border-color: var(--accent-blue);
        color: var(--accent-blue);
      }

      #league-controls .league-pill.active,
      #league-controls .group-pill.active,
      #league-controls .submenu-pill.active {
        border-color: var(--accent-green);
        color: var(--accent-green);
        background: rgba(0,255,132,0.06);
      }

      #league-controls .group-pill::after {
        content: " ▾";
        color: var(--text-muted);
        font-size: 10px;
        letter-spacing: 0;
      }

      #league-controls .group-pill:hover::after,
      #league-controls .group-pill.active::after {
        color: var(--accent-green);
      }

      #league-controls .control-group.open .group-pill {
        border-color: var(--accent-blue);
        color: var(--accent-blue);
        background: rgba(0,191,255,0.04);
      }

      #league-controls .control-group.open .group-pill.active {
        border-color: var(--accent-green);
        color: var(--accent-green);
        background: rgba(0,255,132,0.06);
      }

      #league-controls .submenu {
        position: absolute;
        top: calc(100% + 6px);
        left: 0;
        min-width: 190px;
        display: none;
        flex-direction: column;
        gap: 6px;
        padding: 8px;
        background: var(--background);
        border: 1px solid var(--border-soft);
        box-shadow: 0 18px 44px rgba(0,0,0,0.45);
        z-index: 50;
      }

      #league-controls .control-group.open .submenu {
        display: flex;
      }

      #league-controls .submenu-pill {
        width: 100%;
        text-align: left;
        background: var(--bg-card);
      }

      #league-controls .shared-league-unavailable {
        opacity: 0.4;
        cursor: not-allowed;
        border-style: dashed;
      }

      #league-controls .shared-league-unavailable:hover {
        border-color: var(--border-soft);
        color: var(--text-muted);
        background: transparent;
      }

      #league-controls .shared-group-unavailable {
        opacity: 0.65;
      }

      @media (max-width: 820px) {
        #league-controls.shared-league-nav-host {
          align-items: stretch;
        }

        #league-controls .shared-league-nav-main,
        #league-controls .shared-league-nav-aux {
          width: 100%;
        }

        #league-controls .control-group {
          width: 100%;
          flex-direction: column;
          align-items: stretch;
        }

        #league-controls .league-pill,
        #league-controls .group-pill {
          width: 100%;
          text-align: left;
        }

        #league-controls .submenu {
          position: static;
          width: 100%;
          min-width: 0;
          margin-top: 6px;
          box-shadow: none;
          background: transparent;
        }

        #league-controls .submenu-pill {
          padding-left: 22px;
        }

        #league-controls .shared-league-nav-aux {
          margin-left: 0;
        }

        #league-controls .shared-league-nav-aux > * {
          width: 100%;
          margin-left: 0 !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function getExistingLeaguePills() {
    const map = new Map();

    host.querySelectorAll(".league-pill[data-league-key]").forEach((pill) => {
      const key = String(pill.dataset.leagueKey || "").toLowerCase();
      if (key) map.set(key, pill);
    });

    return map;
  }

  function makeUnavailableLeague(item, asSubmenu) {
    const button = document.createElement("button");
    button.type = "button";
    button.disabled = true;
    button.className =
      (asSubmenu ? "league-pill submenu-pill" : "league-pill") +
      " shared-league-unavailable";
    button.dataset.sharedLeagueKey = item.key;
    button.textContent = item.label;
    button.title = item.label + " stats coverage is not enabled on this page.";
    return button;
  }

  function prepareExistingPill(pill, item, asSubmenu) {
    pill.textContent = item.label;
    pill.classList.remove("placeholder");
    pill.classList.toggle("submenu-pill", !!asSubmenu);
    pill.classList.add("shared-league-option");
    return pill;
  }

  function makeGroup(group, existing) {
    const wrap = document.createElement("div");
    wrap.className = "control-group";
    wrap.dataset.group = group.key;

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "group-pill";
    toggle.dataset.groupToggle = group.key;
    toggle.textContent = group.label;

    const submenu = document.createElement("div");
    submenu.className = "submenu";

    let supported = 0;

    group.leagues.forEach((item) => {
      const pill = existing.get(item.key);

      if (pill) {
        supported += 1;
        submenu.appendChild(
          prepareExistingPill(pill, item, true)
        );
      } else {
        submenu.appendChild(
          makeUnavailableLeague(item, true)
        );
      }
    });

    if (!supported) {
      wrap.classList.add("shared-group-unavailable");
    }

    wrap.appendChild(toggle);
    wrap.appendChild(submenu);

    toggle.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();

      const wasOpen = wrap.classList.contains("open");
      closeAllMenus();

      if (!wasOpen) {
        wrap.classList.add("open");
      }
    });

    return wrap;
  }

  function makeDirect(item, existing) {
    const pill = existing.get(item.key);

    if (pill) {
      return prepareExistingPill(pill, item, false);
    }

    return makeUnavailableLeague(item, false);
  }

  function closeAllMenus() {
    if (!host) return;

    host.querySelectorAll(".control-group.open").forEach((group) => {
      group.classList.remove("open");
    });
  }

  function updateActiveGroups() {
    if (!host) return;

    host.querySelectorAll(".control-group").forEach((group) => {
      const toggle = group.querySelector(".group-pill");
      const activeChild = group.querySelector(
        ".league-pill[data-league-key].active"
      );

      if (toggle) {
        toggle.classList.toggle("active", !!activeChild);
      }
    });
  }

  function preserveAuxiliaryNodes(existingPills) {
    const aux = [];

    Array.from(host.children).forEach((node) => {
      if (
        node.classList &&
        (
          node.classList.contains("shared-league-nav-main") ||
          node.classList.contains("shared-league-nav-aux")
        )
      ) {
        return;
      }

      if (
        node.matches &&
        node.matches(".league-pill[data-league-key]")
      ) {
        return;
      }

      aux.push(node);
    });

    return aux;
  }

  function buildSharedNav() {
    if (!host || transforming) return;

    const existing = getExistingLeaguePills();

    if (!existing.size) return;

    transforming = true;

    if (hostObserver) hostObserver.disconnect();
    if (classObserver) classObserver.disconnect();

    const auxiliary = preserveAuxiliaryNodes(existing);

    const main = document.createElement("div");
    main.className = "shared-league-nav-main";

    main.appendChild(makeGroup(GROUPS[0], existing));
    main.appendChild(
      makeDirect(
        { key: "nhl", label: "NHL" },
        existing
      )
    );
    main.appendChild(
      makeDirect(
        { key: "mlb", label: "MLB" },
        existing
      )
    );
    main.appendChild(makeGroup(GROUPS[1], existing));
    main.appendChild(makeGroup(GROUPS[2], existing));
    main.appendChild(
      makeDirect(
        { key: "ufc", label: "UFC" },
        existing
      )
    );

    const aux = document.createElement("div");
    aux.className = "shared-league-nav-aux";

    auxiliary.forEach((node) => {
      aux.appendChild(node);
    });

    host.innerHTML = "";
    host.classList.add("shared-league-nav-host");
    host.appendChild(main);

    if (aux.children.length) {
      host.appendChild(aux);
    }

    host.dataset.sharedLeagueNavReady = "true";

    updateActiveGroups();
    observeActiveState();
    observeHost();

    transforming = false;
  }

  function observeActiveState() {
    classObserver = new MutationObserver(() => {
      updateActiveGroups();
    });

    host.querySelectorAll(".league-pill[data-league-key]").forEach((pill) => {
      classObserver.observe(pill, {
        attributes: true,
        attributeFilter: ["class"]
      });
    });
  }

  function observeHost() {
    hostObserver = new MutationObserver(() => {
      if (transforming) return;

      const flatPills = Array.from(
        host.querySelectorAll(":scope > .league-pill[data-league-key]")
      );

      if (flatPills.length) {
        host.dataset.sharedLeagueNavReady = "false";
        queueMicrotask(buildSharedNav);
      }
    });

    hostObserver.observe(host, {
      childList: true
    });
  }

  function init() {
    injectStyles();

    host = document.getElementById("league-controls");
    if (!host) return;

    document.addEventListener("click", (event) => {
      if (!event.target.closest("#league-controls .control-group")) {
        closeAllMenus();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeAllMenus();
      }
    });

    observeHost();

    if (host.querySelector(".league-pill[data-league-key]")) {
      buildSharedNav();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
