// Shared data layer for the Injury Tracker page.
// Ported from legacy assets/js/pages/injury_tracker.js (data loading, matching, filtering, impact grouping),
// with AbortSignal support added to every fetch.

export const MID = String.fromCharCode(0xb7);
export const DASH = String.fromCharCode(0x2014);

export type LeagueCfg = {
  key: string;
  label: string;
  group: string;
  sport: string;
  league: string;
};

export type Pick = {
  league: string;
  leagueLabel: string;
  home_team: string;
  away_team: string;
  game_time: string;
  market_type: string;
  bet_side: string;
  line: string;
  text: string;
};

export type Injury = {
  league: string;
  leagueLabel: string;
  group: string;
  player: string;
  position: string;
  team: string;
  status: string;
  injury: string;
  verifiedPickedTeam?: boolean;
};

export type ImpactGroup = {
  league: string;
  leagueLabel: string;
  home_team: string;
  away_team: string;
  game_time: string;
  picks: Pick[];
  homeInjuries: Injury[];
  awayInjuries: Injury[];
};

export type InjuryData = {
  todayPicks: Pick[];
  allInjuries: Injury[];
  pickedTeamsResolved: number;
  pickedTeamInjuriesAdded: number;
  dateDash: string;
};

export type StatusMode = "impact" | "out" | "questionable" | "dtd" | "all";

export const RAW_DOCS = "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/docs/";

export const PAGE_SIZE = 50;

/*
  These are intentionally always available on this page.
  They are not tied to the offseason toggles used by Games Today / Live Scores / Final Scores.
*/
export const LEAGUES: LeagueCfg[] = [
  { key: "NHL", label: "NHL", group: "hockey", sport: "hockey", league: "nhl" },
  { key: "MLB", label: "MLB", group: "baseball", sport: "baseball", league: "mlb" },

  { key: "NBA", label: "NBA", group: "basketball", sport: "basketball", league: "nba" },
  { key: "NCAAM", label: "College Basketball", group: "basketball", sport: "basketball", league: "mens-college-basketball" },
  { key: "WNBA", label: "WNBA", group: "basketball", sport: "basketball", league: "wnba" },

  { key: "MLS", label: "MLS", group: "soccer", sport: "soccer", league: "usa.1" },
  { key: "EPL", label: "EPL", group: "soccer", sport: "soccer", league: "eng.1" },
  { key: "LALIGA", label: "La Liga", group: "soccer", sport: "soccer", league: "esp.1" },
  { key: "LIGUE1", label: "Ligue 1", group: "soccer", sport: "soccer", league: "fra.1" },
  { key: "SERIEA", label: "Serie A", group: "soccer", sport: "soccer", league: "ita.1" },
  { key: "BUNDESLIGA", label: "Bundesliga", group: "soccer", sport: "soccer", league: "ger.1" },

  { key: "UFC", label: "UFC", group: "mma", sport: "mma", league: "ufc" },

  { key: "NFL", label: "NFL", group: "football", sport: "football", league: "nfl" },
  { key: "CFB", label: "College Football", group: "football", sport: "football", league: "college-football" },
  { key: "CFL", label: "CFL", group: "football", sport: "football", league: "cfl" },
];

export const GROUPS: Record<string, string[]> = {
  football: ["NFL", "CFB", "CFL"],
  basketball: ["NBA", "NCAAM", "WNBA"],
  soccer: ["MLS", "EPL", "LALIGA", "LIGUE1", "SERIEA", "BUNDESLIGA"],
};

const leagueByKey: Record<string, LeagueCfg> = {};
LEAGUES.forEach((cfg) => {
  leagueByKey[cfg.key] = cfg;
});

// ---------------------------------------------------------------- utilities

const COMBINING_MARKS = new RegExp("[" + String.fromCharCode(0x300) + "-" + String.fromCharCode(0x36f) + "]", "g");
const APOSTROPHES = new RegExp("['" + String.fromCharCode(0x2019) + "`]", "g");
const BOM = new RegExp("^" + String.fromCharCode(0xfeff));

