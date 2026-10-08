// Shared data layer for the Games Today page.
// Ported from legacy games-today/{csv,format,maps,loaders}.js with AbortSignal support added.

export const MID = String.fromCharCode(0xb7);
const DEG = String.fromCharCode(0xb0);

export type Row = Record<string, string>;

export type CsvResult = { ok: boolean; path: string; rows: Row[] };

export type ModalRow = [string, string | undefined];

export type Game = {
  league: string;
  sport?: string;
  displayLeague: string;
  sortTime: number;
  title: string;
  card?: {
    date?: string;
    time?: string;
    away?: string;
    home?: string;
    moneyline?: string[];
    spread?: string[];
    total?: string;
    projection?: string;
  };
  modal?: ModalRow[];
};

export type LeagueResult = {
  league: string;
  displayName: string;
  games: Game[];
};

type SoccerMeta = { key: string; slug: string; display: string };

// ---------------------------------------------------------------- format.js

export function isPresent(value: unknown): boolean {
  return value !== undefined && value !== null && String(value).trim() !== "";
}

// Legacy esc(): kept as-is because legacy fmt() returned escaped text that render.js escaped again.
export function esc(value: unknown): string {
  const map: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  };
  return String(value ?? "").replace(/[&<>'"]/g, (char) => map[char]);
}

export function fmt(value: unknown): string {
  return isPresent(value) ? esc(String(value).trim()) : "";
}

export function dateToUnderscore(dateStr: unknown): string {
  return String(dateStr || "").trim().replace(/-/g, "_");
}

export function formatDate(value: unknown): string {
  if (!isPresent(value)) return "";

  const raw = String(value).trim().replace(/-/g, "_");
  const parts = raw.split("_");

  if (parts.length < 3) return fmt(value);

  const yyyy = parts[0];
  const mm = parts[1].padStart(2, "0");
  const dd = parts[2].padStart(2, "0");

  return `${mm}/${dd}/${String(yyyy).slice(-2)}`;
}

export function formatTime(value: unknown): string {
  if (!isPresent(value)) return "";

  const raw = String(value).trim();

  const alreadyAmPm = raw.match(/^(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)$/i);
  if (alreadyAmPm) {
    return `${parseInt(alreadyAmPm[1], 10)}:${alreadyAmPm[2]} ${alreadyAmPm[3].toUpperCase()}`;
  }

  const military = raw.match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
  if (military) {
    let hour = parseInt(military[1], 10);
    const minute = military[2];
    const suffix = hour >= 12 ? "PM" : "AM";

    if (hour === 0) hour = 12;
    else if (hour > 12) hour -= 12;

    return `${hour}:${minute} ${suffix}`;
  }

  return fmt(raw);
}

export function parseSortTime(value: unknown): number {
  if (!isPresent(value)) return 99999;

  const formatted = formatTime(value);
  const match = formatted.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);

  if (!match) return 99999;

  let hour = parseInt(match[1], 10);
  const minute = parseInt(match[2], 10);
  const suffix = match[3].toUpperCase();

  if (suffix === "PM" && hour !== 12) hour += 12;
  if (suffix === "AM" && hour === 12) hour = 0;

  return hour * 60 + minute;
}

export function formatProb(value: unknown): string {
  if (!isPresent(value)) return "";

  const number = parseFloat(String(value));
  if (Number.isNaN(number)) return fmt(value);

  return `${(number <= 1 ? number * 100 : number).toFixed(1)}%`;
}

export function formatOneDecimal(value: unknown): string {
  if (!isPresent(value)) return "";

  const number = parseFloat(String(value));
  if (Number.isNaN(number)) return fmt(value);

  return number.toFixed(1);
}

export function formatOdds(value: unknown): string {
  if (!isPresent(value)) return "";

  const raw = String(value).trim();
  if (/^[+-]/.test(raw)) return raw;

  const number = parseFloat(raw);
  if (Number.isNaN(number)) return fmt(raw);

  return number > 0 ? `+${number}` : String(number);
}

export function decimalToAmerican(value: unknown): string {
  if (!isPresent(value)) return "";

  const decimal = parseFloat(String(value));
  if (Number.isNaN(decimal) || decimal <= 1) return "";

  if (decimal >= 2) return `+${Math.round((decimal - 1) * 100)}`;

  return String(Math.round(-100 / (decimal - 1)));
}

