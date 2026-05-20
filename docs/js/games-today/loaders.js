import { fetchCSV, fetchFirstCSV } from "./csv.js";
import { loadMLBMaps, pitcherName, venueName } from "./maps.js";
import {
  dateToUnderscore,
  formatDate,
  formatTime,
  formatProb,
  formatOneDecimal,
  formatOdds,
  decimalToAmerican,
  handLabel,
  parseSortTime,
  plusLine,
} from "./format.js";

const BASKETBALL_ORDER = ["NBA", "NCAAM", "WNBA"];

const SOCCER_ORDER = [
  { key: "MLS",        slug: "mls",        display: "Major League Soccer - MLS" },
  { key: "EPL",        slug: "epl",        display: "English Premier League - EPL" },
  { key: "LALIGA",     slug: "laliga",     display: "Spain - La Liga" },
  { key: "LIGUE1",     slug: "ligue1",     display: "France - Ligue 1" },
  { key: "SERIEA",     slug: "seriea",     display: "Italy - Serie A" },
  { key: "BUNDESLIGA", slug: "bundesliga", display: "Germany - Bundesliga" },
];

function mapByGameId(rows) {
  const map = {};

  rows.forEach(row => {
    if (row.game_id) map[String(row.game_id)] = row;
  });

  return map;
}

function mapNHLByGame(rows) {
  const map = {};

  rows.forEach(row => {
    const key = [
      String(row.game_date || "").replaceAll("-", "_"),
      String(row.home_team || "").toLowerCase(),
      String(row.away_team || "").toLowerCase(),
    ].join("|");

    map[key] = row;
  });

  return map;
}

function nhlGameKey(row) {
  return [
    String(row.game_date || "").replaceAll("-", "_"),
    String(row.home_team || "").toLowerCase(),
    String(row.away_team || "").toLowerCase(),
  ].join("|");
}

function mapUFCByFight(rows) {
  const map = {};

  rows.forEach(row => {
    const key = [
      String(row.match_date || "").replaceAll("-", "_"),
      String(row.fighter_1 || "").toLowerCase(),
      String(row.fighter_2 || "").toLowerCase(),
    ].join("|");

    map[key] = row;
  });

  return map;
}

function ufcFightKey(row) {
  return [
    String(row.match_date || "").replaceAll("-", "_"),
    String(row.fighter_1 || "").toLowerCase(),
    String(row.fighter_2 || "").toLowerCase(),
  ].join("|");
}

function mapMLBContext(rows) {
  const byGamePk = {};
  const byFallback = {};

  rows.forEach(row => {
    if (row.gamePk) byGamePk[String(row.gamePk)] = row;

    const fallbackKey = [
      String(row.game_date || "").replaceAll("-", "_"),
      String(row.home_team_id || ""),
      String(row.away_team_id || ""),
    ].join("|");

    byFallback[fallbackKey] = row;
  });

  return { byGamePk, byFallback };
}

function mlbContextFallbackKey(row) {
  return [
    String(row.game_date || "").replaceAll("-", "_"),
    String(row.home_team_id || ""),
    String(row.away_team_id || ""),
  ].join("|");
}

function doubleHeaderText(row) {
  if (String(row.doubleheader || "").toUpperCase() !== "Y") return "";

  return `Double Header Game ${row.gameNumber || ""}`.trim();
}

function dayNightText(value) {
  const normalized = String(value || "").trim().toLowerCase();

  if (normalized === "day") return "Day Game";
  if (normalized === "night") return "Night Game";

  return "";
}