function padTwo(n: number): string {
  return n < 10 ? "0" + n : String(n);
}

function todayUnderscore(): string {
  const d = new Date();
  return d.getFullYear() + "_" + padTwo(d.getMonth() + 1) + "_" + padTwo(d.getDate());
}

export function todayDash(): string {
  return todayUnderscore().replace(/_/g, "-");
}

function normalizeDate(value: unknown): string {
  return String(value || "").trim().replace(/-/g, "_");
}

function normalizeLeague(value: unknown): string {
  const league = String(value || "").trim().toUpperCase();

  if (league === "NCAAB") return "NCAAM";
  if (league === "COLLEGE-BASKETBALL") return "NCAAM";
  if (league === "COLLEGE BASKETBALL") return "NCAAM";
  if (league === "COLLEGE FOOTBALL") return "CFB";

  return league;
}

/*
  Match ESPN team names against pipeline team names.
  Parenthetical disambiguators are removed, accents are stripped.
*/
export function normalizeTeam(value: unknown): string {
  let text = String(value || "");

  if (typeof text.normalize === "function") {
    text = text.normalize("NFD").replace(COMBINING_MARKS, "");
  }

  return text
    .toLowerCase()
    .replace(/\([^)]*\)/g, " ")
    .replace(/&/g, "and")
    .replace(APOSTROPHES, "")
    .replace(/[^a-z0-9]+/g, "");
}

export function sameTeam(a: unknown, b: unknown): boolean {
  const left = normalizeTeam(a);
  const right = normalizeTeam(b);

  if (!left || !right) return false;
  if (left === right) return true;

  const minLen = Math.min(left.length, right.length);

  if (minLen >= 7 && (left.indexOf(right) !== -1 || right.indexOf(left) !== -1)) {
    return true;
  }

  return false;
}

export function sourceLabel(key: string): string {
  return leagueByKey[key] ? leagueByKey[key].label : key;
}

export function sourceGroup(key: string): string {
  return leagueByKey[key] ? leagueByKey[key].group : "";
}

// ---------------------------------------------------------------- CSV

function cleanCSVCell(value: unknown): string {
  let s = String(value === null || value === undefined ? "" : value).trim();

  if (s.length >= 2 && s.charAt(0) === '"' && s.charAt(s.length - 1) === '"') {
    s = s.slice(1, -1);
  }

  return s.replace(/""/g, '"').trim();
}

function parseCSVLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line.charAt(i);

    if (ch === '"') {
      if (inQuotes && line.charAt(i + 1) === '"') {
        cur += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (ch === "," && !inQuotes) {
      out.push(cur);
      cur = "";
      continue;
    }

    cur += ch;
  }

  out.push(cur);

  return out;
}

function parseCSV(text: unknown): Record<string, string>[] {
  const raw = String(text || "").replace(BOM, "").trim();

  if (!raw) return [];

  const lines = raw.split(/\r?\n/).filter((line) => line.trim() !== "");

  if (lines.length < 2) return [];

  const headers = parseCSVLine(lines[0]).map(cleanCSVCell);

  return lines.slice(1).map((line) => {
    const vals = parseCSVLine(line).map(cleanCSVCell);
    const obj: Record<string, string> = {};

    headers.forEach((header, i) => {
      obj[header] = vals[i] === undefined ? "" : vals[i];
    });

    return obj;
  });
}

type CsvResult = { ok: boolean; rows: Record<string, string>[]; source?: string };

async function fetchCSV(path: string, signal?: AbortSignal): Promise<CsvResult> {
  if (!path) return { ok: false, rows: [] };

  const url = path.indexOf("win/") === 0 ? RAW_DOCS + path : path;

  try {
    const response = await fetch(url, { cache: "no-store", signal });

    if (!response.ok) return { ok: false, rows: [] };

    return { ok: true, rows: parseCSV(await response.text()), source: path };
  } catch (error) {
    return { ok: false, rows: [] };
  }
}

