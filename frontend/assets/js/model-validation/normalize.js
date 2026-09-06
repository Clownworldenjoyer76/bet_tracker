function parseNum(value) {
  if (value === null || value === undefined || String(value).trim() === '') return null;
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
    var value = arguments[i];
    if (value !== null && value !== undefined && String(value).trim() !== '') {
      return String(value).trim();
    }
  }
  return '';
}

function normalizeProbability(value) {
  var n = parseNum(value);
  if (n === null) return null;
  if (n > 1 && n <= 100) n = n / 100;
  return n;
}

function normalizeResult(value) {
  var result = String(value || '').trim().toLowerCase();
  if (result === 'win' || result === 'w' || result === '1' || result === 'true') return 'win';
  if (result === 'loss' || result === 'l' || result === '0' || result === 'false') return 'loss';
  if (result === 'push' || result === 'p' || result === 'tie' || result === 'void') return 'push';
  return 'unknown';
}

function normalizeMarket(r) {
  var raw = firstText(r.market_type, r.market).toLowerCase();
  if (raw === 'moneyline' || raw === 'match_odds' || raw === 'ml') return 'moneyline';
  if (raw === 'spread' || raw === 'puck_line' || raw === 'run_line' || raw === 'line') return 'spread';
  if (
    raw === 'total' || raw === 'over_total' || raw === 'under_total' ||
    raw === 'btts' || raw === 'total25' || raw === 'total35'
  ) return 'total';
  return 'other';
}

function sourceLeague(r, sourceLabel) {
  if (sourceLabel === 'MLB_LINEUPS') return 'MLB_LINEUPS';
  if (sourceLabel === 'SOCCER') return 'SOCCER';
  if (sourceLabel === 'CFB') return 'CFB';
  if (sourceLabel === 'UFC') return 'UFC';

  var league = firstText(r.league).toUpperCase();
  if (league === 'NCAAB') return 'NCAAM';
  return league || sourceLabel;
}

function sourceLeagueSub(r, sourceLabel) {
  if (sourceLabel === 'SOCCER') return firstText(r.league, r.league_lower).toUpperCase();
  return sourceLeague(r, sourceLabel);
}

function truthySelected(value) {
  var v = String(value === null || value === undefined ? '' : value).trim().toLowerCase();
  return v === '1' || v === 'true' || v === 'yes' || v === 'y';
}

function cfbBetRow(row, prefix, market) {
  if (!truthySelected(row[prefix + '_selected'])) return null;

  var selection = firstText(row[prefix + '_selection']);
  var result = firstText(row[prefix + '_grade']);

  var out = Object.assign({}, row);
  out.sport = 'football';
  out.league = 'CFB';
  out.market_type = market;
  out.bet_side = selection.toLowerCase();
  out.take_bet = selection;
  out.line = firstText(row[prefix + '_line']);
  out.dk_odds_american = firstText(row[prefix + '_odds_american']);
  out.model_prob = firstText(row[prefix + '_model_probability']);
  out.ev = firstText(row[prefix + '_ev']);
  out.kelly = firstText(row[prefix + '_kelly']);
  out.edge = firstText(row[prefix + '_edge']);
  out.bet_result = result;
  return out;
}

function expandCFBRow(row) {
  var out = [];
  var ml = cfbBetRow(row, 'ml', 'moneyline');
  var spread = cfbBetRow(row, 'spread', 'spread');
  var total = cfbBetRow(row, 'total', 'total');
  if (ml) out.push(ml);
  if (spread) out.push(spread);
  if (total) out.push(total);
  return out;
}

