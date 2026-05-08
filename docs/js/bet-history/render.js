function render() {
  var rows = filteredRows();

  var graded = rows.filter(function(r) {
    return r.result === 'win' || r.result === 'loss' || r.result === 'push';
  });

  var main = document.getElementById('history-main');
  main.innerHTML = '';

  if (!graded.length) {
    main.innerHTML = '<div class="empty-state">No graded bets match the current filter</div>';
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

  var strip = document.createElement('div');
  strip.className = 'summary-strip';

  [
    {
      val: graded.length,
      lbl: 'Graded Bets',
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

    var ev = rows.reduce(function(s, r) {
      return s + (r.ev || 0);
    }, 0);

    return '<div class="breakdown-card">' +
      '<div class="breakdown-title">' + league + '</div>' +
      '<div class="stat-row"><span class="stat-label">Bets</span><span class="stat-value">' + rows.length + '</span></div>' +
      '<div class="stat-row"><span class="stat-label">W-L</span><span class="stat-value">' + wins + '-' + losses + '</span></div>' +
      '<div class="stat-row"><span class="stat-label">Win Rate</span><span class="stat-value" style="color:' + (rate >= 0.55 ? 'var(--accent-green)' : rate < 0.45 ? 'var(--accent-red)' : 'var(--accent-yellow)') + '">' + (rate * 100).toFixed(1) + '%</span></div>' +
      '<div class="stat-row"><span class="stat-label">Total EV</span><span class="stat-value" style="color:' + (ev >= 0 ? 'var(--accent-green)' : 'var(--accent-red)') + '">' + ev.toFixed(2) + '</span></div>' +
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

    var ev = rows.reduce(function(s, r) {
      return s + (r.ev || 0);
    }, 0);

    var label = market === 'spread'
      ? 'Spread / Line'
      : market.charAt(0).toUpperCase() + market.slice(1);

    return '<div class="breakdown-card">' +
      '<div class="breakdown-title">' + label + '</div>' +
      '<div class="stat-row"><span class="stat-label">Bets</span><span class="stat-value">' + rows.length + '</span></div>' +
      '<div class="stat-row"><span class="stat-label">W-L</span><span class="stat-value">' + wins + '-' + losses + '</span></div>' +
      '<div class="stat-row"><span class="stat-label">Win Rate</span><span class="stat-value" style="color:' + (rate >= 0.55 ? 'var(--accent-green)' : rate < 0.45 ? 'var(--accent-red)' : 'var(--accent-yellow)') + '">' + (rate * 100).toFixed(1) + '%</span></div>' +
      '<div class="stat-row"><span class="stat-label">Total EV</span><span class="stat-value" style="color:' + (ev >= 0 ? 'var(--accent-green)' : 'var(--accent-red)') + '">' + ev.toFixed(2) + '</span></div>' +
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

  var tableRows = sorted.slice(0, 250).map(function(r) {
    var outCls = r.result === 'win'
      ? 'outcome-w'
      : r.result === 'loss'
        ? 'outcome-l'
        : 'outcome-p';

    var outTxt = r.result === 'win'
      ? 'WIN'
      : r.result === 'loss'
        ? 'LOSS'
        : 'PUSH';

    var probCls = (r.model_prob || 0) >= 0.65
      ? 'prob-high'
      : (r.model_prob || 0) >= 0.5
        ? 'prob-mid'
        : 'prob-low';

    var evCls = (r.ev || 0) >= 0 ? 'val-green' : 'val-red';
    var oddsStr = r.odds !== null ? (r.odds > 0 ? '+' + r.odds : r.odds) : '—';
    var probStr = r.model_prob !== null ? (r.model_prob * 100).toFixed(1) + '%' : '—';
    var evStr = r.ev !== null ? r.ev.toFixed(2) : '—';
    var lineStr = r.line !== null ? ' ' + r.line : '';

    var leagueDisplay = r.league === 'SOCCER' && r.league_sub && r.league_sub !== 'SOCCER'
      ? r.league + ' · ' + r.league_sub
      : r.league;

    return '<tr>' +
      '<td>' + (r.game_date || '—') + '</td>' +
      '<td>' + leagueDisplay + '</td>' +
      '<td>' + (r.market_raw || r.market || '—') + '</td>' +
      '<td>' + (r.bet_side || '—') + lineStr + '</td>' +
      '<td>' + oddsStr + '</td>' +
      '<td class="' + probCls + '">' + probStr + '</td>' +
      '<td class="' + evCls + '">' + evStr + '</td>' +
      '<td class="' + outCls + '">' + outTxt + '</td>' +
    '</tr>';
  }).join('');

  var sec = document.createElement('div');
  sec.className = 'section';

  sec.innerHTML =
    '<div class="section-title">Graded Bet History</div>' +
    '<div style="overflow-x:auto">' +
      '<table class="bets-table">' +
        '<thead>' +
          '<tr>' +
            '<th>Date</th>' +
            '<th>League</th>' +
            '<th>Market</th>' +
            '<th>Side / Line</th>' +
            '<th>Odds</th>' +
            '<th>Model%</th>' +
            '<th>EV</th>' +
            '<th>Result</th>' +
          '</tr>' +
        '</thead>' +
        '<tbody>' + tableRows + '</tbody>' +
      '</table>' +
    '</div>';

  if (sorted.length > 250) {
    sec.innerHTML += '<div style="font-size:10px;color:var(--text-muted);padding:8px 0;text-align:center">Showing most recent 250 of ' + sorted.length + ' graded bets</div>';
  }

  main.appendChild(sec);
}
