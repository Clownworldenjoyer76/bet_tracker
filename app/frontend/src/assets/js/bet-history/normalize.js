function parseNum(value) {
  if (value === null || value === undefined || value === '') return null;
  var n = parseFloat(value);
  return isNaN(n) ? null : n;
}

function firstNum() {
  for (var i = 0; i < arguments.length; i++) {
    var n = parseNum(arguments[i]);
    if (n !== null) return n;
  }
  return null;
}

function firstText() {
  for (var i = 0; i < arguments.length; i++) {
    var v = arguments[i];
    if (v !== null && v !== undefined && String(v).trim() !== '') {
      return String(v).trim();
    }
  }
  return '';
}

function normalizeResult(r) {
  var resultCol = ['bet_result', 'result', 'outcome', 'win', 'won', 'correct'].find(function(c) {
    return r[c] !== undefined && r[c] !== '';
  });

  var resultVal = resultCol ? String(r[resultCol]).toLowerCase().trim() : '';

  if (resultVal === 'win' || resultVal === 'w' || resultVal === '1' || resultVal === 'true') return 'win';
  if (resultVal === 'loss' || resultVal === 'l' || resultVal === '0' || resultVal === 'false') return 'loss';
  if (resultVal === 'push' || resultVal === 'p' || resultVal === 'void' || resultVal === 'tie') return 'push';

  return 'unknown';
}

function normalizeMarket(r) {
  var leagueNames = [
    'NBA',
    'NCAAM',
    'NCAAB',
    'WNBA',
    'NHL',
    'MLB',
    'SOCCER',
    'BUNDESLIGA',
    'EPL',
    'LALIGA',
    'LIGUE1',
    'SERIEA',
    'MLS'
  ];

  var mktRaw = r.market_type || '';

  if (!mktRaw) {
    var candidate = (r.market || '').toUpperCase().trim();
    if (leagueNames.indexOf(candidate) === -1) mktRaw = r.market || '';
  }

  var mkt = String(mktRaw).toLowerCase().trim();

  if (mkt === 'moneyline' || mkt === 'match_odds' || mkt === 'ml') return 'moneyline';
  if (mkt === 'spread' || mkt === 'puck_line' || mkt === 'run_line' || mkt === 'line') return 'spread';
  if (
    mkt === 'total' ||
    mkt === 'over_total' ||
    mkt === 'under_total' ||
    mkt === 'btts' ||
    mkt === 'total25' ||
    mkt === 'total35'
  ) return 'total';

  return 'other';
}

function normalizeLeague(r, sourceLabel) {
  var leagueRaw = (r.league || '').toUpperCase().trim();

  if (sourceLabel === 'SOCCER') return 'SOCCER';
  if (leagueRaw === 'NCAAB') return 'NCAAM';
  if (leagueRaw) return leagueRaw;

  return sourceLabel;
}

function formatLineValue(value) {
  if (value === null || value === undefined || value === '') return '';

  var n = parseNum(value);
  if (n === null) return String(value);

  return n > 0 ? '+' + n : String(n);
}

function normalizeLine(r, market, betSide) {
  var line = firstText(r.bet_line, r.line);

  if (line) return line;

  if (market === 'spread') {
    if (betSide === 'home') {
      return firstText(r.home_spread, r.home_puck_line, r.home_run_line);
    }

    if (betSide === 'away') {
      return firstText(r.away_spread, r.away_puck_line, r.away_run_line);
    }
  }

  if (market === 'total') {
    return firstText(r.total, r.dk_total);
  }

  return '';
}

function normalizeOdds(r, betSide) {
  var oddsAmerican = firstNum(
    r.bet_odds_american,
    r.dk_odds_american,
    r.odds_american,
    r.american_odds
  );

  if (oddsAmerican === null) {
    if (betSide === 'home') {
      oddsAmerican = firstNum(
        r.home_dk_moneyline_american,
        r.home_dk_spread_american,
        r.home_dk_puck_line_american,
        r.home_dk_run_line_american,
        r.dk_home_puck_line
      );
    } else if (betSide === 'away') {
      oddsAmerican = firstNum(
        r.away_dk_moneyline_american,
        r.away_dk_spread_american,
        r.away_dk_puck_line_american,
        r.away_dk_run_line_american,
        r.dk_away_puck_line
      );
    } else if (betSide === 'over') {
      oddsAmerican = firstNum(r.dk_total_over_american);
    } else if (betSide === 'under') {
      oddsAmerican = firstNum(r.dk_total_under_american);
    }
  }

  if (oddsAmerican === null) {
    var dec = firstNum(r.odds, r.dk_odds_decimal);

    if (dec !== null) {
      oddsAmerican = dec >= 2
        ? Math.round((dec - 1) * 100)
        : Math.round(-100 / (dec - 1));
    }
  }

  return oddsAmerican;
}

function normalizeOddsDisplay(r, betSide) {
  if (String(r.sport || '').toLowerCase() === 'soccer' || firstText(r.odds)) {
    var soccerOdds = firstText(r.odds);
    if (soccerOdds) return soccerOdds;
  }

  var odds = normalizeOdds(r, betSide);

  if (odds === null) return '';

  return odds > 0 ? '+' + odds : String(odds);
}