async function fetchFirstCSV(paths: unknown, signal?: AbortSignal): Promise<CsvResult> {
  const list: string[] = Array.isArray(paths) ? paths.filter(Boolean) : [];

  for (let i = 0; i < list.length; i++) {
    if (signal?.aborted) break;

    const result = await fetchCSV(list[i], signal);

    if (result.ok) return result;
  }

  return { ok: false, rows: [] };
}

function resolveSelectPaths(cfg: any, date: string): string[] {
  if (!cfg || !cfg.selectFiles) return [];

  try {
    const value = typeof cfg.selectFiles === "function" ? cfg.selectFiles(date) : cfg.selectFiles;

    if (Array.isArray(value)) return value.filter(Boolean);

    return value ? [value] : [];
  } catch (error) {
    return [];
  }
}

function rowMatchesLeague(row: any, cfg: any, leagueKey: string): boolean {
  if (!cfg) return false;

  if (cfg.leagueColumn) {
    return normalizeLeague(row[cfg.leagueColumn]) === leagueKey;
  }

  if (cfg.marketColumn) {
    return normalizeLeague(row[cfg.marketColumn]) === leagueKey;
  }

  const rowLeague = normalizeLeague(row.league);

  return !rowLeague || rowLeague === leagueKey;
}

// ---------------------------------------------------------------- today's picks

function genericPickText(row: any): string {
  const market = String(row.market_type || row.market || "Pick").replace(/_/g, " ").toUpperCase();

  const side = String(row.bet_side || row.side || "").toLowerCase();

  let label = side;

  if (side === "home") label = row.home_team || "Home";
  if (side === "away") label = row.away_team || "Away";
  if (side === "over") label = "Over";
  if (side === "under") label = "Under";
  if (side === "draw") label = "Draw";

  const line = row.bet_line || row.line || "";

  const odds = row.bet_odds_american || row.dk_odds_american || row.take_odds || row.odds || "";

  const lineText = line !== "" ? " " + line : "";
  const oddsText = odds !== "" ? " (" + odds + ")" : "";

  return (market + " " + MID + " " + label + lineText + oddsText).trim();
}

function pickText(row: any, cfg: any): string {
  if (cfg && typeof cfg.buildBetText === "function") {
    try {
      const built = cfg.buildBetText(row, row);

      if (built) return built;
    } catch (error) {
      // fall through to generic text
    }
  }

  return genericPickText(row);
}

async function loadTodayPicks(date: string, signal?: AbortSignal): Promise<Pick[]> {
  const repoConfig = (window as any).REPO_CONFIG || {};
  const keys = Object.keys(leagueByKey);

  const results = await Promise.all(
    keys.map(async (key): Promise<Pick[]> => {
      const cfg = repoConfig[key];

      if (!cfg || !cfg.selectFiles) return [];

      const paths = resolveSelectPaths(cfg, date);

      if (!paths.length) return [];

      const result = await fetchFirstCSV(paths, signal);

      if (!result.ok) return [];

      const normalize =
        typeof cfg.normalizeRow === "function"
          ? (row: any) => cfg.normalizeRow(row)
          : (row: any) => row;

      const rows: Pick[] = [];

      result.rows.forEach((rawRow) => {
        let normalized: any;

        try {
          normalized = normalize(rawRow);
        } catch (error) {
          normalized = rawRow;
        }

        let expanded: any[] = [normalized];

        if (typeof cfg.expandRows === "function") {
          try {
            expanded = cfg.expandRows(normalized) || [];
          } catch (error) {
            expanded = [];
          }
        }

        expanded.forEach((row) => {
          if (!rowMatchesLeague(row, cfg, key)) return;

          const rowDate = normalizeDate(row.game_date || row.match_date);

          if (rowDate && rowDate !== date) return;

          rows.push({
            league: key,
            leagueLabel: cfg.displayName || sourceLabel(key),
            home_team: row.home_team || "",
            away_team: row.away_team || "",
            game_time: row.game_time || row.match_time || row.edt_time || "",
            market_type: row.market_type || row.market || "",
            bet_side: row.bet_side || row.side || "",
            line: row.bet_line || row.line || "",
            text: pickText(row, cfg),
          });
        });
      });

      return rows;
    })
  );

  let picks: Pick[] = [];

  results.forEach((rows) => {
    picks = picks.concat(rows);
  });

  return picks;
}

