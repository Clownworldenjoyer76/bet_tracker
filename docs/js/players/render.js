(function() {
  'use strict';

  var LEAGUES = [
    {
      key: 'nba',
      label: 'NBA',
      sport: 'basketball',
      league: 'nba',
      type: 'team-roster',
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT']
    },
    {
      key: 'nhl',
      label: 'NHL',
      sport: 'hockey',
      league: 'nhl',
      type: 'team-roster',
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT']
    },
    {
      key: 'wnba',
      label: 'WNBA',
      sport: 'basketball',
      league: 'wnba',
      type: 'team-roster',
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT']
    },
    {
      key: 'ncaam',
      label: 'NCAAM',
      sport: 'basketball',
      league: 'mens-college-basketball',
      type: 'team-roster',
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT']
    },
    {
      key: 'mlb',
      label: 'MLB',
      sport: 'baseball',
      league: 'mlb',
      type: 'team-roster',
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'B/T']
    },
    {
      key: 'epl',
      label: 'EPL',
      sport: 'soccer',
      league: 'eng.1',
      type: 'team-roster',
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'Nation']
    },
    {
      key: 'mls',
      label: 'MLS',
      sport: 'soccer',
      league: 'usa.1',
      type: 'team-roster',
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'Nation']
    },
    {
      key: 'laliga',
      label: 'LA LIGA',
      sport: 'soccer',
      league: 'esp.1',
      type: 'team-roster',
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'Nation']
    },
    {
      key: 'ligue1',
      label: 'LIGUE 1',
      sport: 'soccer',
      league: 'fra.1',
      type: 'team-roster',
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'Nation']
    },
    {
      key: 'seriea',
      label: 'SERIE A',
      sport: 'soccer',
      league: 'ita.1',
      type: 'team-roster',
      columns: ['#', 'Name', 'Pos', 'Age', 'HT', 'WT', 'Nation']
    },
    {
      key: 'bundesliga',
      label: 'BUNDESLIGA',
      sport: 'soccer',
      league: 'ger.1',
      type: 'team-roster',
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

  function buildApiBase(league) {
    return 'https://site.api.espn.com/apis/site/v2/sports/' + league.sport + '/' + league.league;
  }

  function buildCommonApiBase(league) {
    return 'https://site.web.api.espn.com/apis/common/v3/sports/' + league.sport + '/' + league.league;
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
        if (this.value) loadRoster(this.value);
        else setMain('<div class="empty-state">Select a team to view roster</div>');
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

    var url = buildApiBase(activeLeague) + '/teams?limit=500';

    try {
      var r = await fetch(url);

      if (!r.ok) {
        throw new Error('HTTP ' + r.status + ' · ' + url);
      }

      var data = await r.json();
      allTeams = normalizeTeams(data);

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

  function normalizeTeams(data) {
    var teams = [];

    try {
      if (
        data &&
        data.sports &&
        data.sports[0] &&
        data.sports[0].leagues &&
        data.sports[0].leagues[0] &&
        Array.isArray(data.sports[0].leagues[0].teams)
      ) {
        teams = data.sports[0].leagues[0].teams;
      } else if (data && Array.isArray(data.teams)) {
        teams = data.teams;
      }
    } catch (e) {
      teams = [];
    }

    return teams.map(function(entry) {
      var t = entry.team || entry;
      var logos = Array.isArray(t.logos) ? t.logos : [];
      var logo = logos.length ? logos[0].href : '';

      return {
        id: t.id || t.uid || t.abbreviation || '',
        name: t.displayName || t.name || t.shortDisplayName || t.abbreviation || 'Unknown Team',
        abbreviation: t.abbreviation || '',
        location: t.location || '',
        logo: logo
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

    var url = buildApiBase(activeLeague) + '/teams/' + encodeURIComponent(teamId) + '/roster';

    try {
      var r = await fetch(url);

      if (!r.ok) {
        throw new Error('HTTP ' + r.status + ' · ' + url);
      }

      var data = await r.json();
      var groupMap = normalizeRosterGroups(data);
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

  function normalizeRosterGroups(data) {
    var rawGroups = [];

    if (data && Array.isArray(data.athletes)) {
      rawGroups = data.athletes;
    } else if (data && data.team && Array.isArray(data.team.athletes)) {
      rawGroups = data.team.athletes;
    } else if (data && Array.isArray(data.roster)) {
      rawGroups = data.roster;
    }

    var groups = [];

    rawGroups.forEach(function(group) {
      var players = [];

      if (group && Array.isArray(group.items)) {
        players = group.items;
      } else if (group && Array.isArray(group.athletes)) {
        players = group.athletes;
      } else if (group && group.id) {
        players = [group];
      }

      if (players.length) {
        groups.push({
          label: group.displayName || group.name || group.position || '',
          players: players
        });
      }
    });

    if (!groups.length && rawGroups.length) {
      groups.push({
        label: '',
        players: rawGroups
      });
    }

    return groups;
  }

  function renderRoster(team, groupMap) {
    var main = $('players-main');
    if (!main) return;

    main.innerHTML = '';

    var hdr = document.createElement('div');
    hdr.className = 'roster-header';

    var logoHtml = team.logo ? '<img class="roster-logo" src="' + esc(team.logo) + '" alt="' + esc(team.name) + ' logo">' : '';

    hdr.innerHTML =
      logoHtml +
      '<div>' +
        '<div class="roster-team-name">' + esc(team.name) + '</div>' +
        '<div class="roster-team-meta">' + esc(activeLeague.label) + ' · ESPN roster</div>' +
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
      return '<span class="player-name-cell">' + esc(player.displayName || player.fullName || player.name || '—') + '</span>';
    }

    if (col === 'Pos') {
      return esc(getPosition(player));
    }

    if (col === 'Age') {
      return esc(valueOrDash(player.age));
    }

    if (col === 'HT') {
      return esc(valueOrDash(player.displayHeight || player.height));
    }

    if (col === 'WT') {
      return esc(valueOrDash(player.displayWeight || player.weight));
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

  function getPosition(player) {
    if (!player || !player.position) return '—';

    if (typeof player.position === 'string') return player.position;

    return player.position.abbreviation ||
      player.position.name ||
      player.position.displayName ||
      player.position.shortDisplayName ||
      '—';
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
      return player.country.abbreviation || player.country.displayName || player.country.name || '—';
    }
    if (player.birthPlace && player.birthPlace.country) return player.birthPlace.country;

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
        var url = buildCommonApiBase(activeLeague) + '/athletes/' + encodeURIComponent(player.id) + '/overview';
        var r = await fetch(url);

        if (!r.ok) {
          throw new Error('HTTP ' + r.status + ' · ' + url);
        }

        data = await r.json();
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
    var stats = data.statistics || {};
    var labels = stats.labels || [];
    var splits = Array.isArray(stats.splits) ? stats.splits : [];
    var vals = splits.length ? splits[0].stats || [] : [];
    var html = '<div class="modal-subtitle">Season Stats</div>';

    if (vals.length && labels.length) {
      html += '<div class="info-grid">';

      labels.slice(0, 12).forEach(function(label, i) {
        html +=
          '<div class="info-item">' +
            '<div class="info-label">' + esc(label) + '</div>' +
            '<div class="info-val">' + esc(vals[i] !== undefined ? vals[i] : '—') + '</div>' +
          '</div>';
      });

      html += '</div>';
    } else {
      html += '<div class="no-data">No season stats available</div>';
    }

    var roto = data.rotowire;

    if (roto && roto.headline) {
      html += '<div class="modal-subtitle" style="margin-top:12px">Latest Note</div>';
      html += '<div style="font-size:11px;color:var(--text-muted);line-height:1.6">' + esc(roto.headline || '') + '</div>';

      if (roto.story) {
        html += '<div style="font-size:11px;color:var(--text-muted);margin-top:6px;line-height:1.6">' + esc(roto.story) + '</div>';
      }
    }

    var fallbackRows = [
      ['League', activeLeague.label],
      ['Team', getPlayerTeam(player)],
      ['Position', getPosition(player)],
      ['Status', stripTags(getPlayerStatus(player))]
    ];

    html += '<div class="modal-subtitle" style="margin-top:12px">Player Snapshot</div>';
    html += fallbackRows.map(function(row) {
      return '<div class="bio-row"><span class="bio-label">' + esc(row[0]) + '</span><span class="bio-val">' + esc(row[1]) + '</span></div>';
    }).join('');

    return html;
  }

  function buildGamelog(data) {
    var gl = data.gameLog || {};
    var statGroups = gl.statistics || [];
    var eventsDict = gl.events || {};

    if (!statGroups.length) {
      return '<div class="no-data">No game log data</div>';
    }

    var statGroup = statGroups[0];
    var labels = statGroup.labels || [];
    var sgEvents = statGroup.events || [];

    if (!sgEvents.length) {
      return '<div class="no-data">No games found</div>';
    }

    var thead =
      '<tr>' +
        '<th>Date</th>' +
        '<th>Opp</th>' +
        '<th>Result</th>' +
        labels.slice(0, 8).map(function(label) {
          return '<th>' + esc(label) + '</th>';
        }).join('') +
      '</tr>';

    var rows = sgEvents.slice(0, 25).map(function(entry) {
      var ev = eventsDict[entry.eventId] || {};
      var dateStr = ev.gameDate
        ? new Date(ev.gameDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        : '—';
      var opp = ev.opponent
        ? ev.opponent.abbreviation || ev.opponent.displayName || ev.atVs || '—'
        : ev.atVs || '—';
      var result = ev.gameResult || '';
      var resStyle = result === 'W'
        ? ' style="color:var(--accent-green);font-weight:700"'
        : result === 'L'
          ? ' style="color:var(--accent-red);font-weight:700"'
          : '';
      var statVals = entry.stats || [];

      return '<tr>' +
        '<td>' + esc(dateStr) + '</td>' +
        '<td>' + esc(opp) + '</td>' +
        '<td' + resStyle + '>' + esc(result) + '</td>' +
        statVals.slice(0, 8).map(function(v) {
          return '<td>' + esc(v !== null && v !== undefined ? v : '—') + '</td>';
        }).join('') +
      '</tr>';
    }).join('');

    return '<div style="overflow-x:auto"><table class="stat-table"><thead>' + thead + '</thead><tbody>' + rows + '</tbody></table></div>';
  }

  function buildSplits(data) {
    var stats = data.statistics || {};
    var labels = stats.labels || [];
    var splits = Array.isArray(stats.splits) ? stats.splits : [];

    if (!splits.length) {
      return '<div class="no-data">No splits data</div>';
    }

    var html =
      '<div style="overflow-x:auto">' +
        '<table class="stat-table">' +
          '<thead>' +
            '<tr>' +
              '<th>Split</th>' +
              labels.slice(0, 8).map(function(label) {
                return '<th>' + esc(label) + '</th>';
              }).join('') +
            '</tr>' +
          '</thead>' +
          '<tbody>';

    splits.forEach(function(split) {
      var vals = split.stats || [];

      html +=
        '<tr>' +
          '<td>' + esc(split.displayName || split.name || '—') + '</td>' +
          vals.slice(0, 8).map(function(v) {
            return '<td>' + esc(v !== null && v !== undefined ? v : '—') + '</td>';
          }).join('') +
        '</tr>';
    });

    html += '</tbody></table></div>';

    return html;
  }

  function buildNews(data) {
    var articles = [];

    if (Array.isArray(data.news)) {
      articles = data.news;
    } else if (data.news && Array.isArray(data.news.articles)) {
      articles = data.news.articles;
    }

    if (!articles.length) {
      return '<div class="no-data">No news available</div>';
    }

    return articles.slice(0, 10).map(function(article) {
      var date = article.published
        ? new Date(article.published).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
        : '';
      var url = article.links && article.links.web
        ? article.links.web.href
        : article.links && article.links.mobile
          ? article.links.mobile.href
          : '#';

      return '<div class="news-item">' +
        '<div class="news-headline">' + esc(article.headline || '') + '</div>' +
        '<div class="news-meta">' + esc(article.source || 'ESPN') + (date ? ' · ' + esc(date) : '') + '</div>' +
        '<a class="news-link" href="' + esc(url) + '" target="_blank" rel="noopener">READ →</a>' +
      '</div>';
    }).join('');
  }

  function buildBio(data, player) {
    var roto = data.rotowire || {};

    var rows = [
      ['Name', player.displayName || player.fullName || player.name || '—'],
      ['League', activeLeague.label],
      ['Team', getPlayerTeam(player)],
      ['Position', getPosition(player)],
      ['Jersey', player.jersey ? '#' + player.jersey : '—'],
      ['Age', player.age || '—'],
      ['Height', player.displayHeight || player.height || '—'],
      ['Weight', player.displayWeight || player.weight || '—'],
      ['Nation', getNation(player)],
      ['Status', stripTags(getPlayerStatus(player))]
    ];

    if (player.injuries && player.injuries.length) {
      rows.push(['Injury', player.injuries[0].status || player.injuries[0].type || '—']);
    }

    var html = rows.map(function(row) {
      return '<div class="bio-row"><span class="bio-label">' + esc(row[0]) + '</span><span class="bio-val">' + esc(row[1]) + '</span></div>';
    }).join('');

    if (roto.story) {
      html += '<div class="modal-subtitle" style="margin-top:12px">Rotowire</div>';
      html += '<div style="font-size:11px;color:var(--text-muted);line-height:1.6">' + esc(roto.story) + '</div>';
    }

    return html;
  }

  function getPlayerTeam(player) {
    if (!player || !player.team) return '—';

    if (typeof player.team === 'string') return player.team;

    return player.team.displayName ||
      player.team.name ||
      player.team.abbreviation ||
      player.team.shortDisplayName ||
      '—';
  }

  function stripTags(html) {
    var div = document.createElement('div');
    div.innerHTML = html || '';
    return div.textContent || div.innerText || '—';
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

    var imgHtml = headshot
      ? '<img class="modal-headshot" src="' + esc(headshot) + '" alt="' + esc(player.displayName || player.fullName || 'Player') + '">'
      : '<div class="modal-headshot-placeholder">👤</div>';

    var pos = getPosition(player);
    var jersey = player.jersey ? '#' + player.jersey : '';
    var team = getPlayerTeam(player);

    header.innerHTML =
      imgHtml +
      '<div>' +
        '<div class="modal-player-name">' + esc(player.displayName || player.fullName || player.name || '') + '</div>' +
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
