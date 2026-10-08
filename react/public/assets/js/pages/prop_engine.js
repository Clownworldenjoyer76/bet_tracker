var activeSport  = 'basketball';
var activeLeague = 'nba';
var allTeams     = [];
var allPlayers   = [];

var PROPS = {
  nba: [
    { label:'Points',           statKeys:['points','PTS'],                abbr:'PTS' },
    { label:'Rebounds',         statKeys:['totalRebounds','REB'],         abbr:'REB' },
    { label:'Assists',          statKeys:['assists','AST'],               abbr:'AST' },
    { label:'3-Point %',        statKeys:['threePointPct','3P%'],         abbr:'3P%' },
    { label:'PRA (Pts+Reb+Ast)',statKeys:['__pra__'],                     abbr:'PRA' },
    { label:'Blocks',           statKeys:['blocks','BLK'],                abbr:'BLK' },
    { label:'Steals',           statKeys:['steals','STL'],                abbr:'STL' }
  ],
  nhl: [
    { label:'Goals',            statKeys:['goals','G'],                   abbr:'G'   },
    { label:'Assists',          statKeys:['assists','A'],                 abbr:'A'   },
    { label:'Points',           statKeys:['points','PTS'],                abbr:'PTS' },
    { label:'Shots on Goal',    statKeys:['shotsTotal','S'],              abbr:'S'   },
    { label:'Power Play Goals', statKeys:['powerPlayGoals','PPG'],        abbr:'PPG' }
  ],
  mlb: [
    { label:'Hits',             statKeys:['hits','H'],                    abbr:'H'   },
    { label:'RBI',              statKeys:['rbi','runsBattedIn','RBI'],    abbr:'RBI' },
    { label:'Strikeouts',       statKeys:['strikeouts','strikeOuts','SO'],abbr:'SO'  },
    { label:'Home Runs',        statKeys:['homeRuns','homerun','HR'],     abbr:'HR'  }
  ]
};

