(function() {
  'use strict';

  var CORE_API_ROOT = 'https://sports.core.api.espn.com/v2';
  var REFRESH_MS = 30000;

  /*
    League activation controls:
    - enabled: true = show and load the league
    - enabled: false = hide the league completely
    - placeholder: true = show the league but do not fetch normal team scores
  */
  var LEAGUES = [
    {
      key: 'NBA',
      label: 'NBA',
      enabled: true,
      sport: 'basketball',
      league: 'nba',
      type: 'scoreboard'
    },
    {
      key: 'NHL',
      label: 'NHL',
      enabled: true,
      sport: 'hockey',
      league: 'nhl',
      type: 'scoreboard'
    },
    {
      key: 'WNBA',
      label: 'WNBA',
      enabled: true,
      sport: 'basketball',
      league: 'wnba',
      type: 'scoreboard'
    },
    {
      key: 'NCAAM',
      label: 'NCAAM',
      enabled: false,
      sport: 'basketball',
      league: 'mens-college-basketball',
      type: 'scoreboard'
    },
    {
      key: 'MLB',
      label: 'MLB',
      enabled: true,
      sport: 'baseball',
      league: 'mlb',
      type: 'scoreboard'
    },
    {
      key: 'EPL',
      label: 'EPL',
      enabled: true,
      sport: 'soccer',
      league: 'eng.1',
      type: 'scoreboard'
    },
    {
      key: 'MLS',
      label: 'MLS',
      enabled: true,
      sport: 'soccer',
      league: 'usa.1',
      type: 'scoreboard'
    },
    {
      key: 'LALIGA',
      label: 'LA LIGA',
      enabled: true,
      sport: 'soccer',
      league: 'esp.1',
      type: 'scoreboard'
    },
    {
      key: 'LIGUE1',
      label: 'LIGUE 1',
      enabled: true,
      sport: 'soccer',
      league: 'fra.1',
      type: 'scoreboard'
    },
    {
      key: 'SERIEA',
      label: 'SERIE A',
      enabled: true,
      sport: 'soccer',
      league: 'ita.1',
      type: 'scoreboard'
    },
    {
      key: 'BUNDESLIGA',
      label: 'BUNDESLIGA',
      enabled: true,
      sport: 'soccer',
      league: 'ger.1',
      type: 'scoreboard'
    },
    {
      key: 'UFC',
      label: 'UFC',
      enabled: false,
      sport: 'mma',
      league: 'ufc',
      type: 'placeholder',
      placeholder: true
    }
  ];

  var activeLeague = 'all';
  var allData = {};
  var refCache = {};
  var refreshTimer = null;

  function $(id) {
    return document.getElementById(id);
  }

  function esc(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function normalizeUrl(url) {
    if (!url) return '';
    return String(url).replace(/^http:\/\//i, 'https://');
  }

  function isRefItem(item) {
    return item && typeof item === 'object' && item.$ref;
  }

  function getRefUrl(item) {
    if (!item) return '';
    if (typeof item === 'string') return normalizeUrl(item);
    if (item.$ref) return normalizeUrl(item.$ref);
    return '';
  }

  function getEnabledLeagues() {
    return LEAGUES.filter(function(league) {
      return league.enabled !== false;
    });
  }

  function getScoreLeagues() {
    return getEnabledLeagues().filter(function(league) {
      return league.type !== 'placeholder';
    });
  }

  function setStatus(text, cls, dotCls) {
    var statusText = $('status-text');
    var statusBar = $('scores-status');
    var statusDot = $('status-dot');

    if (statusText) statusText.textContent = text || '';
    if (statusBar) statusBar.className = 'status-bar ' + (cls || '');
    if (statusDot) statusDot.className = 'status-dot ' + (dotCls || '');
  }

  async function fetchJson(url) {
    var finalUrl = normalizeUrl(url);
    var response = await fetch(finalUrl);

    if (!response.ok) {
      throw new Error('HTTP ' + response.status + ' · ' + finalUrl);
    }

    return response.json();
  }

  async function fetchRef(item) {
    var url = getRefUrl(item);

    if (!url) {
      return item;
    }

    if (refCache[url]) {
      return refCache[url];
    }

    refCache[url] = fetchJson(url).catch(function(error) {
      delete refCache[url];
      throw error;
    });

    return refCache[url];
  }

  async function fetchRefs(items, limit) {
    var list = Array.isArray(items) ? items.slice(0, limit || items.length) : [];
    var results = [];
    var concurrency = 12;
    var index = 0;

    async function worker() {
      while (index < list.length) {
        var currentIndex = index++;
        var item = list[currentIndex];

        try {
          results[currentIndex] = isRefItem(item) ? await fetchRef(item) : item;
        } catch (e) {
          results[currentIndex] = null;
        }
      }
    }

    var workers = [];
    var workerCount = Math.min(concurrency, list.length);

    for (var i = 0; i < workerCount; i++) {
      workers.push(worker());
    }

    await Promise.all(workers);

    return results.filter(Boolean);
  }

  function getTodayDateParam() {
    var now = new Date();
    var yyyy = String(now.getFullYear());
    var mm = String(now.getMonth() + 1).padStart(2, '0');
    var dd = String(now.getDate()).padStart(2, '0');

    return yyyy + mm + dd;
  }

  function siteScoreboardUrl(cfg) {
    return 'https://site.api.espn.com/apis/site/v2/sports/' +
      encodeURIComponent(cfg.sport) +
      '/' +
      encodeURIComponent(cfg.league) +
      '/scoreboard';
  }

  function coreEventsUrl(cfg) {
    return CORE_API_ROOT +
      '/sports/' +
      encodeURIComponent(cfg.sport) +
      '/leagues/' +
      encodeURIComponent(cfg.league) +
      '/events?dates=' +
      encodeURIComponent(getTodayDateParam()) +
      '&limit=200';
  }

  async function loadLeagueEvents(cfg) {
    try {
      var siteData = await fetchJson(siteScoreboardUrl(cfg));
      return normalizeSiteEvents(cfg, siteData.events || []);
    } catch (siteError) {
      return loadCoreEvents(cfg);
    }
  }

  async function loadCoreEvents(cfg) {
    var data = await fetchJson(coreEventsUrl(cfg));
    var eventItems = Array.isArray(data.items) ? data.items : [];
    var events = await fetchRefs(eventItems, 200);
    var normalized = [];

    for (var i = 0; i < events.length; i++) {
      try {
        var ev = await normalizeCoreEvent(cfg, events[i]);

        if (ev) {
          normalized.push(ev);
        }
      } catch (e) {}
    }

    normalized.sort(function(a, b) {
      return new Date(a.date || 0).getTime() - new Date(b.date || 0).getTime();
    });

    return normalized;
  }

  function normalizeSiteEvents(cfg, events) {
    return events.map(function(ev) {
      var comp = ev.competitions && ev.competitions[0] ? ev.competitions[0] : null;
      var competitors = comp && Array.isArray(comp.competitors) ? comp.competitors : [];
      var away = competitors.find(function(t) { return t.homeAway === 'away'; });
      var home = competitors.find(function(t) { return t.homeAway === 'home'; });

      if (!away || !home) return null;

      return {
        id: ev.id || '',
        leagueKey: cfg.key,
        leagueLabel: cfg.label,
        date: ev.date || comp.date || '',
        status: ev.status || comp.status || null,
        away: normalizeSiteCompetitor(away),
        home: normalizeSiteCompetitor(home)
      };
    }).filter(Boolean);
  }

  function normalizeSiteCompetitor(item) {
    var team = item.team || {};
    var logo = '';

    if (Array.isArray(team.logos) && team.logos.length) {
      logo = team.logos[0].href || team.logos[0].url || '';
    } else if (team.logo) {
      logo = team.logo;
    }

    return {
      id: team.id || item.id || '',
      name: team.displayName || team.name || team.shortDisplayName || '—',
      abbr: team.abbreviation || team.shortDisplayName || team.name || '—',
      logo: normalizeUrl(logo),
      score: normalizeScore(item.score),
      winner: item.winner === true,
      homeAway: item.homeAway || ''
    };
  }

  async function normalizeCoreEvent(cfg, ev) {
    if (!ev) return null;

    var competition = null;

    if (Array.isArray(ev.competitions) && ev.competitions.length) {
      competition = isRefItem(ev.competitions[0]) ? await fetchRef(ev.competitions[0]) : ev.competitions[0];
    } else if (ev.competition) {
      competition = isRefItem(ev.competition) ? await fetchRef(ev.competition) : ev.competition;
    }

    if (!competition) return null;

    var competitorsRaw = Array.isArray(competition.competitors) ? competition.competitors : [];
    var competitors = await fetchRefs(competitorsRaw, 20);

    for (var i = 0; i < competitors.length; i++) {
      if (isRefItem(competitors[i].team)) {
        try {
          competitors[i].team = await fetchRef(competitors[i].team);
        } catch (e) {}
      }
    }

    var away = competitors.find(function(t) {
      return String(t.homeAway || '').toLowerCase() === 'away';
    });

    var home = competitors.find(function(t) {
      return String(t.homeAway || '').toLowerCase() === 'home';
    });

    if (!away || !home) {
      if (competitors.length >= 2) {
        away = competitors[0];
        home = competitors[1];
      }
    }

    if (!away || !home) return null;

    var status = await getCoreStatus(ev, competition);

    return {
      id: ev.id || competition.id || '',
      leagueKey: cfg.key,
      leagueLabel: cfg.label,
      date: ev.date || competition.date || '',
      status: status,
      away: normalizeCoreCompetitor(away),
      home: normalizeCoreCompetitor(home)
    };
  }

  async function getCoreStatus(ev, competition) {
    var status = null;

    if (ev.status) {
      status = isRefItem(ev.status) ? await fetchRef(ev.status).catch(function() { return null; }) : ev.status;
    }

    if (!status && competition && competition.status) {
      status = isRefItem(competition.status) ? await fetchRef(competition.status).catch(function() { return null; }) : competition.status;
    }

    return status || {};
  }

  function normalizeCoreCompetitor(item) {
    var team = item.team || {};
    var logo = '';

    if (Array.isArray(team.logos) && team.logos.length) {
      logo = team.logos[0].href || team.logos[0].url || '';
    } else if (team.logo) {
      logo = team.logo;
    }

    return {
      id: team.id || item.id || '',
      name: team.displayName || team.name || team.shortDisplayName || team.abbreviation || '—',
      abbr: team.abbreviation || team.shortDisplayName || team.name || '—',
      logo: normalizeUrl(logo),
      score: normalizeScore(item.score),
      winner: item.winner === true,
      homeAway: item.homeAway || ''
    };
  }

  function normalizeScore(score) {
    if (score === null || score === undefined || score === '') return null;

    if (typeof score === 'object') {
      if (score.displayValue !== undefined) return String(score.displayValue);
      if (score.value !== undefined) return String(score.value);
      if (score.score !== undefined) return String(score.score);
    }

    return String(score);
  }

  function getStatusType(ev) {
    var status = ev.status || {};
    var type = status.type || status;

    return type || {};
  }

  function isLive(ev) {
    var type = getStatusType(ev);
    var state = String(type.state || ev.status.state || '').toLowerCase();
    var completed = type.completed === true || ev.status.completed === true;

    return !completed && state === 'in';
  }

  function isFinal(ev) {
    var type = getStatusType(ev);
    return type.completed === true || ev.status.completed === true;
  }

  function statusLabel(ev) {
    var status = ev.status || {};
    var type = getStatusType(ev);

    return type.shortDetail ||
      type.detail ||
      type.description ||
      status.shortDetail ||
      status.detail ||
      status.description ||
      formatStartTime(ev.date);
  }

  function formatStartTime(value) {
    if (!value) return '';

    var date = new Date(value);

    if (isNaN(date.getTime())) return '';

    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  function renderLeague(cfg, events) {
    var block = document.createElement('div');
    block.className = 'league-block';
    block.dataset.league = cfg.key;

    if (activeLeague !== 'all' && activeLeague !== cfg.key) {
      block.style.display = 'none';
    }

    var hdr = document.createElement('div');
    hdr.className = 'league-header lh-' + cfg.key;
    hdr.textContent = cfg.label;
    block.appendChild(hdr);

    if (cfg.type === 'placeholder') {
      var ph = document.createElement('div');
      ph.className = 'placeholder-state';
      ph.innerHTML =
        '<div class="placeholder-title">' + esc(cfg.label) + ' Coming Next</div>' +
        '<div class="placeholder-copy">' + esc(cfg.label) + ' does not use the same team-score model, so it is parked as a placeholder.</div>';
      block.appendChild(ph);
      return block;
    }

    if (!events || events.length === 0) {
      var ng = document.createElement('div');
      ng.className = 'no-games';
      ng.textContent = 'No games today';
      block.appendChild(ng);
      return block;
    }

    var grid = document.createElement('div');
    grid.className = 'games-grid';

    events.forEach(function(ev) {
      grid.appendChild(renderGameCard(ev));
    });

    block.appendChild(grid);
    return block;
  }

  function renderGameCard(ev) {
    var live = isLive(ev);
    var final = isFinal(ev);
    var status = statusLabel(ev);

    var away = ev.away || {};
    var home = ev.home || {};

    var awayScore = away.score !== null && away.score !== undefined && away.score !== '' ? away.score : null;
    var homeScore = home.score !== null && home.score !== undefined && home.score !== '' ? home.score : null;

    var awayWins = away.winner === true;
    var homeWins = home.winner === true;

    if (final && awayScore !== null && homeScore !== null) {
      var awayNum = parseFloat(awayScore);
      var homeNum = parseFloat(homeScore);

      if (!isNaN(awayNum) && !isNaN(homeNum)) {
        awayWins = awayNum > homeNum;
        homeWins = homeNum > awayNum;
      }
    }

    var card = document.createElement('div');
    card.className = 'game-card' + (live ? ' live' : '');

    var statusCls = live ? 'game-status is-live' : final ? 'game-status is-final' : 'game-status';

    card.innerHTML =
      '<div class="' + statusCls + '">' + esc(status) + '</div>' +
      buildTeamRow(away, awayScore, awayWins) +
      buildTeamRow(home, homeScore, homeWins);

    return card;
  }

  function buildTeamRow(team, score, winner) {
    var logo = team.logo
      ? '<img class="team-logo" src="' + esc(team.logo) + '" loading="lazy" alt="' + esc(team.abbr || team.name || 'team') + ' logo">'
      : '';

    return '<div class="game-row">' +
      '<span class="team-side">' +
        logo +
        '<span class="team-abbr' + (winner ? ' winner' : '') + '">' + esc(team.abbr || team.name || '—') + '</span>' +
      '</span>' +
      '<span class="team-score' + (score === null ? ' no-score' : '') + (winner ? ' winner' : '') + '">' + esc(score !== null ? score : '—') + '</span>' +
    '</div>';
  }

  function render() {
    var main = $('scores-main');
    if (!main) return;

    main.innerHTML = '';

    var enabled = getEnabledLeagues();

    if (!enabled.length) {
      main.innerHTML =
        '<div class="placeholder-state">' +
          '<div class="placeholder-title">No Leagues Enabled</div>' +
          '<div class="placeholder-copy">Enable at least one league in docs/js/live-scores/render.js to show live scores.</div>' +
        '</div>';
      return;
    }

    enabled.forEach(function(cfg) {
      main.appendChild(renderLeague(cfg, allData[cfg.key] || []));
    });
  }

  function applyFilter() {
    document.querySelectorAll('.league-block').forEach(function(block) {
      block.style.display = activeLeague === 'all' || block.dataset.league === activeLeague ? '' : 'none';
    });
  }

  async function loadScores() {
    setStatus('Refreshing...', 'loading', 'yellow');

    var scoreLeagues = getScoreLeagues();

    if (!scoreLeagues.length) {
      render();
      setStatus('No score leagues enabled', '', 'yellow');
      return;
    }

    var results = await Promise.all(scoreLeagues.map(async function(cfg) {
      try {
        var events = await loadLeagueEvents(cfg);
        return {
          key: cfg.key,
          ok: true,
          events: events
        };
      } catch (e) {
        return {
          key: cfg.key,
          ok: false,
          events: []
        };
      }
    }));

    results.forEach(function(result) {
      allData[result.key] = result.events;
    });

    getEnabledLeagues().forEach(function(cfg) {
      if (cfg.type === 'placeholder' && !allData[cfg.key]) {
        allData[cfg.key] = [];
      }
    });

    var total = results.reduce(function(sum, result) {
      return sum + result.events.length;
    }, 0);

    var failed = results.filter(function(result) {
      return !result.ok;
    }).length;

    var now = new Date().toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    });

    render();
    applyFilter();

    if (failed) {
      setStatus(total + ' games loaded · ' + failed + ' league(s) failed · last updated ' + now, '', 'red');
    } else {
      setStatus(total + ' games loaded · last updated ' + now, '', 'green');
    }

    var badge = $('refresh-badge');
    if (badge) badge.textContent = 'UPDATED ' + now;
  }

  function renderLeagueControls() {
    var host = $('league-controls');
    if (!host) return;

    var enabled = getEnabledLeagues();

    var html = '<div class="league-pill active" data-league="all">All</div>';

    html += enabled.map(function(cfg) {
      var cls = 'league-pill';

      if (cfg.placeholder) cls += ' placeholder';

      return '<div class="' + cls + '" data-league="' + esc(cfg.key) + '">' + esc(cfg.label) + '</div>';
    }).join('');

    host.innerHTML = html;
  }

  function bindEvents() {
    var controls = $('league-controls');

    if (controls) {
      controls.addEventListener('click', function(e) {
        var pill = e.target.closest('.league-pill');
        if (!pill) return;

        document.querySelectorAll('.league-pill').forEach(function(p) {
          p.classList.remove('active');
        });

        pill.classList.add('active');
        activeLeague = pill.dataset.league || 'all';

        applyFilter();
      });
    }
  }

  function init() {
    renderLeagueControls();
    bindEvents();
    loadScores();

    if (refreshTimer) {
      clearInterval(refreshTimer);
    }

    refreshTimer = setInterval(loadScores, REFRESH_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
