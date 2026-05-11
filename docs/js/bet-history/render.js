var historySearch = '';
var historySort = 'newest';
var historyCurrentGradedRows = [];

function escapeHtml(value) {
  return String(value === null || value === undefined ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatDateDisplay(date) {
  if (!date) return '—';
  return String(date).replaceAll('_', '-');
}

function formatOdds(odds, oddsDisplay) {
  if (oddsDisplay !== null && oddsDisplay !== undefined && String(oddsDisplay).trim() !== '') {
    return oddsDisplay;
  }

  if (odds === null || odds === undefined || odds === '') return '—';

  var n = parseFloat(odds);
  if (isNaN(n)) return odds;

  return n > 0 ? '+' + n : String(n);
}

function formatProfit(value, profitDisplay) {
  if (value === null || value === undefined || value === '') return '—';

  var n = parseFloat(value);
  if (isNaN(n)) return value;

  return n > 0 ? '+' + n.toFixed(2) + 'u' : n.toFixed(2) + 'u';
}

function formatPercent(value) {
  if (value === null || value === undefined || value === '') return '—';

  var n = parseFloat(value);
  if (isNaN(n)) return '—';

  if (Math.abs(n) <= 1) n = n * 100;

  return n.toFixed(1) + '%';
}

function formatEV(value) {
  if (value === null || value === undefined || value === '') return '—';

  var n = parseFloat(value);
  if (isNaN(n)) return '—';

  return n > 0 ? '+' + n.toFixed(2) : n.toFixed(2);
}

function formatKelly(value) {
  if (value === null || value === undefined || value === '') return '—';

  var n = parseFloat(value);
  if (isNaN(n)) return '—';

  if (Math.abs(n) <= 1) return (n * 100).toFixed(1) + '%';

  return n.toFixed(2);
}

function formatMarketLabel(market) {
  if (!market) return '—';

  if (market === 'moneyline') return 'Moneyline';
  if (market === 'spread') return 'Spread / Line';
  if (market === 'total') return 'Total';

  return String(market).charAt(0).toUpperCase() + String(market).slice(1);
}

function valueClass(value) {
  var n = parseFloat(value);

  if (isNaN(n) || n === 0) return '';
  return n > 0 ? 'val-green' : 'val-red';
}

function probabilityClass(value) {
  var n = parseFloat(value);

  if (isNaN(n)) return '';
  if (n > 1) n = n / 100;

  if (n >= 0.65) return 'val-green';
  if (n >= 0.5) return 'val-yellow';
  return 'val-red';
}

function profitClass(value) {
  var n = parseFloat(value);

  if (isNaN(n) || n === 0) return 'profit-flat';
  return n > 0 ? 'val-green' : 'val-red';
}

function outcomeClass(result) {
  if (result === 'win') return 'outcome-w';
  if (result === 'loss') return 'outcome-l';
  return 'outcome-p';
}

function outcomeText(result) {
  if (result === 'win') return 'WIN';
  if (result === 'loss') return 'LOSS';
  if (result === 'push') return 'PUSH';
  return '—';
}

function leagueDisplayName(r) {
  if (r.league === 'SOCCER' && r.league_sub && r.league_sub !== 'SOCCER') {
    return r.league + ' · ' + r.league_sub;
  }

  return r.league || '—';
}

function numericOrNull(value) {
  if (value === null || value === undefined || value === '') return null;
  var n = parseFloat(value);
  return isNaN(n) ? null : n;
}

function historySearchText(r) {
  return [
    formatDateDisplay(r.game_date),
    leagueDisplayName(r),
    r.matchup || '',
    r.pick || '',
    r.bet_side || '',
    r.market || '',
    r.market_raw || '',
    formatOdds(r.odds, r.odds_display),
    outcomeText(r.result),
    formatProfit(r.profit_unit, r.profit_display),
    r.model_prob !== null && r.model_prob !== undefined ? formatPercent(r.model_prob) : '',
    r.ev !== null && r.ev !== undefined ? String(r.ev) : '',
    r.kelly !== null && r.kelly !== undefined ? String(r.kelly) : '',
    r.source || ''
  ].join(' ').toLowerCase();
}

function applyHistorySearch(rows) {
  var q = String(historySearch || '').trim().toLowerCase();

  if (!q) return rows;

  return rows.filter(function(r) {
    return historySearchText(r).indexOf(q) !== -1;
  });
}

function compareNumberWithMissing(a, b, getter, direction) {
  var av = numericOrNull(getter(a));
  var bv = numericOrNull(getter(b));

  if (av === null && bv === null) return 0;
  if (av === null) return 1;
  if (bv === null) return -1;

  return direction === 'asc' ? av - bv : bv - av;
}

function sortHistoryRows(rows) {
  var sorted = rows.slice();

  sorted.sort(function(a, b) {
    if (historySort === 'oldest') {
      return String(a.game_date).localeCompare(String(b.game_date));
    }

    if (historySort === 'best_profit') {
      return compareNumberWithMissing(a, b, function(r) { return r.profit_unit; }, 'desc');
    }

    if (historySort === 'worst_profit') {
      return compareNumberWithMissing(a, b, function(r) { return r.profit_unit; }, 'asc');
    }

    if (historySort === 'highest_ev') {
      return compareNumberWithMissing(a, b, function(r) { return r.ev; }, 'desc');
    }

    if (historySort === 'lowest_ev') {
      return compareNumberWithMissing(a, b, function(r) { return r.ev; }, 'asc');
    }

    if (historySort === 'league') {
      var leagueCompare = leagueDisplayName(a).localeCompare(leagueDisplayName(b));
      if (leagueCompare !== 0) return leagueCompare;
      return String(b.game_date).localeCompare(String(a.game_date));
    }

    return String(b.game_date).localeCompare(String(a.game_date));
  });

  return sorted;
}

function groupRowsByDate(rows) {
  var groups = [];
  var groupMap = {};

  rows.forEach(function(r) {
    var date = formatDateDisplay(r.game_date);

    if (!groupMap[date]) {
      groupMap[date] = {
        date: date,
        rows: []
      };
      groups.push(groupMap[date]);
    }

    groupMap[date].rows.push(r);
  });

  return groups;
}

function onHistorySearchInput(value) {
  historySearch = value || '';
  updateCompletedHistoryResults();
}

function onHistorySortChange(value) {
  historySort = value || 'newest';
  updateCompletedHistoryResults();
}

function render() {
  var rows = filteredRows();

  var graded = rows.filter(function(r) {
    return r.result === 'win' || r.result === 'loss' || r.result === 'push';
  });

  var main = document.getElementById('history-main');
  main.innerHTML = '';

  if (!graded.length) {
    main.innerHTML = '<div class="empty-state">No completed bets match the current filter</div>';
    return;
  }

  var wins = graded.filter(function(r) { return r.result === 'win'; }).length;
  var losses = graded.filter(function(r) { return r.result === 'loss'; }).length;
  var pushes = graded.filter(function(r) { return r.result === 'push'; }).length;
  var decisions = wins + losses;
  var winRate = decisions ? wins / decisions : 0;

  var avgProbRows = graded.filter(function(r) {
    return r.model_prob !== null;
  });

  var avgProb = avgProbRows.length
    ? avgProbRows.reduce(function(s, r) { return s + r.model_prob; }, 0) / avgProbRows.length
    : 0;

  var evRows = graded.filter(function(r) {
    return r.ev !== null;
  });

  var totalEV = evRows.reduce(function(s, r) {
    return s + r.ev;
  }, 0);

  var profitRows = graded.filter(function(r) {
    return r.profit_unit !== null;
  });

  var totalProfit = profitRows.reduce(function(s, r) {
    return s + r.profit_unit;
  }, 0);

  var strip = document.createElement('div');
  strip.className = 'summary-strip';

  [
    {
      val: graded.length,
      lbl: 'Completed Bets',
      cls: ''
    },
    {
      val: wins + '-' + losses + (pushes ? '-' + pushes : ''),
      lbl: 'W-L-P Record',
      cls: winRate >= 0.55 ? 'val-green' : winRate < 0.45 ? 'val-red' : 'val-yellow'
    },
    {
      val: (winRate * 100).toFixed(1) + '%',
      lbl: 'Win Rate',
      cls: winRate >= 0.55 ? 'val-green' : winRate < 0.45 ? 'val-red' : 'val-yellow'
    },
    {
      val: avgProbRows.length ? (avgProb * 100).toFixed(1) + '%' : '—',
      lbl: 'Avg Model Prob',
      cls: 'val-blue'
    },
    {
      val: profitRows.length ? formatProfit(totalProfit) : '—',
      lbl: 'Profit / Loss',
      cls: totalProfit >= 0 ? 'val-green' : 'val-red'
    },
    {
      val: evRows.length ? totalEV.toFixed(2) : '—',
      lbl: 'Total EV',
      cls: totalEV >= 0 ? 'val-green' : 'val-red'
    }
  ].forEach(function(s) {
    strip.innerHTML +=
      '<div class="summary-item">' +
        '<div class="summary-val ' + s.cls + '">' + escapeHtml(s.val) + '</div>' +
        '<div class="summary-lbl">' + escapeHtml(s.lbl) + '</div>' +
      '</div>';
  });

  main.appendChild(strip);

  renderLeagueBreakdown(main, graded);
  renderMarketBreakdown(main, graded);
  renderBetsTable(main, graded);
}

function renderLeagueBreakdown(main, graded) {
  var leagues = [];

  graded.forEach(function(r) {
    if (leagues.indexOf(r.league) === -1) leagues.push(r.league);
  });

  leagues.sort();

  var html = leagues.map(function(league) {
    var rows = graded.filter(function(r) {
      return r.league === league;
    });

    var wins = rows.filter(function(r) { return r.result === 'win'; }).length;
    var losses = rows.filter(function(r) { return r.result === 'loss'; }).length;
    var decisions = wins + losses;
    var rate = decisions ? wins / decisions : 0;

    var evRows = rows.filter(function(r) {
      return r.ev !== null;
    });

    var ev = evRows.reduce(function(s, r) {
      return s + r.ev;
    }, 0);

    var profitRows = rows.filter(function(r) {
      return r.profit_unit !== null;
    });

    var profit = profitRows.reduce(function(s, r) {
      return s + r.profit_unit;
    }, 0);

    return '<div class="breakdown-card">' +
      '<div class="breakdown-title">' + escapeHtml(league) + '</div>' +
      '<div class="stat-row"><span class="stat-label">Bets</span><span class="stat-value">' + rows.length + '</span></div>' +
      '<div class="stat-row"><span class="stat-label">W-L</span><span class="stat-value">' + wins + '-' + losses + '</span></div>' +
      '<div class="stat-row"><span class="stat-label">Win Rate</span><span class="stat-value" style="color:' + (rate >= 0.55 ? 'var(--accent-green)' : rate < 0.45 ? 'var(--accent-red)' : 'var(--accent-yellow)') + '">' + (rate * 100).toFixed(1) + '%</span></div>' +
      '<div class="stat-row"><span class="stat-label">P/L</span><span class="stat-value" style="color:' + (profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)') + '">' + (profitRows.length ? formatProfit(profit) : '—') + '</span></div>' +
      '<div class="stat-row"><span class="stat-label">Total EV</span><span class="stat-value" style="color:' + (ev >= 0 ? 'var(--accent-green)' : 'var(--accent-red)') + '">' + (evRows.length ? ev.toFixed(2) : '—') + '</span></div>' +
    '</div>';
  }).join('');

  var sec = document.createElement('div');
  sec.className = 'section';
  sec.innerHTML = '<div class="section-title">Performance by League</div><div class="breakdown-grid">' + html + '</div>';

  main.appendChild(sec);
}

function renderMarketBreakdown(main, graded) {
  var markets = ['moneyline', 'spread', 'total', 'other'];

  var html = markets.map(function(market) {
    var rows = graded.filter(function(r) {
      return r.market === market;
    });

    if (!rows.length) return '';

    var wins = rows.filter(function(r) { return r.result === 'win'; }).length;
    var losses = rows.filter(function(r) { return r.result === 'loss'; }).length;
    var decisions = wins + losses;
    var rate = decisions ? wins / decisions : 0;

    var evRows = rows.filter(function(r) {
      return r.ev !== null;
    });

    var ev = evRows.reduce(function(s, r) {
      return s + r.ev;
    }, 0);

    var profitRows = rows.filter(function(r) {
      return r.profit_unit !== null;
    });

    var profit = profitRows.reduce(function(s, r) {
      return s + r.profit_unit;
    }, 0);

    var label = formatMarketLabel(market);

    return '<div class="breakdown-card">' +
      '<div class="breakdown-title">' + escapeHtml(label) + '</div>' +
      '<div class="stat-row"><span class="stat-label">Bets</span><span class="stat-value">' + rows.length + '</span></div>' +
      '<div class="stat-row"><span class="stat-label">W-L</span><span class="stat-value">' + wins + '-' + losses + '</span></div>' +
      '<div class="stat-row"><span class="stat-label">Win Rate</span><span class="stat-value" style="color:' + (rate >= 0.55 ? 'var(--accent-green)' : rate < 0.45 ? 'var(--accent-red)' : 'var(--accent-yellow)') + '">' + (rate * 100).toFixed(1) + '%</span></div>' +
      '<div class="stat-row"><span class="stat-label">P/L</span><span class="stat-value" style="color:' + (profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)') + '">' + (profitRows.length ? formatProfit(profit) : '—') + '</span></div>' +
      '<div class="stat-row"><span class="stat-label">Total EV</span><span class="stat-value" style="color:' + (ev >= 0 ? 'var(--accent-green)' : 'var(--accent-red)') + '">' + (evRows.length ? ev.toFixed(2) : '—') + '</span></div>' +
    '</div>';
  }).join('');

  if (!html.replace(/\s/g, '')) return;

  var sec = document.createElement('div');
  sec.className = 'section';
  sec.innerHTML = '<div class="section-title">Performance by Market</div><div class="breakdown-grid">' + html + '</div>';

  main.appendChild(sec);
}

function buildHistoryTableRows(displayRows) {
  return displayRows.map(function(r) {
    var outCls = outcomeClass(r.result);
    var outTxt = outcomeText(r.result);
    var profitCls = profitClass(r.profit_unit);

    return '<tr>' +
      '<td><span class="history-date">' + escapeHtml(formatDateDisplay(r.game_date)) + '</span></td>' +
      '<td><span class="history-league-pill">' + escapeHtml(leagueDisplayName(r)) + '</span></td>' +
      '<td><span class="history-matchup">' + escapeHtml(r.matchup || '—') + '</span></td>' +
      '<td><span class="history-pick">' + escapeHtml(r.pick || r.bet_side || '—') + '</span></td>' +
      '<td><span class="history-odds">' + escapeHtml(formatOdds(r.odds, r.odds_display)) + '</span></td>' +
      '<td><span class="history-result-badge ' + outCls + '">' + escapeHtml(outTxt) + '</span></td>' +
      '<td><span class="history-profit-badge ' + profitCls + '">' + escapeHtml(formatProfit(r.profit_unit, r.profit_display)) + '</span></td>' +
    '</tr>';
  }).join('');
}

function buildDetailItem(label, value, cls) {
  return '<div class="history-detail-item">' +
    '<div class="history-detail-label">' + escapeHtml(label) + '</div>' +
    '<div class="history-detail-value ' + (cls || '') + '">' + escapeHtml(value) + '</div>' +
  '</div>';
}

function buildCardDetails(r) {
  var modelProb = formatPercent(r.model_prob);
  var ev = formatEV(r.ev);
  var kelly = formatKelly(r.kelly);
  var market = formatMarketLabel(r.market);
  var marketRaw = r.market_raw || '—';
  var source = r.source || '—';

  return '<details class="history-details">' +
    '<summary>Details</summary>' +
    '<div class="history-details-grid">' +
      buildDetailItem('Market', market, '') +
      buildDetailItem('Raw Market', marketRaw, '') +
      buildDetailItem('Model Prob', modelProb, probabilityClass(r.model_prob)) +
      buildDetailItem('EV', ev, valueClass(r.ev)) +
      buildDetailItem('Kelly', kelly, valueClass(r.kelly)) +
      buildDetailItem('Source', source, '') +
    '</div>' +
  '</details>';
}

function buildSingleHistoryCard(r) {
  var outCls = outcomeClass(r.result);
  var outTxt = outcomeText(r.result);
  var profitCls = profitClass(r.profit_unit);

  return '<div class="history-card">' +
    '<div class="history-card-top">' +
      '<div class="history-card-meta">' +
        '<span class="history-league-pill">' + escapeHtml(leagueDisplayName(r)) + '</span>' +
      '</div>' +
      '<span class="history-result-badge ' + outCls + '">' + escapeHtml(outTxt) + '</span>' +
    '</div>' +
    '<div class="history-card-matchup">' + escapeHtml(r.matchup || '—') + '</div>' +
    '<div class="history-card-pick">' + escapeHtml(r.pick || r.bet_side || '—') + '</div>' +
    '<div class="history-card-stats">' +
      '<div>' +
        '<div class="history-card-stat-label">Odds</div>' +
        '<div class="history-card-stat-value">' + escapeHtml(formatOdds(r.odds, r.odds_display)) + '</div>' +
      '</div>' +
      '<div>' +
        '<div class="history-card-stat-label">P/L</div>' +
        '<div class="history-card-stat-value"><span class="' + profitCls + '">' + escapeHtml(formatProfit(r.profit_unit, r.profit_display)) + '</span></div>' +
      '</div>' +
    '</div>' +
    buildCardDetails(r) +
  '</div>';
}

function buildHistoryCards(displayRows) {
  var groups = groupRowsByDate(displayRows);

  return groups.map(function(group) {
    var cards = group.rows.map(function(r) {
      return buildSingleHistoryCard(r);
    }).join('');

    return '<div class="history-date-group">' +
      '<div class="history-date-header">' +
        '<span>' + escapeHtml(group.date) + '</span>' +
        '<span class="history-date-count">' + group.rows.length + ' bet' + (group.rows.length === 1 ? '' : 's') + '</span>' +
      '</div>' +
      '<div class="history-card-grid">' + cards + '</div>' +
    '</div>';
  }).join('');
}

function updateCompletedHistoryResults() {
  var results = document.getElementById('completed-history-results');
  var count = document.getElementById('history-count');

  if (!results) return;

  var sortedRows = sortHistoryRows(historyCurrentGradedRows);
  var searchedRows = applyHistorySearch(sortedRows);
  var displayRows = searchedRows.slice(0, 500);

  if (count) {
    count.textContent = searchedRows.length + ' shown';
  }

  if (!searchedRows.length) {
    results.innerHTML = '<div class="history-empty-results">No bets match your search</div>';
    return;
  }

  results.innerHTML =
    '<div class="bets-table-wrap">' +
      '<table class="bets-table">' +
        '<thead>' +
          '<tr>' +
            '<th>Date</th>' +
            '<th>League</th>' +
            '<th>Game / Matchup</th>' +
            '<th>Pick</th>' +
            '<th>Odds</th>' +
            '<th>Result</th>' +
            '<th>P/L Units</th>' +
          '</tr>' +
        '</thead>' +
        '<tbody>' + buildHistoryTableRows(displayRows) + '</tbody>' +
      '</table>' +
    '</div>' +
    '<div class="history-card-list">' + buildHistoryCards(displayRows) + '</div>' +
    (
      searchedRows.length > 500
        ? '<div class="history-limit-note">Showing first 500 of ' + searchedRows.length + ' matching completed bets</div>'
        : ''
    );
}

function renderBetsTable(main, graded) {
  historyCurrentGradedRows = graded.slice();

  var sortedRows = sortHistoryRows(historyCurrentGradedRows);
  var searchedRows = applyHistorySearch(sortedRows);

  var sec = document.createElement('div');
  sec.className = 'section';
  sec.id = 'completed-history-section';

  sec.innerHTML =
    '<div class="section-title">Completed Bet History</div>' +
    '<div class="history-tools">' +
      '<input class="history-search" type="search" placeholder="Search completed bets..." value="' + escapeHtml(historySearch) + '" oninput="onHistorySearchInput(this.value)">' +
      '<select class="history-sort" onchange="onHistorySortChange(this.value)">' +
        '<option value="newest"' + (historySort === 'newest' ? ' selected' : '') + '>Newest First</option>' +
        '<option value="oldest"' + (historySort === 'oldest' ? ' selected' : '') + '>Oldest First</option>' +
        '<option value="best_profit"' + (historySort === 'best_profit' ? ' selected' : '') + '>Best P/L</option>' +
        '<option value="worst_profit"' + (historySort === 'worst_profit' ? ' selected' : '') + '>Worst P/L</option>' +
        '<option value="highest_ev"' + (historySort === 'highest_ev' ? ' selected' : '') + '>Highest EV</option>' +
        '<option value="lowest_ev"' + (historySort === 'lowest_ev' ? ' selected' : '') + '>Lowest EV</option>' +
        '<option value="league"' + (historySort === 'league' ? ' selected' : '') + '>League A-Z</option>' +
      '</select>' +
      '<div class="history-count" id="history-count">' + searchedRows.length + ' shown</div>' +
    '</div>' +
    '<div id="completed-history-results"></div>';

  main.appendChild(sec);
  updateCompletedHistoryResults();
}
