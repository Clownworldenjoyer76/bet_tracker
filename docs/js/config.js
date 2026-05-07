window.REPO_CONFIG = {

  leagues: ["NHL", "NBA", "WNBA", "NCAAM", "MLB", "UFC"],

  // ─── NHL ──────────────────────────────────────────────────────────────────
  NHL: {
    sport:        "hockey",
    league:       "NHL",
    displayName:  "NHL",
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
    leagueColumn: "league",
    selectFiles:  (date) => [
      `win/basketball/04_select/nba/daily_picks/${date}_nba_selected.csv`,
      `win/basketball/04_select/daily_slate/nba_selected.csv`,
    ],
    predFile:     (date) => `win/basketball/00_intake/predictions/basketball_NBA_${date}.csv`,
    bookFile:     (date) => `win/basketball/00_intake/sportsbook/basketball_NBA_${date}.csv`,
  },

  // ─── WNBA ─────────────────────────────────────────────────────────────────
  WNBA: {
    sport:        "basketball",
    league:       "WNBA",
    displayName:  "WNBA",
    leagueColumn: "league",
    selectFiles:  (date) => [
      `win/basketball/04_select/wnba/daily_picks/${date}_wnba_selected.csv`,
      `win/basketball/04_select/daily_slate/wnba_selected.csv`,
    ],
    predFile:     (date) => `win/basketball/00_intake/predictions/basketball_WNBA_${date}.csv`,
    bookFile:     (date) => `win/basketball/00_intake/sportsbook/basketball_WNBA_${date}.csv`,
  },

  // ─── NCAAM (replaces NCAAB) ───────────────────────────────────────────────
  NCAAM: {
    sport:        "basketball",
    league:       "NCAAM",
    displayName:  "NCAAM",
    leagueColumn: "league",
    selectFiles:  (date) => [
      `win/basketball/04_select/ncaam/daily_picks/${date}_ncaam_selected.csv`,
      `win/basketball/04_select/daily_slate/ncaam_selected.csv`,
    ],
    predFile:     (date) => `win/basketball/00_intake/predictions/basketball_NCAAM_${date}.csv`,
    bookFile:     (date) => `win/basketball/00_intake/sportsbook/basketball_NCAAM_${date}.csv`,
  },

  // ─── MLB ──────────────────────────────────────────────────────────────────
  MLB: {
    sport:        "baseball",
    league:       "MLB",
    displayName:  "MLB",
    isBaseball:   true,
    leagueColumn: "league",
    joinKey:      "game_id",
    selectFiles:  (date) => [`win/baseball/04_select/${date}_MLB.csv`],
    predFile:     (date) => `win/baseball/00_intake/predictions/${date}_MLB.csv`,
    bookFile:     (date) => `win/baseball/00_intake/sportsbook/${date}_MLB.csv`,
  },

  // ─── UFC ──────────────────────────────────────────────────────────────────
  UFC: {
    sport:        "mma",
    league:       "UFC",
    displayName:  "UFC",
    isUFC:        true,
    selectFiles:  (date) => [`win/mma/ufc/03_select/${date}_ufc_select.csv`],
  },

};

/*
  HOW TO ADD A LEAGUE
  ───────────────────
  1. Add name to `leagues` array.
  2. Add config block:
       displayName   — UI label
       leagueColumn  — CSV column name whose value = league  (e.g. "league")
         OR
       marketColumn  — CSV column name whose value = league  (e.g. "market")
       joinKey       — (optional) column to join select↔pred. Default: game_date|home_team|away_team
       isHockey      — true → uses goals/puck_line in modal
       isBaseball    — true → uses runs/run_line/pitchers in modal
       isUFC         — true → uses UFC fighter card/modal, event selector instead of date picker
       selectFiles   — fn(date) => string[]   date format: YYYY_MM_DD
                       Multiple paths = fallback list. The FIRST one that loads wins;
                       subsequent paths are ignored. Use this for "new path with old as
                       fallback" migrations.
       predFile      — fn(date) => string
       bookFile      — fn(date) => string
  3. Nothing else needs to change.

  ADVANCED OVERRIDES
  ──────────────────
  filterFn:     (row, dateFormatted, leagueName) => bool   — custom row filter
  buildBetText: (pick, gameRow) => string                  — custom bet label
*/
