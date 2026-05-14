(function() {
  'use strict';

  var CURRENT_SEASON = 2026;
  var CORE_API_ROOT = 'https://sports.core.api.espn.com/v2';

  var LEAGUES = [
    {
      key: 'nba',
      label: 'NBA',
      sport: 'basketball',
      league: 'nba',
      type: 'team-roster',
      season: CURRENT_SEASON,
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT']
    },
    {
      key: 'nhl',
      label: 'NHL',
      sport: 'hockey',
      league: 'nhl',
      type: 'team-roster',
      season: CURRENT_SEASON,
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT']
    },
    {
      key: 'wnba',
      label: 'WNBA',
      sport: 'basketball',
      league: 'wnba',
      type: 'team-roster',
      season: CURRENT_SEASON,
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT']
    },
    {
      key: 'ncaam',
      label: 'NCAAM',
      sport: 'basketball',
      league: 'mens-college-basketball',
      type: 'team-roster',
      season: CURRENT_SEASON,
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT']
    },
    {
      key: 'mlb',
      label: 'MLB',
      sport: 'baseball',
      league: 'mlb',
      type: 'team-roster',
      season: CURRENT_SEASON,
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'B/T']
    },
    {
      key: 'epl',
      label: 'EPL',
      sport: 'soccer',
      league: 'eng.1',
      type: 'team-roster',
      season: CURRENT_SEASON,
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'Nation']
    },
    {
      key: 'mls',
      label: 'MLS',
      sport: 'soccer',
      league: 'usa.1',
      type: 'team-roster',
      season: CURRENT_SEASON,
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'Nation']
    },
    {
      key: 'laliga',
      label: 'LA LIGA',
      sport: 'soccer',
      league: 'esp.1',
      type: 'team-roster',
      season: CURRENT_SEASON,
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'Nation']
    },
    {
      key: 'ligue1',
      label: 'LIGUE 1',
      sport: 'soccer',
      league: 'fra.1',
      type: 'team-roster',
      season: CURRENT_SEASON,
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'Nation']
    },
    {
      key: 'seriea',
      label: 'SERIE A',
      sport: 'soccer',
      league: 'ita.1',
      type: 'team-roster',
      season: CURRENT_SEASON,
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'Nation']
    },
    {
      key: 'bundesliga',
      label: 'BUNDESLIGA',
      sport: 'soccer',
      league: 'ger.1',
      type: 'team-roster',
      season: CURRENT_SEASON,
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'Nation']
    },
    {
      key: 'ufc',
      label: 'UFC',
      sport: 'mma',
      league: 'ufc',
      type: 'placeholder',
      placeholder: true,
      columns: ['Name', 'Division', 'Record', 'Status']
    }
  ];

  var activeLeagueKey = 'nba';
  var activeLeague = getLeague(activeLeagueKey);
  var allTeams = [];
  var playerDataCache = {};
  var refCache = {};

  var PLAYER_TABS = [
    { key: 'overview', label: 'Overview' },
    { key: 'gamelog',  label: 'Game Log' },
    { key: 'splits',   label: 'Splits' },
    { key: 'news',     label: 'News' },
    { key: 'bio',      label: 'Bio' }
  ];

  function $(id) {
    return document.getElementById(id);
  }

  function getLeague(key) {
    return LEAGUES.find(function(lg) {
      return lg.key === key;
    }) || LEAGUES[0];
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

  function stripTags(html) {
    var div = document.createElement('div');
    div.innerHTML = html || '';
    return div.textContent || div.innerText || '—';
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

  function setStatus(text, dotCls) {
    var statusText = $('status-text');
    var statusDot = $('status-dot');

    if (statusText) statusText.textContent = text || '';
    if (statusDot) statusDot.className = 'status-dot ' + (dotCls || '');
  }

  function setMain(html) {
    var main = $('players-main');
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

  async function hydrateEntityRefs(entity) {
    if (!entity || typeof entity !== 'object') return entity;

    var tasks = [];

    if (isRefItem(entity.position)) {
      tasks.push(fetchRef(entity.position).then(function(position) {
        entity.position = position;
      }).catch(function() {}));
    }

    if (isRefItem(entity.team)) {
      tasks.push(fetchRef(entity.team).then(function(team) {
        entity.team = team;
      }).catch(function() {}));
    }

    if (isRefItem(entity.country)) {
      tasks.push(fetchRef(entity.country).then(function(country) {
        entity.country = country;
      }).catch(function() {}));
    }

    if (isRefItem(entity.college)) {
      tasks.push(fetchRef(entity.college).then(function(college) {
        entity.college = college;
      }).catch(function() {}));
    }

    await Promise.all(tasks);

    return entity;
  }

  function init() {
    renderLeagueControls();
    bindStaticEvents();
    activateLeague(activeLeagueKey);
  }

  function renderLeagueControls() {
    var host = $('league-controls');
    if (!host) return;

    host.style.display = 'contents';
    host.innerHTML = LEAGUES.map(function(league) {
      var cls = 'league-pill';

      if (league.key === activeLeagueKey) cls += ' active';
      if (league.placeholder) cls += ' placeholder';

      return '<button type="button" class="' + cls + '" data-league-key="' + esc(league.key) + '">' + esc(league.label) + '</button>';
    }).join('');

    host.querySelectorAll('.league-pill').forEach(function(pill) {
      pill.addEventListener('click', function() {
        activateLeague(pill.dataset.leagueKey);
      });
    });
  }

  function bindStaticEvents() {
    var teamSelect = $('team-select');
    var modalClose = $('modal-close');
    var modalOverlay = $('modal-overlay');

    if (teamSelect) {
      teamSelect.addEventListener('change', function() {
        if (this.value) {
          loadRoster(this.value);
        } else {
          setMain('<div class="empty-state">Select a team to view roster</div>');
        }
      });
    }

    if (modalClose) {
      modalClose.addEventListener('click', function() {
        closePlayerModal();
      });
    }

    if (modalOverlay) {
      modalOverlay.addEventListener('click', function(e) {
        if (e.target === this) closePlayerModal();
      });
    }

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') closePlayerModal();
    });
  }

  function activateLeague(key) {
    activeLeagueKey = key;
    activeLeague = getLeague(key);
    allTeams = [];
    playerDataCache = {};

    document.querySelectorAll('.league-pill').forEach(function(pill) {
      pill.classList.toggle('active', pill.dataset.leagueKey === key);
    });

    if (activeLeague.type === 'placeholder') {
      showPlaceholderLeague(activeLeague);
      return;
    }

    var wrap = $('team-select-wrap');
    if (wrap) wrap.classList.remove('hidden');

    loadTeamList();
  }

  function showPlaceholderLeague(league) {
    var wrap = $('team-select-wrap');
    var sel = $('team-select');

    if (wrap) wrap.classList.add('hidden');
    if (sel) sel.innerHTML = '<option value="">— Select Team —</option>';

    setStatus(league.label + ' player coverage placeholder', 'yellow');
    setMain(
      '<div class="placeholder-state">' +
        '<div class="placeholder-title">' + esc(league.label) + ' Coming Next</div>' +
        '<div class="placeholder-copy">' +
          'This page is currently built around team rosters. ' +
          league.label +
          ' needs a separate fighter-directory model, so it is intentionally parked as a placeholder while the team-based leagues are wired first.' +
        '</div>' +
      '</div>'
    );
  }

  async function loadTeamList() {
    var sel = $('team-select');
    if (!sel) return;

    setStatus('Loading ' + activeLeague.label + ' teams...', 'yellow');

    sel.innerHTML = '<option value="">— Select Team —</option>';
    allTeams = [];

    var url = coreTeamsUrl(activeLeague);

    try {
      var data = await fetchJson(url);
      var teamItems = Array.isArray(data.items) ? data.items : [];
      var hydratedTeams = await fetchRefs(teamItems, 500);

      allTeams = normalizeTeams(hydratedTeams);

      if (!allTeams.length) {
        setStatus('No teams found for ' + activeLeague.label, 'red');
        setMain(
          '<div class="empty-state">' +
            'No teams found' +
            '<div class="error-details">' + esc(url) + '</div>' +
          '</div>'
        );
        return;
      }

      allTeams.forEach(function(team) {
        var opt = document.createElement('option');
        opt.value = team.id;
        opt.textContent = team.name;
        sel.appendChild(opt);
      });

      setStatus(activeLeague.label + ' · select a team', '');
      setMain('<div class="empty-state">Select a team to view roster</div>');
    } catch (e) {
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

    return teams.map(function(t) {
      var logos = Array.isArray(t.logos) ? t.logos : [];
      var logo = '';

      if (logos.length) {
        logo = logos[0].href || logos[0].url || '';
      }

      return {
        id: t.id || t.uid || t.abbreviation || '',
        uid: t.uid || '',
        name: t.displayName || t.name || t.shortDisplayName || t.abbreviation || 'Unknown Team',
        abbreviation: t.abbreviation || '',
        location: t.location || '',
        nickname: t.nickname || '',
        slug: t.slug || '',
        logo: logo,
        raw: t
      };
    }).filter(function(team) {
      return team.id && team.name;
    }).sort(function(a, b) {
      return a.name.localeCompare(b.name);
    });
  }

  async function loadRoster(teamId) {
    var team = allTeams.find(function(t) {
      return String(t.id) === String(teamId);
    });

    if (!team) return;

    setStatus('Loading ' + team.name + ' roster...', 'yellow');

    var url = coreRosterUrl(activeLeague, teamId);

    try {
      var data = await fetchJson(url);
      var athleteItems = Array.isArray(data.items) ? data.items : [];
      var athletes = await fetchRefs(athleteItems, 500);

      await Promise.all(athletes.map(function(player) {
        return hydrateEntityRefs(player);
      }));

      athletes.forEach(function(player) {
        if (!player.team) player.team = team.raw || team;
        player.__team = team;
        player.__league = activeLeague;
      });

      var groupMap = normalizeRosterGroups(athletes);
      renderRoster(team, groupMap);

      var count = groupMap.reduce(function(total, grp) {
        return total + grp.players.length;
      }, 0);

      setStatus(team.name + ' · ' + count + ' players · click any player for profile', 'green');
    } catch (e) {
      setStatus('Failed to load ' + team.name + ' roster', 'red');
      setMain(
        '<div class="empty-state">' +
          'Failed to load roster' +
          '<div class="error-details">' + esc(e.message || url) + '</div>' +
        '</div>'
      );
    }
  }

  function normalizeRosterGroups(players) {
    var list = Array.isArray(players) ? players : [];

    if (!list.length) {
      return [];
    }

    if (activeLeague.sport === 'soccer') {
      return groupPlayersByPositionType(list);
    }

    if (activeLeague.key === 'mlb') {
      return groupPlayersByPositionType(list);
    }

    return [
      {
        label: '',
        players: list.sort(sortPlayers)
      }
    ];
  }

  function groupPlayersByPositionType(players) {
    var buckets = {};
    var order = [];

    players.forEach(function(player) {
      var label = getPositionGroup(player);

      if (!buckets[label]) {
        buckets[label] = [];
        order.push(label);
      }

      buckets[label].push(player);
    });

    return order.map(function(label) {
      return {
        label: label,
        players: buckets[label].sort(sortPlayers)
      };
    });
  }

  function getPositionGroup(player) {
    var position = player && player.position ? player.position : null;
    var parent = '';

    if (position && typeof position === 'object') {
      parent = position.parent && typeof position.parent === 'object'
        ? position.parent.displayName || position.parent.name || ''
        : '';
    }

    if (parent) return parent;

    var pos = getPosition(player);

    if (activeLeague.sport === 'soccer') {
      if (/goalkeeper|^gk$/i.test(pos)) return 'Goalkeepers';
      if (/defender|^d$|^cb$|^lb$|^rb$/i.test(pos)) return 'Defenders';
      if (/midfielder|^m$|^cm$|^dm$|^am$/i.test(pos)) return 'Midfielders';
      if (/forward|striker|^f$|^st$|^fw$/i.test(pos)) return 'Forwards';
    }

    if (activeLeague.key === 'mlb') {
      if (/pitcher|^p$/i.test(pos)) return 'Pitchers';
      if (/catcher|^c$/i.test(pos)) return 'Catchers';
      if (/first|second|third|shortstop|infield|^1b$|^2b$|^3b$|^ss$/i.test(pos)) return 'Infielders';
      if (/outfield|left|center|right|^lf$|^cf$|^rf$|^of$/i.test(pos)) return 'Outfielders';
    }

    return 'Roster';
  }

  function sortPlayers(a, b) {
    var aNum = parseInt(a.jersey || a.uniformNumber || '999', 10);
    var bNum = parseInt(b.jersey || b.uniformNumber || '999', 10);

    if (!isNaN(aNum) && !isNaN(bNum) && aNum !== bNum) {
      return aNum - bNum;
    }

    return getPlayerName(a).localeCompare(getPlayerName(b));
  }

  function renderRoster(team, groupMap) {
    var main = $('players-main');
    if (!main) return;

    main.innerHTML = '';

    var hdr = document.createElement('div');
    hdr.className = 'roster-header';

    var logoHtml = team.logo
      ? '<img class="roster-logo" src="' + esc(team.logo) + '" alt="' + esc(team.name) + ' logo">'
      : '';

    hdr.innerHTML =
      logoHtml +
      '<div>' +
        '<div class="roster-team-name">' + esc(team.name) + '</div>' +
        '<div class="roster-team-meta">' + esc(activeLeague.label) + ' · ESPN core roster</div>' +
      '</div>';

    main.appendChild(hdr);

    if (!groupMap.length) {
      var empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = 'No roster data available';
      main.appendChild(empty);
      return;
    }

    var cols = activeLeague.columns || ['#', 'Name', 'Pos', 'Age'];
    var wrap = document.createElement('div');
    wrap.className = 'players-wrap';

    var table = document.createElement('table');
    table.className = 'players-table';
    table.innerHTML =
      '<thead><tr>' +
      cols.map(function(c) {
        return '<th>' + esc(c) + '</th>';
      }).join('') +
      '<th>Status</th>' +
      '</tr></thead>';

    var tbody = document.createElement('tbody');

    groupMap.forEach(function(group) {
      if (group.label) {
        var gh = document.createElement('tr');
        gh.className = 'roster-group-row';
        gh.innerHTML =
          '<td colspan="' + (cols.length + 1) + '">' +
            '<div class="roster-group-header">' + esc(group.label) + '</div>' +
          '</td>';
        tbody.appendChild(gh);
      }

      group.players.forEach(function(player) {
        tbody.appendChild(buildPlayerRow(player, cols));
      });
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    main.appendChild(wrap);
  }

  function buildPlayerRow(player, cols) {
    var tr = document.createElement('tr');
    tr.className = 'player-row';

    var cells = cols.map(function(col) {
      return getPlayerCell(player, col);
    });

    var status = getPlayerStatus(player);

    tr.innerHTML =
      cells.map(function(cell) {
        return '<td>' + cell + '</td>';
      }).join('') +
      '<td>' + status + '</td>';

    if (player && player.id) {
      tr.addEventListener('click', function() {
        openPlayerModal(player);
      });
    }

    return tr;
  }

  function getPlayerCell(player, col) {
    if (!player) return '—';

    if (col === '#') {
      return esc(valueOrDash(player.jersey || player.uniformNumber));
    }

    if (col === 'Name') {
      return '<span class="player-name-cell">' + esc(getPlayerName(player)) + '</span>';
    }

    if (col === 'Pos') {
      return esc(getPosition(player));
    }

    if (col === 'Age') {
      return esc(valueOrDash(player.age));
    }

    if (col === 'HT') {
      return esc(valueOrDash(formatHeight(player)));
    }

    if (col === 'WT') {
      return esc(valueOrDash(formatWeight(player)));
    }

    if (col === 'B/T') {
      return esc(getBatsThrows(player));
    }

    if (col === 'Nation') {
      return esc(getNation(player));
    }

    if (col === 'Division') {
      return esc(valueOrDash(player.division || player.weightClass || player.weightclass));
    }

    if (col === 'Record') {
      return esc(valueOrDash(player.record || player.displayRecord));
    }

    if (col === 'Status') {
      return getPlayerStatus(player);
    }

    return '—';
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

  function getBatsThrows(player) {
    var batsVal = '—';
    var throwsVal = '—';

    if (player.bats) {
      batsVal = typeof player.bats === 'string'
        ? player.bats
        : player.bats.abbreviation || player.bats.displayValue || player.bats.name || '—';
    }

    if (player.throws) {
      throwsVal = typeof player.throws === 'string'
        ? player.throws
        : player.throws.abbreviation || player.throws.displayValue || player.throws.name || '—';
    }

    if (batsVal === '—' && throwsVal === '—') return '—';

    return batsVal + '/' + throwsVal;
  }

  function getNation(player) {
    if (!player) return '—';

    if (player.citizenship) return player.citizenship;
    if (player.nationality) return player.nationality;

    if (player.country) {
      if (typeof player.country === 'string') return player.country;

      return player.country.abbreviation ||
        player.country.displayName ||
        player.country.name ||
        '—';
    }

    if (player.birthPlace && player.birthPlace.country) return player.birthPlace.country;
    if (player.birthCountry) return player.birthCountry;

    return '—';
  }

  function getPlayerStatus(player) {
    if (!player) return '—';

    if (player.injuries && player.injuries.length) {
      return '<span class="inj-badge">' + esc(player.injuries[0].status || player.injuries[0].type || 'Injured') + '</span>';
    }

    if (player.status) {
      if (typeof player.status === 'string') return esc(player.status);

      return esc(player.status.name || player.status.type || player.status.displayName || '—');
    }

    if (player.active === false) return 'Inactive';

    return '—';
  }

  function switchTab(tabKey) {
    document.querySelectorAll('.modal-tab').forEach(function(t) {
      t.classList.remove('active');
    });

    document.querySelectorAll('.modal-panel').forEach(function(p) {
      p.classList.remove('active');
    });

    var tab = document.querySelector('.modal-tab[data-tab="' + tabKey + '"]');
    var panel = $('ppanel-' + tabKey);

    if (tab) tab.classList.add('active');
    if (panel) panel.classList.add('active');
  }

  async function loadPlayerPanel(panelId, player, tab) {
    var panel = $(panelId);
    if (!panel || panel.dataset.loaded) return;

    panel.innerHTML = '<div class="modal-loading">Loading...</div>';

    try {
      var cacheKey = activeLeague.key + ':' + player.id;
      var data = playerDataCache[cacheKey];

      if (!data) {
        data = await hydrateEntityRefs(player);
        playerDataCache[cacheKey] = data;
      }

      var html = '';

      if (tab === 'overview') {
        html = buildOverview(data, player);
      } else if (tab === 'gamelog') {
        html = buildGamelog(data);
      } else if (tab === 'splits') {
        html = buildSplits(data);
      } else if (tab === 'news') {
        html = buildNews(data);
      } else if (tab === 'bio') {
        html = buildBio(data, player);
      }

      panel.innerHTML = html || '<div class="no-data">No data available</div>';
      panel.dataset.loaded = '1';
    } catch (e) {
      panel.innerHTML =
        '<div class="modal-error">' +
          'Failed to load player data' +
          '<div class="error-details">' + esc(e.message || '') + '</div>' +
        '</div>';
    }
  }

  function buildOverview(data, player) {
    var html = '<div class="modal-subtitle">Player Snapshot</div>';

    var rows = [
      ['League', activeLeague.label],
      ['Team', getPlayerTeam(player)],
      ['Position', getPosition(player)],
      ['Jersey', player.jersey ? '#' + player.jersey : '—'],
      ['Age', player.age || '—'],
      ['Height', formatHeight(player)],
      ['Weight', formatWeight(player)],
      ['Nation', getNation(player)],
      ['Status', stripTags(getPlayerStatus(player))]
    ];

    html += '<div class="info-grid">';

    rows.forEach(function(row) {
      html +=
        '<div class="info-item">' +
          '<div class="info-label">' + esc(row[0]) + '</div>' +
          '<div class="info-val">' + esc(valueOrDash(row[1])) + '</div>' +
        '</div>';
    });

    html += '</div>';

    if (data && data.dateOfBirth) {
      html += '<div class="modal-subtitle" style="margin-top:12px">Bio</div>';
      html += '<div class="bio-row"><span class="bio-label">Date of Birth</span><span class="bio-val">' + esc(formatDate(data.dateOfBirth)) + '</span></div>';
    }

    if (data && data.birthPlace) {
      html += '<div class="bio-row"><span class="bio-label">Birthplace</span><span class="bio-val">' + esc(formatBirthPlace(data.birthPlace)) + '</span></div>';
    }

    return html;
  }

  function buildGamelog() {
    return '<div class="no-data">Game log data is not wired on the ESPN core roster route yet</div>';
  }

  function buildSplits() {
    return '<div class="no-data">Splits data is not wired on the ESPN core roster route yet</div>';
  }

  function buildNews() {
    return '<div class="no-data">News data is not wired on the ESPN core roster route yet</div>';
  }

  function buildBio(data, player) {
    var rows = [
      ['Name', getPlayerName(player)],
      ['League', activeLeague.label],
      ['Team', getPlayerTeam(player)],
      ['Position', getPosition(player)],
      ['Jersey', player.jersey ? '#' + player.jersey : '—'],
      ['Age', player.age || '—'],
      ['Height', formatHeight(player)],
      ['Weight', formatWeight(player)],
      ['Nation', getNation(player)],
      ['Date of Birth', data && data.dateOfBirth ? formatDate(data.dateOfBirth) : '—'],
      ['Birthplace', data && data.birthPlace ? formatBirthPlace(data.birthPlace) : '—'],
      ['Status', stripTags(getPlayerStatus(player))]
    ];

    return rows.map(function(row) {
      return '<div class="bio-row"><span class="bio-label">' + esc(row[0]) + '</span><span class="bio-val">' + esc(valueOrDash(row[1])) + '</span></div>';
    }).join('');
  }

  function formatDate(value) {
    if (!value) return '—';

    var d = new Date(value);

    if (isNaN(d.getTime())) return value;

    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  function formatBirthPlace(place) {
    if (!place) return '—';

    if (typeof place === 'string') return place;

    return [
      place.city,
      place.state,
      place.country
    ].filter(Boolean).join(', ') || '—';
  }

  function getPlayerTeam(player) {
    if (!player) return '—';

    if (player.__team && player.__team.name) return player.__team.name;

    if (!player.team) return '—';

    if (typeof player.team === 'string') return player.team;

    return player.team.displayName ||
      player.team.name ||
      player.team.abbreviation ||
      player.team.shortDisplayName ||
      '—';
  }

  function openPlayerModal(player) {
    var overlay = $('modal-overlay');
    var header = $('modal-player-header');
    var tabs = $('modal-tabs');
    var panels = $('modal-panels');

    if (!overlay || !header || !tabs || !panels) return;

    overlay.classList.add('open');

    var headshot = '';

    if (player.headshot) {
      headshot = player.headshot.href || player.headshot;
    } else if (player.images && player.images.length) {
      headshot = player.images[0].href || player.images[0].url || '';
    }

    headshot = normalizeRefUrl(headshot);

    var imgHtml = headshot
      ? '<img class="modal-headshot" src="' + esc(headshot) + '" alt="' + esc(getPlayerName(player)) + '">'
      : '<div class="modal-headshot-placeholder">👤</div>';

    var pos = getPosition(player);
    var jersey = player.jersey ? '#' + player.jersey : '';
    var team = getPlayerTeam(player);

    header.innerHTML =
      imgHtml +
      '<div>' +
        '<div class="modal-player-name">' + esc(getPlayerName(player)) + '</div>' +
        '<div class="modal-player-meta">' +
          (pos && pos !== '—' ? '<span class="tag">' + esc(pos) + '</span>' : '') +
          (jersey ? '<span>' + esc(jersey) + '</span>' : '') +
          (team && team !== '—' ? '<span>' + esc(team) + '</span>' : '') +
          '<span>' + esc(activeLeague.label) + '</span>' +
        '</div>' +
      '</div>';

    tabs.innerHTML = PLAYER_TABS.map(function(tab) {
      return '<div class="modal-tab' + (tab.key === 'overview' ? ' active' : '') + '" data-tab="' + esc(tab.key) + '">' + esc(tab.label) + '</div>';
    }).join('');

    panels.innerHTML = PLAYER_TABS.map(function(tab) {
      return '<div class="modal-panel' + (tab.key === 'overview' ? ' active' : '') + '" id="ppanel-' + esc(tab.key) + '">' +
        '<div class="modal-loading">Loading...</div>' +
      '</div>';
    }).join('');

    tabs.querySelectorAll('.modal-tab').forEach(function(tabEl) {
      tabEl.addEventListener('click', function() {
        switchTab(tabEl.dataset.tab);
        loadPlayerPanel('ppanel-' + tabEl.dataset.tab, player, tabEl.dataset.tab);
      });
    });

    loadPlayerPanel('ppanel-overview', player, 'overview');
  }

  function closePlayerModal() {
    var overlay = $('modal-overlay');
    if (overlay) overlay.classList.remove('open');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