function expandUFCRow(row) {
  var bet = String(row.bet || '').trim().toLowerCase();
  var index = bet === 'fighter_1' ? 1 : bet === 'fighter_2' ? 2 : 0;
  if (!index) return [];

  var out = Object.assign({}, row);
  var fighter = index === 1 ? row.fighter_1 : row.fighter_2;

  out.sport = 'mma';
  out.league = 'UFC';
  out.game_date = row.match_date;
  out.market_type = 'moneyline';
  out.bet_side = fighter;
  out.take_bet = fighter;
  out.dk_odds_american = index === 1 ? row.moneyline_f1 : row.moneyline_f2;
  out.model_prob = index === 1 ? row.model_prob_f1 : row.model_prob_f2;
  out.ev = index === 1 ? row.ev_f1 : row.ev_f2;
  out.kelly = index === 1 ? row.kelly_f1 : row.kelly_f2;
  out.edge = index === 1 ? row.edge_f1 : row.edge_f2;
  out.bet_result = index === 1 ? row.result_fighter_1 : row.result_fighter_2;
  return [out];
}

function expandSourceRows(rows, source) {
  var out = [];

  rows.forEach(function(row) {
    var expanded;
    if (source.adapter === 'cfb') expanded = expandCFBRow(row);
    else if (source.adapter === 'ufc') expanded = expandUFCRow(row);
    else expanded = [row];

    expanded.forEach(function(item) { out.push(item); });
  });

  return out;
}

function normalizeOdds(r, betSide) {
  var odds = firstNum(
    r.bet_odds_american,
    r.dk_odds_american,
    r.odds_american,
    r.american_odds
  );

  if (odds !== null) return odds;

  if (betSide === 'home') {
    odds = firstNum(r.home_dk_moneyline_american, r.home_dk_spread_american, r.home_dk_puck_line_american, r.home_dk_run_line_american);
  } else if (betSide === 'away') {
    odds = firstNum(r.away_dk_moneyline_american, r.away_dk_spread_american, r.away_dk_puck_line_american, r.away_dk_run_line_american);
  } else if (betSide === 'over') {
    odds = firstNum(r.dk_total_over_american);
  } else if (betSide === 'under') {
    odds = firstNum(r.dk_total_under_american);
  }

  if (odds !== null) return odds;

  var decimal = firstNum(r.odds, r.dk_odds_decimal, r.odds_decimal);
  if (decimal !== null && decimal > 1) {
    return decimal >= 2
      ? Math.round((decimal - 1) * 100)
      : Math.round(-100 / (decimal - 1));
  }

  return null;
}

function normalizeModelProb(r, betSide) {
  var probability = normalizeProbability(firstText(r.bet_model_prob, r.model_prob));
  if (probability !== null) return probability;

  if (betSide === 'home') return normalizeProbability(firstText(r.home_model_prob, r.home_prob));
  if (betSide === 'away') return normalizeProbability(firstText(r.away_model_prob, r.away_prob));
  if (betSide === 'over') return normalizeProbability(firstText(r.over_model_prob, r.over_prob));
  if (betSide === 'under') return normalizeProbability(firstText(r.under_model_prob, r.under_prob));
  return null;
}

function normalizeRow(r, sourceLabel) {
  var betSide = firstText(r.bet_side, r.side, r.take_bet, r.pick).toLowerCase();
  var result = normalizeResult(firstText(r.bet_result, r.result, r.outcome, r.win, r.won, r.correct));
  var modelProb = normalizeModelProb(r, betSide);

  return {
    source: sourceLabel,
    league: sourceLeague(r, sourceLabel),
    league_sub: sourceLeagueSub(r, sourceLabel),
    market: normalizeMarket(r),
    market_raw: firstText(r.market_type, r.market),
    bet_side: firstText(r.bet_side, r.side, r.take_bet, r.pick),
    line: firstNum(r.bet_line, r.line),
    model_prob: modelProb,
    ev: firstNum(r.bet_ev, r.ev, r.selected_ev, r.edge_pct),
    kelly: firstNum(r.bet_kelly, r.kelly),
    odds: normalizeOdds(r, betSide),
    game_date: firstText(r.game_date, r.match_date, r.date, r.score_game_date),
    result: result,
    win: result === 'win' ? true : result === 'loss' ? false : null
  };
}