export function handLabel(value: unknown): string {
  const hand = String(value || "").trim().toUpperCase();

  if (hand === "R") return "Right Handed";
  if (hand === "L") return "Left Handed";

  return "";
}

export function plusLine(value: unknown): string {
  if (!isPresent(value)) return "";

  const raw = String(value).trim();
  const number = parseFloat(raw);

  if (Number.isNaN(number)) return fmt(raw);

  return number > 0 ? `+${number}` : String(number);
}

// ------------------------------------------------------------------- csv.js

export function parseCSV(text: unknown): Row[] {
  const clean = String(text || "").replace(/^\uFEFF/, "").trim();
  if (!clean) return [];

  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;

  for (let i = 0; i < clean.length; i++) {
    const ch = clean[i];
    const next = clean[i + 1];

    if (ch === '"') {
      if (quoted && next === '"') {
        cell += '"';
        i++;
      } else {
        quoted = !quoted;
      }
      continue;
    }

    if (ch === "," && !quoted) {
      row.push(cell.trim());
      cell = "";
      continue;
    }

    if ((ch === "\n" || ch === "\r") && !quoted) {
      if (ch === "\r" && next === "\n") i++;
      row.push(cell.trim());
      rows.push(row);
      row = [];
      cell = "";
      continue;
    }

    cell += ch;
  }

  row.push(cell.trim());
  rows.push(row);

  if (rows.length < 2) return [];

  const headers = rows[0].map((h) =>
    String(h || "")
      .replace(/^\uFEFF/, "")
      .replace(/^"+|"+$/g, "")
      .trim()
  );

  return rows
    .slice(1)
    .filter((r) => r.some((v) => String(v || "").trim() !== ""))
    .map((vals) => {
      const obj: Row = {};
      headers.forEach((h, i) => {
        obj[h] = String(vals[i] ?? "").trim();
      });
      return obj;
    });
}

const RAW_DOCS_ROOT = "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/docs/";

export async function fetchCSV(path: string, signal?: AbortSignal): Promise<CsvResult> {
  if (!path) return { ok: false, path, rows: [] };

  try {
    const resolvedPath = path.startsWith("win/") ? RAW_DOCS_ROOT + path : path;
    const cacheBust = resolvedPath.includes("?") ? `&v=${Date.now()}` : `?v=${Date.now()}`;
    const res = await fetch(`${resolvedPath}${cacheBust}`, { cache: "no-store", signal });

    if (!res.ok) return { ok: false, path, rows: [] };

    const text = await res.text();
    return { ok: true, path, rows: parseCSV(text) };
  } catch {
    return { ok: false, path, rows: [] };
  }
}

export async function fetchFirstCSV(paths: string[], signal?: AbortSignal): Promise<CsvResult> {
  for (const path of paths || []) {
    if (signal?.aborted) break;
    const res = await fetchCSV(path, signal);
    if (res.ok) return res;
  }

  return { ok: false, path: "", rows: [] };
}

// ------------------------------------------------------------------ maps.js

type MlbMaps = {
  pitcherById: Record<string, Row>;
  teamById: Record<string, Row>;
  venueById: Record<string, Row>;
};

let cachedMaps: MlbMaps | null = null;

export async function loadMLBMaps(signal?: AbortSignal): Promise<MlbMaps> {
  if (cachedMaps) return cachedMaps;

  const [pitchers, teams, venues] = await Promise.all([
    fetchCSV("win/baseball/mlb/maps/mlb_pitcher_ids.csv", signal),
    fetchCSV("win/baseball/mlb/maps/mlb_team_ids.csv", signal),
    fetchCSV("win/baseball/mlb/maps/mlb_venue_ids.csv", signal),
  ]);

  const pitcherById: Record<string, Row> = {};
  const teamById: Record<string, Row> = {};
  const venueById: Record<string, Row> = {};

  pitchers.rows.forEach((row) => {
    if (row.pitcher_id) pitcherById[String(row.pitcher_id)] = row;
  });

  teams.rows.forEach((row) => {
    if (row.team_id) teamById[String(row.team_id)] = row;
  });

  venues.rows.forEach((row) => {
    if (row.venue_id) venueById[String(row.venue_id)] = row;
  });

  const maps: MlbMaps = { pitcherById, teamById, venueById };

  // An aborted load must not poison the cache with empty maps.
  if (!signal?.aborted) cachedMaps = maps;

  return maps;
}

