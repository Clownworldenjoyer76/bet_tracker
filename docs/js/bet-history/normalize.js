function parseNum(value) {
  var n = parseFloat(value);
  return isNaN(n) ? null : n;
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

function normalizeOdds(r, betSide) {
  var oddsAmerican =
    parseNum(r.dk_odds_american) ||
    parseNum(r.odds_american) ||
    parseNum(r.american_odds) ||
    null;

  if (!oddsAmerican) {
    if (betSide === 'home') {
      oddsAmerican = parseNum(r.home_dk_moneyline_american) || parseNum(r.home_dk_spread_american) || null;
    } else if (betSide === 'away') {
      oddsAmerican = parseNum(r.away_dk_moneyline_american) || parseNum(r.away_dk_spread_american) || null;
    } else if (betSide === 'over') {
      oddsAmerican = parseNum(r.dk_total_over_american) || null;
    } else if (betSide === 'under') {
      oddsAmerican = parseNum(r.dk_total_under_american) || null;
    }
  }

  if (!oddsAmerican) {
    var dec = parseNum(r.odds) || parseNum(r.dk_odds_decimal) || null;

    if (dec) {
      oddsAmerican = dec >= 2
        ? Math.round((dec - 1) * 100)
        : Math.round(-100 / (dec - 1));
    }
  }

  return oddsAmerican;
}

function normalizeModelProb(r, betSide) {
  var modelProb = parseNum(r.model_prob);

  if (modelProb === null) {
    if (betSide === 'home' && r.home_prob) modelProb = parseNum(r.home_prob);
    else if (betSide === 'away' && r.away_prob) modelProb = parseNum(r.away_prob);
    else if (betSide === 'over' && r.over_prob) modelProb = parseNum(r.over_prob);
    else if (betSide === 'under' && r.under_prob) modelProb = parseNum(r.under_prob);
  }

  if (modelProb !== null && modelProb > 1) modelProb = modelProb / 100;

  return modelProb;
}

function normalizeRow(r, sourceLabel) {
  var betSide = String(r.bet_side || r.side || r.take_bet || r.pick || '').toLowerCase().trim();

  var league = normalizeLeague(r, sourceLabel);
  var leagueSub = (r.league || '').toUpperCase().trim();

  return {
    source: sourceLabel,
    league: league,
    league_sub: leagueSub,
    game_date: r.game_date || r.match_date || r.date || '',
    matchup: r.matchup || r.game || r.event || r.home_away || '',
    market: normalizeMarket(r),
    market_raw: r.market_type || r.market || '',
    bet_side: r.bet_side || r.side || r.take_bet || r.pick || '',
    line: parseNum(r.line),
    odds: normalizeOdds(r, betSide),
    model_prob: normalizeModelProb(r, betSide),
    ev: parseNum(r.bet_ev) || parseNum(r.ev) || parseNum(r.selected_ev) || parseNum(r.edge_pct),    kelly: parseNum(r.kelly),
    result: normalizeResult(r)
  };
}
