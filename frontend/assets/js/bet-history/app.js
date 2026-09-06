var allRows = [];
var activeLeague = 'all';
var activeMarket = 'all';
var activeResult = 'all';

function setStatus(text, dotCls) {
  document.getElementById('status-text').textContent = text;
  document.getElementById('status-dot').className = 'status-dot ' + (dotCls || '');
}

function padTwo(n) {
  return n < 10 ? '0' + n : '' + n;
}

function todayFileDate() {
  var d = new Date();
  return d.getFullYear() + '_' + padTwo(d.getMonth() + 1) + '_' + padTwo(d.getDate());
}

function normalizeFileDate(value) {
  return String(value || '').trim().replaceAll('-', '_');
}

function dateFromFileDate(value) {
  var parts = normalizeFileDate(value).split('_').map(function(v) {
    return parseInt(v, 10);
  });

  if (parts.length !== 3 || parts.some(function(v) { return isNaN(v); })) {
    return null;
  }

  return new Date(parts[0], parts[1] - 1, parts[2]);
}

function fileDateFromDate(d) {
  return d.getFullYear() + '_' + padTwo(d.getMonth() + 1) + '_' + padTwo(d.getDate());
}

function buildDateList(startDate, endDate) {
  var start = dateFromFileDate(startDate);
  var end = dateFromFileDate(endDate || todayFileDate());
  var dates = [];

  if (!start || !end || start > end) return dates;

  var cur = new Date(start.getTime());
  while (cur <= end) {
    dates.push(fileDateFromDate(cur));
    cur.setDate(cur.getDate() + 1);
  }

  return dates;
}

function fetchSourceUrl(url, label, warnOnFail) {
  return fetch(url)
    .then(function(res) {
      if (!res.ok) throw new Error(label + ' ' + res.status);
      return res.text();
    })
    .then(function(text) {
      return parseCSV(text);
    })
    .catch(function(err) {
      if (warnOnFail) console.warn('Failed to load ' + label + ':', err);
      return [];
    });
}

function resolveSourceUrls(src) {
  if (Array.isArray(src.urls)) return Promise.resolve(src.urls);
  if (src.url) return Promise.resolve([src.url]);

  if (src.indexUrl) {
    return fetch(src.indexUrl)
      .then(function(res) {
        if (!res.ok) throw new Error(src.label + ' index ' + res.status);
        return res.json();
      })
      .then(function(items) {
        if (!Array.isArray(items)) return [];

        if (typeof src.indexItemToUrl === 'function') {
          return items.map(function(item) {
            return src.indexItemToUrl(item);
          }).filter(function(url) {
            return !!url;
          });
        }

        if (typeof src.datePattern !== 'function') return [];

        return items.map(function(date) {
          return src.datePattern(normalizeFileDate(date));
        });
      })
      .catch(function(err) {
        console.warn('Failed to load ' + src.label + ' index:', err);
        return [];
      });
  }

  if (typeof src.datePattern === 'function') {
    return Promise.resolve(
      buildDateList(src.startDate, src.endDate).map(function(date) {
        return src.datePattern(date);
      })
    );
  }

  return Promise.resolve([]);
}

function loadSource(src) {
  return resolveSourceUrls(src).then(function(urls) {
    if (!urls.length) {
      return {
        label: src.label,
        rows: []
      };
    }

    var warnOnFail = !src.datePattern;

    return Promise.all(urls.map(function(url) {
      return fetchSourceUrl(url, src.label, warnOnFail);
    })).then(function(groups) {
      return {
        label: src.label,
        rows: groups.reduce(function(out, rows) {
          return out.concat(rows);
        }, [])
      };
    });
  });
}