export function pitcherName(id: unknown, maps: MlbMaps | null): string {
  if (!id) return "";
  return maps?.pitcherById?.[String(id)]?.full_name || "";
}

export function venueName(id: unknown, maps: MlbMaps | null): string {
  if (!id) return "";
  return maps?.venueById?.[String(id)]?.venue_name || "";
}

// ---------------------------------------------------------------- loaders.js

const BASKETBALL_ORDER = ["NBA", "NCAAM", "WNBA"];

const SOCCER_ORDER: SoccerMeta[] = [
  { key: "MLS", slug: "mls", display: "Major League Soccer - MLS" },
  { key: "EPL", slug: "epl", display: "English Premier League - EPL" },
  { key: "LALIGA", slug: "laliga", display: "Spain - La Liga" },
  { key: "LIGUE1", slug: "ligue1", display: "France - Ligue 1" },
  { key: "SERIEA", slug: "seriea", display: "Italy - Serie A" },
  { key: "BUNDESLIGA", slug: "bundesliga", display: "Germany - Bundesliga" },
];

function mapByGameId(rows: Row[]): Record<string, Row> {
  const map: Record<string, Row> = {};

  rows.forEach((row) => {
    if (row.game_id) map[String(row.game_id)] = row;
  });

  return map;
}

function mapUFCByFight(rows: Row[]): Record<string, Row> {
  const map: Record<string, Row> = {};

  rows.forEach((row) => {
    map[ufcFightKey(row)] = row;
  });

  return map;
}

function ufcFightKey(row: Row): string {
  return [
    String(row.match_date || "").replace(/-/g, "_"),
    String(row.fighter_1 || "").toLowerCase(),
    String(row.fighter_2 || "").toLowerCase(),
  ].join("|");
}

function mlbContextFallbackKey(row: Row): string {
  return [
    String(row.game_date || "").replace(/-/g, "_"),
    String(row.home_team_id || ""),
    String(row.away_team_id || ""),
  ].join("|");
}

function mapMLBContext(rows: Row[]) {
  const byGamePk: Record<string, Row> = {};
  const byFallback: Record<string, Row> = {};

  rows.forEach((row) => {
    if (row.gamePk) byGamePk[String(row.gamePk)] = row;
    byFallback[mlbContextFallbackKey(row)] = row;
  });

  return { byGamePk, byFallback };
}

function doubleHeaderText(row: Row): string {
  if (String(row.doubleheader || "").toUpperCase() !== "Y") return "";
  return `Double Header Game ${row.gameNumber || ""}`.trim();
}

function dayNightText(value: unknown): string {
  const normalized = String(value || "").trim().toLowerCase();

  if (normalized === "day") return "Day Game";
  if (normalized === "night") return "Night Game";

  return "";
}

function weatherRows(context: Row): ModalRow[] {
  const rows: ModalRow[] = [];

  if (context.roof_type) rows.push(["Roof", `${context.roof_type} Roof`]);
  if (context.turf_type) rows.push(["Turf", `${context.turf_type} Turf`]);
  if (context.park_factor) rows.push(["Park Factor", `${context.park_factor} Park Factor`]);
  if (context.temp_f) rows.push(["Temperature", `${context.temp_f}${DEG} F`]);

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

function cleanModalRows(rows: ModalRow[]): ModalRow[] {
  return rows.filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== "");
}

function displayLeagueConfig(key: string, fallbackName: string): string {
  const cfg = (window as any).REPO_CONFIG?.[key] || {};
  return cfg.displayName || fallbackName || key;
}