function weatherRows(context) {
  const rows = [];

  if (context.roof_type) rows.push(["Roof", `${context.roof_type} Roof`]);
  if (context.turf_type) rows.push(["Turf", `${context.turf_type} Turf`]);
  if (context.park_factor) rows.push(["Park Factor", `${context.park_factor} Park Factor`]);
  if (context.temp_f) rows.push(["Temperature", `${context.temp_f}° F`]);

  if (context.wind_mph || context.wind_dir) {
    rows.push(["Wind", `Wind ${context.wind_mph || ""} MPH ${context.wind_dir || ""}`.trim()]);
  }

  if (context.humidity) rows.push(["Humidity", `${context.humidity}% Humidity`]);
  if (context.chance_of_rain) rows.push(["Chance of Rain", `${context.chance_of_rain}% Chance of Rain`]);

  if (String(context.wind_blowing_out || "").trim() === "1") {
    rows.push(["Wind", "Wind Blowing Out"]);
  }

  return rows;
}

function cleanModalRows(rows) {
  return rows.filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== "");
}

function displayLeagueConfig(key, fallbackName) {
  const cfg = window.REPO_CONFIG?.[key] || {};
  return cfg.displayName || fallbackName || key;
}

export async function loadMLB(date) {
  const maps = await loadMLBMaps();

  const [gamesRes, predRes, bookRes, contextRes] = await Promise.all([
    fetchCSV(`win/baseball/00_intake/games/${date}_games.csv`),
    fetchCSV(`win/baseball/00_intake/predictions/pred_with_game_id/${date}_MLB.csv`),
    fetchCSV(`win/baseball/00_intake/sportsbook/${date}_MLB.csv`),
    fetchCSV(`win/baseball/00_intake/mlb_raw/${date}_game_context.csv`),
  ]);

  const predictionByGameId = mapByGameId(predRes.rows);
  const bookByGameId = mapByGameId(bookRes.rows);
  const contextMap = mapMLBContext(contextRes.rows);

  const games = gamesRes.rows.map(base => {
    const pred = predictionByGameId[base.game_id] || {};
    const book = bookByGameId[base.game_id] || {};
    const context =
      contextMap.byGamePk[String(base.gamePk)] ||
      contextMap.byFallback[mlbContextFallbackKey(base)] ||
      {};

    const gameTime = base.game_time || pred.game_time || book.game_time;

    const homePitcher =
      pred.home_pitcher ||
      pitcherName(base.home_pitcher_id, maps) ||
      pitcherName(context.home_pitcher_id, maps);

    const awayPitcher =
      pred.away_pitcher ||
      pitcherName(base.away_pitcher_id, maps) ||
      pitcherName(context.away_pitcher_id, maps);

    const displayLeague = displayLeagueConfig("MLB", "MLB");

    return {
      league: "MLB",
      sport: "baseball",
      displayLeague,
      sortTime: parseSortTime(gameTime),
      title: `${base.away_team} @ ${base.home_team}`,
      card: {
        date: formatDate(base.game_date),
        time: formatTime(gameTime),
        away: base.away_team,
        home: base.home_team,
        moneyline: [
          book.away_dk_moneyline_american && `${base.away_team} ${formatOdds(book.away_dk_moneyline_american)}`,
          book.home_dk_moneyline_american && `${base.home_team} ${formatOdds(book.home_dk_moneyline_american)}`,
        ].filter(Boolean),
        spread: [
          book.away_run_line && `${base.away_team} ${plusLine(book.away_run_line)} (${formatOdds(book.away_dk_run_line_american)})`,
          book.home_run_line && `${base.home_team} ${plusLine(book.home_run_line)} (${formatOdds(book.home_dk_run_line_american)})`,
        ].filter(Boolean),
        total: book.total ? `Total ${book.total} O ${formatOdds(book.dk_total_over_american)} / U ${formatOdds(book.dk_total_under_american)}` : "",
        projection: pred.total_projected_runs
          ? `${base.away_team} ${formatOneDecimal(pred.away_projected_runs)} · ${base.home_team} ${formatOneDecimal(pred.home_projected_runs)} · Total ${formatOneDecimal(pred.total_projected_runs)}`
          : "",
      },
      modal: cleanModalRows([
        ["Date", formatDate(base.game_date)],
        ["Time", formatTime(gameTime)],
        ["Venue", venueName(base.venue_id, maps)],
        ["Double Header", doubleHeaderText(base)],
        ["Day/Night", dayNightText(base.day_night)],
        ["Away Pitcher", [awayPitcher, handLabel(context.away_pitcher_hand)].filter(Boolean).join(" · ")],
        ["Home Pitcher", [homePitcher, handLabel(context.home_pitcher_hand)].filter(Boolean).join(" · ")],
        ["Away Win Probability", formatProb(pred.away_prob)],
        ["Home Win Probability", formatProb(pred.home_prob)],
        ["Away Projected Runs", formatOneDecimal(pred.away_projected_runs)],
        ["Home Projected Runs", formatOneDecimal(pred.home_projected_runs)],
        ["Projected Total Runs", formatOneDecimal(pred.total_projected_runs)],
        ["Away Run Line", book.away_run_line && `${plusLine(book.away_run_line)} (${formatOdds(book.away_dk_run_line_american)})`],
        ["Home Run Line", book.home_run_line && `${plusLine(book.home_run_line)} (${formatOdds(book.home_dk_run_line_american)})`],
        ["Total", book.total],
        ["Total Over", formatOdds(book.dk_total_over_american)],
        ["Total Under", formatOdds(book.dk_total_under_american)],
        ["Away Moneyline", formatOdds(book.away_dk_moneyline_american)],
        ["Home Moneyline", formatOdds(book.home_dk_moneyline_american)],
        ...weatherRows(context),
      ]),
    };
  });

  return {
    league: "MLB",
    displayName: displayLeagueConfig("MLB", "MLB"),
    games,
  };
}

