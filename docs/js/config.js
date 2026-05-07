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

window.REPO_CONFIG = {

  leagues: [
    "NHL", "NBA", "WNBA", "NCAAM", "MLB",
    "EPL", "MLS", "LIGUE1", "LALIGA", "SERIEA", "BUNDESLIGA",
    "UFC",
  ],

  // ─── NHL ──────────────────────────────────────────────────────────────────
  NHL: {
    sport:        "hockey",
    league:       "NHL",
    displayName:  "NHL",
    enabled: true,
    isHockey:     true,
    leagueColumn: "league",
    selectFiles:  (date) => [`win/hockey/04_select/${date}_NHL.csv`],
    predFile:     (date) => `win/hockey/00_intake/predictions/hockey_${date}.csv`,
    bookFile:     (date) => `win/hockey/00_intake/sportsbook/hockey_${date}.csv`,
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
    selectFiles:  (date) => [`win/baseball/04_select/${date}_MLB.csv`],
    predFile:     (date) => `win/baseball/00_intake/predictions//pred_with_game_id/${date}_MLB.csv`,
    bookFile:     (date) => `win/baseball/00_intake/sportsbook/${date}_MLB.csv`,
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
       predFile      — (optional) fn(date) => string
       bookFile      — (optional) fn(date) => string
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