async function fetchJSON(url) {
  try {
    var r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch(e) { return null; }
}

function setStatus(text, dotCls) {
  document.getElementById('status-text').textContent = text;
  document.getElementById('status-dot').className = 'status-dot ' + (dotCls || '');
}

function populatePropSelect() {
  var sel = document.getElementById('prop-select');
  sel.innerHTML = (PROPS[activeLeague] || []).map(function(p, i) {
    return '<option value="' + i + '">' + p.label + '</option>';
  }).join('');
}

async function loadTeams() {
  setStatus('Loading teams...', 'yellow');
  var teamSelect = document.getElementById('team-select');
  var playerSelect = document.getElementById('player-select');
  teamSelect.innerHTML = '<option value="">— Select Team —</option>';
  playerSelect.innerHTML = '<option value="">— Select Player —</option>';
  allTeams = [];
  allPlayers = [];

  try {
    var url = 'https://site.api.espn.com/apis/site/v2/sports/' + activeSport + '/' + activeLeague + '/scoreboard?dates=20260428';
    var data = await fetchJSON(url);
    var events = (data && data.events) || [];

    if (!events.length) {
      setStatus('No games today', '');
      return;
    }

    var teamMap = {};
    events.forEach(function(e) {
      var comp = e.competitions && e.competitions[0];
      if (!comp) return;
      (comp.competitors || []).forEach(function(c) {
        var t = c.team;
        if (t && t.id && t.displayName && !teamMap[t.id]) {
          teamMap[t.id] = {
            id: t.id,
            name: t.displayName,
            abbr: t.abbreviation || ''
          };
        }
      });
    });

    allTeams = Object.values(teamMap).sort(function(a,b) {
      return a.name.localeCompare(b.name);
    });

    allTeams.forEach(function(t) {
      var o = document.createElement('option');
      o.value = t.id;
      o.textContent = t.name;
      teamSelect.appendChild(o);
    });

    setStatus('Select a team', '');
  } catch(e) {
    console.error('loadTeams failed:', e);
    setStatus('Failed to load teams', '');
  }
}

async function loadPlayers(teamId) {
  var psel = document.getElementById('player-select');
  psel.innerHTML = '<option value="">Loading...</option>';
  allPlayers = [];

  try {
    var url = 'https://site.api.espn.com/apis/site/v2/sports/' + activeSport + '/' + activeLeague + '/teams/' + teamId + '/roster';
    var data = await fetchJSON(url);

    if (!data) throw new Error('Failed to fetch roster');

    (data.athletes || []).forEach(function(g) {
      (g.items || g.athletes || (g.id ? [g] : [])).forEach(function(p) {
        if (p.id) allPlayers.push(p);
      });
    });

    allPlayers.sort(function(a,b) {
      return (a.displayName || '').localeCompare(b.displayName || '');
    });

    psel.innerHTML = '<option value="">— Select Player —</option>';
    allPlayers.forEach(function(p) {
      var o = document.createElement('option');
      o.value = p.id;
      o.textContent = p.displayName || p.fullName || p.id;
      psel.appendChild(o);
    });

    setStatus('Select a player', '');
  } catch(e) {
    console.error('loadPlayers failed:', e);
    psel.innerHTML = '<option value="">Failed to load</option>';
    setStatus('Failed to load players', '');
  }
}

function extractStatByLabels(labels, names, statsArr, keys) {
  for (var k = 0; k < keys.length; k++) {
    var key = keys[k].toLowerCase();
    for (var i = 0; i < labels.length; i++) {
      if ((labels[i] || '').toLowerCase() === key) {
        var v = parseFloat(statsArr[i]);
        return isNaN(v) ? null : v;
      }
    }
    for (var j = 0; j < (names || []).length; j++) {
      if ((names[j] || '').toLowerCase() === key) {
        var v2 = parseFloat(statsArr[j]);
        return isNaN(v2) ? null : v2;
      }
    }
  }
  return null;
}

function parseGamelog(data, propDef) {
  var gl = data.gameLog || {};
  var sg = (gl.statistics || [])[0];
  if (!sg) return [];

  var labels = sg.labels || [];
  var names = sg.names || [];
  var sgEvts = sg.events || [];
  var evDict = gl.events || {};
  var games = [];

  sgEvts.forEach(function(entry) {
    var statsArr = entry.stats || [];
    var val = null;

    if (propDef.statKeys[0] === '__pra__') {
      var pts = extractStatByLabels(labels, names, statsArr, ['points','pts','PTS']);
      var reb = extractStatByLabels(labels, names, statsArr, ['totalRebounds','rebounds','REB']);
      var ast = extractStatByLabels(labels, names, statsArr, ['assists','AST']);
      if (pts !== null && reb !== null && ast !== null) val = pts + reb + ast;
    } else {
      val = extractStatByLabels(labels, names, statsArr, propDef.statKeys.concat([propDef.abbr]));
    }

    if (val !== null) {
      var ev = evDict[entry.eventId] || {};
      games.push({
        date: ev.gameDate ? new Date(ev.gameDate) : null,
        val: val,
        opp: ev.opponent ? (ev.opponent.abbreviation || '?') : (ev.atVs || '?'),
        result: ev.gameResult || ''
      });
    }
  });

  return games.sort(function(a,b) {
    return (b.date ? b.date.getTime() : 0) - (a.date ? a.date.getTime() : 0);
  });
}

function calcHitRate(games, line) {
  var hits = games.filter(function(g) { return g.val > line; }).length;
  return { rate: games.length ? hits / games.length : 0, hits: hits, total: games.length };
}

function barColor(r) {
  return r >= 0.65 ? 'var(--accent-green)' : r >= 0.5 ? 'var(--accent-yellow)' : 'var(--accent-red)';
}

function pctColor(r) {
  return r >= 0.65 ? 'var(--accent-green)' : r >= 0.5 ? 'var(--accent-yellow)' : 'var(--accent-red)';
}

function renderResults(player, games, propDef, n) {
  var main = document.getElementById('prop-main');
  main.innerHTML = '';
  var recent = games.slice(0, n);

  if (!recent.length) {
    main.innerHTML = '<div class="empty-state">No data for ' + propDef.label + '</div>';
    return;
  }

  var vals = recent.map(function(g) { return g.val; });
  var avg = vals.reduce(function(s,v) { return s + v; }, 0) / vals.length;
  var max = Math.max.apply(null, vals);
  var min = Math.min.apply(null, vals);
  var avg3 = vals.slice(0,3).reduce(function(s,v) { return s + v; }, 0) / Math.min(3, vals.length);
  var trendCls = avg3 > avg * 1.1 ? 'trend-hot' : avg3 < avg * 0.9 ? 'trend-cold' : 'trend-mid';
  var trendTxt = avg3 > avg * 1.1 ? '▲ HOT' : avg3 < avg * 0.9 ? '▼ COLD' : '→ AVG';

  var hs = player.headshot ? (player.headshot.href || '') : '';
  var pos = player.position ? (player.position.abbreviation || '') : '';
  var team = allTeams.find(function(t) { return t.id == document.getElementById('team-select').value; });

  var banner = document.createElement('div');
  banner.className = 'player-banner';
  banner.innerHTML = (hs ? '<img class="player-headshot" src="' + hs + '">' : '<div class="player-headshot-ph">👤</div>') + '<div><div class="player-banner-name">' + (player.displayName || '') + '</div>' + '<div class="player-banner-meta">' + (pos || '') + (team ? ' · ' + team.name : '') + ' · ' + activeLeague.toUpperCase() + '</div>' + '<div class="player-banner-prop">' + propDef.label + ' · Last ' + n + ' Games</div></div>';
  main.appendChild(banner);

  var strip = document.createElement('div');
  strip.className = 'stat-strip';
  [
    { val: avg.toFixed(1), lbl: propDef.abbr + ' Average', trend: '' },
    { val: avg3.toFixed(1), lbl: 'Last 3 Avg', trend: '<span class="stat-trend ' + trendCls + '">' + trendTxt + '</span>' },
    { val: max, lbl: 'Season High', trend: '' },
    { val: min, lbl: 'Season Low', trend: '' }
  ].forEach(function(s) {
    strip.innerHTML += '<div class="stat-strip-item"><div class="stat-val">' + s.val + '</div><div class="stat-lbl">' + s.lbl + '</div>' + s.trend + '</div>';
  });
  main.appendChild(strip);

  var grid = document.createElement('div');
  grid.className = 'results-grid';

  var hitSec = document.createElement('div');
  hitSec.className = 'hit-section';
  hitSec.innerHTML = '<div class="section-title">Hit Rate by Line (Over)</div>';

  var step = 0.5;
  var lo = Math.max(0, Math.floor((avg - 2) / step) * step);

  for (var i = 0; i < 7; i++) {
    var line = +(lo + i * step).toFixed(1);
    var hr = calcHitRate(recent, line);
    var pct = (hr.rate * 100).toFixed(0);
    hitSec.innerHTML += '<div class="hit-row"><span class="hit-line-label">' + line + '</span><div class="hit-bar-track"><div class="hit-bar-fill" style="width:' + (hr.rate * 100) + '%;background:' + barColor(hr.rate) + '"></div></div><span class="hit-pct" style="color:' + pctColor(hr.rate) + '">' + pct + '%</span><span class="hit-count">' + hr.hits + '/' + hr.total + '</span></div>';
  }

  grid.appendChild(hitSec);

  var logSec = document.createElement('div');
  logSec.className = 'log-section';
  logSec.innerHTML = '<div class="section-title">Game Log</div>';

  var midLine = +(avg).toFixed(1);
  var rows = recent.map(function(g) {
    var ds = g.date ? g.date.toLocaleDateString('en-US', { month:'short', day:'numeric' }) : '—';
    var cls = g.val > midLine ? 'cell-over' : g.val < midLine ? 'cell-under' : '';
    var rc = g.result === 'W' ? 'style="color:var(--accent-green)"' : g.result === 'L' ? 'style="color:var(--accent-red)"' : '';
    return '<tr><td>' + ds + '</td><td>' + (g.opp || '—') + '</td><td ' + rc + '>' + (g.result || '—') + '</td><td class="' + cls + '">' + g.val + '</td></tr>';
  }).join('');

  logSec.innerHTML += '<table class="log-table"><thead><tr><th>Date</th><th>Opp</th><th>W/L</th><th>' + propDef.abbr + '</th></tr></thead><tbody>' + rows + '</tbody></table>';
  grid.appendChild(logSec);
  main.appendChild(grid);
}

async function analyze() {
  var playerId = document.getElementById('player-select').value;
  var propIdx = parseInt(document.getElementById('prop-select').value);
  var n = Math.max(5, Math.min(82, parseInt(document.getElementById('game-count').value) || 15));
  var propDef = (PROPS[activeLeague] || [])[propIdx];

  if (!playerId || !propDef) {
    setStatus('Select a player and prop', '');
    return;
  }

  var player = allPlayers.find(function(p) { return p.id == playerId; });
  if (!player) return;

  setStatus('Loading...', 'yellow');
  document.getElementById('prop-main').innerHTML = '<div class="empty-state">Loading...</div>';

  try {
    var url = 'https://site.web.api.espn.com/apis/common/v3/sports/' + activeSport + '/' + activeLeague + '/athletes/' + playerId + '/overview';
    var data = await fetchJSON(url);

    if (!data) throw new Error('No data');

    var games = parseGamelog(data, propDef);

    if (!games.length) {
      setStatus('No data for ' + propDef.label, '');
      document.getElementById('prop-main').innerHTML = '<div class="empty-state">No game log data for ' + propDef.label + '</div>';
      return;
    }

    setStatus(games.length + ' games · ' + propDef.label, 'green');
    renderResults(player, games, propDef, n);
  } catch(e) {
    console.error('analyze failed:', e);
    setStatus('Failed to load', '');
    document.getElementById('prop-main').innerHTML = '<div class="empty-state">Failed to load data</div>';
  }
}

document.getElementById('team-select').addEventListener('change', function() {
  if (this.value) loadPlayers(this.value);
});
document.getElementById('analyze-btn').addEventListener('click', analyze);
document.getElementById('player-select').addEventListener('change', function() {
  if (this.value) analyze();
});
document.getElementById('prop-select').addEventListener('change', function() {
  if (document.getElementById('player-select').value) analyze();
});

document.querySelectorAll('.league-pill').forEach(function(pill) {
  pill.addEventListener('click', function() {
    document.querySelectorAll('.league-pill').forEach(function(p) { p.classList.remove('active'); });
    pill.classList.add('active');
    activeSport = pill.dataset.sport;
    activeLeague = pill.dataset.league;
    populatePropSelect();
    loadTeams();
    document.getElementById('prop-main').innerHTML = '<div class="empty-state">Select a player and prop to begin analysis<div class="empty-sub">NBA · NHL · MLB</div></div>';
  });
});

populatePropSelect();
loadTeams();
