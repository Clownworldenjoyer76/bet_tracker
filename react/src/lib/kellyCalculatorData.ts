// Shared data layer for the Kelly Calculator page.
// Ported from legacy assets/js/pages/kelly_calculator.js (league availability) and
// kelly_calculator.2.js (CSV loading, pick processing, UFC event lookup, account preferences),
// with AbortSignal support added to the fetches.

export const MID = String.fromCharCode(0xb7);
export const DASH = String.fromCharCode(0x2014);

export const BASE = "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/";
export const BASE_DOCS = BASE + "docs/";

const PREFERENCES_URL = "https://api.sportsmodelhub.com/api/account/preferences/";

// Legacy kelly_calculator.js: window.KELLY_LEAGUE_AVAILABILITY (read by the shared league nav).
export const KELLY_LEAGUE_AVAILABILITY: Record<string, boolean> = {
  nfl: false,
  cfb: true,
  cfl: false,
  nhl: true,
  mlb: true,
  mlb_lineups: true,
  nba: false,
  ncaam: false,
  wnba: true,
  mls: true,
  epl: true,
  laliga: true,
  ligue1: true,
  seriea: true,
  bundesliga: true,
  ufc: true,
};

export type KellyPick = {
  matchup: string;
  time: string;
  market_type: string;
  side: string;
  odds: string;
  ev: number | null;
  kelly: number;
  isUFC?: boolean;
};

export type SportKey =
  | "cfb"
  | "nhl"
  | "mlb"
  | "mlb_lineups"
  | "nba"
  | "wnba"
  | "mls"
  | "epl"
  | "laliga"
  | "ligue1"
  | "seriea"
  | "bundesliga"
  | "ufc";

export type AllPicks = Record<SportKey, KellyPick[]>;

export const SPORTS: { key: SportKey; label: string }[] = [
  { key: "cfb", label: "COLLEGE FOOTBALL" },
  { key: "nhl", label: "NHL" },
  { key: "mlb", label: "MLB" },
  { key: "mlb_lineups", label: "MLB " + MID + " WITH LINEUPS" },
  { key: "nba", label: "NBA" },
  { key: "wnba", label: "WNBA" },
  { key: "mls", label: "MLS" },
  { key: "epl", label: "EPL" },
  { key: "laliga", label: "LA LIGA" },
  { key: "ligue1", label: "LIGUE 1" },
  { key: "seriea", label: "SERIE A" },
  { key: "bundesliga", label: "BUNDESLIGA" },
  { key: "ufc", label: "UFC" },
];

export function emptyPicks(): AllPicks {
  return {
    cfb: [],
    nhl: [],
    mlb: [],
    mlb_lineups: [],
    nba: [],
    wnba: [],
    mls: [],
    epl: [],
    laliga: [],
    ligue1: [],
    seriea: [],
    bundesliga: [],
    ufc: [],
  };
}

const FEEDS: { sport: SportKey; configKey: string }[] = [
  { sport: "cfb", configKey: "CFB" },
  { sport: "nhl", configKey: "NHL" },
  { sport: "mlb", configKey: "MLB" },
  { sport: "mlb_lineups", configKey: "MLB_LINEUPS" },
  { sport: "nba", configKey: "NBA" },
  { sport: "wnba", configKey: "WNBA" },
  { sport: "mls", configKey: "MLS" },
  { sport: "epl", configKey: "EPL" },
  { sport: "laliga", configKey: "LALIGA" },
  { sport: "ligue1", configKey: "LIGUE1" },
  { sport: "seriea", configKey: "SERIEA" },
  { sport: "bundesliga", configKey: "BUNDESLIGA" },
];

// ---------------------------------------------------------------- dates

export function todayDateInputValue(): string {
  const d = new Date();

  return (
    d.getFullYear() +
    "-" +
    String(d.getMonth() + 1).padStart(2, "0") +
    "-" +
    String(d.getDate()).padStart(2, "0")
  );
}

export function toDateStr(v: string): string {
  return v.split("-").join("_");
}

function normalizeDateValue(value: unknown): string {
  return String(value || "").trim().split("-").join("_");
}

// ---------------------------------------------------------------- CSV

const BOM = new RegExp("^" + String.fromCharCode(0xfeff));

function parseCSVLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];

    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (ch === "," && !inQuotes) {
      out.push(cur.trim());
      cur = "";
      continue;
    }

    cur += ch;
  }

  out.push(cur.trim());

  return out;
}

function cleanCSVCell(v: unknown): string {
  let s = String(v ?? "").trim();

  if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) s = s.slice(1, -1);

  return s.split('""').join('"').trim();
}