export async function loadNHL(date) {
  const [bookRes, predRes] = await Promise.all([
    fetchCSV(`win/hockey/00_intake/sportsbook/hockey_${date}.csv`),
    fetchCSV(`win/hockey/00_intake/predictions/hockey_${date}.csv`),
  ]);

  const predictionByGame = mapNHLByGame(predRes.rows);

  const games = bookRes.rows.map(book => {
    const pred = predictionByGame[nhlGameKey(book)] || {};
    const displayLeague = displayLeagueConfig("NHL", "NHL");

    return {
      league: "NHL",
      sport: "hockey",
      displayLeague,
      sortTime: parseSortTime(book.game_time),
      title: `${book.away_team} @ ${book.home_team}`,
      card: {
        date: formatDate(book.game_date),
        time: formatTime(book.game_time),
        away: book.away_team,
        home: book.home_team,
        moneyline: [
          book.away_dk_moneyline_american && `${book.away_team} ${formatOdds(book.away_dk_moneyline_american)}`,
          book.home_dk_moneyline_american && `${book.home_team} ${formatOdds(book.home_dk_moneyline_american)}`,
        ].filter(Boolean),
        spread: [
          book.away_puck_line && `${book.away_team} ${plusLine(book.away_puck_line)} (${formatOdds(book.away_dk_puck_line_american)})`,
          book.home_puck_line && `${book.home_team} ${plusLine(book.home_puck_line)} (${formatOdds(book.home_dk_puck_line_american)})`,
        ].filter(Boolean),
        total: book.total ? `Total ${book.total} O ${formatOdds(book.dk_total_over_american)} / U ${formatOdds(book.dk_total_under_american)}` : "",
        projection: pred.total_projected_goals
          ? `${book.away_team} ${formatOneDecimal(pred.away_projected_goals)} · ${book.home_team} ${formatOneDecimal(pred.home_projected_goals)} · Total ${formatOneDecimal(pred.total_projected_goals)}`
          : "",
      },
      modal: cleanModalRows([
        ["Date", formatDate(book.game_date)],
        ["Time", formatTime(book.game_time)],
        ["Away Win Probability", formatProb(pred.away_prob)],
        ["Home Win Probability", formatProb(pred.home_prob)],
        ["Away Projected Goals", formatOneDecimal(pred.away_projected_goals)],
        ["Home Projected Goals", formatOneDecimal(pred.home_projected_goals)],
        ["Projected Total Goals", formatOneDecimal(pred.total_projected_goals)],
        ["Away Puck Line", book.away_puck_line && `${plusLine(book.away_puck_line)} (${formatOdds(book.away_dk_puck_line_american)})`],
        ["Home Puck Line", book.home_puck_line && `${plusLine(book.home_puck_line)} (${formatOdds(book.home_dk_puck_line_american)})`],
        ["Total", book.total],
        ["Total Over", formatOdds(book.dk_total_over_american)],
        ["Total Under", formatOdds(book.dk_total_under_american)],
        ["Away Moneyline", formatOdds(book.away_dk_moneyline_american)],
        ["Home Moneyline", formatOdds(book.home_dk_moneyline_american)],
      ]),
    };
  });

  return {
    league: "NHL",
    displayName: displayLeagueConfig("NHL", "NHL"),
    games,
  };
}

