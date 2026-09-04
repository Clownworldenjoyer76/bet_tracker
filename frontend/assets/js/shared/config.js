// ─── Page-specific league visibility ──────────────────────────────────────────
// These switches control ONLY the Games Today and Live Scores pages.
// Set a league to false during its offseason to hide it completely and prevent
// that page from loading/fetching it. Other pages continue to use REPO_CONFIG.
window.PAGE_LEAGUES = {
  gamesToday: {
    MLB:        true,
    NHL:        false,
    CFB:        true,
    NBA:        false,
    WNBA:       true,
    NCAAM:      false,
    EPL:        true,
    MLS:        true,
    LIGUE1:     true,
    LALIGA:     true,
    SERIEA:     true,
    BUNDESLIGA: true,
    UFC:        true,
  },

  liveScores: {
    MLB:        true,
    NHL:        false,
    CFB:        true,
    NBA:        false,
    WNBA:       true,
    NCAAM:      false,
    EPL:        true,
    MLS:        true,
    LIGUE1:     true,
    LALIGA:     true,
    SERIEA:     true,
    BUNDESLIGA: true,
    UFC:        false,
  },
};

window.isPageLeagueEnabled = function(pageKey, leagueKey, fallbackValue = true) {
  const pageConfig = window.PAGE_LEAGUES?.[pageKey];

  if (!pageConfig || !Object.prototype.hasOwnProperty.call(pageConfig, leagueKey)) {
    return fallbackValue;
  }

  return pageConfig[leagueKey] !== false;
};

// ─── Soccer shared base ───────────────────────────────────────────────────────
// One CSV at win/soccer/04_select/{date}_soccer_bets.csv contains all 6 leagues.
// Each league entry below extends this base and only sets its own league/displayName.
const SOCCER_BASE = {
  sport:        "soccer",
  isSoccer:     true,
  leagueColumn: "league",
  joinKey:      "game_id",
  selectFiles:  (date) => [`win/soccer/04_select/${date}_soccer_bets.csv`],
  // Soccer CSV uses different column names than the basketball/baseball/hockey schema.
  // Remap into the canonical shape so the existing renderer/filter code "just works".
  normalizeRow: (r) => ({
    ...r,
    game_date:   r.match_date,
    game_time:   r.match_time,
    bet_side:    r.side,
    market_type: r.market,
  }),
  // Soccer markets aren't spread/total/moneyline. Format them appropriately.
  // Odds are decimal in this file (e.g. 1.68), not American.
  buildBetText: (p, r) => {
    const market = (p.market || p.market_type || "").toLowerCase();
    const side   = (p.side   || p.bet_side    || "").toLowerCase();
    const odds   = p.odds || "";

    const sideLabel = (() => {
      if (side === "home")  return r.home_team || "Home";
      if (side === "away")  return r.away_team || "Away";
      if (side === "draw")  return "Draw";
      if (side === "yes")   return "Yes";
      if (side === "no")    return "No";
      if (side === "over")  return "Over";
      if (side === "under") return "Under";
      return side;
    })();

    const marketLabel = (() => {
      if (market === "match_odds")     return "1X2";
      if (market === "btts")           return "BTTS";
      if (market === "double_chance")  return "DC";
      if (market === "draw_no_bet")    return "DNB";
      if (market === "over_under" ||
          market === "total" ||
          market === "goals")          return "Total";
      // total25 → "Total 2.5"; total35 → "Total 3.5"; total105 → "Total 10.5"
      const totalMatch = market.match(/^total(\d{2,3})$/);
      if (totalMatch) return `Total ${parseInt(totalMatch[1], 10) / 10}`;
      // Unknown market — show it cleanly rather than crashing.
      return market.toUpperCase().replace(/_/g, " ");
    })();

    return `${marketLabel}: ${sideLabel} (${odds})`;
  },
};


// ─── Football week mapping ────────────────────────────────────────────────────
// Only verified date ranges belong here.
// CFB Week 1 verified from the existing 2026 week_1 file.
// NFL remains disabled until its selected files exist.