// ---------------------------------------------------------------- ESPN injuries

async function fetchLeagueInjuries(cfg: LeagueCfg, signal?: AbortSignal): Promise<Injury[]> {
  const url =
    "https://site.api.espn.com/" + "apis/site/v2/sports/" + cfg.sport + "/" + cfg.league + "/injuries";

  try {
    const response = await fetch(url, { cache: "no-store", signal });

    if (!response.ok) return [];

    const data = await response.json();

    const teamGroups: any[] = data.injuries || [];

    const rows: Injury[] = [];

    teamGroups.forEach((group) => {
      const teamObject = group.team || {};

      const teamName = group.displayName || teamObject.displayName || teamObject.name || "Unknown";

      const injuries: any[] = group.injuries || [];

      injuries.forEach((injury) => {
        const athlete = injury.athlete || {};

        const position =
          athlete.position && athlete.position.abbreviation ? athlete.position.abbreviation : "-";

        const injuryType = injury.details && injury.details.type ? injury.details.type : "-";

        rows.push({
          league: cfg.key,
          leagueLabel: cfg.label,
          group: cfg.group,
          player: athlete.displayName || "Unknown",
          position,
          team: teamName,
          status: injury.status || "Unknown",
          injury: injuryType,
        });
      });
    });

    return rows;
  } catch (error) {
    if (!signal?.aborted) console.warn(cfg.key + " injuries failed:", error);

    return [];
  }
}

async function loadAllInjuries(signal?: AbortSignal): Promise<Injury[]> {
  const results = await Promise.all(LEAGUES.map((cfg) => fetchLeagueInjuries(cfg, signal)));

  let all: Injury[] = [];

  results.forEach((rows) => {
    all = all.concat(rows);
  });

  return all;
}

// ---------------------------------------------------------------- picked-team verification

async function fetchJson(url: string, signal?: AbortSignal): Promise<any> {
  try {
    const response = await fetch(url, { cache: "no-store", signal });

    if (!response.ok) return null;

    return await response.json();
  } catch (error) {
    return null;
  }
}

function espnDateCompact(date: string): string {
  return date.replace(/_/g, "");
}

function scoreboardUrl(cfg: LeagueCfg, date: string): string {
  return (
    "https://site.api.espn.com/" +
    "apis/site/v2/sports/" +
    cfg.sport +
    "/" +
    cfg.league +
    "/scoreboard?dates=" +
    espnDateCompact(date)
  );
}

function teamInjuryUrl(cfg: LeagueCfg, teamId: string): string {
  return (
    "https://site.api.espn.com/" +
    "apis/site/v2/sports/" +
    cfg.sport +
    "/" +
    cfg.league +
    "/teams/" +
    encodeURIComponent(teamId) +
    "/injuries"
  );
}

function competitorNames(competitor: any): string[] {
  const team = competitor && competitor.team ? competitor.team : {};

  return [
    team.displayName,
    team.shortDisplayName,
    team.name,
    team.location,
    team.nickname,
    team.abbreviation,
  ].filter(Boolean);
}

function competitorMatchesTeam(competitor: any, pipelineTeamName: string): boolean {
  return competitorNames(competitor).some((name) => sameTeam(name, pipelineTeamName));
}

function uniquePickedTeamsForLeague(todayPicks: Pick[], leagueKey: string): string[] {
  const found: Record<string, string> = {};

  todayPicks
    .filter((pick) => pick.league === leagueKey)
    .forEach((pick) => {
      [pick.away_team, pick.home_team].forEach((teamName) => {
        if (!teamName) return;

        const key = normalizeTeam(teamName);

        if (!key) return;

        found[key] = teamName;
      });
    });

  return Object.keys(found).map((key) => found[key]);
}

type PickedTarget = {
  leagueKey: string;
  cfg: LeagueCfg;
  teamId: string;
  pipelineTeamName: string;
  espnTeamName: string;
};