export async function loadBasketball(league, date) {
  const lower = league.toLowerCase();
  const upper = league.toUpperCase();

  const [gamesRes, predRes, bookRes] = await Promise.all([
    fetchFirstCSV([
      `win/basketball/daily_games/${lower}/${date}_${lower}.csv`,
      `win/basketball/daily_games/${lower}/${date}_${upper}.csv`,
      `win/basketball/daily_games/${upper}/${date}_${lower}.csv`,
      `win/basketball/daily_games/${upper}/${date}_${upper}.csv`,
    ]),
    fetchFirstCSV([
      `win/basketball/00_intake/predictions/predictions_cleaned/${lower}/${date}_${lower}_predictions.csv`,
      `win/basketball/00_intake/predictions/predictions_cleaned/${lower}/${date}_${upper}_predictions.csv`,
      `win/basketball/00_intake/predictions/predictions_cleaned/${upper}/${date}_${lower}_predictions.csv`,
      `win/basketball/00_intake/predictions/predictions_cleaned/${upper}/${date}_${upper}_predictions.csv`,
    ]),
    fetchFirstCSV([
      `win/basketball/00_intake/sportsbook/sportsbook_cleaned/${lower}/${date}_${lower}_odds.csv`,
      `win/basketball/00_intake/sportsbook/sportsbook_cleaned/${lower}/${date}_${upper}_odds.csv`,
      `win/basketball/00_intake/sportsbook/sportsbook_cleaned/${upper}/${date}_${lower}_odds.csv`,
      `win/basketball/00_intake/sportsbook/sportsbook_cleaned/${upper}/${date}_${upper}_odds.csv`,
    ]),
  ]);

  const predictionByGameId = mapByGameId(predRes.rows);
  const bookByGameId = mapByGameId(bookRes.rows);
  const displayLeague = displayLeagueConfig(league, league);

  const games = gamesRes.rows.map(base => {
    const pred = predictionByGameId[base.game_id] || {};
    const book = bookByGameId[base.game_id] || {};
    const gameTime = base.game_time || pred.game_time || book.game_time;

    return {
      league,
      sport: "basketball",
      displayLeague,
      sortTime: parseSortTime(gameTime),
      title: `${base.away_team} @ ${base.home_team}`,
      card: {
        date: formatDate(base.game_date),
        time: formatTime(gameTime),
        away: base.away_team,
        home: base.home_team,
        moneyline: [
          book.away_dk_moneyline_american && `${base.away_team} ${formatOdds(book.away_dk_moneyline_american)}`,
          book.home_dk_moneyline_american && `${base.home_team} ${formatOdds(book.home_dk_moneyline_american)}`,
        ].filter(Boolean),
        spread: [
          book.away_spread && `${base.away_team} ${plusLine(book.away_spread)} (${formatOdds(book.away_dk_spread_american)})`,
          book.home_spread && `${base.home_team} ${plusLine(book.home_spread)} (${formatOdds(book.home_dk_spread_american)})`,
        ].filter(Boolean),
        total: book.total ? `Total ${book.total} O ${formatOdds(book.dk_total_over_american)} / U ${formatOdds(book.dk_total_under_american)}` : "",
        projection: pred.total_projected_points
          ? `${base.away_team} ${formatOneDecimal(pred.away_projected_points)} · ${base.home_team} ${formatOneDecimal(pred.home_projected_points)} · Total ${formatOneDecimal(pred.total_projected_points)}`
          : "",
      },
      modal: cleanModalRows([
        ["Date", formatDate(base.game_date)],
        ["Time", formatTime(gameTime)],
        ["Away Win Probability", formatProb(pred.away_prob)],
        ["Home Win Probability", formatProb(pred.home_prob)],
        ["Away Projected Points", formatOneDecimal(pred.away_projected_points)],
        ["Home Projected Points", formatOneDecimal(pred.home_projected_points)],
        ["Projected Total Points", formatOneDecimal(pred.total_projected_points)],
        ["Away Spread", book.away_spread && `${plusLine(book.away_spread)} (${formatOdds(book.away_dk_spread_american)})`],
        ["Home Spread", book.home_spread && `${plusLine(book.home_spread)} (${formatOdds(book.home_dk_spread_american)})`],
        ["Total", book.total],
        ["Away Moneyline", formatOdds(book.away_dk_moneyline_american)],
        ["Home Moneyline", formatOdds(book.home_dk_moneyline_american)],
        ["Total Over", formatOdds(book.dk_total_over_american)],
        ["Total Under", formatOdds(book.dk_total_under_american)],
      ]),
    };
  });

  return {
    league,
    displayName: displayLeague,
    games,
  };
}