const FOOTBALL_WEEK_RANGES = {
  CFB: [
    {
      season: 2026,
      week: 1,
      start: "2026_08_29",
      end:   "2026_09_06",
    },
  ],

  NFL: [],
};

function footballWeekForDate(league, date) {
  const ranges = FOOTBALL_WEEK_RANGES[league] || [];

  const match = ranges.find(r =>
    date >= r.start &&
    date <= r.end
  );

  return match ? match.week : null;
}

function cleanFootballOdds(value) {
  if (value === null || value === undefined || value === "") return "";

  const n = parseFloat(value);
  if (Number.isNaN(n)) return String(value);

  return n > 0 ? `+${n}` : String(n);
}

function cleanFootballLine(value) {
  if (value === null || value === undefined || value === "") return "";

  const n = parseFloat(value);
  if (Number.isNaN(n)) return String(value);

  return n > 0 ? `+${n}` : String(n);
}

function buildFootballBetText(p, r) {
  const market = (p.market_type || "").toLowerCase();
  const side   = (p.bet_side || "").toLowerCase();

  const odds = cleanFootballOdds(
    p.bet_odds_american ||
    p.dk_odds_american ||
    ""
  );

  const oddsText = odds ? ` (${odds})` : "";

  let team = side;

  if (side === "home") {
    team = r.home_team || "Home";
  }

  if (side === "away") {
    team = r.away_team || "Away";
  }

  if (market === "moneyline") {
    return `ML · ${team}${oddsText}`;
  }

  if (market === "spread") {
    const line = cleanFootballLine(p.bet_line || p.line || "");
    return `Spread · ${team} ${line}${oddsText}`.trim();
  }

  if (market === "total") {
    const line = cleanFootballLine(p.bet_line || p.line || "");
    const label =
      side === "over" ? "Over" :
      side === "under" ? "Under" :
      side;

    return `Total · ${label} ${line}${oddsText}`.trim();
  }

  return `${market || "Pick"} · ${team}${oddsText}`;
}