function prepareSourceRow(row, sourceLabel) {
  if (sourceLabel === 'MLB_LINEUPS') {
    var lineupRow = Object.assign({}, row);
    lineupRow.league = 'MLB_LINEUPS';
    return lineupRow;
  }

  if (sourceLabel === 'UFC') {
    var bet = String(row.bet || '').toLowerCase().trim();
    var fighterIndex = bet === 'fighter_1' ? 1 : bet === 'fighter_2' ? 2 : 0;

    if (!fighterIndex) return row;

    var ufcRow = Object.assign({}, row);
    var fighter = fighterIndex === 1 ? row.fighter_1 : row.fighter_2;

    ufcRow.sport = 'mma';
    ufcRow.league = 'UFC';
    ufcRow.game_date = row.match_date;
    ufcRow.matchup = [row.fighter_1, row.fighter_2].filter(Boolean).join(' vs ');
    ufcRow.market_type = 'moneyline';
    ufcRow.bet_side = fighter;
    ufcRow.take_bet = fighter;
    ufcRow.dk_odds_american = fighterIndex === 1 ? row.moneyline_f1 : row.moneyline_f2;
    ufcRow.model_prob = fighterIndex === 1 ? row.model_prob_f1 : row.model_prob_f2;
    ufcRow.ev = fighterIndex === 1 ? row.ev_f1 : row.ev_f2;
    ufcRow.kelly = fighterIndex === 1 ? row.kelly_f1 : row.kelly_f2;
    ufcRow.edge = fighterIndex === 1 ? row.edge_f1 : row.edge_f2;
    ufcRow.bet_result = fighterIndex === 1 ? row.result_fighter_1 : row.result_fighter_2;

    return ufcRow;
  }

  return row;
}

function loadAll() {
  var activeSources = SOURCES.filter(function(src) {
    return src.enabled !== false;
  });

  if (!activeSources.length) {
    allRows = [];
    setStatus('No leagues are currently enabled.', 'red');
    render();
    return;
  }

  setStatus(
    'Fetching data from GitHub: ' + activeSources.map(function(s) {
      return s.label;
    }).join(', ') + '...',
    'yellow'
  );

  document.getElementById('history-main').innerHTML = '';

  Promise.all(activeSources.map(loadSource)).then(function(results) {
    allRows = [];

    results.forEach(function(result) {
      result.rows.forEach(function(row) {
        var preparedRow = prepareSourceRow(row, result.label);
        allRows.push(normalizeRow(preparedRow, result.label));
      });
    });

    var graded = allRows.filter(function(r) {
      return r.result === 'win' || r.result === 'loss' || r.result === 'push';
    }).length;

    setStatus(
      allRows.length + ' bets loaded · ' + graded + ' graded · active: ' +
      activeSources.map(function(s) {
        return s.label;
      }).join(', '),
      'green'
    );

    render();
  });
}

function filteredRows() {
  return allRows.filter(function(r) {
    if (activeLeague !== 'all' && r.league !== activeLeague) return false;
    if (activeMarket !== 'all' && r.market !== activeMarket) return false;
    if (activeResult !== 'all' && r.result !== activeResult) return false;

    return true;
  });
}

document.querySelectorAll('.league-pill').forEach(function(pill) {
  pill.addEventListener('click', function() {
    document.querySelectorAll('.league-pill').forEach(function(p) {
      p.classList.remove('active');
    });

    pill.classList.add('active');
    activeLeague = pill.dataset.league;

    if (allRows.length) render();
  });
});

document.querySelectorAll('.market-pill').forEach(function(pill) {
  pill.addEventListener('click', function() {
    document.querySelectorAll('.market-pill').forEach(function(p) {
      p.classList.remove('active');
    });

    pill.classList.add('active');
    activeMarket = pill.dataset.market;

    if (allRows.length) render();
  });
});

document.querySelectorAll('.result-pill').forEach(function(pill) {
  pill.addEventListener('click', function() {
    document.querySelectorAll('.result-pill').forEach(function(p) {
      p.classList.remove('active');
    });

    pill.classList.add('active');
    activeResult = pill.dataset.result;

    if (allRows.length) render();
  });
});

loadAll();
