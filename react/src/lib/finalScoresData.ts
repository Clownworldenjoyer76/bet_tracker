// Shared data helpers for the Final Scores page (ported from legacy final-scores/render.js).
// ESPN fetching, normalization, final-game detection, and game-summary view-model building.

export type LeagueConfig = {
  key: string;
  label: string;
  enabled: boolean;
  sport: string;
  league: string;
  type: "scoreboard" | "placeholder";
  placeholder?: boolean;
};

export type Team = {
  id: string;
  name: string;
  abbr: string;
  logo: string;
  score: string | null;
  winner: boolean;
  homeAway: string;
};

export type Game = {
  id: string;
  leagueKey: string;
  leagueLabel: string;
  sport: string;
  league: string;
  date: string;
  status: any;
  source: "site" | "core";
  away: Team;
  home: Team;
};

export type SummaryView = {
  odds: { spread: string; total: string } | null;
  lines: string[];
  stats: { team: string; text: string }[];
  leaders: string[];
};

export const CORE_API_ROOT = "https://sports.core.api.espn.com/v2";

export const LEAGUES: LeagueConfig[] = [
  { key: "NBA", label: "NBA", enabled: true, sport: "basketball", league: "nba", type: "scoreboard" },
  { key: "NHL", label: "NHL", enabled: true, sport: "hockey", league: "nhl", type: "scoreboard" },
  { key: "CFB", label: "CFB", enabled: true, sport: "football", league: "college-football", type: "scoreboard" },
  { key: "WNBA", label: "WNBA", enabled: true, sport: "basketball", league: "wnba", type: "scoreboard" },
  { key: "NCAAM", label: "NCAAM", enabled: false, sport: "basketball", league: "mens-college-basketball", type: "scoreboard" },
  { key: "MLB", label: "MLB", enabled: true, sport: "baseball", league: "mlb", type: "scoreboard" },
  { key: "EPL", label: "EPL", enabled: true, sport: "soccer", league: "eng.1", type: "scoreboard" },
  { key: "MLS", label: "MLS", enabled: true, sport: "soccer", league: "usa.1", type: "scoreboard" },
  { key: "LALIGA", label: "LA LIGA", enabled: true, sport: "soccer", league: "esp.1", type: "scoreboard" },
  { key: "LIGUE1", label: "LIGUE 1", enabled: true, sport: "soccer", league: "fra.1", type: "scoreboard" },
  { key: "SERIEA", label: "SERIE A", enabled: true, sport: "soccer", league: "ita.1", type: "scoreboard" },
  { key: "BUNDESLIGA", label: "BUNDESLIGA", enabled: true, sport: "soccer", league: "ger.1", type: "scoreboard" },
  { key: "UFC", label: "UFC", enabled: false, sport: "mma", league: "ufc", type: "placeholder", placeholder: true },
];

export const DASH = String.fromCharCode(0x2014);
export const DOT = " " + String.fromCharCode(0xb7) + " ";

// ---- small utilities -------------------------------------------------------

export function todayStr(): string {
  const now = new Date();
  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
}

export function toEspnDate(value: string): string {
  return String(value || todayStr()).replace(/-/g, "");
}