export async function loadMLB(date: string, signal?: AbortSignal): Promise<LeagueResult> {
  const maps = await loadMLBMaps(signal);

  const [gamesRes, predRes, bookRes, contextRes] = await Promise.all([
    fetchCSV(`win/baseball/mlb/00_intake/games/${date}_games.csv`, signal),
    fetchCSV(`win/baseball/mlb/00_intake/predictions/pred_with_game_id/${date}_MLB.csv`, signal),
    fetchCSV(`win/baseball/mlb/00_intake/sportsbook/${date}_MLB.csv`, signal),
    fetchCSV(`win/baseball/mlb/00_intake/mlb_raw/${date}_game_context.csv`, signal),
  ]);

  const predictionByGameId = mapByGameId(predRes.rows);
  const bookByGameId = mapByGameId(bookRes.rows);
  const contextMap = mapMLBContext(contextRes.rows);

  const games: Game[] = gamesRes.rows.map((base) => {
    const pred: Row = predictionByGameId[base.game_id] || {};
    const book: Row = bookByGameId[base.game_id] || {};
    const context: Row =
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
        ].filter(Boolean) as string[],
        spread: [
          book.away_run_line && `${base.away_team} ${plusLine(book.away_run_line)} (${formatOdds(book.away_dk_run_line_american)})`,
          book.home_run_line && `${base.home_team} ${plusLine(book.home_run_line)} (${formatOdds(book.home_dk_run_line_american)})`,
        ].filter(Boolean) as string[],
        total: book.total ? `Total ${book.total} O ${formatOdds(book.dk_total_over_american)} / U ${formatOdds(book.dk_total_under_american)}` : "",
        projection: pred.total_projected_runs
          ? `${base.away_team} ${formatOneDecimal(pred.away_projected_runs)} ${MID} ${base.home_team} ${formatOneDecimal(pred.home_projected_runs)} ${MID} Total ${formatOneDecimal(pred.total_projected_runs)}`
          : "",
      },
      modal: cleanModalRows([
        ["Date", formatDate(base.game_date)],
        ["Time", formatTime(gameTime)],
        ["Venue", venueName(base.venue_id, maps)],
        ["Double Header", doubleHeaderText(base)],
        ["Day/Night", dayNightText(base.day_night)],
        ["Away Pitcher", [awayPitcher, handLabel(context.away_pitcher_hand)].filter(Boolean).join(` ${MID} `)],
        ["Home Pitcher", [homePitcher, handLabel(context.home_pitcher_hand)].filter(Boolean).join(` ${MID} `)],
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

export async function loadNHL(date: string, signal?: AbortSignal): Promise<LeagueResult> {
  const [gamesRes, bookRes, predRes] = await Promise.all([
    fetchCSV(`win/hockey/nhl/00_intake/games/${date}_nhl_games.csv`, signal),
    fetchFirstCSV(
      [
        `win/hockey/nhl/00_intake/sportsbook/NHL_${date}.csv`,
        `win/hockey/nhl/00_intake/sportsbook/nhl_${date}.csv`,
      ],
      signal
    ),
    fetchCSV(`win/hockey/nhl/00_intake/predictions/hockey_${date}.csv`, signal),
  ]);

  const predictionByGameId = mapByGameId(predRes.rows);
  const bookByGameId = mapByGameId(bookRes.rows);
  const baseRows = gamesRes.rows.length ? gamesRes.rows : bookRes.rows;

  const games: Game[] = baseRows.map((base) => {
    const pred: Row = predictionByGameId[base.game_id] || {};
    const book: Row = bookByGameId[base.game_id] || {};
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
        ].filter(Boolean) as string[],
        spread: [
          book.away_puck_line && `${awayTeam} ${plusLine(book.away_puck_line)} (${formatOdds(book.away_dk_puck_line_american)})`,
          book.home_puck_line && `${homeTeam} ${plusLine(book.home_puck_line)} (${formatOdds(book.home_dk_puck_line_american)})`,
        ].filter(Boolean) as string[],
        total: book.total ? `Total ${book.total} O ${formatOdds(book.dk_total_over_american)} / U ${formatOdds(book.dk_total_under_american)}` : "",
        projection: pred.total_projected_goals
          ? `${awayTeam} ${formatOneDecimal(pred.away_projected_goals)} ${MID} ${homeTeam} ${formatOneDecimal(pred.home_projected_goals)} ${MID} Total ${formatOneDecimal(pred.total_projected_goals)}`
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

export async function loadCFB(date: string, signal?: AbortSignal): Promise<LeagueResult> {
  const gameDate = String(date || "").replace(/_/g, "-");
  const season = gameDate.slice(0, 4);
  const displayLeague = displayLeagueConfig("CFB", "CFB");

  const scheduleRes = await fetchCSV(`win/football/cfb/00_intake/schedule/${season}_schedule.csv`, signal);

  const scheduleRows = scheduleRes.rows.filter((row) => String(row.game_date || "") === gameDate);

  if (!scheduleRows.length) {
    return { league: "CFB", displayName: displayLeague, games: [] };
  }

  const weeks = Array.from(
    new Set(scheduleRows.map((row) => String(row.week || "").trim()).filter(Boolean))
  );

  const weeklyResults = await Promise.all(
    weeks.map((week) =>
      fetchCSV(`win/football/cfb/00_intake/schedule/weekly/week_${week}_CFB_weekly_schedule.csv`, signal)
    )
  );

  const weeklyRows = weeklyResults.flatMap((result) => result.rows);
  const weeklyByGameId = mapByGameId(weeklyRows);

  const games: Game[] = scheduleRows.map((base) => {
    const book: Row = weeklyByGameId[String(base.game_id)] || {};
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
          book.away_moneyline_american && `${awayTeam} ${formatOdds(book.away_moneyline_american)}`,
          book.home_moneyline_american && `${homeTeam} ${formatOdds(book.home_moneyline_american)}`,
        ].filter(Boolean) as string[],
        spread: [
          book.away_spread && `${awayTeam} ${plusLine(book.away_spread)} (${formatOdds(book.away_spread_american)})`,
          book.home_spread && `${homeTeam} ${plusLine(book.home_spread)} (${formatOdds(book.home_spread_american)})`,
        ].filter(Boolean) as string[],
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
          book.away_spread && `${plusLine(book.away_spread)} (${formatOdds(book.away_spread_american)})`,
        ],
        [
          "Home Spread",
          book.home_spread && `${plusLine(book.home_spread)} (${formatOdds(book.home_spread_american)})`,
        ],
        ["Total", book.total],
        ["Total Over", formatOdds(book.over_american)],
        ["Total Under", formatOdds(book.under_american)],
      ]),
    };
  });

  return { league: "CFB", displayName: displayLeague, games };
}