function parseCSV(text: unknown): Record<string, string>[] {
  const raw = String(text || "").replace(BOM, "").trim();

  if (!raw) return [];

  const lines = raw.split(/\r?\n/).filter((line) => line.trim() !== "");

  if (lines.length < 2) return [];

  const headers = parseCSVLine(lines[0]).map(cleanCSVCell);

  return lines.slice(1).map((line) => {
    const vals = parseCSVLine(line).map(cleanCSVCell);

    return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? ""]));
  });
}

function repoConfig(): any {
  return (window as any).REPO_CONFIG;
}

function resolveSelectFiles(configKey: string, dateStr: string): string[] {
  const rc = repoConfig();
  const cfg = rc && rc[configKey];

  if (!cfg || !cfg.selectFiles) return [];

  const resolved = typeof cfg.selectFiles === "function" ? cfg.selectFiles(dateStr) : cfg.selectFiles;

  if (Array.isArray(resolved)) return resolved.filter(Boolean);

  return resolved ? [resolved] : [];
}

function resolveSelectUrl(path: string): string {
  if (!path) return "";

  if (/^https?:\/\//i.test(path)) return path;

  return path.startsWith("win/") ? BASE_DOCS + path : BASE + path.replace(/^\/+/, "");
}

async function loadConfigSelectedRows(
  configKey: string,
  dateStr: string,
  signal?: AbortSignal
): Promise<Record<string, string>[]> {
  const paths = resolveSelectFiles(configKey, dateStr);

  for (const path of paths) {
    try {
      const r = await fetch(resolveSelectUrl(path), { cache: "no-store", signal });

      if (!r.ok) continue;

      return parseCSV(await r.text());
    } catch {
      // try next path
    }
  }

  return [];
}

function rowMatchesConfig(row: any, configKey: string, cfg: any): boolean {
  if (cfg.filterFn) {
    try {
      return cfg.filterFn(row, null, String(configKey).toUpperCase()) !== false;
    } catch {
      return true;
    }
  }

  if (cfg.leagueColumn) {
    return String(row[cfg.leagueColumn] || "").trim().toUpperCase() === String(configKey).toUpperCase();
  }

  return true;
}

function prepareConfigRows(rows: any[], configKey: string, dateStr: string): any[] {
  const rc = repoConfig();
  const cfg = rc && rc[configKey];

  if (!cfg) return [];

  const normalize = cfg.normalizeRow ? (row: any) => cfg.normalizeRow(row) : (row: any) => row;

  const expanded = rows.flatMap((row) => {
    const normalized = normalize(row);

    if (cfg.expandRows) {
      return cfg.expandRows(normalized);
    }

    return [normalized];
  });

  return expanded.filter((row: any) => {
    if (!rowMatchesConfig(row, configKey, cfg)) return false;

    return normalizeDateValue(row.game_date) === dateStr;
  });
}

// ---------------------------------------------------------------- math / formatting

function americanToDecimal(odds: unknown): number | null {
  const n = parseFloat(String(odds));

  if (isNaN(n) || n === 0) return null;

  return n > 0 ? 1 + n / 100 : 1 + 100 / Math.abs(n);
}

function calcKellyFromProbability(probability: unknown, americanOdds: unknown): number | null {
  const p = parseFloat(String(probability));
  const decimal = americanToDecimal(americanOdds);

  if (isNaN(p) || !decimal || decimal <= 1) return null;

  const b = decimal - 1;
  const q = 1 - p;
  const k = (b * p - q) / b;

  return Math.max(0, Math.min(1, k));
}

function calcEvFromProbability(probability: unknown, americanOdds: unknown): number | null {
  const p = parseFloat(String(probability));
  const decimal = americanToDecimal(americanOdds);

  if (isNaN(p) || !decimal) return null;

  return p * decimal - 1;
}

function firstNumeric(...values: unknown[]): number | null {
  for (const value of values) {
    const n = parseFloat(String(value));

    if (!isNaN(n)) return n;
  }

  return null;
}

export function formatOdds(val: unknown): string {
  const n = parseFloat(String(val));

  if (isNaN(n)) return DASH;

  return n > 0 ? `+${Math.round(n)}` : `${Math.round(n)}`;
}

export function formatDollar(n: number): string {
  return "$" + n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

export function formatPct(n: number): string {
  return (n * 100).toFixed(1) + "%";
}

function getNBAKelly(row: any): any {
  const mt = (row.market_type || "").toLowerCase();
  const side = (row.bet_side || "").toLowerCase();

  if (mt === "spread") return side === "home" ? row.home_spread_kelly : row.away_spread_kelly;
  if (mt === "moneyline") return side === "home" ? row.home_ml_kelly : row.away_ml_kelly;
  if (mt === "total") return side === "over" ? row.over_kelly : row.under_kelly;

  return null;
}

function getNBAEV(row: any): any {
  const mt = (row.market_type || "").toLowerCase();
  const side = (row.bet_side || "").toLowerCase();

  if (mt === "spread") return side === "home" ? row.home_spread_ev : row.away_spread_ev;
  if (mt === "moneyline") return side === "home" ? row.home_ml_ev : row.away_ml_ev;
  if (mt === "total") return side === "over" ? row.over_ev : row.under_ev;

  return row.selected_ev;
}

function getNBAOdds(row: any): any {
  const mt = (row.market_type || "").toLowerCase();
  const side = (row.bet_side || "").toLowerCase();

  if (mt === "spread") return side === "home" ? row.home_dk_spread_american : row.away_dk_spread_american;
  if (mt === "moneyline") return side === "home" ? row.home_dk_moneyline_american : row.away_dk_moneyline_american;
  if (mt === "total") return side === "over" ? row.dk_total_over_american : row.dk_total_under_american;

  return null;
}

function getGenericOdds(row: any, sportKey: string): any {
  if (sportKey === "nba") {
    const nbaOdds = getNBAOdds(row);

    if (nbaOdds !== null && nbaOdds !== undefined && nbaOdds !== "") {
      return nbaOdds;
    }
  }

  return row.bet_odds_american || row.dk_odds_american || row.american_odds || row.take_odds || "";
}

function getGenericKelly(row: any, sportKey: string, odds: unknown): number | null {
  const direct = firstNumeric(row.kelly, row.bet_kelly, row.bet_final_stake_pct, row.bet_stake_pct);

  if (direct !== null) return direct;

  if (sportKey === "nba") {
    const nbaKelly = parseFloat(getNBAKelly(row));

    if (!isNaN(nbaKelly)) return nbaKelly;
  }

  const modelProb = firstNumeric(row.model_prob, row.bet_model_prob, row.bet_adjusted_model_prob);

  if (modelProb !== null) {
    return calcKellyFromProbability(modelProb, odds);
  }

  return null;
}

function getGenericEv(row: any, sportKey: string, odds: unknown): number | null {
  const direct = firstNumeric(row.ev, row.bet_ev, row.selected_ev);

  if (direct !== null) return direct;

  if (sportKey === "nba") {
    const nbaEv = parseFloat(getNBAEV(row));

    if (!isNaN(nbaEv)) return nbaEv;
  }

  const modelProb = firstNumeric(row.model_prob, row.bet_model_prob, row.bet_adjusted_model_prob);

  if (modelProb !== null) {
    return calcEvFromProbability(modelProb, odds);
  }

  return null;
}

function buildSideLabel(row: any): string {
  const mt = (row.market_type || "").toLowerCase();
  const side = (row.bet_side || "").toLowerCase();
  const line = parseFloat(row.line);

  if (mt === "total") return `${side.toUpperCase()} ${row.line || ""}`;

  if (["spread", "puck_line", "run_line"].includes(mt)) {
    const team = side === "home" ? row.home_team : row.away_team;
    const lineStr = !isNaN(line) ? ` ${line > 0 ? "+" : ""}${line}` : "";

    return `${team}${lineStr}`;
  }

  if (mt === "moneyline") return side === "home" ? row.home_team : row.away_team;

  return side;
}

function buildConfigSideLabel(row: any, cfg: any): string {
  if (cfg && typeof cfg.buildBetText === "function") {
    try {
      return cfg.buildBetText(row, row);
    } catch {
      // fall through to the generic label
    }
  }

  return buildSideLabel(row);
}

function processConfigPicks(rows: any[], configKey: string, sportKey: string, dateStr: string): KellyPick[] {
  const rc = repoConfig();
  const cfg = rc && rc[configKey];

  if (!cfg) return [];

  const prepared = prepareConfigRows(rows, configKey, dateStr);

  return prepared
    .map((row: any): KellyPick | null => {
      const odds = getGenericOdds(row, sportKey);
      const kelly = getGenericKelly(row, sportKey, odds);
      const ev = getGenericEv(row, sportKey, odds);

      if (kelly === null || isNaN(kelly) || kelly <= 0) return null;

      return {
        matchup: `${row.away_team || DASH} @ ${row.home_team || DASH}`,
        time: row.game_time || row.match_time || "",
        market_type: String(row.market_type || row.market || "").toLowerCase(),
        side: buildConfigSideLabel(row, cfg),
        odds: formatOdds(odds),
        ev,
        kelly,
      };
    })
    .filter((p): p is KellyPick => p !== null);
}

// ---------------------------------------------------------------- UFC

async function findUFCEventDate(signal?: AbortSignal): Promise<string | null> {
  const today = new Date();
  const candidates: { date: string; offset: number }[] = [];

  for (let offset = -30; offset <= 30; offset++) {
    const d = new Date(today);

    d.setDate(today.getDate() + offset);

    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");

    candidates.push({ date: `${y}_${m}_${day}`, offset: Math.abs(offset) });
  }

  const results = await Promise.all(
    candidates.map(async ({ date, offset }) => {
      const url = `${BASE_DOCS}win/mma/ufc/03_select/${date}_ufc_select.csv`;

      try {
        const r = await fetch(url, { method: "HEAD", signal });

        return r.ok ? { date, offset } : null;
      } catch {
        return null;
      }
    })
  );

  const valid = results
    .filter((x): x is { date: string; offset: number } => x !== null)
    .sort((a, b) => a.offset - b.offset);

  return valid.length ? valid[0].date : null;
}

async function loadUFCPicks(signal: AbortSignal | undefined, onUfcEvent: (text: string) => void): Promise<KellyPick[]> {
  const eventDate = await findUFCEventDate(signal);

  if (!eventDate) {
    onUfcEvent("No event");

    return [];
  }

  onUfcEvent(eventDate.split("_").join("-"));

  try {
    const url = `${BASE_DOCS}win/mma/ufc/03_select/${eventDate}_ufc_select.csv`;
    const r = await fetch(url, { signal });

    if (!r.ok) return [];

    const rows = parseCSV(await r.text());

    return rows
      .map((row: any): KellyPick | null => {
        const kelly = parseFloat(row.kelly || 0);
        const ev = parseFloat(row.ev || 0);

        if (isNaN(kelly) || kelly <= 0) return null;

        return {
          matchup: `${row.fighter} vs ${row.opponent}`,
          time: "",
          market_type: "ufc",
          side: `${row.fighter} ${row.moneyline || ""}`,
          odds: row.moneyline || DASH,
          ev: isNaN(ev) ? null : ev,
          kelly,
          isUFC: true,
        };
      })
      .filter((p): p is KellyPick => p !== null);
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------- full load (legacy loadAll)

export async function loadKellyPicks(
  dateStr: string,
  signal: AbortSignal | undefined,
  onUfcEvent: (text: string) => void
): Promise<AllPicks> {
  const picks = emptyPicks();

  await Promise.all([
    ...FEEDS.map(async ({ sport, configKey }) => {
      try {
        const rc = repoConfig();
        const cfg = rc && rc[configKey];

        if (!cfg || cfg.enabled === false) {
          picks[sport] = [];

          return;
        }

        const rows = await loadConfigSelectedRows(configKey, dateStr, signal);

        picks[sport] = processConfigPicks(rows, configKey, sport === "mlb_lineups" ? "mlb" : sport, dateStr);
      } catch {
        picks[sport] = [];
      }
    }),
    loadUFCPicks(signal, onUfcEvent).then((p) => {
      picks.ufc = p;
    }),
  ]);

  return picks;
}

// ---------------------------------------------------------------- account preferences

export type AccountPreferences = {
  csrfToken: string | null;
  bankroll: unknown;
  kelly_fraction: unknown;
};

// Returns null when not signed in or on any failure (anonymous behavior unchanged).
export async function fetchAccountPreferences(signal?: AbortSignal): Promise<AccountPreferences | null> {
  try {
    const response = await fetch(PREFERENCES_URL, {
      credentials: "include",
      headers: { Accept: "application/json" },
      signal,
    });

    if (!response.ok) return null;

    const data = await response.json();

    if (!data.authenticated) return null;

    return {
      csrfToken: data.csrfToken || null,
      bankroll: data.bankroll,
      kelly_fraction: data.kelly_fraction,
    };
  } catch {
    return null;
  }
}

// Returns the new CSRF token if the server sent one, otherwise null.
export async function saveAccountPreferences(patch: Record<string, unknown>, csrfToken: string): Promise<string | null> {
  try {
    const response = await fetch(PREFERENCES_URL, {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(patch),
    });

    if (!response.ok) return null;

    const data = await response.json();

    return data.csrfToken ? data.csrfToken : null;
  } catch {
    return null;
  }
}