export async function loadSoccer(meta, date) {
  const [predRes, bookRes] = await Promise.all([
    fetchCSV(`win/soccer/00_intake/predictions/normalized/${date}_${meta.slug}.csv`),
    fetchCSV(`win/soccer/00_intake/sportsbook/normalized/${date}_${meta.slug}.csv`),
  ]);

  const bookByGameId = mapByGameId(bookRes.rows);

  const games = predRes.rows.map(pred => {
    const book = bookByGameId[pred.game_id] || {};
    const gameTime = pred.match_time || book.match_time;

    return {
      league: meta.key,
      sport: "soccer",
      displayLeague: meta.display,
      sortTime: parseSortTime(gameTime),
      title: `${pred.away_team} @ ${pred.home_team}`,
      card: {
        date: formatDate(pred.match_date),
        time: formatTime(gameTime),
        away: pred.away_team,
        home: pred.home_team,
        moneyline: [
          book.dk_away_decimal && `${pred.away_team} ${decimalToAmerican(book.dk_away_decimal)}`,
          book.dk_draw_decimal && `Draw ${decimalToAmerican(book.dk_draw_decimal)}`,
          book.dk_home_decimal && `${pred.home_team} ${decimalToAmerican(book.dk_home_decimal)}`,
        ].filter(Boolean),
        spread: [],
        total: pred.expected_total_goals ? `Expected Total Goals ${formatOneDecimal(pred.expected_total_goals)}` : "",
        projection: [
          pred.away_xg && `${pred.away_team} xG ${formatOneDecimal(pred.away_xg)}`,
          pred.home_xg && `${pred.home_team} xG ${formatOneDecimal(pred.home_xg)}`,
        ].filter(Boolean).join(" · "),
      },
      modal: cleanModalRows([
        ["Date", formatDate(pred.match_date)],
        ["Time", formatTime(gameTime)],
        ["Home Win Probability", formatProb(pred.home_prob)],
        ["Draw Probability", formatProb(pred.draw_prob)],
        ["Away Win Probability", formatProb(pred.away_prob)],
        ["Home Expected Goals", formatOneDecimal(pred.home_xg)],
        ["Away Expected Goals", formatOneDecimal(pred.away_xg)],
        ["Expected Total Goals", formatOneDecimal(pred.expected_total_goals)],
        ["Home Moneyline", decimalToAmerican(book.dk_home_decimal)],
        ["Draw Moneyline", decimalToAmerican(book.dk_draw_decimal)],
        ["Away Moneyline", decimalToAmerican(book.dk_away_decimal)],
        ["Over 2.5 Goals", decimalToAmerican(book.dk_over25_decimal)],
        ["Under 2.5 Goals", decimalToAmerican(book.dk_under25_decimal)],
        ["Over 3.5 Goals", decimalToAmerican(book.dk_over35_decimal)],
        ["Under 3.5 Goals", decimalToAmerican(book.dk_under35_decimal)],
        ["BTTS Yes", book.btts_yes],
        ["BTTS No", book.btts_no],
      ]),
    };
  });

  return {
    league: meta.key,
    displayName: meta.display,
    games,
  };
}