export async function loadBasketball(league: string, date: string, signal?: AbortSignal): Promise<LeagueResult> {
  const lower = league.toLowerCase();
  const upper = league.toUpperCase();

  const [gamesRes, predRes, bookRes] = await Promise.all([
    fetchFirstCSV(
      [
        `win/basketball/daily_games/${lower}/${date}_${lower}.csv`,
        `win/basketball/daily_games/${lower}/${date}_${upper}.csv`,
        `win/basketball/daily_games/${upper}/${date}_${lower}.csv`,
        `win/basketball/daily_games/${upper}/${date}_${upper}.csv`,
      ],
      signal
    ),
    fetchFirstCSV(
      [
        `win/basketball/00_intake/predictions/predictions_cleaned/${lower}/${date}_${lower}_predictions.csv`,
        `win/basketball/00_intake/predictions/predictions_cleaned/${lower}/${date}_${upper}_predictions.csv`,
        `win/basketball/00_intake/predictions/predictions_cleaned/${upper}/${date}_${lower}_predictions.csv`,
        `win/basketball/00_intake/predictions/predictions_cleaned/${upper}/${date}_${upper}_predictions.csv`,
      ],
      signal
    ),
    fetchFirstCSV(
      [
        `win/basketball/00_intake/sportsbook/sportsbook_cleaned/${lower}/${date}_${lower}_odds.csv`,
        `win/basketball/00_intake/sportsbook/sportsbook_cleaned/${lower}/${date}_${upper}_odds.csv`,
        `win/basketball/00_intake/sportsbook/sportsbook_cleaned/${upper}/${date}_${lower}_odds.csv`,
        `win/basketball/00_intake/sportsbook/sportsbook_cleaned/${upper}/${date}_${upper}_odds.csv`,
      ],
      signal
    ),
  ]);

  const predictionByGameId = mapByGameId(predRes.rows);
  const bookByGameId = mapByGameId(bookRes.rows);
  const displayLeague = displayLeagueConfig(league, league);

  const games: Game[] = gamesRes.rows.map((base) => {
    const pred: Row = predictionByGameId[base.game_id] || {};
    const book: Row = bookByGameId[base.game_id] || {};
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
        ].filter(Boolean) as string[],
        spread: [
          book.away_spread && `${base.away_team} ${plusLine(book.away_spread)} (${formatOdds(book.away_dk_spread_american)})`,
          book.home_spread && `${base.home_team} ${plusLine(book.home_spread)} (${formatOdds(book.home_dk_spread_american)})`,
        ].filter(Boolean) as string[],
        total: book.total ? `Total ${book.total} O ${formatOdds(book.dk_total_over_american)} / U ${formatOdds(book.dk_total_under_american)}` : "",
        projection: pred.total_projected_points
          ? `${base.away_team} ${formatOneDecimal(pred.away_projected_points)} ${MID} ${base.home_team} ${formatOneDecimal(pred.home_projected_points)} ${MID} Total ${formatOneDecimal(pred.total_projected_points)}`
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

  return { league, displayName: displayLeague, games };
}

export async function loadSoccer(meta: SoccerMeta, date: string, signal?: AbortSignal): Promise<LeagueResult> {
  const [predRes, bookRes] = await Promise.all([
    fetchCSV(`win/soccer/00_intake/predictions/normalized/${date}_${meta.slug}.csv`, signal),
    fetchCSV(`win/soccer/00_intake/sportsbook/normalized/${date}_${meta.slug}.csv`, signal),
  ]);

  const bookByGameId = mapByGameId(bookRes.rows);

  const games: Game[] = predRes.rows.map((pred) => {
    const book: Row = bookByGameId[pred.game_id] || {};
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
        ].filter(Boolean) as string[],
        spread: [],
        total: pred.expected_total_goals ? `Expected Total Goals ${formatOneDecimal(pred.expected_total_goals)}` : "",
        projection: [
          pred.away_xg && `${pred.away_team} xG ${formatOneDecimal(pred.away_xg)}`,
          pred.home_xg && `${pred.home_team} xG ${formatOneDecimal(pred.home_xg)}`,
        ].filter(Boolean).join(` ${MID} `),
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

  return { league: meta.key, displayName: meta.display, games };
}

export async function loadUFC(date: string, signal?: AbortSignal): Promise<LeagueResult> {
  const [predRes, bookRes] = await Promise.all([
    fetchCSV(`win/mma/ufc/00_intake/predictions/${date}_ufc_predictions.csv`, signal),
    fetchCSV(`win/mma/ufc/00_intake/sportsbook/${date}_ufc_odds.csv`, signal),
  ]);

  const bookByFight = mapUFCByFight(bookRes.rows);
  const displayLeague = displayLeagueConfig("UFC", "UFC");

  const games: Game[] = predRes.rows.map((pred) => {
    const book: Row = bookByFight[ufcFightKey(pred)] || {};

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
        ].filter(Boolean) as string[],
        spread: [],
        total: "",
        projection: [
          pred.fighter_1_win_prob && `${pred.fighter_1} ${formatProb(pred.fighter_1_win_prob)}`,
          pred.fighter_2_win_prob && `${pred.fighter_2} ${formatProb(pred.fighter_2_win_prob)}`,
        ].filter(Boolean).join(` ${MID} `),
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

  return { league: "UFC", displayName: displayLeague, games };
}

export async function loadAllLeagues(dateStr: string, signal?: AbortSignal): Promise<LeagueResult[]> {
  const date = dateToUnderscore(dateStr);
  const config = (window as any).REPO_CONFIG || {};

  const enabled = (league: string): boolean => {
    if (!config[league]) return false;

    const fallback = config[league].enabled !== false;
    const w = window as any;

    if (typeof w.isPageLeagueEnabled === "function") {
      return w.isPageLeagueEnabled("gamesToday", league, fallback);
    }

    const pageConfig = w.PAGE_LEAGUES?.gamesToday;

    if (pageConfig && Object.prototype.hasOwnProperty.call(pageConfig, league)) {
      return pageConfig[league] !== false;
    }

    return fallback;
  };

  const tasks: Promise<LeagueResult>[] = [];

  if (enabled("MLB")) tasks.push(loadMLB(date, signal));
  if (enabled("NHL")) tasks.push(loadNHL(date, signal));
  if (enabled("CFB")) tasks.push(loadCFB(date, signal));

  BASKETBALL_ORDER.forEach((league) => {
    if (enabled(league)) tasks.push(loadBasketball(league, date, signal));
  });

  SOCCER_ORDER.forEach((meta) => {
    if (enabled(meta.key)) tasks.push(loadSoccer(meta, date, signal));
  });

  if (enabled("UFC")) tasks.push(loadUFC(date, signal));

  const results = await Promise.all(tasks);

  return results.map((result) => ({
    ...result,
    games: result.games.sort((a, b) => a.sortTime - b.sortTime),
  }));
}