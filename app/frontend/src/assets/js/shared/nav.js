/* SMH_FAVICON_START */
(() => {
  const icons = [
    ['image/png', '16x16', 'assets/images/favicon-16x16.png'],
    ['image/png', '32x32', 'assets/images/favicon-32x32.png'],
    ['image/png', '48x48', 'assets/images/favicon-48x48.png'],
    ['image/svg+xml', 'any', 'assets/images/sportsmodelhub-favicon.svg']
  ];

  icons.forEach(([type, sizes, href]) => {
    const link = document.createElement('link');
    link.rel = 'icon';
    link.type = type;
    link.sizes = sizes;
    link.href = href;
    document.head.appendChild(link);
  });
})();
/* SMH_FAVICON_END */
/* SMH_POSTHOG_LOADER_START */
(() => {
  if (window.__smhPostHogLoaderAdded) return;
  window.__smhPostHogLoaderAdded = true;

  const script = document.createElement("script");
  script.src = "assets/js/shared/analytics.js";
  script.async = true;
  document.head.appendChild(script);
})();
/* SMH_POSTHOG_LOADER_END */
(() => {
  const el = document.getElementById("nav-placeholder");
  if (!el) return;

  // Shared league selector used by Stats pages.
  // The component watches #league-controls, so it can load before the
  // page-specific renderer creates its league pills.
  const currentPage = (
    location.pathname.split('/').pop() || ''
  ).replace('.html', '').toLowerCase();

  if (['teams', 'players', 'standings'].includes(currentPage)) {
    const sharedLeagueNav = document.createElement('script');
    sharedLeagueNav.src = 'assets/js/shared/league_nav.js';
    sharedLeagueNav.defer = true;
    document.head.appendChild(sharedLeagueNav);
  }

  fetch("nav.html")
    .then(r => {
      if (!r.ok) throw new Error("nav.html not found");
      return r.text();
    })
    .then(html => {
      el.innerHTML = html;

      // Active state
      const page = location.pathname.split('/').pop().replace('.html', '') || 'index';
      el.querySelectorAll('a[data-page]').forEach(a => {
        if (a.dataset.page === page) {
          a.classList.add('active');
          const parent = a.closest('.nav-dropdown');
          if (parent) parent.querySelector('.nav-dropdown-toggle').classList.add('active');
        }
      });

      // Mobile navigation
      const siteNav = el.querySelector('.site-nav');
      const mobileNavToggle = el.querySelector('#nav-mobile-toggle');
      const mobileNavState = mobileNavToggle ? mobileNavToggle.querySelector('.nav-mobile-state') : null;
      const mobileQuery = window.matchMedia('(max-width: 900px)');

      function closeMobileNav() {
        if (!siteNav || !mobileNavToggle) return;
        siteNav.classList.remove('nav-open');
        mobileNavToggle.setAttribute('aria-expanded', 'false');
        if (mobileNavState) mobileNavState.textContent = '☰';
        el.querySelectorAll('.nav-dropdown.open').forEach(item => item.classList.remove('open'));
      }

      if (siteNav && mobileNavToggle) {
        mobileNavToggle.addEventListener('click', () => {
          const opening = !siteNav.classList.contains('nav-open');
          siteNav.classList.toggle('nav-open', opening);
          mobileNavToggle.setAttribute('aria-expanded', opening ? 'true' : 'false');
          if (mobileNavState) mobileNavState.textContent = opening ? 'CLOSE' : '☰';
        });

        el.querySelectorAll('.nav-dropdown-toggle').forEach(toggle => {
          toggle.addEventListener('click', event => {
            if (!mobileQuery.matches) return;
            event.preventDefault();
            const item = toggle.closest('.nav-dropdown');
            if (!item) return;
            const opening = !item.classList.contains('open');
            el.querySelectorAll('.nav-dropdown.open').forEach(other => {
              if (other !== item) other.classList.remove('open');
            });
            item.classList.toggle('open', opening);
          });
        });

        el.querySelectorAll('.nav-links a[href]').forEach(link => {
          link.addEventListener('click', () => {
            if (mobileQuery.matches) closeMobileNav();
          });
        });

        window.addEventListener('keydown', event => {
          if (event.key === 'Escape') closeMobileNav();
        });

        window.addEventListener('resize', () => {
          if (!mobileQuery.matches) closeMobileNav();
        });
      }

      // Clock + signed-in Account timezone sync.
      const clockEl = document.getElementById('live-clock');
      let clockTimeZone = 'America/New_York';

      function timeZoneLabel(now) {
        try {
          const part = new Intl.DateTimeFormat('en-US', {
            timeZone: clockTimeZone,
            timeZoneName: 'short'
          }).formatToParts(now).find(part => part.type === 'timeZoneName');

          return part ? part.value : '';
        } catch {
          return '';
        }
      }

      function tick() {
        const now = new Date();
        const compact = window.matchMedia('(max-width: 900px)').matches;

        const t = now.toLocaleTimeString('en-US', {
          timeZone: clockTimeZone,
          hour12: true,
          hour: 'numeric',
          minute: '2-digit'
        });

        const d = now.toLocaleDateString('en-US', compact
          ? {
              timeZone: clockTimeZone,
              month: 'short',
              day: 'numeric'
            }
          : {
              timeZone: clockTimeZone,
              weekday: 'long',
              month: 'long',
              day: 'numeric',
              year: 'numeric'
            });

        const label = timeZoneLabel(now);

        clockEl.textContent = compact
          ? `${t} · ${d}`
          : `${label ? label + '  ' : ''}${t}   ${d}`;
      }

      async function loadAccountPreferences() {
        try {
          const response = await fetch('https://api.sportsmodelhub.com/api/account/preferences/', {
            credentials: 'include',
            headers: { 'Accept': 'application/json' }
          });

          if (!response.ok) return;

          const data = await response.json();
          if (!data.authenticated || !data.timezone) return;

          try {
            new Intl.DateTimeFormat('en-US', {
              timeZone: data.timezone
            }).format(new Date());

            clockTimeZone = data.timezone;
            tick();
          } catch {
            // Keep default timezone if saved value is invalid.
          }
        } catch {
          // Default timezone remains the fallback.
        }
      }

      tick();
      loadAccountPreferences();
      setInterval(tick, 1000);

      // Ticker
      initTicker();
    })
    .catch(() => { el.innerHTML = ""; });

  // ── TICKER ──────────────────────────────────────────────────────────────

  const CACHE_TTL = 5 * 60 * 1000;

  function cacheGet(key) {
    try {
      var raw = sessionStorage.getItem(key);
      if (!raw) return null;
      var obj = JSON.parse(raw);
      if (Date.now() - obj.ts > CACHE_TTL) { sessionStorage.removeItem(key); return null; }
      return obj.data;
    } catch(e) { return null; }
  }

  function cacheSet(key, data) {
    try { sessionStorage.setItem(key, JSON.stringify({ ts: Date.now(), data: data })); } catch(e) {}
  }

  async function fetchCached(key, url) {
    var cached = cacheGet(key);
    if (cached) return cached;
    try {
      var r = await fetch(url);
      if (!r.ok) return null;
      var data = await r.json();
      cacheSet(key, data);
      return data;
    } catch(e) { return null; }
  }

  function padTwo(n) { return n < 10 ? '0' + n : '' + n; }

  function todayESPN() {
    var d = new Date();
    return '' + d.getFullYear() + padTwo(d.getMonth() + 1) + padTwo(d.getDate());
  }

  var LEAGUES = [
    { key: 'NHL', sport: 'hockey',     league: 'nhl' },
    { key: 'NBA', sport: 'basketball', league: 'nba' },
    { key: 'MLB', sport: 'baseball',   league: 'mlb' }
  ];

  async function fetchGames() {
    var items = [];
    await Promise.all(LEAGUES.map(async function(cfg) {
      var url  = 'https://site.api.espn.com/apis/site/v2/sports/' + cfg.sport + '/' + cfg.league + '/scoreboard?dates=' + todayESPN();
      var data = await fetchCached('ticker_games_' + cfg.key, url);
      if (!data || !data.events) return;
      data.events.forEach(function(ev) {
        var comps = ev.competitions && ev.competitions[0];
        if (!comps) return;
        var competitors = comps.competitors || [];
        var home = competitors.find(function(c) { return c.homeAway === 'home'; });
        var away = competitors.find(function(c) { return c.homeAway === 'away'; });
        if (!home || !away) return;
        var status   = ev.status && ev.status.type ? ev.status.type.shortDetail || ev.status.type.description : '';
        var homeAbbr = home.team ? (home.team.abbreviation || home.team.shortDisplayName || '') : '';
        var awayAbbr = away.team ? (away.team.abbreviation || away.team.shortDisplayName || '') : '';
        var score    = (ev.status && ev.status.type && ev.status.type.completed)
          ? away.score + '-' + home.score
          : status;
        items.push('[' + cfg.key + '] ' + awayAbbr + ' @ ' + homeAbbr + '  ' + score);
      });
    }));
    return items;
  }

  async function fetchInjuries() {
    var items = [];
    await Promise.all(LEAGUES.map(async function(cfg) {
      var url  = 'https://site.api.espn.com/apis/site/v2/sports/' + cfg.sport + '/' + cfg.league + '/injuries';
      var data = await fetchCached('ticker_injuries_' + cfg.key, url);
      if (!data || !data.injuries) return;
      data.injuries.forEach(function(group) {
        var team = group.displayName || '';
        (group.injuries || []).forEach(function(inj) {
          var player = inj.athlete ? (inj.athlete.displayName || '') : '';
          var status = inj.status || '';
          if (player && (status.toLowerCase() === 'out' || status.toLowerCase() === 'doubtful')) {
            items.push('[INJ] ' + team + ' — ' + player + ' (' + status + ')');
          }
        });
      });
    }));
    return items;
  }

  async function fetchTransactions() {
    var items = [];
    await Promise.all(LEAGUES.map(async function(cfg) {
      var url  = 'https://site.api.espn.com/apis/site/v2/sports/' + cfg.sport + '/' + cfg.league + '/transactions';
      var data = await fetchCached('ticker_txns_' + cfg.key, url);
      if (!data || !data.transactions) return;
      data.transactions.slice(0, 5).forEach(function(t) {
        var team = t.team ? (t.team.abbreviation || t.team.displayName || '') : '';
        var desc = t.description || '';
        if (desc) items.push('[TXN] ' + (team ? team + ': ' : '') + desc);
      });
    }));
    return items;
  }

  function injectTickerStyle() {
    if (document.getElementById('ticker-style')) return;
    var s = document.createElement('style');
    s.id = 'ticker-style';
    s.textContent = [
      '.ticker-wrap{overflow:hidden;border-bottom:1px solid #222;background:#0d0d0d;height:28px;display:flex;align-items:center;}',
      '.ticker-label{font-family:"Barlow Condensed",sans-serif;font-size:11px;font-weight:900;letter-spacing:0.12em;color:#0a0a0a;background:#00ff84;padding:0 10px;height:100%;display:flex;align-items:center;white-space:nowrap;flex-shrink:0;}',
      '.ticker-track{display:flex;align-items:center;overflow:hidden;flex:1;}',
      '.ticker-inner{display:flex;align-items:center;white-space:nowrap;animation:ticker-scroll 850s linear infinite;}',
      '.ticker-inner:hover{animation-play-state:paused;}',
      '.ticker-item{font-family:"IBM Plex Mono",monospace;font-size:11px;color:#888;padding:0 32px;border-right:1px solid #222;}',
      '.ti-tag{font-family:"Barlow Condensed",sans-serif;font-weight:700;letter-spacing:0.08em;margin-right:6px;}',
      '.ti-tag-game{color:#00bfff;}',
      '.ti-tag-inj{color:#ff4444;}',
      '.ti-tag-txn{color:#facc15;}',
      '.ti-body{color:#aaa;}',
      '@keyframes ticker-scroll{0%{transform:translateX(0);}100%{transform:translateX(-50%);}}',
      '@media(max-width:900px){.ticker-item{padding:0 18px}.ticker-label{padding:0 8px}.ticker-wrap{height:27px}}'
    ].join('');
    document.head.appendChild(s);
  }

  function buildTickerItem(raw) {
    var match = raw.match(/^\[([^\]]+)\]\s*(.*)/);
    if (!match) return '<span class="ticker-item"><span class="ti-body">' + raw + '</span></span>';
    var tag  = match[1];
    var body = match[2];
    var tagClass = tag === 'INJ' ? 'ti-tag-inj' : tag === 'TXN' ? 'ti-tag-txn' : 'ti-tag-game';
    return '<span class="ticker-item"><span class="ti-tag ' + tagClass + '">' + tag + '</span><span class="ti-body">' + body + '</span></span>';
  }

  function renderTicker(items) {
    var existing = document.getElementById('site-ticker');
    if (existing) existing.remove();

    injectTickerStyle();

    var wrap = document.createElement('div');
    wrap.id = 'site-ticker';
    wrap.className = 'ticker-wrap';

    var label = document.createElement('div');
    label.className = 'ticker-label';
    label.textContent = 'LIVE';

    var track = document.createElement('div');
    track.className = 'ticker-track';

    var inner = document.createElement('div');
    inner.className = 'ticker-inner';
    var html = items.map(buildTickerItem).join('');
    inner.innerHTML = html + html; // duplicate for seamless loop

    track.appendChild(inner);
    wrap.appendChild(label);
    wrap.appendChild(track);

    var navEl = document.getElementById('nav-placeholder');
    if (navEl) navEl.insertAdjacentElement('afterend', wrap);
  }

  async function initTicker() {
    var [games, injuries, txns] = await Promise.all([
      fetchGames(),
      fetchInjuries(),
      fetchTransactions()
    ]);

    var items = games.concat(injuries).concat(txns);
    if (items.length === 0) items = ['No data available'];
    renderTicker(items);
  }

})();