async function resolvePickedTeamTargets(
  todayPicks: Pick[],
  date: string,
  signal?: AbortSignal
): Promise<PickedTarget[]> {
  const targets: PickedTarget[] = [];
  const targetKeys: Record<string, boolean> = {};

  const leaguesWithPicks: string[] = [];

  todayPicks.forEach((pick) => {
    if (leaguesWithPicks.indexOf(pick.league) === -1) {
      leaguesWithPicks.push(pick.league);
    }
  });

  for (let i = 0; i < leaguesWithPicks.length; i++) {
    const leagueKey = leaguesWithPicks[i];
    const cfg = leagueByKey[leagueKey];

    // Team injury reports only make sense for team sports.
    if (!cfg || cfg.sport === "mma") continue;

    const scoreboard = await fetchJson(scoreboardUrl(cfg, date), signal);

    if (!scoreboard || !Array.isArray(scoreboard.events)) continue;

    const competitors: any[] = [];

    scoreboard.events.forEach((event: any) => {
      const competition = event.competitions && event.competitions[0] ? event.competitions[0] : null;

      if (!competition || !Array.isArray(competition.competitors)) return;

      competition.competitors.forEach((competitor: any) => {
        competitors.push(competitor);
      });
    });

    const pickedTeams = uniquePickedTeamsForLeague(todayPicks, leagueKey);

    pickedTeams.forEach((pipelineTeamName) => {
      const competitor = competitors.find((item) => competitorMatchesTeam(item, pipelineTeamName));

      if (!competitor || !competitor.team || !competitor.team.id) {
        console.warn("[injuries] Could not resolve picked team:", leagueKey, pipelineTeamName);

        return;
      }

      const targetKey = leagueKey + "|" + competitor.team.id;

      if (targetKeys[targetKey]) return;

      targetKeys[targetKey] = true;

      targets.push({
        leagueKey,
        cfg,
        teamId: String(competitor.team.id),
        pipelineTeamName,
        espnTeamName:
          competitor.team.displayName ||
          competitor.team.shortDisplayName ||
          competitor.team.name ||
          pipelineTeamName,
      });
    });
  }

  return targets;
}

function normalizeTeamInjuryEntry(injury: any, target: PickedTarget): Injury {
  const athlete = injury && injury.athlete ? injury.athlete : {};

  const position = athlete.position && athlete.position.abbreviation ? athlete.position.abbreviation : "-";

  const injuryType = injury && injury.details && injury.details.type ? injury.details.type : "-";

  return {
    league: target.leagueKey,
    leagueLabel: target.cfg.label,
    group: target.cfg.group,
    player: athlete.displayName || athlete.fullName || athlete.name || "Unknown",
    position,
    // The pipeline team name is used deliberately so the fallback record matches today's Picks page exactly.
    team: target.pipelineTeamName,
    status: injury.status || injury.type || "Unknown",
    injury: injuryType,
    verifiedPickedTeam: true,
  };
}

async function fetchPickedTeamInjuries(target: PickedTarget, signal?: AbortSignal): Promise<Injury[]> {
  const data = await fetchJson(teamInjuryUrl(target.cfg, target.teamId), signal);

  if (!data) return [];

  let raw: any[] = [];

  /*
    ESPN has returned both shapes historically:
      injuries: [ injury, injury, ... ]
      injuries: [ { injuries: [ injury, injury, ... ] } ]
    Handle both.
  */
  if (Array.isArray(data.injuries)) {
    data.injuries.forEach((item: any) => {
      if (item && Array.isArray(item.injuries)) {
        raw = raw.concat(item.injuries);
      } else if (item) {
        raw.push(item);
      }
    });
  }

  if (!raw.length && Array.isArray(data.items)) {
    raw = data.items.filter(Boolean);
  }

  return raw.map((injury) => normalizeTeamInjuryEntry(injury, target));
}

function injuryDedupKey(row: Injury): string {
  return [
    row.league,
    normalizeTeam(row.team),
    String(row.player || "").trim().toLowerCase(),
    String(row.status || "").trim().toLowerCase(),
    String(row.injury || "").trim().toLowerCase(),
  ].join("|");
}