function expandFootballSelections(row) {
  const picks = [];

  const addPick = (
    selected,
    market,
    selection,
    line,
    odds,
    modelProb
  ) => {
    if (String(selected || "").trim() !== "1") return;

    const side = String(selection || "").trim().toLowerCase();
    if (!side) return;

    picks.push({
      ...row,

      game_time:
        row.game_time ||
        row.edt_time ||
        "",

      market_type: market,
      bet_side: side,

      line: line || "",
      bet_line: line || "",

      dk_odds_american: odds || "",
      bet_odds_american: odds || "",

      model_prob: modelProb || "",
    });
  };

  addPick(
    row.ml_selected,
    "moneyline",
    row.ml_selection,
    "",
    row.ml_odds_american,
    row.ml_model_probability
  );

  addPick(
    row.spread_selected,
    "spread",
    row.spread_selection,
    row.spread_line,
    row.spread_odds_american,
    ""
  );

  addPick(
    row.total_selected,
    "total",
    row.total_selection,
    row.total_line,
    row.total_odds_american,
    row.total_model_probability
  );

  return picks;
}
window.REPO_CONFIG = {

  leagues: [
    "NHL", "NBA", "WNBA", "NCAAM", "MLB", "MLB_LINEUPS",
    "EPL", "MLS", "LIGUE1", "LALIGA", "SERIEA", "BUNDESLIGA",
    "UFC", "CFB", "NFL",
  ],

  // ─── NHL ──────────────────────────────────────────────────────────────────
  NHL: {
    sport:        "hockey",
    league:       "NHL",
    displayName:  "NHL",
    enabled: true,
    isHockey:     true,
    leagueColumn: "league",
    joinKey:      "game_id",
    statDecimals: 4,
    selectFiles:  (date) => [`win/hockey/nhl/04_select/${date}_NHL.csv`],
    predFile:     (date) => `win/hockey/nhl/00_intake/predictions/hockey_${date}.csv`,
    bookFile:     (date) => [
      `win/hockey/nhl/00_intake/sportsbook/NHL_${date}.csv`,
      `win/hockey/nhl/00_intake/sportsbook/nhl_${date}.csv`,
    ],

    buildBetText: (p, r) => {
      const market = (p.market_type || "").toLowerCase();
      const side   = (p.bet_side || "").toLowerCase();

      const cleanOdds = (odds) => {
        if (odds === null || odds === undefined || odds === "") return "";
        const n = parseFloat(odds);
        if (isNaN(n)) return String(odds).trim();
        return n > 0 ? "+" + n : String(n);
      };

      const fmtPuckLine = (line) => {
        const n = parseFloat(line);
        if (isNaN(n)) return line || "";
        return n > 0 ? "+" + n : String(n);
      };

      const fmtTotalLine = (line) => {
        const n = parseFloat(line);
        if (isNaN(n)) return line || "";
        return String(n);
      };

      const odds = cleanOdds(p.dk_odds_american || p.bet_odds_american || p.take_odds || "");
      const oddsText = odds ? ` (${odds})` : "";

      let label = "";
      if (side === "home")  label = r.home_team || "Home";
      if (side === "away")  label = r.away_team || "Away";
      if (side === "over")  label = "Over";
      if (side === "under") label = "Under";

      if (market === "puck_line") {
        return `${label} ${fmtPuckLine(p.line || "")}${oddsText}`.trim();
      }

      if (market === "total") {
        return `${label} ${fmtTotalLine(p.line || r.total || "")}${oddsText}`.trim();
      }

      if (market === "moneyline") {
        return `${label}${oddsText}`.trim();
      }

      return `${label || side} ${p.line || ""}${oddsText}`.trim();
    },
  },

  // ─── NBA ──────────────────────────────────────────────────────────────────
  NBA: {
    sport:        "basketball",
    league:       "NBA",
    displayName:  "NBA",
    enabled: true,
    leagueColumn: "league",
    joinKey:      "game_id",
    selectFiles:  (date) => [
      `win/basketball/04_select/nba/daily_picks/${date}_nba_selected.csv`,
      `win/basketball/04_select/daily_slate/nba_selected.csv`,
    ],
    predFile:     (date) => `win/basketball/00_intake/predictions/basketball_NBA_${date}.csv`,
    bookFile:     (date) => `win/basketball/00_intake/sportsbook/sportsbook_cleaned/nba/${date}_NBA_odds.csv`,
  },

  // ─── WNBA ─────────────────────────────────────────────────────────────────

  WNBA: {
    sport:        "basketball",
    league:       "WNBA",
    displayName:  "WNBA",
    enabled: true,
    leagueColumn: "league",
    joinKey:      "game_id",
    selectFiles:  (date) => [
      `win/basketball/04_select/wnba/daily_picks/${date}_wnba_selected.csv`,
      `win/basketball/04_select/daily_slate/wnba_selected.csv`,
    ],
    predFile:     (date) => `win/basketball/00_intake/predictions/basketball_WNBA_${date}.csv`,
    bookFile:     (date) => `win/basketball/00_intake/sportsbook/sportsbook_cleaned/wnba/${date}_WNBA_odds.csv`,

    buildBetText: (p, r) => {
      const market = (p.market_type || "").toLowerCase();
      const side   = (p.bet_side || "").toLowerCase();

      const fmtLine = (line) => {
        const n = parseFloat(line);
        if (isNaN(n)) return line || "";
        return n > 0 ? "+" + n : String(n);
      };

      let label = "";
      if (side === "home") label = r.home_team || "Home";
      if (side === "away") label = r.away_team || "Away";
      if (side === "over") label = "Over";
      if (side === "under") label = "Under";

      if (market === "spread") {
        const line = side === "home"
          ? (p.line || r.home_spread || "")
          : (p.line || r.away_spread || "");

        const odds = side === "home"
          ? (r.home_dk_spread_american || p.dk_odds_american || p.take_odds || "")
          : (r.away_dk_spread_american || p.dk_odds_american || p.take_odds || "");

        return `${label} ${fmtLine(line)} (${odds})`.trim();
      }

      if (market === "total") {
        const odds = side === "over"
          ? (r.dk_total_over_american || p.dk_odds_american || p.take_odds || "")
          : (r.dk_total_under_american || p.dk_odds_american || p.take_odds || "");

        return `${label} ${p.line || r.total || ""} (${odds})`.trim();
      }

      if (market === "moneyline") {
        const odds = side === "home"
          ? (r.home_dk_moneyline_american || p.dk_odds_american || p.take_odds || "")
          : (r.away_dk_moneyline_american || p.dk_odds_american || p.take_odds || "");

        return `${label} (${odds})`.trim();
      }

      return `${label || side} ${p.line || ""} ${p.dk_odds_american || p.take_odds || ""}`.trim();
    },
  },
  // ─── NCAAM (replaces NCAAB) ───────────────────────────────────────────────
  NCAAM: {
    sport:        "basketball",
    league:       "NCAAM",
    displayName:  "NCAAM",
    enabled: false,
    leagueColumn: "league",
    joinKey:      "game_id",
    selectFiles:  (date) => [
      `win/basketball/04_select/ncaam/daily_picks/${date}_ncaam_selected.csv`,
      `win/basketball/04_select/daily_slate/ncaam_selected.csv`,
    ],
    predFile:     (date) => `win/basketball/00_intake/predictions/basketball_NCAAM_${date}.csv`,
    bookFile:     (date) => `win/basketball/00_intake/sportsbook/sportsbook_cleaned/ncaam/${date}_NCAAM_odds.csv`,
  },

  // ─── MLB ──────────────────────────────────────────────────────────────────
  MLB: {
    sport:        "baseball",
    league:       "MLB",
    displayName:  "MLB",
    enabled: true,
    isBaseball:   true,
    leagueColumn: "league",
    joinKey:      "game_id",
    selectFiles:  (date) => [`win/baseball/mlb/04_select/morning/${date}_MLB.csv`],
    predFile:     (date) => [
      `win/baseball/mlb/00_intake/predictions/pred_with_game_id/${date}_MLB.csv`,
      `win/baseball/mlb/00_intake/predictions/${date}_MLB.csv`,
    ],
    bookFile:     (date) => [
      `win/baseball/mlb/00_intake/sportsbook/${date}_MLB.csv`,
    ],
  },

  // ─── MLB (With Lineups) ───────────────────────────────────────────────────
  // Second MLB feed, different selection criteria. Uses filterFn instead of
  // leagueColumn because filterRows matches the CSV `league` value against the
  // CONFIG KEY ("MLB_LINEUPS"), which would never equal "MLB". This file is
  // MLB-only, so accepting every row is safe.
  MLB_LINEUPS: {
    sport:        "baseball",
    league:       "MLB",
    displayName:  "MLB · With Lineups",
    enabled:      true,
    isBaseball:   true,
    filterFn:     () => true,
    joinKey:      "game_id",
    selectFiles:  (date) => [`win/baseball/mlb/04_select/${date}_MLB.csv`],
    predFile:     (date) => [
      `win/baseball/mlb/00_intake/predictions/pred_with_game_id/${date}_MLB.csv`,
      `win/baseball/mlb/00_intake/predictions/${date}_MLB.csv`,
    ],
    bookFile:     (date) => [
      `win/baseball/mlb/00_intake/sportsbook/${date}_MLB.csv`,
    ],
  },

  // ─── Soccer (6 leagues, one shared file) ──────────────────────────────────
  // All 6 entries inherit from SOCCER_BASE and only override what they need.
  // The CSV's `league` column values must match the `league` field below
  // (case-insensitive — the row matcher uppercases both sides).
  EPL:        Object.assign({}, SOCCER_BASE, { league: "EPL",        displayName: "EPL",        enabled: true }),
  MLS:        Object.assign({}, SOCCER_BASE, { league: "MLS",        displayName: "MLS",        enabled: true }),
  LIGUE1:     Object.assign({}, SOCCER_BASE, { league: "LIGUE1",     displayName: "Ligue 1",    enabled: true }),
  LALIGA:     Object.assign({}, SOCCER_BASE, { league: "LALIGA",     displayName: "La Liga",    enabled: true }),
  SERIEA:     Object.assign({}, SOCCER_BASE, { league: "SERIEA",     displayName: "Serie A",    enabled: true }),
  BUNDESLIGA: Object.assign({}, SOCCER_BASE, { league: "BUNDESLIGA", displayName: "Bundesliga", enabled: true }),

  // ─── CFB ──────────────────────────────────────────────────────────────────
  CFB: {
    sport:        "football",
    league:       "CFB",
    displayName:  "CFB",
    enabled:      true,
    isFootball:   true,
    filterFn:     () => true,
    joinKey:      "game_id",

    selectFiles: (date) => {
      const week = footballWeekForDate("CFB", date);

      return week
        ? [`win/football/cfb/03_picks/selected/week_${week}_CFB_select_picks.csv`]
        : [];
    },

    expandRows:   expandFootballSelections,
    buildBetText: buildFootballBetText,
  },

  // ─── NFL ──────────────────────────────────────────────────────────────────
  // Disabled until the selected-picks pipeline files exist.
  NFL: {
    sport:        "football",
    league:       "NFL",
    displayName:  "NFL",
    enabled:      false,
    isFootball:   true,
    filterFn:     () => true,
    joinKey:      "game_id",

    selectFiles: (date) => {
      const week = footballWeekForDate("NFL", date);

      return week
        ? [`win/football/nfl/03_picks/selected/week_${week}_NFL_select_picks.csv`]
        : [];
    },

    expandRows:   expandFootballSelections,
    buildBetText: buildFootballBetText,
  },

  // ─── UFC ──────────────────────────────────────────────────────────────────
  UFC: {
    sport:        "mma",
    league:       "UFC",
    displayName:  "UFC",
    enabled: true,
    isUFC:        true,
    selectFiles:  (date) => [`win/mma/ufc/03_select/${date}_ufc_select.csv`],
  },

};

