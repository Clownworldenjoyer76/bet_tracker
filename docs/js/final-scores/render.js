(function() {
  'use strict';

  var CORE_API_ROOT = 'https://sports.core.api.espn.com/v2';

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
      enabled: true,
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
      enabled: true,
      sport: 'mma',
      league: 'ufc',
      type: 'placeholder',
      placeholder: true
    }
  ];

  var activeLeague = 'all';
  var allData = {};
  var refCache = {};

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

  function todayStr() {
    return new Date().toISOString().slice(0, 10);
  }

  function toESPNDate(dateValue) {
    return String(dateValue || todayStr()).replace(/-/g, '');
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

  function siteScoreboardUrl(cfg, espnDate) {
    return 'https://site.api.espn.com/apis/site/v2/sports/' +
      encodeURIComponent(cfg.sport) +
      '/' +
      encodeURIComponent(cfg.league) +
      '/scoreboard?dates=' +
      encodeURIComponent(espnDate);
  }

  function coreEventsUrl(cfg, espnDate) {
    return CORE_API_ROOT +
      '/sports/' +
      encodeURIComponent(cfg.sport) +
      '/leagues/' +
      encodeURIComponent(cfg.league) +
      '/events?dates=' +
      encodeURIComponent(espnDate) +
      '&limit=200';
  }

  async function loadLeagueEvents(cfg, espnDate) {
    try {
      var siteData = await fetchJson(siteScoreboardUrl(cfg, espnDate));
      return normalizeSiteEvents(cfg, siteData.events || []);
    } catch (siteError) {
      return loadCoreEvents(cfg, espnDate);
    }
  }

  async function loadCoreEvents(cfg, espnDate) {
    var data = await fetchJson(coreEventsUrl(cfg, espnDate));
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
        sport: cfg.sport,
        league: cfg.league,
        date: ev.date || comp.date || '',
        status: ev.status || comp.status || null,
        source: 'site',
        raw: ev,
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
      sport: cfg.sport,
      league: cfg.league,
      date: ev.date || competition.date || '',
      status: status,
      source: 'core',
      raw: ev,
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

  function isFinal(ev) {
    var type = getStatusType(ev);

    return type.completed === true ||
      ev.status.completed === true ||
      String(type.state || ev.status.state || '').toLowerCase() === 'post';
  }

  function getWinnerFlags(ev) {
    var awayScore = ev.away && ev.away.score !== null ? parseFloat(ev.away.score) : NaN;
    var homeScore = ev.home && ev.home.score !== null ? parseFloat(ev.home.score) : NaN;
    var awayWins = ev.away && ev.away.winner === true;
    var homeWins = ev.home && ev.home.winner === true;

    if (!isNaN(awayScore) && !isNaN(homeScore)) {
      awayWins = awayScore > homeScore;
      homeWins = homeScore > awayScore;
    }

    return {
      awayWins: awayWins,
      homeWins: homeWins
    };
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

    html += '<input type="date" class="date-input" id="score-date">';

    host.innerHTML = html;

    var dateInput = $('score-date');
    if (dateInput) {
      dateInput.value = todayStr();
      dateInput.addEventListener('change', loadFinalScores);
    }
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
        '<div class="placeholder-copy">' + esc(cfg.label) + ' does not use the same team final-score model, so it is parked as a placeholder.</div>';
      block.appendChild(ph);
      return block;
    }

    var completed = (events || []).filter(isFinal);

    if (!completed.length) {
      var ng = document.createElement('div');
      ng.className = 'no-games';
      ng.textContent = 'No completed games';
      block.appendChild(ng);
      return block;
    }

    var grid = document.createElement('div');
    grid.className = 'games-grid';

    completed.forEach(function(ev) {
      grid.appendChild(renderGameCard(ev));
    });

    block.appendChild(grid);
    return block;
  }

  function renderGameCard(ev) {
    var winnerFlags = getWinnerFlags(ev);
    var away = ev.away || {};
    var home = ev.home || {};
    var awayScore = away.score !== null && away.score !== undefined ? away.score : '0';
    var homeScore = home.score !== null && home.score !== undefined ? home.score : '0';

    var card = document.createElement('div');
    card.className = 'game-card';
    card.dataset.event = ev.id || '';
    card.dataset.sport = ev.sport || '';
    card.dataset.league = ev.league || '';
    card.dataset.leagueKey = ev.leagueKey || '';

    card.innerHTML =
      '<div class="game-status">FINAL</div>' +
      buildTeamRow(away, awayScore, winnerFlags.awayWins) +
      buildTeamRow(home, homeScore, winnerFlags.homeWins);

    card.addEventListener('click', function() {
      openSummaryModal(ev);
    });

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
      '<span class="team-score' + (winner ? ' winner' : '') + '">' + esc(score) + '</span>' +
    '</div>';
  }

  function render() {
    var main = $('scores-main');
    var empty = $('scores-empty');

    if (!main || !empty) return;

    main.innerHTML = '';

    var enabled = getEnabledLeagues();

    if (!enabled.length) {
      empty.style.display = 'none';
      main.innerHTML =
        '<div class="placeholder-state">' +
          '<div class="placeholder-title">No Leagues Enabled</div>' +
          '<div class="placeholder-copy">Enable at least one league in docs/js/final-scores/render.js to show final scores.</div>' +
        '</div>';
      return;
    }

    var total = 0;

    enabled.forEach(function(cfg) {
      var completed = (allData[cfg.key] || []).filter(isFinal);

      if (cfg.type !== 'placeholder') {
        total += completed.length;
      }

      main.appendChild(renderLeague(cfg, allData[cfg.key] || []));
    });

    empty.style.display = total === 0 ? '' : 'none';
  }

  function applyFilter() {
    document.querySelectorAll('.league-block').forEach(function(block) {
      block.style.display = activeLeague === 'all' || block.dataset.league === activeLeague ? '' : 'none';
    });
  }

  async function loadFinalScores() {
    var dateInput = $('score-date');
    var date = dateInput && dateInput.value ? dateInput.value : todayStr();
    var espnDate = toESPNDate(date);

    setStatus('Loading...', 'loading', 'yellow');

    var scoreLeagues = getScoreLeagues();

    if (!scoreLeagues.length) {
      render();
      setStatus('No score leagues enabled', '', 'yellow');
      return;
    }

    var results = await Promise.all(scoreLeagues.map(async function(cfg) {
      try {
        var events = await loadLeagueEvents(cfg, espnDate);

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

    render();
    applyFilter();

    var total = results.reduce(function(sum, result) {
      return sum + result.events.filter(isFinal).length;
    }, 0);

    var failed = results.filter(function(result) {
      return !result.ok;
    }).length;

    if (failed) {
      setStatus(total + ' completed games · ' + failed + ' league(s) failed · ' + date, '', 'red');
    } else {
      setStatus(total + ' completed games · ' + date, '', 'green');
    }
  }

  function siteSummaryUrl(eventId, sport, league) {
    return 'https://site.api.espn.com/apis/site/v2/sports/' +
      encodeURIComponent(sport) +
      '/' +
      encodeURIComponent(league) +
      '/summary?event=' +
      encodeURIComponent(eventId);
  }

  async function openSummaryModal(ev) {
    var overlay = $('modal-overlay');
    var inner = $('modal-inner');

    if (!overlay || !inner) return;

    inner.innerHTML = '<div style="padding:20px;color:var(--text-muted);font-size:11px;">Loading...</div>';
    overlay.classList.add('open');

    try {
      var data = null;

      try {
        data = await fetchJson(siteSummaryUrl(ev.id, ev.sport, ev.league));
      } catch (summaryError) {
        data = null;
      }

      inner.innerHTML = buildSummaryModal(ev, data);
    } catch (e) {
      inner.innerHTML =
        '<div class="modal-error">' +
          'Failed to load game summary' +
          '<div class="error-details">' + esc(e.message || '') + '</div>' +
        '</div>';
    }
  }

  function buildSummaryModal(ev, data) {
    var away = ev.away || {};
    var home = ev.home || {};
    var winnerFlags = getWinnerFlags(ev);
    var awayScore = away.score !== null && away.score !== undefined ? away.score : '0';
    var homeScore = home.score !== null && home.score !== undefined ? home.score : '0';

    var oddsHTML = buildOddsHTML(data);
    var linesHTML = buildLinesHTML(ev, data);
    var statsHTML = buildStatsHTML(ev, data);
    var leadersHTML = buildLeadersHTML(data);

    return '<div class="modal-top">' +
        '<span class="modal-league-tag tag-' + esc(ev.leagueKey) + '">' + esc(ev.leagueLabel || ev.leagueKey) + '</span>' +
        '<span class="modal-final-tag">FINAL</span>' +
      '</div>' +
      '<div class="modal-matchup">' + esc(away.name || away.abbr || 'Away') + ' @ ' + esc(home.name || home.abbr || 'Home') + '</div>' +
      '<div class="modal-scoreboard">' +
        '<div class="modal-score-row">' +
          '<span class="modal-team' + (winnerFlags.awayWins ? ' winner' : '') + '">' + esc(away.abbr || away.name || '—') + '</span>' +
          '<span class="modal-pts' + (winnerFlags.awayWins ? ' winner' : '') + '">' + esc(awayScore) + '</span>' +
        '</div>' +
        '<div class="modal-score-row">' +
          '<span class="modal-team' + (winnerFlags.homeWins ? ' winner' : '') + '">' + esc(home.abbr || home.name || '—') + '</span>' +
          '<span class="modal-pts' + (winnerFlags.homeWins ? ' winner' : '') + '">' + esc(homeScore) + '</span>' +
        '</div>' +
      '</div>' +
      (oddsHTML ? '<div class="modal-section"><div class="modal-subtitle">Betting Lines</div>' + oddsHTML + '</div>' : '') +
      (linesHTML ? '<div class="modal-section"><div class="modal-subtitle">Scoring by Period</div>' + linesHTML + '</div>' : '') +
      (statsHTML ? '<div class="modal-section"><div class="modal-subtitle">Team Stats</div>' + statsHTML + '</div>' : '') +
      (leadersHTML ? '<div class="modal-section"><div class="modal-subtitle">Leaders</div>' + leadersHTML + '</div>' : '');
  }

  function buildOddsHTML(data) {
    if (!data || !data.header || !data.header.competitions || !data.header.competitions[0]) {
      return '';
    }

    var odds = data.header.competitions[0].odds && data.header.competitions[0].odds[0];

    if (!odds) {
      return '';
    }

    return '<div class="modal-row">Spread: ' + esc(odds.details || '—') + '</div>' +
      '<div class="modal-row">Total: ' + esc(odds.overUnder || '—') + '</div>';
  }

  function buildLinesHTML(ev, data) {
    if (!data || !data.header || !data.header.competitions || !data.header.competitions[0]) {
      return '';
    }

    var comp = data.header.competitions[0];
    var teams = comp.competitors || [];
    var away = teams.find(function(t) { return t.homeAway === 'away'; });
    var home = teams.find(function(t) { return t.homeAway === 'home'; });

    if (!away || !home) return '';

    var awayLines = away.linescores || [];
    var homeLines = home.linescores || [];

    if (!awayLines.length) return '';

    var periodLabel = ev.sport === 'baseball' ? 'Inn' : ev.sport === 'hockey' ? 'P' : ev.sport === 'soccer' ? 'H' : 'Q';

    return awayLines.map(function(line, i) {
      var period = line.period || i + 1;
      var awayVal = line.displayValue || line.value || '0';
      var homeLine = homeLines[i];
      var homeVal = homeLine ? homeLine.displayValue || homeLine.value || '0' : '0';
      var awayAbbr = away.team ? away.team.abbreviation || ev.away.abbr || 'AWAY' : ev.away.abbr || 'AWAY';
      var homeAbbr = home.team ? home.team.abbreviation || ev.home.abbr || 'HOME' : ev.home.abbr || 'HOME';

      return '<div class="modal-row">' + esc(periodLabel + period) + ': ' + esc(awayAbbr) + ' ' + esc(awayVal) + ' · ' + esc(homeAbbr) + ' ' + esc(homeVal) + '</div>';
    }).join('');
  }

  function buildStatsHTML(ev, data) {
    if (!data || !data.boxscore || !data.boxscore.teams) {
      return '';
    }

    var NHL_STATS = ['shots on goal', 'hits', 'power play goals', 'power play opportunities', 'giveaways', 'takeaways'];
    var MLB_STATS = ['runs', 'hits', 'errors', 'strikeouts', 'home runs', 'runs batted in', 'batting average', 'left on base'];
    var SOCCER_STATS = ['possession', 'shots on target', 'shots', 'fouls', 'yellow cards', 'red cards', 'corner kicks', 'offsides'];

    return data.boxscore.teams.map(function(teamBox) {
      var allStats = teamBox.statistics || [];
      var flat = [];

      allStats.forEach(function(statGroup) {
        if (statGroup.stats && statGroup.stats.length) {
          statGroup.stats.forEach(function(stat) {
            flat.push(stat);
          });
        } else {
          flat.push(statGroup);
        }
      });

      var whitelist = null;

      if (ev.sport === 'hockey') {
        whitelist = NHL_STATS;
      } else if (ev.sport === 'baseball') {
        whitelist = MLB_STATS;
      } else if (ev.sport === 'soccer') {
        whitelist = SOCCER_STATS;
      }

      var rows = flat.filter(function(stat) {
        var val = stat.displayValue || stat.value || '';
        var label = String(stat.label || stat.displayName || stat.name || '').toLowerCase();

        if (!val && val !== 0) return false;
        if (whitelist) return whitelist.indexOf(label) !== -1;

        return true;
      }).slice(0, 8).map(function(stat) {
        var label = stat.label || stat.displayName || stat.name || '';
        var val = stat.displayValue || stat.value || '';

        return esc(label) + ': ' + esc(val);
      });

      if (!rows.length) return '';

      var teamName = teamBox.team ? teamBox.team.displayName || teamBox.team.abbreviation || '' : '';

      return '<div class="modal-row"><strong style="color:var(--text-main)">' + esc(teamName) + '</strong><br>' + rows.join(' · ') + '</div>';
    }).filter(Boolean).join('');
  }

  function buildLeadersHTML(data) {
    if (!data || !data.leaders) {
      return '';
    }

    return data.leaders.map(function(leaderGroup) {
      var top = leaderGroup.leaders && leaderGroup.leaders[0];
      var name = leaderGroup.displayName || leaderGroup.name || '';
      var val = top ? top.displayValue || top.value || '' : '';
      var athlete = top && top.athlete ? top.athlete.displayName || '' : '';

      return name && val
        ? '<div class="modal-row">' + esc(name) + ': ' + esc(athlete ? athlete + ' — ' : '') + esc(val) + '</div>'
        : '';
    }).filter(Boolean).join('');
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

    var closeBtn = $('modal-close');
    var overlay = $('modal-overlay');

    if (closeBtn) {
      closeBtn.addEventListener('click', function() {
        if (overlay) overlay.classList.remove('open');
      });
    }

    if (overlay) {
      overlay.addEventListener('click', function(e) {
        if (e.target === overlay) overlay.classList.remove('open');
      });
    }

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && overlay) {
        overlay.classList.remove('open');
      }
    });
  }

  function init() {
    renderLeagueControls();
    bindEvents();
    loadFinalScores();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