async function augmentPickedTeamInjuries(
  todayPicks: Pick[],
  allInjuries: Injury[],
  date: string,
  signal?: AbortSignal
): Promise<{ pickedTeamsResolved: number; pickedTeamInjuriesAdded: number }> {
  let pickedTeamInjuriesAdded = 0;

  const targets = await resolvePickedTeamTargets(todayPicks, date, signal);

  const pickedTeamsResolved = targets.length;

  if (!targets.length) return { pickedTeamsResolved, pickedTeamInjuriesAdded };

  const results = await Promise.all(targets.map((target) => fetchPickedTeamInjuries(target, signal)));

  const existing: Record<string, boolean> = {};

  allInjuries.forEach((row) => {
    existing[injuryDedupKey(row)] = true;
  });

  results.forEach((rows) => {
    rows.forEach((row) => {
      const key = injuryDedupKey(row);

      if (existing[key]) return;

      existing[key] = true;

      allInjuries.push(row);

      pickedTeamInjuriesAdded++;
    });
  });

  console.info(
    "[injuries] Picked teams resolved:",
    pickedTeamsResolved,
    "team-specific injuries added:",
    pickedTeamInjuriesAdded
  );

  return { pickedTeamsResolved, pickedTeamInjuriesAdded };
}

// Full load, same order as the legacy init(): picks + league feeds, then picked-team verification.
export async function loadInjuryData(signal?: AbortSignal): Promise<InjuryData> {
  const date = todayUnderscore();

  const [todayPicks, allInjuries] = await Promise.all([loadTodayPicks(date, signal), loadAllInjuries(signal)]);

  const { pickedTeamsResolved, pickedTeamInjuriesAdded } = await augmentPickedTeamInjuries(
    todayPicks,
    allInjuries,
    date,
    signal
  );

  return {
    todayPicks,
    allInjuries,
    pickedTeamsResolved,
    pickedTeamInjuriesAdded,
    dateDash: date.replace(/_/g, "-"),
  };
}

// ---------------------------------------------------------------- status helpers

function statusKey(value: unknown): string {
  return String(value || "").trim().toLowerCase();
}

export function isOut(row: Injury): boolean {
  return statusKey(row.status) === "out";
}

export function isQuestionable(row: Injury): boolean {
  const key = statusKey(row.status);

  return key === "questionable" || key === "doubtful";
}

function isDayToDay(row: Injury): boolean {
  return statusKey(row.status) === "day-to-day";
}

function isPrimaryImpact(row: Injury): boolean {
  return isOut(row) || isQuestionable(row) || isDayToDay(row);
}

function matchesStatusFilter(row: Injury, statusMode: StatusMode): boolean {
  if (statusMode === "all") return true;
  if (statusMode === "out") return isOut(row);
  if (statusMode === "questionable") return isQuestionable(row);
  if (statusMode === "dtd") return isDayToDay(row);

  // Default general browser: OUT + DOUBTFUL + QUESTIONABLE.
  return isOut(row) || isQuestionable(row);
}

export function statusRank(value: unknown): number {
  const key = statusKey(value);

  if (key === "out") return 0;
  if (key === "doubtful") return 1;
  if (key === "questionable") return 2;
  if (key === "day-to-day") return 3;
  if (key === "probable") return 4;

  return 5;
}

export function statusClass(value: unknown): string {
  const key = statusKey(value);

  if (key === "out") return "s-out";
  if (key === "doubtful") return "s-doubtful";
  if (key === "questionable") return "s-questionable";
  if (key === "day-to-day") return "s-day-to-day";
  if (key === "probable") return "s-probable";

  return "s-other";
}

// ---------------------------------------------------------------- general injury browser