function normalizeUrl(url: unknown): string {
  if (!url) return "";
  return String(url).replace(/^http:\/\//i, "https://");
}

function isRefItem(item: any): boolean {
  return !!item && typeof item === "object" && !!item.$ref;
}

function getRefUrl(item: any): string {
  if (!item) return "";
  if (typeof item === "string") return normalizeUrl(item);
  if (item.$ref) return normalizeUrl(item.$ref);
  return "";
}

export function isLeagueEnabled(cfg: LeagueConfig): boolean {
  const fn = (window as any).isPageLeagueEnabled;
  if (typeof fn === "function") {
    return fn("finalScores", cfg.key, cfg.enabled !== false);
  }
  return cfg.enabled !== false;
}

// ---- fetching --------------------------------------------------------------

// Resolved $ref responses are kept for the life of the page (legacy refCache).
const resolvedRefs = new Map<string, any>();

type RefContext = {
  signal: AbortSignal;
  inflight: Map<string, Promise<any>>;
};

export async function fetchJson(url: string, signal?: AbortSignal): Promise<any> {
  const finalUrl = normalizeUrl(url);
  const response = await fetch(finalUrl, { signal });
  if (!response.ok) {
    throw new Error("HTTP " + response.status + DOT + finalUrl);
  }
  return response.json();
}

async function fetchRef(item: any, ctx: RefContext): Promise<any> {
  const url = getRefUrl(item);
  if (!url) return item;

  if (resolvedRefs.has(url)) return resolvedRefs.get(url);

  const pending = ctx.inflight.get(url);
  if (pending) return pending;

  const promise = fetchJson(url, ctx.signal)
    .then((value) => {
      resolvedRefs.set(url, value);
      return value;
    })
    .finally(() => {
      ctx.inflight.delete(url);
    });

  ctx.inflight.set(url, promise);
  return promise;
}

async function fetchRefs(items: any, limit: number | undefined, ctx: RefContext): Promise<any[]> {
  const list: any[] = Array.isArray(items) ? items.slice(0, limit || items.length) : [];
  const results: any[] = [];
  const concurrency = 12;
  let index = 0;

  async function worker() {
    while (index < list.length) {
      const currentIndex = index++;
      const item = list[currentIndex];
      try {
        results[currentIndex] = isRefItem(item) ? await fetchRef(item, ctx) : item;
      } catch (e) {
        if (ctx.signal.aborted) throw e;
        results[currentIndex] = null;
      }
    }
  }

  const workers: Promise<void>[] = [];
  const workerCount = Math.min(concurrency, list.length);
  for (let i = 0; i < workerCount; i++) workers.push(worker());
  await Promise.all(workers);

  return results.filter(Boolean);
}

function siteScoreboardUrl(cfg: LeagueConfig, espnDate: string): string {
  return (
    "https://site.api.espn.com/apis/site/v2/sports/" +
    encodeURIComponent(cfg.sport) +
    "/" +
    encodeURIComponent(cfg.league) +
    "/scoreboard?dates=" +
    encodeURIComponent(espnDate)
  );
}

function coreEventsUrl(cfg: LeagueConfig, espnDate: string): string {
  return (
    CORE_API_ROOT +
    "/sports/" +
    encodeURIComponent(cfg.sport) +
    "/leagues/" +
    encodeURIComponent(cfg.league) +
    "/events?dates=" +
    encodeURIComponent(espnDate) +
    "&limit=200"
  );
}

export function summaryUrl(game: Game): string {
  return (
    "https://site.api.espn.com/apis/site/v2/sports/" +
    encodeURIComponent(game.sport) +
    "/" +
    encodeURIComponent(game.league) +
    "/summary?event=" +
    encodeURIComponent(game.id)
  );
}

// ---- normalization ---------------------------------------------------------

export function normalizeScore(score: any): string | null {
  if (score === null || score === undefined || score === "") return null;

  if (typeof score === "object") {
    const keys = ["displayValue", "value", "score", "points", "total"];
    for (let i = 0; i < keys.length; i++) {
      if (!Object.prototype.hasOwnProperty.call(score, keys[i])) continue;
      const value = score[keys[i]];
      if (value === null || value === undefined || value === "") continue;
      if (typeof value === "object") {
        const nested = normalizeScore(value);
        if (nested !== null) return nested;
        continue;
      }
      return String(value);
    }
    return null;
  }

  return String(score);
}

function logoOf(team: any): string {
  let logo = "";
  if (Array.isArray(team.logos) && team.logos.length) {
    logo = team.logos[0].href || team.logos[0].url || "";
  } else if (team.logo) {
    logo = team.logo;
  }
  return normalizeUrl(logo);
}

function normalizeSiteCompetitor(item: any): Team {
  const team = item.team || {};
  return {
    id: team.id || item.id || "",
    name: team.displayName || team.name || team.shortDisplayName || DASH,
    abbr: team.abbreviation || team.shortDisplayName || team.name || DASH,
    logo: logoOf(team),
    score: normalizeScore(item.score),
    winner: item.winner === true,
    homeAway: item.homeAway || "",
  };
}

function normalizeCoreCompetitor(item: any): Team {
  const team = item.team || {};
  return {
    id: team.id || item.id || "",
    name: team.displayName || team.name || team.shortDisplayName || team.abbreviation || DASH,
    abbr: team.abbreviation || team.shortDisplayName || team.name || DASH,
    logo: logoOf(team),
    score: normalizeScore(item.score),
    winner: item.winner === true,
    homeAway: item.homeAway || "",
  };
}

function normalizeSiteEvents(cfg: LeagueConfig, events: any[]): Game[] {
  return events
    .map((ev: any): Game | null => {
      const comp = ev.competitions && ev.competitions[0] ? ev.competitions[0] : null;
      const competitors = comp && Array.isArray(comp.competitors) ? comp.competitors : [];
      const away = competitors.find((t: any) => t.homeAway === "away");
      const home = competitors.find((t: any) => t.homeAway === "home");

      if (!away || !home) return null;

      return {
        id: ev.id || "",
        leagueKey: cfg.key,
        leagueLabel: cfg.label,
        sport: cfg.sport,
        league: cfg.league,
        date: ev.date || comp.date || "",
        status: ev.status || comp.status || null,
        source: "site",
        away: normalizeSiteCompetitor(away),
        home: normalizeSiteCompetitor(home),
      };
    })
    .filter((g): g is Game => g !== null);
}

async function getCoreStatus(ev: any, competition: any, ctx: RefContext): Promise<any> {
  let status: any = null;

  if (ev.status) {
    status = isRefItem(ev.status)
      ? await fetchRef(ev.status, ctx).catch((e) => {
          if (ctx.signal.aborted) throw e;
          return null;
        })
      : ev.status;
  }

  if (!status && competition && competition.status) {
    status = isRefItem(competition.status)
      ? await fetchRef(competition.status, ctx).catch((e) => {
          if (ctx.signal.aborted) throw e;
          return null;
        })
      : competition.status;
  }

  return status || {};
}

async function normalizeCoreEvent(cfg: LeagueConfig, ev: any, ctx: RefContext): Promise<Game | null> {
  if (!ev) return null;

  let competition: any = null;

  if (Array.isArray(ev.competitions) && ev.competitions.length) {
    competition = isRefItem(ev.competitions[0])
      ? await fetchRef(ev.competitions[0], ctx)
      : ev.competitions[0];
  } else if (ev.competition) {
    competition = isRefItem(ev.competition) ? await fetchRef(ev.competition, ctx) : ev.competition;
  }

  if (!competition) return null;

  const competitorsRaw = Array.isArray(competition.competitors) ? competition.competitors : [];
  const fetched = await fetchRefs(competitorsRaw, 20, ctx);
  const competitors: any[] = [];

  for (let i = 0; i < fetched.length; i++) {
    const competitor: any = { ...fetched[i] };

    if (isRefItem(competitor.team)) {
      try {
        competitor.team = await fetchRef(competitor.team, ctx);
      } catch (e) {
        if (ctx.signal.aborted) throw e;
      }
    }

    if (isRefItem(competitor.score)) {
      try {
        competitor.score = await fetchRef(competitor.score, ctx);
      } catch (e) {
        if (ctx.signal.aborted) throw e;
        competitor.score = null;
      }
    }

    competitors.push(competitor);
  }

  let away = competitors.find((t) => String(t.homeAway || "").toLowerCase() === "away");
  let home = competitors.find((t) => String(t.homeAway || "").toLowerCase() === "home");

  if (!away || !home) {
    if (competitors.length >= 2) {
      away = competitors[0];
      home = competitors[1];
    }
  }

  if (!away || !home) return null;

  const status = await getCoreStatus(ev, competition, ctx);

  return {
    id: ev.id || competition.id || "",
    leagueKey: cfg.key,
    leagueLabel: cfg.label,
    sport: cfg.sport,
    league: cfg.league,
    date: ev.date || competition.date || "",
    status,
    source: "core",
    away: normalizeCoreCompetitor(away),
    home: normalizeCoreCompetitor(home),
  };
}

async function loadCoreEvents(cfg: LeagueConfig, espnDate: string, signal: AbortSignal): Promise<Game[]> {
  const ctx: RefContext = { signal, inflight: new Map() };
  const data = await fetchJson(coreEventsUrl(cfg, espnDate), signal);
  const eventItems = Array.isArray(data.items) ? data.items : [];
  const events = await fetchRefs(eventItems, 200, ctx);
  const normalized: Game[] = [];

  for (let i = 0; i < events.length; i++) {
    try {
      const ev = await normalizeCoreEvent(cfg, events[i], ctx);
      if (ev) normalized.push(ev);
    } catch (e) {
      if (signal.aborted) throw e;
    }
  }

  normalized.sort((a, b) => new Date(a.date || 0).getTime() - new Date(b.date || 0).getTime());

  return normalized;
}

export async function loadLeagueEvents(cfg: LeagueConfig, espnDate: string, signal: AbortSignal): Promise<Game[]> {
  try {
    const siteData = await fetchJson(siteScoreboardUrl(cfg, espnDate), signal);
    return normalizeSiteEvents(cfg, siteData.events || []);
  } catch (siteError) {
    if (signal.aborted) throw siteError;
    return loadCoreEvents(cfg, espnDate, signal);
  }
}

// ---- game state ------------------------------------------------------------

export function isFinal(game: Game): boolean {
  const status = game.status || {};
  const type = status.type || status;
  return (
    type.completed === true ||
    status.completed === true ||
    String(type.state || status.state || "").toLowerCase() === "post"
  );
}

export function getWinnerFlags(game: Game): { awayWins: boolean; homeWins: boolean } {
  const awayScore = game.away && game.away.score !== null ? parseFloat(game.away.score) : NaN;
  const homeScore = game.home && game.home.score !== null ? parseFloat(game.home.score) : NaN;

  let awayWins = !!game.away && game.away.winner === true;
  let homeWins = !!game.home && game.home.winner === true;

  if (!isNaN(awayScore) && !isNaN(homeScore)) {
    awayWins = awayScore > homeScore;
    homeWins = homeScore > awayScore;
  }

  return { awayWins, homeWins };
}

export function scoreText(team: Team): string {
  return team.score !== null && team.score !== undefined ? team.score : "0";
}

// ---- game summary view model (legacy buildOdds/Lines/Stats/LeadersHTML) -----

function buildOdds(data: any): SummaryView["odds"] {
  if (!data || !data.header || !data.header.competitions || !data.header.competitions[0]) return null;
  const odds = data.header.competitions[0].odds && data.header.competitions[0].odds[0];
  if (!odds) return null;
  return {
    spread: String(odds.details || DASH),
    total: String(odds.overUnder || DASH),
  };
}

function buildLines(game: Game, data: any): string[] {
  if (!data || !data.header || !data.header.competitions || !data.header.competitions[0]) return [];

  const comp = data.header.competitions[0];
  const teams = comp.competitors || [];
  const away = teams.find((t: any) => t.homeAway === "away");
  const home = teams.find((t: any) => t.homeAway === "home");

  if (!away || !home) return [];

  const awayLines = away.linescores || [];
  const homeLines = home.linescores || [];

  if (!awayLines.length) return [];

  const periodLabel =
    game.sport === "baseball" ? "Inn" :
    game.sport === "hockey" ? "P" :
    game.sport === "soccer" ? "H" :
    "Q";

  return awayLines.map((line: any, i: number) => {
    const period = line.period || i + 1;
    const awayVal = line.displayValue || line.value || "0";
    const homeLine = homeLines[i];
    const homeVal = homeLine ? homeLine.displayValue || homeLine.value || "0" : "0";

    const awayAbbr = away.team
      ? away.team.abbreviation || game.away.abbr || "AWAY"
      : game.away.abbr || "AWAY";

    const homeAbbr = home.team
      ? home.team.abbreviation || game.home.abbr || "HOME"
      : game.home.abbr || "HOME";

    return periodLabel + period + ": " + awayAbbr + " " + awayVal + DOT + homeAbbr + " " + homeVal;
  });
}

const NHL_STATS = [
  "shots on goal", "hits", "power play goals", "power play opportunities", "giveaways", "takeaways",
];
const MLB_STATS = [
  "runs", "hits", "errors", "strikeouts", "home runs", "runs batted in", "batting average", "left on base",
];
const SOCCER_STATS = [
  "possession", "shots on target", "shots", "fouls", "yellow cards", "red cards", "corner kicks", "offsides",
];

function buildStats(game: Game, data: any): { team: string; text: string }[] {
  if (!data || !data.boxscore || !data.boxscore.teams) return [];

  const out: { team: string; text: string }[] = [];

  data.boxscore.teams.forEach((teamBox: any) => {
    const allStats = teamBox.statistics || [];
    const flat: any[] = [];

    allStats.forEach((statGroup: any) => {
      if (statGroup.stats && statGroup.stats.length) {
        statGroup.stats.forEach((stat: any) => flat.push(stat));
      } else {
        flat.push(statGroup);
      }
    });

    let whitelist: string[] | null = null;
    if (game.sport === "hockey") whitelist = NHL_STATS;
    else if (game.sport === "baseball") whitelist = MLB_STATS;
    else if (game.sport === "soccer") whitelist = SOCCER_STATS;

    const rows = flat
      .filter((stat) => {
        const val = stat.displayValue || stat.value || "";
        const label = String(stat.label || stat.displayName || stat.name || "").toLowerCase();

        if (!val && val !== 0) return false;
        if (whitelist) return whitelist.indexOf(label) !== -1;
        return true;
      })
      .slice(0, 8)
      .map((stat) => {
        const label = stat.label || stat.displayName || stat.name || "";
        const val = stat.displayValue || stat.value || "";
        return label + ": " + val;
      });

    if (!rows.length) return;

    const teamName = teamBox.team ? teamBox.team.displayName || teamBox.team.abbreviation || "" : "";

    out.push({ team: teamName, text: rows.join(DOT) });
  });

  return out;
}

function buildLeaders(data: any): string[] {
  if (!data || !data.leaders) return [];

  const out: string[] = [];

  data.leaders.forEach((group: any) => {
    const top = group.leaders && group.leaders[0];
    const name = group.displayName || group.name || "";
    const val = top ? top.displayValue || top.value || "" : "";
    const athlete = top && top.athlete ? top.athlete.displayName || "" : "";

    if (name && val) {
      out.push(name + ": " + (athlete ? athlete + " " + DASH + " " : "") + val);
    }
  });

  return out;
}

export function buildSummaryView(game: Game, data: any): SummaryView {
  return {
    odds: buildOdds(data),
    lines: buildLines(game, data),
    stats: buildStats(game, data),
    leaders: buildLeaders(data),
  };
}