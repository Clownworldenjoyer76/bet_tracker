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
  // The published consolidated CSV is the sole MLB runtime data source.
  const csv = await fetchCSV(`https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/frontend/data/mlb/games/${date}_mlb_games.csv`);

  const games = csv.rows.map(row => {
    const home = row.home_team || "";
    const away = row.away_team || "";
    const gameTime = row.game_time || "";
    const homePitcher = (row.home_pitcher || "").trim().replace(/^undecided\s+undecided$/i, "Undecided");
    const awayPitcher = (row.away_pitcher || "").trim().replace(/^undecided\s+undecided$/i, "Undecided");

    const homeProb = row.home_model_prob_moneyline || row.home_prob || "";
    const awayProb = row.away_model_prob_moneyline || row.away_prob || "";
    const homeRuns = row.model_home_runs || row.home_projected_runs || "";
    const awayRuns = row.model_away_runs || row.away_projected_runs || "";
    const totalRuns = row.model_total_runs || row.total_projected_runs || "";

    return {
      league: "MLB",
      sport: "baseball",
      displayLeague: displayLeagueConfig("MLB", "MLB"),
      sortTime: parseSortTime(gameTime),
      title: `${away} @ ${home}`,
      card: {
        date: formatDate(row.game_date),
        time: formatTime(gameTime),
        away,
        home,
        moneyline: [
          row.away_dk_moneyline_american && `${away} ${formatOdds(row.away_dk_moneyline_american)}`,
          row.home_dk_moneyline_american && `${home} ${formatOdds(row.home_dk_moneyline_american)}`,
        ].filter(Boolean),
        spread: [
          row.away_run_line && `${away} ${plusLine(row.away_run_line)} (${formatOdds(row.away_dk_run_line_american)})`,
          row.home_run_line && `${home} ${plusLine(row.home_run_line)} (${formatOdds(row.home_dk_run_line_american)})`,
        ].filter(Boolean),
        total: row.total
          ? `Total ${row.total} O ${formatOdds(row.dk_total_over_american)} / U ${formatOdds(row.dk_total_under_american)}`
          : "",
        projection: homeRuns && awayRuns && totalRuns
          ? `${away} ${formatOneDecimal(awayRuns)} \u00b7 ${home} ${formatOneDecimal(homeRuns)} \u00b7 Total ${formatOneDecimal(totalRuns)}`
          : "",
      },
      modal: cleanModalRows([
        ["Date", formatDate(row.game_date)],
        ["Time", formatTime(gameTime)],
        ["Venue", row.venue_name],
        ["Double Header", doubleHeaderText(row)],
        ["Day/Night", dayNightText(row.day_night)],
        ["Away Pitcher", [awayPitcher, handLabel(row.away_pitcher_hand)].filter(Boolean).join(" \u00b7 ")],
        ["Home Pitcher", [homePitcher, handLabel(row.home_pitcher_hand)].filter(Boolean).join(" \u00b7 ")],
        ["Away Win Probability", formatProb(awayProb)],
        ["Home Win Probability", formatProb(homeProb)],
        ["Away Projected Runs", formatOneDecimal(awayRuns)],
        ["Home Projected Runs", formatOneDecimal(homeRuns)],
        ["Projected Total Runs", formatOneDecimal(totalRuns)],
        ["Away Run Line", row.away_run_line && `${plusLine(row.away_run_line)} (${formatOdds(row.away_dk_run_line_american)})`],
        ["Home Run Line", row.home_run_line && `${plusLine(row.home_run_line)} (${formatOdds(row.home_dk_run_line_american)})`],
        ["Total", row.total],
        ["Total Over", formatOdds(row.dk_total_over_american)],
        ["Total Under", formatOdds(row.dk_total_under_american)],
        ["Away Moneyline", formatOdds(row.away_dk_moneyline_american)],
        ["Home Moneyline", formatOdds(row.home_dk_moneyline_american)],
        ...weatherRows(row),
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
  const [gamesRes, bookRes, predRes] = await Promise.all([
    fetchCSV(`win/hockey/nhl/00_intake/games/${date}_nhl_games.csv`),
    fetchFirstCSV([
      `win/hockey/nhl/00_intake/sportsbook/NHL_${date}.csv`,
      `win/hockey/nhl/00_intake/sportsbook/nhl_${date}.csv`,
    ]),
    fetchCSV(`win/hockey/nhl/00_intake/predictions/hockey_${date}.csv`),
  ]);

  const predictionByGameId = mapByGameId(predRes.rows);
  const bookByGameId = mapByGameId(bookRes.rows);
  const baseRows = gamesRes.rows.length ? gamesRes.rows : bookRes.rows;

  const games = baseRows.map(base => {
    const pred = predictionByGameId[base.game_id] || {};
    const book = bookByGameId[base.game_id] || {};
    const displayLeague = displayLeagueConfig("NHL", "NHL");

    const gameTime = base.game_time || book.game_time || pred.game_time;
    const awayTeam = base.away_team || book.away_team || pred.away_team;
    const homeTeam = base.home_team || book.home_team || pred.home_team;

    return {
      league: "NHL",
      sport: "hockey",
      displayLeague,
      sortTime: parseSortTime(gameTime),
      title: `${awayTeam} @ ${homeTeam}`,
      card: {
        date: formatDate(base.game_date || book.game_date || pred.game_date),
        time: formatTime(gameTime),
        away: awayTeam,
        home: homeTeam,
        moneyline: [
          book.away_dk_moneyline_american && `${awayTeam} ${formatOdds(book.away_dk_moneyline_american)}`,
          book.home_dk_moneyline_american && `${homeTeam} ${formatOdds(book.home_dk_moneyline_american)}`,
        ].filter(Boolean),
        spread: [
          book.away_puck_line && `${awayTeam} ${plusLine(book.away_puck_line)} (${formatOdds(book.away_dk_puck_line_american)})`,
          book.home_puck_line && `${homeTeam} ${plusLine(book.home_puck_line)} (${formatOdds(book.home_dk_puck_line_american)})`,
        ].filter(Boolean),
        total: book.total ? `Total ${book.total} O ${formatOdds(book.dk_total_over_american)} / U ${formatOdds(book.dk_total_under_american)}` : "",
        projection: pred.total_projected_goals
          ? `${awayTeam} ${formatOneDecimal(pred.away_projected_goals)} · ${homeTeam} ${formatOneDecimal(pred.home_projected_goals)} · Total ${formatOneDecimal(pred.total_projected_goals)}`
          : "",
      },
      modal: cleanModalRows([
        ["Date", formatDate(base.game_date || book.game_date || pred.game_date)],
        ["Time", formatTime(gameTime)],
        ["Away Win Probability", formatProb(pred.away_prob_moneyline || pred.away_prob)],
        ["Home Win Probability", formatProb(pred.home_prob_moneyline || pred.home_prob)],
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

export async function loadCFB(date) {
  const gameDate = String(date || "").replaceAll("_", "-");
  const season = gameDate.slice(0, 4);
  const displayLeague = displayLeagueConfig("CFB", "CFB");

  const scheduleRes = await fetchCSV(
    `win/football/cfb/00_intake/schedule/${season}_schedule.csv`
  );

  const scheduleRows = scheduleRes.rows.filter(
    row => String(row.game_date || "") === gameDate
  );

  if (!scheduleRows.length) {
    return {
      league: "CFB",
      displayName: displayLeague,
      games: [],
    };
  }

  const weeks = [
    ...new Set(
      scheduleRows
        .map(row => String(row.week || "").trim())
        .filter(Boolean)
    ),
  ];

  const weeklyResults = await Promise.all(
    weeks.map(week =>
      fetchCSV(
        `win/football/cfb/00_intake/schedule/weekly/week_${week}_CFB_weekly_schedule.csv`
      )
    )
  );

  const weeklyRows = weeklyResults.flatMap(result => result.rows);
  const weeklyByGameId = mapByGameId(weeklyRows);

  const games = scheduleRows.map(base => {
    const book = weeklyByGameId[String(base.game_id)] || {};
    const gameTime = book.game_time || base.game_time;
    const awayTeam = book.away_team || base.away_team;
    const homeTeam = book.home_team || base.home_team;

    return {
      league: "CFB",
      sport: "football",
      displayLeague,
      sortTime: parseSortTime(gameTime),
      title: `${awayTeam} @ ${homeTeam}`,
      card: {
        date: formatDate(book.game_date || base.game_date),
        time: formatTime(gameTime),
        away: awayTeam,
        home: homeTeam,
        moneyline: [
          book.away_moneyline_american &&
            `${awayTeam} ${formatOdds(book.away_moneyline_american)}`,
          book.home_moneyline_american &&
            `${homeTeam} ${formatOdds(book.home_moneyline_american)}`,
        ].filter(Boolean),
        spread: [
          book.away_spread &&
            `${awayTeam} ${plusLine(book.away_spread)} (${formatOdds(book.away_spread_american)})`,
          book.home_spread &&
            `${homeTeam} ${plusLine(book.home_spread)} (${formatOdds(book.home_spread_american)})`,
        ].filter(Boolean),
        total: book.total
          ? `Total ${book.total} O ${formatOdds(book.over_american)} / U ${formatOdds(book.under_american)}`
          : "",
        projection: "",
      },
      modal: cleanModalRows([
        ["Date", formatDate(book.game_date || base.game_date)],
        ["Time", formatTime(gameTime)],
        ["Week", book.week || base.week],
        ["Venue", book.stadium || base.stadium],
        ["Roof", book.roof || base.roof],
        ["Surface", book.surface || base.surface],
        ["Bookmaker", book.bookmaker],
        ["Away Moneyline", formatOdds(book.away_moneyline_american)],
        ["Home Moneyline", formatOdds(book.home_moneyline_american)],
        [
          "Away Spread",
          book.away_spread &&
            `${plusLine(book.away_spread)} (${formatOdds(book.away_spread_american)})`,
        ],
        [
          "Home Spread",
          book.home_spread &&
            `${plusLine(book.home_spread)} (${formatOdds(book.home_spread_american)})`,
        ],
        ["Total", book.total],
        ["Total Over", formatOdds(book.over_american)],
        ["Total Under", formatOdds(book.under_american)],
      ]),
    };
  });

  return {
    league: "CFB",
    displayName: displayLeague,
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
  const csv = await fetchCSV(`https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/frontend/data/ufc/pred_sb_sel/${date}_pred_sb_sel_ufc.csv`);
  const displayLeague = displayLeagueConfig("UFC", "UFC");
  const games = csv.rows.map(row => ({
    league: "UFC",
    sport: "mma",
    displayLeague,
    sortTime: 99998,
    title: `${row.fighter_1} vs ${row.fighter_2}`,
    card: {
      date: formatDate(row.match_date),
      time: "",
      away: row.fighter_2,
      home: row.fighter_1,
      moneyline: [
        row.moneyline_f1 && `${row.fighter_1} ${formatOdds(row.moneyline_f1)}`,
        row.moneyline_f2 && `${row.fighter_2} ${formatOdds(row.moneyline_f2)}`,
      ].filter(Boolean),
      spread: [],
      total: "",
      projection: [
        row.model_prob_f1 && `${row.fighter_1} ${formatProb(row.model_prob_f1)}`,
        row.model_prob_f2 && `${row.fighter_2} ${formatProb(row.model_prob_f2)}`,
      ].filter(Boolean).join(" " + String.fromCharCode(0xb7) + " "),
    },
    modal: cleanModalRows([
      ["Date", formatDate(row.match_date)],
      ["Fighter 1", row.fighter_1],
      ["Fighter 2", row.fighter_2],
      ["Fighter 1 Win Probability", formatProb(row.model_prob_f1)],
      ["Fighter 2 Win Probability", formatProb(row.model_prob_f2)],
      ["Fighter 1 Moneyline", formatOdds(row.moneyline_f1)],
      ["Fighter 2 Moneyline", formatOdds(row.moneyline_f2)],
    ]),
  }));
  return { league: "UFC", displayName: displayLeague, games };
}

export async function loadAllLeagues(dateStr) {
  const date = dateToUnderscore(dateStr);
  const config = window.REPO_CONFIG || {};
  const enabled = league => {
    if (!config[league]) return false;

    const fallback = config[league].enabled !== false;

    if (typeof window.isPageLeagueEnabled === "function") {
      return window.isPageLeagueEnabled("gamesToday", league, fallback);
    }

    const pageConfig = window.PAGE_LEAGUES?.gamesToday;

    if (pageConfig && Object.prototype.hasOwnProperty.call(pageConfig, league)) {
      return pageConfig[league] !== false;
    }

    return fallback;
  };

  const tasks = [];

  if (enabled("MLB")) tasks.push(loadMLB(date));
  if (enabled("NHL")) tasks.push(loadNHL(date));
  if (enabled("CFB")) tasks.push(loadCFB(date));

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