export function filteredBrowserRows(
  allInjuries: Injury[],
  activeFilterType: string,
  activeFilterValue: string,
  statusMode: StatusMode,
  searchQuery: string
): Injury[] {
  let rows = allInjuries.slice();

  if (activeFilterType === "league") {
    rows = rows.filter((row) => row.league === activeFilterValue);
  }

  if (activeFilterType === "group") {
    const allowed = GROUPS[activeFilterValue] || [];

    rows = rows.filter((row) => allowed.indexOf(row.league) !== -1);
  }

  rows = rows.filter((row) => matchesStatusFilter(row, statusMode));

  if (searchQuery) {
    const query = searchQuery.toLowerCase();

    rows = rows.filter(
      (row) =>
        String(row.player || "").toLowerCase().indexOf(query) !== -1 ||
        String(row.team || "").toLowerCase().indexOf(query) !== -1 ||
        String(row.injury || "").toLowerCase().indexOf(query) !== -1 ||
        String(row.leagueLabel || "").toLowerCase().indexOf(query) !== -1
    );
  }

  rows.sort((a, b) => {
    const statusDiff = statusRank(a.status) - statusRank(b.status);

    if (statusDiff !== 0) return statusDiff;

    const leagueDiff = String(a.leagueLabel || "").localeCompare(String(b.leagueLabel || ""));

    if (leagueDiff !== 0) return leagueDiff;

    const teamDiff = String(a.team || "").localeCompare(String(b.team || ""));

    if (teamDiff !== 0) return teamDiff;

    return String(a.player || "").localeCompare(String(b.player || ""));
  });

  return rows;
}

// ---------------------------------------------------------------- picks impact matching

function gameKey(pick: Pick): string {
  return [pick.league, normalizeTeam(pick.away_team), normalizeTeam(pick.home_team)].join("|");
}

export function buildImpactGroups(todayPicks: Pick[], allInjuries: Injury[]): ImpactGroup[] {
  const groups: Record<string, ImpactGroup> = {};

  todayPicks.forEach((pick) => {
    if (!pick.home_team && !pick.away_team) return;

    const key = gameKey(pick);

    if (!groups[key]) {
      groups[key] = {
        league: pick.league,
        leagueLabel: pick.leagueLabel || sourceLabel(pick.league),
        home_team: pick.home_team,
        away_team: pick.away_team,
        game_time: pick.game_time,
        picks: [],
        homeInjuries: [],
        awayInjuries: [],
      };
    }

    groups[key].picks.push(pick);
  });

  Object.keys(groups).forEach((key) => {
    const group = groups[key];

    group.homeInjuries = allInjuries.filter(
      (row) => row.league === group.league && sameTeam(row.team, group.home_team) && isPrimaryImpact(row)
    );

    group.awayInjuries = allInjuries.filter(
      (row) => row.league === group.league && sameTeam(row.team, group.away_team) && isPrimaryImpact(row)
    );
  });

  return Object.keys(groups)
    .map((key) => groups[key])
    .filter((group) => group.homeInjuries.length || group.awayInjuries.length);
}

export function impactSummary(groups: ImpactGroup[]): {
  affectedTeams: number;
  out: number;
  questionable: number;
} {
  const affectedTeams: Record<string, boolean> = {};
  let pickedImpactRows: Injury[] = [];

  groups.forEach((group) => {
    if (group.awayInjuries.length) {
      affectedTeams[group.league + "|" + normalizeTeam(group.away_team)] = true;
      pickedImpactRows = pickedImpactRows.concat(group.awayInjuries);
    }

    if (group.homeInjuries.length) {
      affectedTeams[group.league + "|" + normalizeTeam(group.home_team)] = true;
      pickedImpactRows = pickedImpactRows.concat(group.homeInjuries);
    }
  });

  // Deduplicate the same injury if multiple picks exist on the same game.
  const uniqueImpact: Record<string, Injury> = {};

  pickedImpactRows.forEach((row) => {
    const key = [
      row.league,
      normalizeTeam(row.team),
      String(row.player || "").toLowerCase(),
      statusKey(row.status),
      String(row.injury || "").toLowerCase(),
    ].join("|");

    uniqueImpact[key] = row;
  });

  const uniqueRows = Object.keys(uniqueImpact).map((key) => uniqueImpact[key]);

  return {
    affectedTeams: Object.keys(affectedTeams).length,
    out: uniqueRows.filter(isOut).length,
    questionable: uniqueRows.filter(isQuestionable).length,
  };
}