/* NAV ACCESSIBILITY POLISH 2026-09-29 */
(() => {
  if (window.__smhNavAccessibilityPolish) return;
  window.__smhNavAccessibilityPolish = true;

  function syncDropdownAria() {
    document.querySelectorAll('.nav-dropdown-toggle').forEach(toggle => {
      const parent = toggle.closest('.nav-dropdown');
      const expanded = !!parent && (
        parent.classList.contains('open') ||
        parent.matches(':focus-within')
      );
      toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    });
  }

  document.addEventListener('keydown', event => {
    const toggle = event.target.closest?.('.nav-dropdown-toggle');

    if (toggle && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      toggle.click();
      queueMicrotask(syncDropdownAria);
      return;
    }

    if (toggle && event.key === 'ArrowDown') {
      event.preventDefault();

      const parent = toggle.closest('.nav-dropdown');
      if (parent && !parent.classList.contains('open')) {
        toggle.click();
      }

      requestAnimationFrame(() => {
        const first = parent?.querySelector(
          ':scope > .nav-dropdown-menu a[href], :scope > .nav-dropdown-menu button'
        );
        first?.focus();
        syncDropdownAria();
      });
      return;
    }

    if (event.key === 'Escape') {
      const parent = event.target.closest?.('.nav-dropdown');
      if (!parent) return;

      const parentToggle = parent.querySelector(':scope > .nav-dropdown-toggle');
      parent.classList.remove('open');
      parentToggle?.focus();
      syncDropdownAria();
    }
  });

  document.addEventListener('click', () => {
    queueMicrotask(syncDropdownAria);
  });

  document.addEventListener('focusin', syncDropdownAria);
  document.addEventListener('focusout', () => {
    setTimeout(syncDropdownAria, 0);
  });

  const navHost = document.getElementById('nav-placeholder');
  if (navHost) {
    new MutationObserver(syncDropdownAria).observe(navHost, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class']
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', syncDropdownAria);
  } else {
    syncDropdownAria();
  }
})();

/* NAV ESCAPE SUPPRESSION 2026-09-29 */
(() => {
  if (window.__smhNavEscapeSuppression) return;
  window.__smhNavEscapeSuppression = true;

  const enforce = () => {
    document.querySelectorAll('.nav-dropdown.keyboard-closed').forEach(parent => {
      parent.querySelector(':scope > .nav-dropdown-toggle')
        ?.setAttribute('aria-expanded', 'false');
    });
  };

  document.addEventListener('keydown', event => {
    const toggle = event.target.closest?.('.nav-dropdown-toggle');
    const parent = event.target.closest?.('.nav-dropdown');

    if (toggle && (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown')) {
      parent?.classList.remove('keyboard-closed');
      return;
    }

    if (event.key !== 'Escape' || !parent) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    const parentToggle = parent.querySelector(':scope > .nav-dropdown-toggle');

    parent.classList.remove('open');
    parent.classList.add('keyboard-closed');
    parentToggle?.setAttribute('aria-expanded', 'false');

    requestAnimationFrame(() => {
      parentToggle?.focus();
      parentToggle?.setAttribute('aria-expanded', 'false');
      queueMicrotask(enforce);
    });
  }, true);

  document.addEventListener('focusin', event => {
    const parent = event.target.closest?.('.nav-dropdown');
    if (parent && (!event.relatedTarget || !parent.contains(event.relatedTarget))) {
      parent.classList.remove('keyboard-closed');
    }
    queueMicrotask(enforce);
  }, true);

  document.addEventListener('pointerover', event => {
    event.target.closest?.('.nav-dropdown')?.classList.remove('keyboard-closed');
  }, true);

  const host = document.getElementById('nav-placeholder');
  if (host) {
    new MutationObserver(enforce).observe(host,{
      subtree:true,
      attributes:true,
      attributeFilter:['class']
    });
  }
})();