function normalizeModelProb(r, betSide) {
  var modelProb = firstNum(r.bet_model_prob, r.model_prob);

  if (modelProb === null) {
    if (betSide === 'home') {
      modelProb = firstNum(r.home_model_prob, r.home_prob);
    } else if (betSide === 'away') {
      modelProb = firstNum(r.away_model_prob, r.away_prob);
    } else if (betSide === 'over') {
      modelProb = firstNum(r.over_model_prob, r.over_prob);
    } else if (betSide === 'under') {
      modelProb = firstNum(r.under_model_prob, r.under_prob);
    }
  }

  if (modelProb !== null && modelProb > 1) modelProb = modelProb / 100;

  return modelProb;
}

function normalizeMatchup(r) {
  var away = firstText(r.away_team, r.score_away_team);
  var home = firstText(r.home_team, r.score_home_team);

  if (away || home) {
    return (away || 'Away') + ' @ ' + (home || 'Home');
  }

  return firstText(r.matchup, r.game, r.event, r.home_away);
}

function soccerTotalFromMarket(market, takeBet) {
  var raw = String(market || takeBet || '').toLowerCase();

  var totalMatch = raw.match(/total(\d{2,3})/);
  if (totalMatch) return String(parseInt(totalMatch[1], 10) / 10);

  var takeMatch = raw.match(/(?:over|under)(\d{2,3})/);
  if (takeMatch) return String(parseInt(takeMatch[1], 10) / 10);

  return '';
}

function normalizePick(r, market, betSide, line) {
  var label = '';

  if (betSide === 'home') {
    label = firstText(r.home_team, r.score_home_team, 'Home');
  } else if (betSide === 'away') {
    label = firstText(r.away_team, r.score_away_team, 'Away');
  } else if (betSide === 'over') {
    label = 'Over';
  } else if (betSide === 'under') {
    label = 'Under';
  } else if (betSide === 'draw') {
    label = 'Draw';
  } else if (betSide === 'yes') {
    label = 'Yes';
  } else if (betSide === 'no') {
    label = 'No';
  } else {
    label = firstText(r.take_bet, r.bet_side, r.side, r.pick);
  }

  if (String(r.sport || '').toLowerCase() === 'soccer') {
    var soccerMarket = String(firstText(r.market_type, r.market)).toLowerCase();
    var soccerLine = soccerTotalFromMarket(soccerMarket, r.take_bet);

    if (soccerMarket === 'match_odds') {
      return label;
    }

    if (soccerMarket === 'btts') {
      return 'BTTS ' + label;
    }

    if (soccerLine && (betSide === 'over' || betSide === 'under')) {
      return label + ' ' + soccerLine;
    }

    return firstText(r.take_bet, label);
  }

  if (market === 'spread') {
    return (label + ' ' + formatLineValue(line)).trim();
  }

  if (market === 'total') {
    return (label + ' ' + line).trim();
  }

  if (market === 'moneyline') {
    if (label && label !== 'Home' && label !== 'Away') return label + ' ML';
    return label;
  }

  return label;
}

function normalizeProfitDisplay(value) {
  var n = parseNum(value);

  if (n === null) return '';

  return n > 0 ? '+' + n.toFixed(2) : n.toFixed(2);
}

function normalizeRow(r, sourceLabel) {
  var betSide = String(firstText(r.bet_side, r.side, r.take_bet, r.pick)).toLowerCase().trim();

  var league = normalizeLeague(r, sourceLabel);
  var leagueSub = (r.league || '').toUpperCase().trim();
  var market = normalizeMarket(r);
  var line = normalizeLine(r, market, betSide);
  var odds = normalizeOdds(r, betSide);
  var profitUnit = firstNum(r.profit_unit, r.profit, r.pnl, r.units, r.profit_loss);

  return {
    source: sourceLabel,
    league: league,
    league_sub: leagueSub,

    game_date: firstText(r.game_date, r.match_date, r.date, r.score_game_date),
    game_time: firstText(r.game_time, r.match_time, r.score_match_time),
    matchup: normalizeMatchup(r),

    market: market,
    market_raw: firstText(r.market_type, r.market),
    bet_side: firstText(r.bet_side, r.side, r.take_bet, r.pick),
    pick: normalizePick(r, market, betSide, line),

    line: parseNum(line),
    odds: odds,
    odds_display: normalizeOddsDisplay(r, betSide),

    model_prob: normalizeModelProb(r, betSide),
    ev: firstNum(r.bet_ev, r.ev, r.selected_ev, r.edge_pct),
    kelly: firstNum(r.bet_kelly, r.kelly),
    edge: firstNum(r.bet_edge_vs_market, r.edge_vs_market, r.edge),

    profit_unit: profitUnit,
    profit_kelly: firstNum(r.profit_kelly),
    profit_display: normalizeProfitDisplay(profitUnit),

    result: normalizeResult(r)
  };
}
