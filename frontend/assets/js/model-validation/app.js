var allRows = [];
var activeLeague = 'all';
var activeLeagueSub = 'all';
var activeMarket = 'all';

function setStatus(text, dotCls) {
  document.getElementById('status-text').textContent = text;
  document.getElementById('status-dot').className = 'status-dot ' + (dotCls || '');
}

function fetchSourceUrl(url, label) {
  return fetch(url)
    .then(function(res) {
      if (!res.ok) throw new Error(label + ' ' + res.status + ' · ' + url);
      return res.text();
    })
    .then(function(text) {
      return { ok: true, rows: parseCSV(text), error: null };
    })
    .catch(function(error) {
      console.warn('Failed to load ' + label + ':', error);
      return { ok: false, rows: [], error: error };
    });
}

function resolveSourceUrls(source) {
  if (Array.isArray(source.urls)) return Promise.resolve({ ok: true, urls: source.urls });
  if (source.url) return Promise.resolve({ ok: true, urls: [source.url] });

  if (source.indexUrl) {
    return fetch(source.indexUrl)
      .then(function(res) {
        if (!res.ok) throw new Error(source.label + ' index ' + res.status);
        return res.json();
      })
      .then(function(items) {
        if (!Array.isArray(items)) return { ok: true, urls: [] };

        var urls = items.map(function(item) {
          return typeof source.indexItemToUrl === 'function'
            ? source.indexItemToUrl(item)
            : '';
        }).filter(function(url) { return !!url; });

        return { ok: true, urls: urls };
      })
      .catch(function(error) {
        console.warn('Failed to load ' + source.label + ' index:', error);
        return { ok: false, urls: [], error: error };
      });
  }

  return Promise.resolve({ ok: true, urls: [] });
}

function loadSource(source) {
  return resolveSourceUrls(source).then(function(resolved) {
    if (!resolved.ok) {
      return {
        label: source.label,
        rows: [],
        failedFiles: 1,
        totalFiles: 0
      };
    }

    if (!resolved.urls.length) {
      return {
        label: source.label,
        rows: [],
        failedFiles: 0,
        totalFiles: 0
      };
    }

    return Promise.all(resolved.urls.map(function(url) {
      return fetchSourceUrl(url, source.label);
    })).then(function(groups) {
      var rawRows = [];
      var failed = 0;

      groups.forEach(function(group) {
        if (!group.ok) failed++;
        rawRows = rawRows.concat(group.rows);
      });

      return {
        label: source.label,
        rows: expandSourceRows(rawRows, source),
        failedFiles: failed,
        totalFiles: resolved.urls.length
      };
    });
  });
}

function loadAll() {
  var activeSources = SOURCES.filter(function(source) {
    return source.enabled !== false;
  });

  setStatus('Fetching graded model history from GitHub...', 'yellow');
  document.getElementById('val-main').innerHTML = '';

  Promise.all(activeSources.map(loadSource)).then(function(results) {
    allRows = [];
    var failedFiles = 0;
    var totalFiles = 0;

    results.forEach(function(result) {
      failedFiles += result.failedFiles;
      totalFiles += result.totalFiles;

      result.rows.forEach(function(row) {
        allRows.push(normalizeRow(row, result.label));
      });
    });

    var decisions = allRows.filter(function(row) {
      return row.win === true || row.win === false;
    }).length;

    if (!allRows.length && failedFiles) {
      setStatus('No data loaded · ' + failedFiles + ' source file/index request(s) failed', 'red');
    } else if (failedFiles) {
      setStatus(
        allRows.length + ' bets loaded · ' + decisions + ' decisions · ' + failedFiles +
        ' of ' + totalFiles + ' file request(s) failed',
        'yellow'
      );
    } else {
      setStatus(
        allRows.length + ' bets loaded · ' + decisions + ' decisions · ' + totalFiles + ' source file(s)',
        'green'
      );
    }

    render();
  });
}

function filteredRows() {
  return allRows.filter(function(row) {
    if (activeLeague !== 'all' && row.league !== activeLeague) return false;

    if (
      activeLeague === 'SOCCER' &&
      activeLeagueSub !== 'all' &&
      row.league_sub !== activeLeagueSub
    ) return false;

    if (activeMarket !== 'all' && row.market !== activeMarket) return false;
    return true;
  });
}

function safePct(value) {
  return value === null || value === undefined ? '—' : (value * 100).toFixed(1) + '%';
}

function formatOdds(value) {
  if (value === null || value === undefined) return '—';
  return value > 0 ? '+' + value : String(value);
}

function formatEV(value) {
  if (value === null || value === undefined) return '—';
  return value.toFixed(2);
}

