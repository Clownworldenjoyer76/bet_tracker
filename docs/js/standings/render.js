(function() {
  'use strict';

  var CURRENT_SEASON = 2026;

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
      cdnSlug: 'nba',
      type: 'standings',
      season: CURRENT_SEASON,
      playoffSpots: 8,
      showRankings: false
    },
    {
      key: 'nhl',
      label: 'NHL',
      enabled: true,
      sport: 'hockey',
      league: 'nhl',
      cdnSlug: 'nhl',
      type: 'standings',
      season: CURRENT_SEASON,
      playoffSpots: 8,
      showRankings: false
    },
    {
      key: 'wnba',
      label: 'WNBA',
      enabled: true,
      sport: 'basketball',
      league: 'wnba',
      cdnSlug: 'wnba',
      type: 'standings',
      season: CURRENT_SEASON,
      playoffSpots: 8,
      showRankings: false
    },
    {
      key: 'ncaam',
      label: 'NCAAM',
      enabled: true,
      sport: 'basketball',
      league: 'mens-college-basketball',
      cdnSlug: 'mens-college-basketball',
      type: 'standings',
      season: CURRENT_SEASON,
      playoffSpots: null,
      showRankings: true
    },
    {
      key: 'mlb',
      label: 'MLB',
      enabled: true,
      sport: 'baseball',
      league: 'mlb',
      cdnSlug: 'mlb',
      type: 'standings',
      season: CURRENT_SEASON,
      playoffSpots: 3,
      showRankings: false
    },
    {
      key: 'epl',
      label: 'EPL',
      enabled: true,
      sport: 'soccer',
      league: 'eng.1',
      cdnSlug: 'soccer',
      type: 'standings',
      season: CURRENT_SEASON,
      playoffSpots: null,
      showRankings: false
    },
    {
      key: 'mls',
      label: 'MLS',
      enabled: true,
      sport: 'soccer',
      league: 'usa.1',
      cdnSlug: 'soccer',
      type: 'standings',
      season: CURRENT_SEASON,
      playoffSpots: null,
      showRankings: false
    },
    {
      key: 'laliga',
      label: 'LA LIGA',
      enabled: true,
      sport: 'soccer',
      league: 'esp.1',
      cdnSlug: 'soccer',
      type: 'standings',
      season: CURRENT_SEASON,
      playoffSpots: null,
      showRankings: false
    },
    {
      key: 'ligue1',
      label: 'LIGUE 1',
      enabled: true,
      sport: 'soccer',
      league: 'fra.1',
      cdnSlug: 'soccer',
      type: 'standings',
      season: CURRENT_SEASON,
      playoffSpots: null,
      showRankings: false
    },
    {
      key: 'seriea',
      label: 'SERIE A',
      enabled: true,
      sport: 'soccer',
      league: 'ita.1',
      cdnSlug: 'soccer',
      type: 'standings',
      season: CURRENT_SEASON,
      playoffSpots: null,
      showRankings: false
    },
    {
      key: 'bundesliga',
      label: 'BUNDESLIGA',
      enabled: true,
      sport: 'soccer',
      league: 'ger.1',
      cdnSlug: 'soccer',
      type: 'standings',
      season: CURRENT_SEASON,
      playoffSpots: null,
      showRankings: false
    },
    {
      key: 'ufc',
      label: 'UFC',
      enabled: true,
      sport: 'mma',
      league: 'ufc',
      cdnSlug: 'ufc',
      type: 'placeholder',
      placeholder: true,
      season: CURRENT_SEASON,
      playoffSpots: null,
      showRankings: false
    }
  ];

  var activeLeagueKey = getDefaultLeagueKey();
  var activeLeague = getLeague(activeLeagueKey);
  var activeView = 'standings';

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
    var main = $('standings-main');
    if (main) main.innerHTML = html;
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

  function buildStandingsUrls(league) {
    var encodedLeague = encodeURIComponent(league.league);
    var sport = encodeURIComponent(league.sport);
    var siteUrl = 'https://site.api.espn.com/apis/v2/sports/' + sport + '/' + encodedLeague + '/standings';

    var urls = [
      siteUrl,
      siteUrl + '?season=' + encodeURIComponent(league.season || CURRENT_SEASON)
    ];

    if (league.sport === 'soccer') {
      urls.push('https://cdn.espn.com/core/soccer/standings?xhr=1&league=' + encodedLeague);
      urls.push('https://www.espn.com/soccer/standings/_/league/' + encodedLeague + '?xhr=1');
    } else {
      urls.push('https://cdn.espn.com/core/' + encodeURIComponent(league.cdnSlug || league.league) + '/standings?xhr=1');
      urls.push('https://www.espn.com/' + encodeURIComponent(league.cdnSlug || league.league) + '/standings?xhr=1');
    }

    return urls;
  }

  function buildRankingsUrls(league) {
    var encodedLeague = encodeURIComponent(league.league);
    var sport = encodeURIComponent(league.sport);

    return [
      'https://site.api.espn.com/apis/site/v2/sports/' + sport + '/' + encodedLeague + '/rankings',
      'https://site.api.espn.com/apis/site/v2/sports/' + sport + '/' + encodedLeague + '/rankings?season=' + encodeURIComponent(league.season || CURRENT_SEASON)
    ];
  }

  async function fetchJson(url) {
    var finalUrl = normalizeUrl(url);
    var response = await fetch(finalUrl);

    if (!response.ok) {
      throw new Error('HTTP ' + response.status + ' · ' + finalUrl);
    }

    return response.json();
  }

  async function fetchFirstJson(urls) {
    var lastError = null;

    for (var i = 0; i < urls.length; i++) {
      try {
        return {
          url: urls[i],
          data: await fetchJson(urls[i])
        };
      } catch (e) {
        lastError = e;
      }
    }

    throw lastError || new Error('No usable standings endpoint');
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
      '<div class="view-pill hidden" id="rankings-pill">Rankings</div>';

    updateRankingsPill();
  }

  function bindEvents() {
    var controls = $('league-controls');

    if (controls) {
      controls.addEventListener('click', function(e) {
        var leaguePill = e.target.closest('.league-pill');
        var rankingsPill = e.target.closest('#rankings-pill');

        if (leaguePill) {
          activateLeague(leaguePill.dataset.leagueKey);
          return;
        }

        if (rankingsPill && !rankingsPill.classList.contains('hidden')) {
          toggleRankings();
        }
      });
    }
  }

  function activateLeague(key) {
    var league = getLeague(key);

    if (!league) {
      showNoEnabledLeagues();
      return;
    }

    activeLeagueKey = league.key;
    activeLeague = league;
    activeView = 'standings';

    document.querySelectorAll('.league-pill').forEach(function(pill) {
      pill.classList.toggle('active', pill.dataset.leagueKey === activeLeagueKey);
    });

    updateRankingsPill();

    if (activeLeague.type === 'placeholder') {
      showPlaceholderLeague(activeLeague);
      return;
    }

    loadStandings();
  }

  function toggleRankings() {
    var pill = $('rankings-pill');

    if (!activeLeague || !activeLeague.showRankings) return;

    if (activeView === 'rankings') {
      activeView = 'standings';
      if (pill) pill.classList.remove('active');
      loadStandings();
    } else {
      activeView = 'rankings';
      if (pill) pill.classList.add('active');
      loadRankings();
    }
  }

  function updateRankingsPill() {
    var pill = $('rankings-pill');
    if (!pill) return;

    if (activeLeague && activeLeague.showRankings && activeLeague.type !== 'placeholder') {
      pill.classList.remove('hidden');
    } else {
      pill.classList.add('hidden');
      pill.classList.remove('active');
    }
  }

  function showNoEnabledLeagues() {
    var empty = $('standings-empty');
    if (empty) empty.style.display = 'none';

    setStatus('No standings leagues enabled', 'yellow');
    setMain(
      '<div class="placeholder-state">' +
        '<div class="placeholder-title">No Leagues Enabled</div>' +
        '<div class="placeholder-copy">Enable at least one league in docs/js/standings/render.js to show standings coverage.</div>' +
      '</div>'
    );
  }

  function showPlaceholderLeague(league) {
    var empty = $('standings-empty');
    if (empty) empty.style.display = 'none';

    setStatus(league.label + ' standings placeholder', 'yellow');
    setMain(
      '<div class="placeholder-state">' +
        '<div class="placeholder-title">' + esc(league.label) + ' Coming Next</div>' +
        '<div class="placeholder-copy">' +
          league.label +
          ' does not use a normal team standings table, so it is parked as a placeholder while the team-based leagues are wired first.' +
        '</div>' +
      '</div>'
    );
  }

  function getStat(stats, names) {
    if (!stats) return '—';

    var nameList = Array.isArray(names) ? names : [names];

    for (var i = 0; i < stats.length; i++) {
      var stat = stats[i];
      var statName = String(stat.name || stat.shortDisplayName || stat.displayName || '').toLowerCase();

      for (var j = 0; j < nameList.length; j++) {
        if (statName === String(nameList[j]).toLowerCase()) {
          return stat.displayValue !== undefined ? stat.displayValue : stat.value !== undefined ? stat.value : '—';
        }
      }
    }

    return '—';
  }

  function getNumericStat(entry, names) {
    var raw = getStat(entry.stats || [], names);
    var parsed = parseFloat(String(raw).replace(/[^\d.-]/g, ''));

    return isNaN(parsed) ? 0 : parsed;
  }

  function sortEntries(entries) {
    return entries.slice().sort(function(a, b) {
      if (activeLeague && activeLeague.sport === 'hockey') {
        return getNumericStat(b, ['points', 'pts']) - getNumericStat(a, ['points', 'pts']);
      }

      if (activeLeague && activeLeague.sport === 'soccer') {
        var ptsDiff = getNumericStat(b, ['points', 'pts']) - getNumericStat(a, ['points', 'pts']);
        if (ptsDiff !== 0) return ptsDiff;

        var gdDiff = getNumericStat(b, ['pointdifferential', 'differential', 'goaldifference', 'gd']) -
          getNumericStat(a, ['pointdifferential', 'differential', 'goaldifference', 'gd']);

        if (gdDiff !== 0) return gdDiff;
      }

      return getNumericStat(b, ['wins', 'w']) - getNumericStat(a, ['wins', 'w']);
    });
  }

  function getColumnsForLeague(league) {
    if (!league) {
      return [
        { label: 'W', names: ['wins', 'w'] },
        { label: 'L', names: ['losses', 'l'] },
        { label: 'PCT', names: ['winpercent', 'pct', 'win%'] }
      ];
    }

    if (league.sport === 'soccer') {
      return [
        { label: 'GP', names: ['gamesplayed', 'gp', 'played'] },
        { label: 'W', names: ['wins', 'w'] },
        { label: 'D', names: ['ties', 'draws', 'd'] },
        { label: 'L', names: ['losses', 'l'] },
        { label: 'GD', names: ['pointdifferential', 'differential', 'goaldifference', 'gd'] },
        { label: 'PTS', names: ['points', 'pts'] }
      ];
    }

    if (league.sport === 'hockey') {
      return [
        { label: 'GP', names: ['gamesplayed', 'gp'] },
        { label: 'W', names: ['wins', 'w'] },
        { label: 'L', names: ['losses', 'l'] },
        { label: 'OTL', names: ['otlosses', 'otl'] },
        { label: 'PTS', names: ['points', 'pts'] },
        { label: 'STRK', names: ['streak'] }
      ];
    }

    if (league.sport === 'baseball') {
      return [
        { label: 'W', names: ['wins', 'w'] },
        { label: 'L', names: ['losses', 'l'] },
        { label: 'PCT', names: ['winpercent', 'pct'] },
        { label: 'GB', names: ['gamesbehind', 'gb'] },
        { label: 'STRK', names: ['streak'] }
      ];
    }

    return [
      { label: 'W', names: ['wins', 'w'] },
      { label: 'L', names: ['losses', 'l'] },
      { label: 'PCT', names: ['winpercent', 'pct', 'win%'] },
      { label: 'GB', names: ['gamesbehind', 'gb'] },
      { label: 'STRK', names: ['streak'] }
    ];
  }

  function getTeamLogo(team) {
    if (!team) return '';

    if (Array.isArray(team.logos) && team.logos.length) {
      return normalizeUrl(team.logos[0].href || team.logos[0].url || '');
    }

    if (team.logo) return normalizeUrl(team.logo);

    return '';
  }

  function getTeamName(team) {
    if (!team) return '—';

    return team.shortDisplayName ||
      team.displayName ||
      team.name ||
      team.abbreviation ||
      '—';
  }

  function buildTable(entries, cutoff) {
    var cols = getColumnsForLeague(activeLeague);

    var thead =
      '<thead><tr><th>#</th><th>Team</th>' +
      cols.map(function(col) {
        return '<th>' + esc(col.label) + '</th>';
      }).join('') +
      '</tr></thead>';

    var rows = sortEntries(entries).map(function(entry, idx) {
      var team = entry.team || {};
      var stats = entry.stats || [];
      var logo = getTeamLogo(team);
      var logoHtml = logo
        ? '<img class="team-logo-sm" src="' + esc(logo) + '" loading="lazy" alt="' + esc(getTeamName(team)) + ' logo">'
        : '';

      var statCells = cols.map(function(col) {
        return '<td>' + esc(getStat(stats, col.names)) + '</td>';
      }).join('');

      var cutoffClass = cutoff && idx === cutoff - 1 ? ' class="playoff-cutoff"' : '';

      return '<tr' + cutoffClass + '>' +
        '<td class="rank-cell">' + (idx + 1) + '</td>' +
        '<td><div class="team-cell">' + logoHtml + '<span class="team-name-cell">' + esc(getTeamName(team)) + '</span></div></td>' +
        statCells +
      '</tr>';
    }).join('');

    var cutoffNote = cutoff
      ? '<tr><td colspan="' + (cols.length + 2) + '" class="playoff-label">— PLAYOFF LINE —</td></tr>'
      : '';

    return '<div class="table-scroll"><table class="standings-table">' + thead + '<tbody>' + rows + cutoffNote + '</tbody></table></div>';
  }

  function extractStandingsPayload(data) {
    if (!data) return null;

    if (data.children || data.standings) {
      return data;
    }

    if (data.content && data.content.standings) {
      return data.content.standings;
    }

    if (data.page && data.page.content && data.page.content.standings) {
      return data.page.content.standings;
    }

    if (data.standings && data.standings.groups) {
      return data.standings;
    }

    if (data.sports && data.sports[0] && data.sports[0].leagues && data.sports[0].leagues[0]) {
      var league = data.sports[0].leagues[0];

      if (league.standings) return league.standings;
    }

    return data;
  }

  function getGroupsFromPayload(payload) {
    if (!payload) return [];

    if (Array.isArray(payload.children)) return payload.children;
    if (Array.isArray(payload.groups)) return payload.groups;
    if (payload.standings && Array.isArray(payload.standings.groups)) return payload.standings.groups;
    if (payload.content && payload.content.standings && Array.isArray(payload.content.standings.groups)) return payload.content.standings.groups;

    return [];
  }

  function getEntriesFromNode(node) {
    if (!node) return [];

    if (node.standings && Array.isArray(node.standings.entries)) {
      return node.standings.entries;
    }

    if (Array.isArray(node.entries)) {
      return node.entries;
    }

    return [];
  }

  function getChildrenFromNode(node) {
    if (!node) return [];

    if (Array.isArray(node.children)) return node.children;
    if (Array.isArray(node.groups)) return node.groups;

    return [];
  }

  function getNodeName(node) {
    if (!node) return '';

    return node.name ||
      node.displayName ||
      node.shortDisplayName ||
      node.abbreviation ||
      '';
  }

  function renderStandingsData(data) {
    var main = $('standings-main');
    var empty = $('standings-empty');

    if (!main || !empty) return;

    var payload = extractStandingsPayload(data);
    var groups = getGroupsFromPayload(payload);

    main.innerHTML = '';
    empty.style.display = 'none';

    if (!groups.length) {
      var entries = getEntriesFromNode(payload && payload.standings ? payload.standings : payload);

      if (!entries.length) {
        empty.style.display = '';
        setStatus('No data', '');
        return;
      }

      var block = document.createElement('div');
      block.className = 'conference-block';
      block.innerHTML = buildTable(entries, activeLeague.playoffSpots || null);
      main.appendChild(block);
      setStatus(activeLeague.label + ' standings loaded', 'green');
      return;
    }

    var confWrap = document.createElement('div');
    confWrap.className = 'conferences-wrap';

    groups.forEach(function(group) {
      var confBlock = document.createElement('div');
      confBlock.className = 'conference-block';

      var groupName = getNodeName(group);

      if (groupName) {
        var header = document.createElement('div');
        header.className = 'conference-header';
        header.textContent = groupName;
        confBlock.appendChild(header);
      }

      var children = getChildrenFromNode(group);

      if (children.length) {
        children.forEach(function(child) {
          var childEntries = getEntriesFromNode(child);
          if (!childEntries.length) return;

          var divBlock = document.createElement('div');
          divBlock.className = 'division-block';

          var childName = getNodeName(child);

          if (childName) {
            var childHeader = document.createElement('div');
            childHeader.className = 'division-header';
            childHeader.textContent = childName;
            divBlock.appendChild(childHeader);
          }

          var childCutoff = activeLeague && activeLeague.sport === 'baseball' ? 1 : null;

          divBlock.innerHTML += buildTable(childEntries, childCutoff);
          confBlock.appendChild(divBlock);
        });
      } else {
        var entries = getEntriesFromNode(group);

        if (entries.length) {
          confBlock.innerHTML += buildTable(entries, activeLeague.playoffSpots || null);
        }
      }

      confWrap.appendChild(confBlock);
    });

    main.appendChild(confWrap);
    setStatus(activeLeague.label + ' standings loaded', 'green');
  }

  async function loadStandings() {
    if (!activeLeague) return;

    var main = $('standings-main');
    var empty = $('standings-empty');

    if (main) main.innerHTML = '';
    if (empty) empty.style.display = 'none';

    setStatus('Loading ' + activeLeague.label + ' standings...', 'yellow');

    try {
      var result = await fetchFirstJson(buildStandingsUrls(activeLeague));
      renderStandingsData(result.data);
    } catch(e) {
      setStatus('Failed to load ' + activeLeague.label + ' standings', 'red');

      if (empty) empty.style.display = 'none';

      setMain(
        '<div class="empty-state">' +
          'Failed to load standings' +
          '<div class="error-details">' + esc(e.message || '') + '</div>' +
        '</div>'
      );
    }
  }

  function normalizeRankingsPayload(data) {
    if (!data) return [];

    if (Array.isArray(data.rankings)) return data.rankings;

    if (data.content && Array.isArray(data.content.rankings)) {
      return data.content.rankings;
    }

    if (data.page && data.page.content && Array.isArray(data.page.content.rankings)) {
      return data.page.content.rankings;
    }

    return [];
  }

  async function loadRankings() {
    if (!activeLeague) return;

    var main = $('standings-main');
    var empty = $('standings-empty');

    if (main) main.innerHTML = '';
    if (empty) empty.style.display = 'none';

    setStatus('Loading ' + activeLeague.label + ' rankings...', 'yellow');

    try {
      var result = await fetchFirstJson(buildRankingsUrls(activeLeague));
      var polls = normalizeRankingsPayload(result.data);

      if (!polls.length) {
        if (empty) empty.style.display = '';
        setStatus('No rankings available', '');
        return;
      }

      var wrap = document.createElement('div');
      wrap.className = 'rankings-wrap';

      polls.forEach(function(poll) {
        var block = document.createElement('div');
        block.className = 'poll-block';

        var pollName = poll.name || poll.shortName || 'Poll';
        var updated = poll.lastUpdated
          ? new Date(poll.lastUpdated).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
          : '';

        block.innerHTML =
          '<div class="poll-header">' +
            esc(pollName) +
            (updated ? ' <span style="font-size:10px;color:var(--text-muted);font-weight:400">· Updated ' + esc(updated) + '</span>' : '') +
          '</div>';

        var ranks = poll.ranks || [];

        if (!ranks.length) {
          block.innerHTML += '<div class="no-data">No data</div>';
          wrap.appendChild(block);
          return;
        }

        var rows = ranks.map(function(entry) {
          var team = entry.team || {};
          var logo = getTeamLogo(team);
          var logoHtml = logo
            ? '<img class="team-logo-sm" src="' + esc(logo) + '" loading="lazy" alt="' + esc(getTeamName(team)) + ' logo">'
            : '';

          var record = entry.recordSummary || '';
          var points = entry.points !== undefined ? entry.points : '—';
          var prevRank = entry.previousRank || 0;
          var curRank = entry.current || entry.rank || 0;
          var change = '';

          if (prevRank && curRank) {
            var diff = prevRank - curRank;

            if (diff > 0) {
              change = '<span class="rank-chg-up">▲' + diff + '</span>';
            } else if (diff < 0) {
              change = '<span class="rank-chg-down">▼' + Math.abs(diff) + '</span>';
            } else {
              change = '<span class="rank-chg-same">—</span>';
            }
          }

          return '<tr>' +
            '<td><span class="rank-num">' + esc(curRank) + '</span></td>' +
            '<td><div class="team-cell">' + logoHtml + '<span class="team-name-cell">' + esc(getTeamName(team)) + '</span></div></td>' +
            '<td>' + esc(record) + '</td>' +
            '<td>' + esc(points) + '</td>' +
            '<td>' + change + '</td>' +
          '</tr>';
        }).join('');

        block.innerHTML +=
          '<div class="table-scroll">' +
            '<table class="rankings-table">' +
              '<thead><tr><th>#</th><th>Team</th><th>Record</th><th>Pts</th><th>Chg</th></tr></thead>' +
              '<tbody>' + rows + '</tbody>' +
            '</table>' +
          '</div>';

        wrap.appendChild(block);
      });

      main.appendChild(wrap);
      setStatus(polls.length + ' poll' + (polls.length > 1 ? 's' : '') + ' loaded', 'green');
    } catch(e) {
      setStatus('Failed to load rankings', 'red');
      setMain(
        '<div class="empty-state">' +
          'Failed to load rankings' +
          '<div class="error-details">' + esc(e.message || '') + '</div>' +
        '</div>'
      );
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
