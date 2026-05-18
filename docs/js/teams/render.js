(function() {
  'use strict';

  var CURRENT_SEASON = 2026;
  var CORE_API_ROOT = 'https://sports.core.api.espn.com/v2';

  /*
    League activation controls:
    - enabled: true  = show and load the league
    - enabled: false = hide the league completely
    - placeholder: true = show the league as a placeholder, if enabled is not false
  */
  var LEAGUES = [
    {
      key: 'nba',
      label: 'NBA',
      enabled: true,
      sport: 'basketball',
      league: 'nba',
      type: 'team-roster',
      season: CURRENT_SEASON
    },
    {
      key: 'nhl',
      label: 'NHL',
      enabled: true,
      sport: 'hockey',
      league: 'nhl',
      type: 'team-roster',
      season: CURRENT_SEASON
    },
    {
      key: 'wnba',
      label: 'WNBA',
      enabled: true,
      sport: 'basketball',
      league: 'wnba',
      type: 'team-roster',
      season: CURRENT_SEASON
    },
    {
      key: 'ncaam',
      label: 'NCAAM',
      enabled: true,
      sport: 'basketball',
      league: 'mens-college-basketball',
      type: 'team-roster',
      season: CURRENT_SEASON
    },
    {
      key: 'mlb',
      label: 'MLB',
      enabled: true,
      sport: 'baseball',
      league: 'mlb',
      type: 'team-roster',
      season: CURRENT_SEASON
    },
    {
      key: 'epl',
      label: 'EPL',
      enabled: true,
      sport: 'soccer',
      league: 'eng.1',
      type: 'team-roster',
      season: CURRENT_SEASON
    },
    {
      key: 'mls',
      label: 'MLS',
      enabled: true,
      sport: 'soccer',
      league: 'usa.1',
      type: 'team-roster',
      season: CURRENT_SEASON
    },
    {
      key: 'laliga',
      label: 'LA LIGA',
      enabled: true,
      sport: 'soccer',
      league: 'esp.1',
      type: 'team-roster',
      season: CURRENT_SEASON
    },
    {
      key: 'ligue1',
      label: 'LIGUE 1',
      enabled: true,
      sport: 'soccer',
      league: 'fra.1',
      type: 'team-roster',
      season: CURRENT_SEASON
    },
    {
      key: 'seriea',
      label: 'SERIE A',
      enabled: true,
      sport: 'soccer',
      league: 'ita.1',
      type: 'team-roster',
      season: CURRENT_SEASON
    },
    {
      key: 'bundesliga',
      label: 'BUNDESLIGA',
      enabled: true,
      sport: 'soccer',
      league: 'ger.1',
      type: 'team-roster',
      season: CURRENT_SEASON
    },
    {
      key: 'ufc',
      label: 'UFC',
      enabled: true,
      sport: 'mma',
      league: 'ufc',
      type: 'placeholder',
      placeholder: true,
      season: CURRENT_SEASON
    }
  ];

  var activeLeagueKey = getDefaultLeagueKey();
  var activeLeague = getLeague(activeLeagueKey);
  var allTeams = [];
  var searchQuery = '';
  var refCache = {};
  var rosterCache = {};

  var TEAM_TABS = [
    { key: 'overview', label: 'Overview' },
    { key: 'roster', label: 'Roster' },
    { key: 'schedule', label: 'Schedule' },
    { key: 'depth', label: 'Depth' },
    { key: 'history', label: 'History' }
  ];

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

  function valueOrDash(value) {
    if (value === null || value === undefined || value === '') return '—';
    return value;
  }

  function normalizeRefUrl(url) {
    if (!url) return '';
    return String(url).replace(/^http:\/\//i, 'https://');
  }

  function isRefItem(item) {
    return item && typeof item === 'object' && item.$ref;
  }

  function getRefUrl(item) {
    if (!item) return '';
    if (typeof item === 'string') return normalizeRefUrl(item);
    if (item.$ref) return normalizeRefUrl(item.$ref);
    return '';
  }

  function getEnabledLeagues() {
    return LEAGUES.filter(function(league) {
      return league.enabled !== false;
    });
  }

  function getDefaultLeagueKey() {
    var enabled = getEnabledLeagues();

    if (!enabled.length) {
      return '';
    }

    var preferred = enabled.find(function(league) {
      return league.key === 'nba';
    });

    return preferred ? preferred.key : enabled[0].key;
  }

  function getLeague(key) {
    var enabled = getEnabledLeagues();

    if (!enabled.length) {
      return null;
    }

    return enabled.find(function(league) {
      return league.key === key;
    }) || enabled[0];
  }

  function setStatus(text, dotCls) {
    var statusText = $('status-text');
    var statusDot = $('status-dot');

    if (statusText) statusText.textContent = text || '';
    if (statusDot) statusDot.className = 'status-dot ' + (dotCls || '');
  }

  function setMain(html) {
    var main = $('teams-main');
    if (main) main.innerHTML = html;
  }

  function coreLeagueBase(league) {
    return CORE_API_ROOT + '/sports/' + league.sport + '/leagues/' + league.league;
  }

  function coreTeamsUrl(league) {
    return coreLeagueBase(league) + '/teams?limit=500';
  }

  function coreRosterUrl(league, teamId) {
    return coreLeagueBase(league) +
      '/seasons/' + encodeURIComponent(league.season || CURRENT_SEASON) +
      '/teams/' + encodeURIComponent(teamId) +
      '/athletes?limit=500';
  }

  async function fetchJson(url) {
    var finalUrl = normalizeRefUrl(url);
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

  async function hydrateAthleteRefs(player) {
    if (!player || typeof player !== 'object') return player;

    var tasks = [];

    if (isRefItem(player.position)) {
      tasks.push(fetchRef(player.position).then(function(position) {
        player.position = position;
      }).catch(function() {}));
    }

    if (isRefItem(player.team)) {
      tasks.push(fetchRef(player.team).then(function(team) {
        player.team = team;
      }).catch(function() {}));
    }

    if (isRefItem(player.country)) {
      tasks.push(fetchRef(player.country).then(function(country) {
        player.country = country;
      }).catch(function() {}));
    }

    if (isRefItem(player.college)) {
      tasks.push(fetchRef(player.college).then(function(college) {
        player.college = college;
      }).catch(function() {}));
    }

    await Promise.all(tasks);

    return player;
  }

  function init() {
    renderLeagueControls();
    bindEvents();

    if (!activeLeague) {
      showNoEnabledLeagues();
      return;
    }

    activateLeague(activeLeagueKey);
  }

  function renderLeagueControls() {
    var host = $('league-controls');
    if (!host) return;

    var enabled = getEnabledLeagues();

    host.innerHTML = enabled.map(function(league) {
      var cls = 'league-pill';

      if (league.key === activeLeagueKey) cls += ' active';
      if (league.placeholder) cls += ' placeholder';

      return '<div class="' + cls + '" data-league-key="' + esc(league.key) + '">' + esc(league.label) + '</div>';
    }).join('') +
      '<input type="text" class="search-box" id="team-search" placeholder="Search team...">';
  }

  function bindEvents() {
    var controls = $('league-controls');

    if (controls) {
      controls.addEventListener('click', function(e) {
        var pill = e.target.closest('.league-pill');
        if (!pill) return;

        activateLeague(pill.dataset.leagueKey);
      });
    }

    document.addEventListener('input', function(e) {
      if (e.target && e.target.id === 'team-search') {
        searchQuery = e.target.value.trim();
        render();
      }
    });

    var closeBtn = $('modal-close');
    var overlay = $('modal-overlay');

    if (closeBtn) {
      closeBtn.addEventListener('click', closeTeamModal);
    }

    if (overlay) {
      overlay.addEventListener('click', function(e) {
        if (e.target === this) closeTeamModal();
      });
    }

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') closeTeamModal();
    });
  }

  function activateLeague(key) {
    var league = getLeague(key);

    if (!league) {
      showNoEnabledLeagues();
      return;
    }

    activeLeagueKey = league.key;
    activeLeague = league;
    allTeams = [];
    searchQuery = '';

    document.querySelectorAll('.league-pill').forEach(function(pill) {
      pill.classList.toggle('active', pill.dataset.leagueKey === activeLeagueKey);
    });

    var search = $('team-search');
    if (search) search.value = '';

    if (activeLeague.type === 'placeholder') {
      showPlaceholderLeague(activeLeague);
      return;
    }

    loadTeams();
  }

  function showNoEnabledLeagues() {
    setStatus('No team leagues enabled', 'yellow');
    setMain(
      '<div class="placeholder-state">' +
        '<div class="placeholder-title">No Leagues Enabled</div>' +
        '<div class="placeholder-copy">Enable at least one league in docs/js/teams/render.js to show team coverage.</div>' +
      '</div>'
    );
  }

  function showPlaceholderLeague(league) {
    var empty = $('teams-empty');
    if (empty) empty.style.display = 'none';

    setStatus(league.label + ' team coverage placeholder', 'yellow');
    setMain(
      '<div class="placeholder-state">' +
        '<div class="placeholder-title">' + esc(league.label) + ' Coming Next</div>' +
        '<div class="placeholder-copy">' +
          'This page is currently built around teams and rosters. ' +
          league.label +
          ' does not fit the same team model, so it is parked as a placeholder while the team-based leagues are wired first.' +
        '</div>' +
      '</div>'
    );
  }

  function render() {
    var main = $('teams-main');
    var empty = $('teams-empty');

    if (!main || !empty) return;

    main.innerHTML = '';

    var teams = allTeams.slice();

    if (searchQuery) {
      var q = searchQuery.toLowerCase();

      teams = teams.filter(function(team) {
        return String(team.name || '').toLowerCase().indexOf(q) !== -1 ||
          String(team.abbr || '').toLowerCase().indexOf(q) !== -1 ||
          String(team.location || '').toLowerCase().indexOf(q) !== -1 ||
          String(team.nickname || '').toLowerCase().indexOf(q) !== -1;
      });
    }

    if (!teams.length) {
      empty.style.display = '';
      return;
    }

    empty.style.display = 'none';

    var grid = document.createElement('div');
    grid.className = 'team-grid';

    teams.forEach(function(team) {
      var card = document.createElement('div');
      card.className = 'team-card';

      var imgHtml = team.logo
        ? '<img class="team-logo" src="' + esc(team.logo) + '" loading="lazy" alt="' + esc(team.name) + ' logo">'
        : '<div class="team-logo-placeholder"></div>';

      card.innerHTML =
        imgHtml +
        '<div class="team-info">' +
          '<div class="team-name">' + esc(team.name) + '</div>' +
          '<div class="team-abbr">' + esc(team.abbr || team.location || activeLeague.label) + '</div>' +
        '</div>';

      card.addEventListener('click', function() {
        openTeamModal(team);
      });

      grid.appendChild(card);
    });

    main.appendChild(grid);
  }

  async function loadTeams() {
    if (!activeLeague) return;

    setStatus('Loading ' + activeLeague.label + ' teams...', 'yellow');
    allTeams = [];

    var empty = $('teams-empty');
    if (empty) empty.style.display = 'none';

    setMain('');

    var url = coreTeamsUrl(activeLeague);

    try {
      var data = await fetchJson(url);
      var teamItems = Array.isArray(data.items) ? data.items : [];
      var hydratedTeams = await fetchRefs(teamItems, 500);

      allTeams = normalizeTeams(hydratedTeams);

      render();
      setStatus(allTeams.length + ' teams · ' + activeLeague.label, 'green');
    } catch(e) {
      setStatus('Failed to load ' + activeLeague.label + ' teams', 'red');
      setMain(
        '<div class="empty-state">' +
          'Failed to load teams' +
          '<div class="error-details">' + esc(e.message || url) + '</div>' +
        '</div>'
      );
    }
  }

  function normalizeTeams(rawTeams) {
    var teams = Array.isArray(rawTeams) ? rawTeams : [];

    return teams.map(function(team) {
      var logos = Array.isArray(team.logos) ? team.logos : [];
      var logo = '';

      if (logos.length) {
        logo = normalizeRefUrl(logos[0].href || logos[0].url || '');
      }

      return {
        id: team.id || team.uid || team.abbreviation || '',
        uid: team.uid || '',
        name: team.displayName || team.name || team.shortDisplayName || team.abbreviation || 'Unknown Team',
        abbr: team.abbreviation || '',
        location: team.location || '',
        nickname: team.nickname || '',
        slug: team.slug || '',
        logo: logo,
        sport: activeLeague.sport,
        league: activeLeague.league,
        leagueKey: activeLeague.key,
        leagueLabel: activeLeague.label,
        season: activeLeague.season || CURRENT_SEASON,
        raw: team
      };
    }).filter(function(team) {
      return team.id && team.name;
    }).sort(function(a, b) {
      return a.name.localeCompare(b.name);
    });
  }

  function switchTab(tabName) {
    document.querySelectorAll('.modal-tab').forEach(function(tab) {
      tab.classList.remove('active');
    });

    document.querySelectorAll('.modal-panel').forEach(function(panel) {
      panel.classList.remove('active');
    });

    var tab = document.querySelector('.modal-tab[data-tab="' + tabName + '"]');
    var panel = $('panel-' + tabName);

    if (tab) tab.classList.add('active');
    if (panel) panel.classList.add('active');
  }

  function openTeamModal(team) {
    var overlay = $('modal-overlay');
    var hdr = $('modal-team-header');
    var tabsEl = $('modal-tabs');
    var panelsEl = $('modal-panels');

    if (!overlay || !hdr || !tabsEl || !panelsEl) return;

    overlay.classList.add('open');

    var logoHtml = team.logo
      ? '<img class="modal-logo" src="' + esc(team.logo) + '" alt="' + esc(team.name) + ' logo">'
      : '';

    hdr.innerHTML =
      logoHtml +
      '<div>' +
        '<div class="modal-team-name">' + esc(team.name) + '</div>' +
        '<div class="modal-team-sub">' +
          '<span>' + esc(team.leagueLabel || activeLeague.label) + '</span>' +
          (team.abbr ? '<span>' + esc(team.abbr) + '</span>' : '') +
          (team.location ? '<span>' + esc(team.location) + '</span>' : '') +
        '</div>' +
      '</div>';

    tabsEl.innerHTML = TEAM_TABS.map(function(tab) {
      return '<div class="modal-tab' + (tab.key === 'overview' ? ' active' : '') + '" data-tab="' + esc(tab.key) + '">' + esc(tab.label) + '</div>';
    }).join('');

    panelsEl.innerHTML = TEAM_TABS.map(function(tab) {
      return '<div class="modal-panel' + (tab.key === 'overview' ? ' active' : '') + '" id="panel-' + esc(tab.key) + '">' +
        '<div class="modal-loading">Loading...</div>' +
      '</div>';
    }).join('');

    tabsEl.querySelectorAll('.modal-tab').forEach(function(tabEl) {
      tabEl.addEventListener('click', function() {
        switchTab(tabEl.dataset.tab);
        loadPanel('panel-' + tabEl.dataset.tab, team, tabEl.dataset.tab);
      });
    });

    loadPanel('panel-overview', team, 'overview');
  }

  async function loadPanel(panelId, team, tab) {
    var panel = $(panelId);
    if (!panel || panel.dataset.loaded) return;

    panel.innerHTML = '<div class="modal-loading">Loading...</div>';

    try {
      var html = '';

      if (tab === 'overview') {
        html = buildOverviewPanel(team);
      } else if (tab === 'roster') {
        var players = await loadRoster(team);
        html = buildRosterPanel(players);
      } else if (tab === 'schedule') {
        html = buildSchedulePanel(team);
      } else if (tab === 'depth') {
        html = buildDepthPanel(team);
      } else if (tab === 'history') {
        html = buildHistoryPanel(team);
      }

      panel.innerHTML = html || '<div class="no-data">No data</div>';
      panel.dataset.loaded = '1';
    } catch(e) {
      panel.innerHTML =
        '<div class="modal-error">' +
          'Failed to load' +
          '<div class="error-details">' + esc(e.message || '') + '</div>' +
        '</div>';
    }
  }

  function buildOverviewPanel(team) {
    var raw = team.raw || {};

    var rows = [
      ['League', team.leagueLabel || activeLeague.label],
      ['Team ID', team.id || '—'],
      ['Abbreviation', team.abbr || '—'],
      ['Location', team.location || '—'],
      ['Nickname', team.nickname || '—'],
      ['Slug', team.slug || '—']
    ];

    if (raw.color) rows.push(['Primary Color', '#' + raw.color]);
    if (raw.alternateColor) rows.push(['Alt Color', '#' + raw.alternateColor]);

    var html = '<div class="modal-subtitle">Team Snapshot</div><div class="info-grid">';

    rows.forEach(function(row) {
      html +=
        '<div class="info-item">' +
          '<div class="info-label">' + esc(row[0]) + '</div>' +
          '<div class="info-val">' + esc(valueOrDash(row[1])) + '</div>' +
        '</div>';
    });

    html += '</div>';

    if (raw.links && Array.isArray(raw.links) && raw.links.length) {
      var web = raw.links.find(function(link) {
        return link && link.rel && link.rel.indexOf('clubhouse') !== -1;
      }) || raw.links[0];

      if (web && web.href) {
        html += '<div class="modal-subtitle">ESPN</div>';
        html += '<a href="' + esc(normalizeRefUrl(web.href)) + '" target="_blank" rel="noopener" style="font-size:11px;color:var(--accent-green);text-decoration:none;">OPEN TEAM PAGE →</a>';
      }
    }

    return html;
  }

  async function loadRoster(team) {
    var cacheKey = team.leagueKey + ':' + team.id;

    if (rosterCache[cacheKey]) {
      return rosterCache[cacheKey];
    }

    var league = {
      sport: team.sport,
      league: team.league,
      season: team.season
    };

    var url = coreRosterUrl(league, team.id);
    var data = await fetchJson(url);
    var athleteItems = Array.isArray(data.items) ? data.items : [];
    var athletes = await fetchRefs(athleteItems, 500);

    await Promise.all(athletes.map(function(player) {
      return hydrateAthleteRefs(player);
    }));

    athletes.forEach(function(player) {
      if (!player.team) player.team = team.raw || team;
      player.__team = team;
    });

    rosterCache[cacheKey] = athletes;

    return athletes;
  }

  function buildRosterPanel(players) {
    var list = Array.isArray(players) ? players.slice() : [];

    if (!list.length) {
      return '<div class="no-data">No roster data</div>';
    }

    list.sort(sortPlayers);

    var rows = list.map(function(player) {
      var pos = getPosition(player);
      var jersey = player.jersey || player.uniformNumber ? '#' + (player.jersey || player.uniformNumber) : '—';
      var inj = player.injuries && player.injuries.length
        ? '<span class="inj-dot" title="' + esc(player.injuries[0].status || 'Injured') + '"></span>'
        : '';

      return '<tr>' +
        '<td>' + esc(jersey) + '</td>' +
        '<td><span class="p-name">' + esc(getPlayerName(player)) + '</span>' + inj + '</td>' +
        '<td>' + esc(pos) + '</td>' +
        '<td>' + esc(formatHeight(player)) + '</td>' +
        '<td>' + esc(formatWeight(player)) + '</td>' +
      '</tr>';
    }).join('');

    return '<div style="overflow-x:auto">' +
      '<table class="roster-table">' +
        '<thead><tr><th>#</th><th>Name</th><th>Pos</th><th>HT</th><th>WT</th></tr></thead>' +
        '<tbody>' + rows + '</tbody>' +
      '</table>' +
    '</div>';
  }

  function buildSchedulePanel() {
    return '<div class="no-data">Schedule is not wired on this ESPN Core version yet</div>';
  }

  function buildDepthPanel() {
    return '<div class="no-data">Depth chart is not wired on this ESPN Core version yet</div>';
  }

  function buildHistoryPanel(team) {
    var raw = team.raw || {};

    var rows = [
      ['Name', team.name || '—'],
      ['League', team.leagueLabel || activeLeague.label],
      ['Team ID', team.id || '—'],
      ['UID', team.uid || '—'],
      ['Abbreviation', team.abbr || '—'],
      ['Location', team.location || '—'],
      ['Nickname', team.nickname || '—'],
      ['Slug', team.slug || '—']
    ];

    if (raw.color) rows.push(['Primary Color', '#' + raw.color]);
    if (raw.alternateColor) rows.push(['Alt Color', '#' + raw.alternateColor]);

    return rows.map(function(row) {
      return '<div class="bio-row"><span class="bio-label">' + esc(row[0]) + '</span><span class="bio-val">' + esc(valueOrDash(row[1])) + '</span></div>';
    }).join('');
  }

  function getPlayerName(player) {
    if (!player) return '—';

    return player.displayName ||
      player.fullName ||
      player.shortName ||
      player.name ||
      [player.firstName, player.lastName].filter(Boolean).join(' ') ||
      '—';
  }

  function getPosition(player) {
    if (!player || !player.position) return '—';

    if (typeof player.position === 'string') return player.position;

    return player.position.abbreviation ||
      player.position.name ||
      player.position.displayName ||
      player.position.shortDisplayName ||
      '—';
  }

  function formatHeight(player) {
    if (!player) return '—';

    if (player.displayHeight) return player.displayHeight;

    var height = player.height;

    if (!height) return '—';

    if (typeof height === 'string') return height;

    var inches = Number(height);

    if (!inches || isNaN(inches)) return '—';

    var feet = Math.floor(inches / 12);
    var rem = inches % 12;

    return feet + "'" + rem + '"';
  }

  function formatWeight(player) {
    if (!player) return '—';

    if (player.displayWeight) return player.displayWeight;

    var weight = player.weight;

    if (!weight) return '—';

    if (typeof weight === 'string') return weight;

    return String(weight) + ' lbs';
  }

  function sortPlayers(a, b) {
    var aNum = parseInt(a.jersey || a.uniformNumber || '999', 10);
    var bNum = parseInt(b.jersey || b.uniformNumber || '999', 10);

    if (!isNaN(aNum) && !isNaN(bNum) && aNum !== bNum) {
      return aNum - bNum;
    }

    return getPlayerName(a).localeCompare(getPlayerName(b));
  }

  function closeTeamModal() {
    var overlay = $('modal-overlay');
    if (overlay) overlay.classList.remove('open');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