export async function loadUFC(date) {
  const [predRes, bookRes] = await Promise.all([
    fetchCSV(`win/mma/ufc/00_intake/predictions/${date}_ufc_predictions.csv`),
    fetchCSV(`win/mma/ufc/00_intake/sportsbook/${date}_ufc_odds.csv`),
  ]);

  const bookByFight = mapUFCByFight(bookRes.rows);
  const displayLeague = displayLeagueConfig("UFC", "UFC");

  const games = predRes.rows.map(pred => {
    const book = bookByFight[ufcFightKey(pred)] || {};

    return {
      league: "UFC",
      sport: "mma",
      displayLeague,
      sortTime: 99998,
      title: `${pred.fighter_1} vs ${pred.fighter_2}`,
      card: {
        date: formatDate(pred.match_date),
        time: "",
        away: pred.fighter_2,
        home: pred.fighter_1,
        moneyline: [
          book.moneyline_fighter_1 && `${pred.fighter_1} ${formatOdds(book.moneyline_fighter_1)}`,
          book.moneyline_fighter_2 && `${pred.fighter_2} ${formatOdds(book.moneyline_fighter_2)}`,
        ].filter(Boolean),
        spread: [],
        total: "",
        projection: [
          pred.fighter_1_win_prob && `${pred.fighter_1} ${formatProb(pred.fighter_1_win_prob)}`,
          pred.fighter_2_win_prob && `${pred.fighter_2} ${formatProb(pred.fighter_2_win_prob)}`,
        ].filter(Boolean).join(" · "),
      },
      modal: cleanModalRows([
        ["Date", formatDate(pred.match_date)],
        ["Fighter 1", pred.fighter_1],
        ["Fighter 2", pred.fighter_2],
        ["Fighter 1 Win Probability", formatProb(pred.fighter_1_win_prob)],
        ["Fighter 2 Win Probability", formatProb(pred.fighter_2_win_prob)],
        ["Fighter 1 Moneyline", formatOdds(book.moneyline_fighter_1)],
        ["Fighter 2 Moneyline", formatOdds(book.moneyline_fighter_2)],
      ]),
    };
  });

  return {
    league: "UFC",
    displayName: displayLeague,
    games,
  };
}

export async function loadAllLeagues(dateStr) {
  const date = dateToUnderscore(dateStr);
  const config = window.REPO_CONFIG || {};
  const enabled = league => config[league] && config[league].enabled !== false;

  const tasks = [];

  if (enabled("MLB")) tasks.push(loadMLB(date));
  if (enabled("NHL")) tasks.push(loadNHL(date));

  BASKETBALL_ORDER.forEach(league => {
    if (enabled(league)) tasks.push(loadBasketball(league, date));
  });

  SOCCER_ORDER.forEach(meta => {
    if (enabled(meta.key)) tasks.push(loadSoccer(meta, date));
  });

  if (enabled("UFC")) tasks.push(loadUFC(date));

  const results = await Promise.all(tasks);

  return results.map(result => ({
    ...result,
    games: result.games.sort((a, b) => a.sortTime - b.sortTime),
  }));
}
