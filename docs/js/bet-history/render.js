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
  if (profitDisplay !== null && profitDisplay !== undefined && String(profitDisplay).trim() !== '') {
    return profitDisplay;
  }

  if (value === null || value === undefined || value === '') return '—';

  var n = parseFloat(value);
  if (isNaN(n)) return value;

  return n > 0 ? '+' + n.toFixed(2) : n.toFixed(2);
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
        '<div class="summary-val ' + s.cls + '">' + s.val + '</div>' +
        '<div class="summary-lbl">' + s.lbl + '</div>' +
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
      '<div class="breakdown-title">' + league + '</div>' +
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

    var label = market === 'spread'
      ? 'Spread / Line'
      : market.charAt(0).toUpperCase() + market.slice(1);

    return '<div class="breakdown-card">' +
      '<div class="breakdown-title">' + label + '</div>' +
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

function renderBetsTable(main, graded) {
  var sorted = graded.slice().sort(function(a, b) {
    return String(b.game_date).localeCompare(String(a.game_date));
  });

  var displayRows = sorted.slice(0, 500);

  var tableRows = displayRows.map(function(r) {
    var outCls = outcomeClass(r.result);
    var outTxt = outcomeText(r.result);
    var profitCls = profitClass(r.profit_unit);

    return '<tr>' +
      '<td>' + formatDateDisplay(r.game_date) + '</td>' +
      '<td>' + leagueDisplayName(r) + '</td>' +
      '<td>' + (r.matchup || '—') + '</td>' +
      '<td>' + (r.pick || r.bet_side || '—') + '</td>' +
      '<td>' + formatOdds(r.odds, r.odds_display) + '</td>' +
      '<td class="' + outCls + '">' + outTxt + '</td>' +
      '<td class="' + profitCls + '">' + formatProfit(r.profit_unit, r.profit_display) + '</td>' +
    '</tr>';
  }).join('');

  var sec = document.createElement('div');
  sec.className = 'section';

  sec.innerHTML =
    '<div class="section-title">Completed Bet History</div>' +
    '<div style="overflow-x:auto">' +
      '<table class="bets-table">' +
        '<thead>' +
          '<tr>' +
            '<th>Date</th>' +
            '<th>League</th>' +
            '<th>Game / Matchup</th>' +
            '<th>Pick</th>' +
            '<th>Odds</th>' +
            '<th>Result</th>' +
            '<th>Profit / Loss</th>' +
          '</tr>' +
        '</thead>' +
        '<tbody>' + tableRows + '</tbody>' +
      '</table>' +
    '</div>';

  if (sorted.length > 500) {
    sec.innerHTML += '<div style="font-size:10px;color:var(--text-muted);padding:8px 0;text-align:center">Showing most recent 500 of ' + sorted.length + ' completed bets</div>';
  }

  main.appendChild(sec);
}