function escapeHtml(value) {
  return String(value === null || value === undefined ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function render() {
  var rows = filteredRows();
  var graded = rows.filter(function(row) {
    return row.win === true || row.win === false;
  });
  var main = document.getElementById('val-main');
  main.innerHTML = '';

  if (!graded.length) {
    main.innerHTML = '<div class="empty-state">No graded bets match the current filter</div>';
    return;
  }

  var wins = graded.filter(function(row) { return row.win === true; }).length;
  var losses = graded.length - wins;
  var winRate = wins / graded.length;

  var probabilityRows = graded.filter(function(row) {
    return row.model_prob !== null && row.model_prob >= 0 && row.model_prob <= 1;
  });
  var avgProb = probabilityRows.length
    ? probabilityRows.reduce(function(sum, row) { return sum + row.model_prob; }, 0) / probabilityRows.length
    : null;

  var evRows = graded.filter(function(row) { return row.ev !== null; });
  var totalEV = evRows.reduce(function(sum, row) { return sum + row.ev; }, 0);

  var strip = document.createElement('div');
  strip.className = 'summary-strip';
  [
    { val: graded.length, lbl: 'Graded Bets', cls: '' },
    { val: wins + '-' + losses, lbl: 'W-L Record', cls: winRate >= 0.55 ? 'val-green' : winRate < 0.45 ? 'val-red' : 'val-yellow' },
    { val: (winRate * 100).toFixed(1) + '%', lbl: 'Win Rate', cls: winRate >= 0.55 ? 'val-green' : winRate < 0.45 ? 'val-red' : 'val-yellow' },
    { val: avgProb === null ? '—' : (avgProb * 100).toFixed(1) + '%', lbl: 'Avg Model Prob', cls: 'val-blue' },
    { val: evRows.length ? totalEV.toFixed(2) : '—', lbl: 'Total EV', cls: totalEV >= 0 ? 'val-green' : 'val-red' }
  ].forEach(function(item) {
    strip.innerHTML += '<div class="summary-item"><div class="summary-val ' + item.cls + '">' +
      escapeHtml(item.val) + '</div><div class="summary-lbl">' + escapeHtml(item.lbl) + '</div></div>';
  });
  main.appendChild(strip);

  var calSec = document.createElement('div');
  calSec.className = 'calibration-section';
  calSec.innerHTML = '<div class="section-title">Model Calibration · Predicted Probability vs Actual Win Rate</div>';

  var buckets = [
    [0, 0.45, '< 45%'],
    [0.45, 0.55, '45–55%'],
    [0.55, 0.65, '55–65%'],
    [0.65, 0.75, '65–75%'],
    [0.75, 1.000001, '> 75%']
  ];

  buckets.forEach(function(bucket) {
    var bucketRows = probabilityRows.filter(function(row) {
      return row.model_prob >= bucket[0] && row.model_prob < bucket[1];
    });
    if (!bucketRows.length) return;

    var bucketWins = bucketRows.filter(function(row) { return row.win === true; }).length;
    var predAvg = bucketRows.reduce(function(sum, row) { return sum + row.model_prob; }, 0) / bucketRows.length;
    var actual = bucketWins / bucketRows.length;
    var diff = actual - predAvg;
    var diffStr = (diff >= 0 ? '+' : '') + (diff * 100).toFixed(1) + '%';
    var diffCls = diff > 0.05 ? 'val-green' : diff < -0.05 ? 'val-red' : '';

    calSec.innerHTML +=
      '<div class="cal-row">' +
        '<span class="cal-bucket">' + bucket[2] + '</span>' +
        '<div class="cal-bar-wrap">' +
          '<div class="cal-bar-pred" style="width:' + (predAvg * 100) + '%"></div>' +
          '<div class="cal-bar-act" style="width:' + (actual * 100) + '%"></div>' +
        '</div>' +
        '<span class="cal-pct"><span style="color:var(--accent-blue)">' + (predAvg * 100).toFixed(0) +
        '%</span> pred · <span style="color:var(--accent-green)">' + (actual * 100).toFixed(0) +
        '%</span> act · <span class="' + diffCls + '">' + diffStr + '</span></span>' +
        '<span style="font-size:10px;color:var(--text-muted);min-width:40px;text-align:right">' +
        bucketRows.length + ' bets</span></div>';
  });
  main.appendChild(calSec);

  var markets = ['moneyline', 'spread', 'total'];
  var marketCards = markets.map(function(market) {
    var marketRows = graded.filter(function(row) { return row.market === market; });
    if (!marketRows.length) return '';

    var marketWins = marketRows.filter(function(row) { return row.win === true; }).length;
    var marketRate = marketWins / marketRows.length;
    var marketEVRows = marketRows.filter(function(row) { return row.ev !== null; });
    var marketEV = marketEVRows.reduce(function(sum, row) { return sum + row.ev; }, 0);

    var label = market === 'spread'
      ? ({ NHL: 'Puck Line', MLB: 'Run Line', MLB_LINEUPS: 'Run Line', CFB: 'Spread' }[activeLeague] || 'Spread / Line')
      : market.charAt(0).toUpperCase() + market.slice(1);

    return '<div class="mkt-card"><div class="mkt-card-title">' + escapeHtml(label) + '</div>' +
      '<div class="mkt-stat-row"><span class="mkt-stat-label">Bets</span><span class="mkt-stat-val">' + marketRows.length + '</span></div>' +
      '<div class="mkt-stat-row"><span class="mkt-stat-label">W-L</span><span class="mkt-stat-val">' + marketWins + '-' + (marketRows.length - marketWins) + '</span></div>' +
      '<div class="mkt-stat-row"><span class="mkt-stat-label">Win Rate</span><span class="mkt-stat-val" style="color:' +
      (marketRate >= 0.55 ? 'var(--accent-green)' : marketRate < 0.45 ? 'var(--accent-red)' : 'var(--accent-yellow)') + '">' +
      (marketRate * 100).toFixed(1) + '%</span></div>' +
      '<div class="mkt-stat-row"><span class="mkt-stat-label">Total EV</span><span class="mkt-stat-val" style="color:' +
      (marketEV >= 0 ? 'var(--accent-green)' : 'var(--accent-red)') + '">' +
      (marketEVRows.length ? marketEV.toFixed(2) : '—') + '</span></div></div>';
  }).join('');

  if (marketCards) {
    var evSec = document.createElement('div');
    evSec.className = 'ev-section';
    evSec.innerHTML = '<div class="section-title">Performance by Market</div><div class="market-breakdown">' + marketCards + '</div>';
    main.appendChild(evSec);
  }

  var betsSec = document.createElement('div');
  betsSec.className = 'bets-section';
  betsSec.innerHTML = '<div class="section-title">Graded Bets</div>';

  var recent = graded.slice().sort(function(a, b) {
    return String(b.game_date).localeCompare(String(a.game_date));
  }).slice(0, 100);

  var tableRows = recent.map(function(row) {
    var outcomeClass = row.win ? 'outcome-w' : 'outcome-l';
    var outcomeText = row.win ? 'WIN' : 'LOSS';
    var probClass = row.model_prob === null ? '' : row.model_prob >= 0.65 ? 'prob-high' : row.model_prob >= 0.5 ? 'prob-mid' : 'prob-low';
    var evClass = row.ev === null ? '' : row.ev >= 0 ? 'val-green' : 'val-red';
    var leagueText = row.league === 'SOCCER' && row.league_sub && row.league_sub !== 'SOCCER'
      ? row.league + ' · ' + row.league_sub
      : row.league;
    var sideLine = row.bet_side || '—';
    if (row.line !== null) sideLine += ' ' + (row.line > 0 ? '+' + row.line : row.line);

    return '<tr>' +
      '<td>' + escapeHtml(row.game_date || '—') + '</td>' +
      '<td>' + escapeHtml(leagueText || '—') + '</td>' +
      '<td>' + escapeHtml(row.market_raw || row.market || '—') + '</td>' +
      '<td>' + escapeHtml(sideLine) + '</td>' +
      '<td>' + escapeHtml(formatOdds(row.odds)) + '</td>' +
      '<td class="' + probClass + '">' + escapeHtml(safePct(row.model_prob)) + '</td>' +
      '<td class="' + evClass + '">' + escapeHtml(formatEV(row.ev)) + '</td>' +
      '<td class="' + outcomeClass + '">' + outcomeText + '</td>' +
      '</tr>';
  }).join('');

  betsSec.innerHTML += '<div style="overflow-x:auto"><table class="bets-table"><thead><tr>' +
    '<th>Date</th><th>League</th><th>Market</th><th>Side/Line</th><th>Odds</th><th>Model%</th><th>EV</th><th>Result</th>' +
    '</tr></thead><tbody>' + tableRows + '</tbody></table></div>';

  if (graded.length > 100) {
    betsSec.innerHTML += '<div style="font-size:10px;color:var(--text-muted);padding:8px 0;text-align:center">' +
      'Showing most recent 100 of ' + graded.length + ' graded bets</div>';
  }

  main.appendChild(betsSec);
}

document.querySelectorAll('#league-controls .league-pill').forEach(function(pill) {
  pill.addEventListener('click', function() {
    if (pill.disabled) return;

    document.querySelectorAll('#league-controls .league-pill').forEach(function(item) {
      item.classList.remove('active');
    });

    pill.classList.add('active');
    activeLeague = pill.dataset.league;
    activeLeagueSub = pill.dataset.leagueSub || 'all';
    if (allRows.length) render();
  });
});

document.querySelectorAll('.market-pill').forEach(function(pill) {
  pill.addEventListener('click', function() {
    document.querySelectorAll('.market-pill').forEach(function(item) {
      item.classList.remove('active');
    });
    pill.classList.add('active');
    activeMarket = pill.dataset.market;
    if (allRows.length) render();
  });
});

loadAll();