/*
  HOW TO ADD A LEAGUE
  ───────────────────
  1. Add name to `leagues` array.
  2. Add config block:
       displayName   — UI label (shown in column header + filter pill)
       leagueColumn  — CSV column name whose value = league  (e.g. "league")
         OR
       marketColumn  — CSV column name whose value = league  (e.g. "market")
       joinKey       — (optional) column to join select↔pred. Default: game_date|home_team|away_team
       isHockey      — true → uses goals/puck_line in modal
       isBaseball    — true → uses runs/run_line/pitchers in modal
       isUFC         — true → uses UFC fighter card/modal, event selector instead of date picker
       isSoccer      — true → uses slim soccer modal
       selectFiles   — fn(date) => string[]   date format: YYYY_MM_DD
                       Multiple paths = fallback list. The FIRST one that loads wins;
                       subsequent paths are ignored.
       predFile      — (optional) fn(date) => string OR string[]
       bookFile      — (optional) fn(date) => string OR string[]
       enabled       — (optional) set to `false` to hide this league from the page
                       without deleting its config block. Useful at season end.
  3. Nothing else needs to change.

  HOW TO DISABLE A LEAGUE
  ───────────────────────
  Either remove its name from the `leagues` array, OR set `enabled: false`
  on its config block. Setting `enabled: false` is preferred because it
  preserves the league config for next season.

  ADVANCED OVERRIDES
  ──────────────────
  filterFn:      (row, dateFormatted, leagueName) => bool — custom row filter
  buildBetText:  (pick, gameRow) => string                — custom bet label
  normalizeRow:  (row) => row                             — column rename / shape fix
                                                            applied right after fetch,
                                                            before any other logic
*/
