// Shared data layer for the Bet History Daily page.
// Ported from legacy assets/js/bet-history/{sources,csv,normalize}.js and the data/formatting
// functions of assets/js/pages/index.js (public copies, which are the ones the page loaded),
// with AbortSignal support added to the fetches.

export type Row = Record<string, any>;

export type NormalizedRow = {
  source: string;
  league: string;
  league_sub: string;
  game_date: string;
  game_time: string;
  matchup: string;
  market: string;
  market_raw: string;
  bet_side: string;
  pick: string;
  line: number | null;
  odds: number | null;
  odds_display: string;
  model_prob: number | null;
  ev: number | null;
  kelly: number | null;
  edge: number | null;
  profit_unit: number | null;
  profit_kelly: number | null;
  profit_display: string;
  result: string;
};

export type Source = {
  url?: string;
  urls?: string[];
  indexUrl?: string;
  indexItemToUrl?: (item: any) => string;
  datePattern?: (date: string) => string;
  startDate?: string;
  endDate?: string;
  label: string;
  enabled?: boolean;
};

// Legacy public/assets/js/bet-history/sources.js
export const SOURCES: Source[] = [
  { url: "history-data/MLB.csv", label: "MLB", enabled: true },
  { url: "history-data/MLB_LINEUPS.csv", label: "MLB_LINEUPS", enabled: true },
  { url: "history-data/WNBA.csv", label: "WNBA", enabled: true },
  { url: "history-data/NHL.csv", label: "NHL", enabled: true },
  { url: "history-data/SOCCER.csv", label: "SOCCER", enabled: true },
  { url: "history-data/UFC.csv", label: "UFC", enabled: true },
];

// ---- csv.js -------------------------------------------------------------

export function parseCSV(text: string): Row[] {
  const rows: string[][] = [];
  let current: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const next = text[i + 1];

    if (char === '"' && inQuotes && next === '"') {
      field += '"';
      i++;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      current.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") i++;
      current.push(field);
      field = "";

      if (current.some((v) => v.trim() !== "")) {
        rows.push(current);
      }

      current = [];
    } else {
      field += char;
    }
  }

  if (field || current.length) {
    current.push(field);

    if (current.some((v) => v.trim() !== "")) {
      rows.push(current);
    }
  }

  if (rows.length < 2) return [];

  const headers = rows[0].map((h) => h.trim().toLowerCase().replace(/"/g, ""));

  return rows.slice(1).map((row) => {
    const obj: Row = {};

    headers.forEach((h, i) => {
      obj[h] = (row[i] || "").trim().replace(/^"|"$/g, "");
    });

    return obj;
  });
}

// ---- normalize.js -------------------------------------------------------

function parseNum(value: any): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = parseFloat(value);
  return isNaN(n) ? null : n;
}

function firstNum(...args: any[]): number | null {
  for (let i = 0; i < args.length; i++) {
    const n = parseNum(args[i]);
    if (n !== null) return n;
  }
  return null;
}

function firstText(...args: any[]): string {
  for (let i = 0; i < args.length; i++) {
    const v = args[i];
    if (v !== null && v !== undefined && String(v).trim() !== "") {
      return String(v).trim();
    }
  }
  return "";
}

function normalizeResult(r: Row): string {
  const resultCol = ["bet_result", "result", "outcome", "win", "won", "correct"].find(
    (c) => r[c] !== undefined && r[c] !== ""
  );

  const resultVal = resultCol ? String(r[resultCol]).toLowerCase().trim() : "";

  if (resultVal === "win" || resultVal === "w" || resultVal === "1" || resultVal === "true") return "win";
  if (resultVal === "loss" || resultVal === "l" || resultVal === "0" || resultVal === "false") return "loss";
  if (resultVal === "push" || resultVal === "p" || resultVal === "void" || resultVal === "tie") return "push";

  return "unknown";
}

function normalizeMarket(r: Row): string {
  const leagueNames = [
    "NBA",
    "NCAAM",
    "NCAAB",
    "WNBA",
    "NHL",
    "MLB",
    "SOCCER",
    "BUNDESLIGA",
    "EPL",
    "LALIGA",
    "LIGUE1",
    "SERIEA",
    "MLS",
  ];

  let mktRaw = r.market_type || "";

  if (!mktRaw) {
    const candidate = (r.market || "").toUpperCase().trim();
    if (leagueNames.indexOf(candidate) === -1) mktRaw = r.market || "";
  }

  const mkt = String(mktRaw).toLowerCase().trim();

  if (mkt === "moneyline" || mkt === "match_odds" || mkt === "ml") return "moneyline";
  if (mkt === "spread" || mkt === "puck_line" || mkt === "run_line" || mkt === "line") return "spread";
  if (
    mkt === "total" ||
    mkt === "over_total" ||
    mkt === "under_total" ||
    mkt === "btts" ||
    mkt === "total25" ||
    mkt === "total35"
  )
    return "total";

  return "other";
}

function normalizeLeague(r: Row, sourceLabel: string): string {
  const leagueRaw = (r.league || "").toUpperCase().trim();

  if (sourceLabel === "SOCCER") return "SOCCER";
  if (leagueRaw === "NCAAB") return "NCAAM";
  if (leagueRaw) return leagueRaw;

  return sourceLabel;
}

function formatLineValue(value: any): string {
  if (value === null || value === undefined || value === "") return "";

  const n = parseNum(value);
  if (n === null) return String(value);

  return n > 0 ? "+" + n : String(n);
}

function normalizeLine(r: Row, market: string, betSide: string): string {
  const line = firstText(r.bet_line, r.line);

  if (line) return line;

  if (market === "spread") {
    if (betSide === "home") {
      return firstText(r.home_spread, r.home_puck_line, r.home_run_line);
    }

    if (betSide === "away") {
      return firstText(r.away_spread, r.away_puck_line, r.away_run_line);
    }
  }

  if (market === "total") {
    return firstText(r.total, r.dk_total);
  }

  return "";
}

function normalizeOdds(r: Row, betSide: string): number | null {
  let oddsAmerican = firstNum(r.bet_odds_american, r.dk_odds_american, r.odds_american, r.american_odds);

  if (oddsAmerican === null) {
    if (betSide === "home") {
      oddsAmerican = firstNum(
        r.home_dk_moneyline_american,
        r.home_dk_spread_american,
        r.home_dk_puck_line_american,
        r.home_dk_run_line_american,
        r.dk_home_puck_line
      );
    } else if (betSide === "away") {
      oddsAmerican = firstNum(
        r.away_dk_moneyline_american,
        r.away_dk_spread_american,
        r.away_dk_puck_line_american,
        r.away_dk_run_line_american,
        r.dk_away_puck_line
      );
    } else if (betSide === "over") {
      oddsAmerican = firstNum(r.dk_total_over_american);
    } else if (betSide === "under") {
      oddsAmerican = firstNum(r.dk_total_under_american);
    }
  }

  if (oddsAmerican === null) {
    const dec = firstNum(r.odds, r.dk_odds_decimal);

    if (dec !== null) {
      oddsAmerican = dec >= 2 ? Math.round((dec - 1) * 100) : Math.round(-100 / (dec - 1));
    }
  }

  return oddsAmerican;
}

function normalizeOddsDisplay(r: Row, betSide: string): string {
  if (String(r.sport || "").toLowerCase() === "soccer" || firstText(r.odds)) {
    const soccerOdds = firstText(r.odds);
    if (soccerOdds) return soccerOdds;
  }

  const odds = normalizeOdds(r, betSide);

  if (odds === null) return "";

  return odds > 0 ? "+" + odds : String(odds);
}

function normalizeModelProb(r: Row, betSide: string): number | null {
  let modelProb = firstNum(r.bet_model_prob, r.model_prob);

  if (modelProb === null) {
    if (betSide === "home") {
      modelProb = firstNum(r.home_model_prob, r.home_prob);
    } else if (betSide === "away") {
      modelProb = firstNum(r.away_model_prob, r.away_prob);
    } else if (betSide === "over") {
      modelProb = firstNum(r.over_model_prob, r.over_prob);
    } else if (betSide === "under") {
      modelProb = firstNum(r.under_model_prob, r.under_prob);
    }
  }

  if (modelProb !== null && modelProb > 1) modelProb = modelProb / 100;

  return modelProb;
}

function normalizeMatchup(r: Row): string {
  const away = firstText(r.away_team, r.score_away_team);
  const home = firstText(r.home_team, r.score_home_team);

  if (away || home) {
    return (away || "Away") + " @ " + (home || "Home");
  }

  return firstText(r.matchup, r.game, r.event, r.home_away);
}

function soccerTotalFromMarket(market: any, takeBet: any): string {
  const raw = String(market || takeBet || "").toLowerCase();

  const totalMatch = raw.match(/total(\d{2,3})/);
  if (totalMatch) return String(parseInt(totalMatch[1], 10) / 10);

  const takeMatch = raw.match(/(?:over|under)(\d{2,3})/);
  if (takeMatch) return String(parseInt(takeMatch[1], 10) / 10);

  return "";
}

function normalizePick(r: Row, market: string, betSide: string, line: string): string {
  let label = "";

  if (betSide === "home") {
    label = firstText(r.home_team, r.score_home_team, "Home");
  } else if (betSide === "away") {
    label = firstText(r.away_team, r.score_away_team, "Away");
  } else if (betSide === "over") {
    label = "Over";
  } else if (betSide === "under") {
    label = "Under";
  } else if (betSide === "draw") {
    label = "Draw";
  } else if (betSide === "yes") {
    label = "Yes";
  } else if (betSide === "no") {
    label = "No";
  } else {
    label = firstText(r.take_bet, r.bet_side, r.side, r.pick);
  }

  if (String(r.sport || "").toLowerCase() === "soccer") {
    const soccerMarket = String(firstText(r.market_type, r.market)).toLowerCase();
    const soccerLine = soccerTotalFromMarket(soccerMarket, r.take_bet);

    if (soccerMarket === "match_odds") {
      return label;
    }

    if (soccerMarket === "btts") {
      return "BTTS " + label;
    }

    if (soccerLine && (betSide === "over" || betSide === "under")) {
      return label + " " + soccerLine;
    }

    return firstText(r.take_bet, label);
  }

  if (market === "spread") {
    return (label + " " + formatLineValue(line)).trim();
  }

  if (market === "total") {
    return (label + " " + line).trim();
  }

  if (market === "moneyline") {
    if (label && label !== "Home" && label !== "Away") return label + " ML";
    return label;
  }

  return label;
}

function normalizeProfitDisplay(value: any): string {
  const n = parseNum(value);

  if (n === null) return "";

  return n > 0 ? "+" + n.toFixed(2) : n.toFixed(2);
}

export function normalizeRow(r: Row, sourceLabel: string): NormalizedRow {
  const betSide = String(firstText(r.bet_side, r.side, r.take_bet, r.pick)).toLowerCase().trim();

  const league = normalizeLeague(r, sourceLabel);
  const leagueSub = (r.league || "").toUpperCase().trim();
  const market = normalizeMarket(r);
  const line = normalizeLine(r, market, betSide);
  const odds = normalizeOdds(r, betSide);
  const profitUnit = firstNum(r.profit_unit, r.profit, r.pnl, r.units, r.profit_loss);

  return {
    source: sourceLabel,
    league,
    league_sub: leagueSub,

    game_date: firstText(r.game_date, r.match_date, r.date, r.score_game_date),
    game_time: firstText(r.game_time, r.match_time, r.score_match_time),
    matchup: normalizeMatchup(r),

    market,
    market_raw: firstText(r.market_type, r.market),
    bet_side: firstText(r.bet_side, r.side, r.take_bet, r.pick),
    pick: normalizePick(r, market, betSide, line),

    line: parseNum(line),
    odds,
    odds_display: normalizeOddsDisplay(r, betSide),

    model_prob: normalizeModelProb(r, betSide),
    ev: firstNum(r.bet_ev, r.ev, r.selected_ev, r.edge_pct),
    kelly: firstNum(r.bet_kelly, r.kelly),
    edge: firstNum(r.bet_edge_vs_market, r.edge_vs_market, r.edge),

    profit_unit: profitUnit,
    profit_kelly: firstNum(r.profit_kelly),
    profit_display: normalizeProfitDisplay(profitUnit),

    result: normalizeResult(r),
  };
}

// ---- pages/index.js: loading --------------------------------------------

function padTwo(n: number): string {
  return n < 10 ? "0" + n : String(n);
}

function todayFileDate(): string {
  const d = new Date();
  return d.getFullYear() + "_" + padTwo(d.getMonth() + 1) + "_" + padTwo(d.getDate());
}

function normalizeFileDate(value: any): string {
  return String(value || "").trim().split("-").join("_");
}

function dateFromFileDate(value: any): Date | null {
  const parts = normalizeFileDate(value)
    .split("_")
    .map((v) => parseInt(v, 10));

  if (parts.length !== 3 || parts.some((v) => isNaN(v))) {
    return null;
  }

  return new Date(parts[0], parts[1] - 1, parts[2]);
}

function fileDateFromDate(d: Date): string {
  return d.getFullYear() + "_" + padTwo(d.getMonth() + 1) + "_" + padTwo(d.getDate());
}

function buildDateList(startDate: any, endDate: any): string[] {
  const start = dateFromFileDate(startDate);
  const end = dateFromFileDate(endDate || todayFileDate());
  const dates: string[] = [];

  if (!start || !end || start > end) return dates;

  const current = new Date(start.getTime());

  while (current <= end) {
    dates.push(fileDateFromDate(current));
    current.setDate(current.getDate() + 1);
  }

  return dates;
}

function fetchSourceUrl(url: string, label: string, warnOnFail: boolean, signal: AbortSignal): Promise<Row[]> {
  return fetch(url, { signal })
    .then((response) => {
      if (!response.ok) {
        throw new Error(label + " " + response.status);
      }
      return response.text();
    })
    .then((text) => parseCSV(text))
    .catch((error) => {
      if (warnOnFail && !signal.aborted) {
        console.warn("Failed to load " + label + ":", error);
      }
      return [] as Row[];
    });
}

function resolveSourceUrls(source: Source, signal: AbortSignal): Promise<string[]> {
  if (Array.isArray(source.urls)) {
    return Promise.resolve(source.urls);
  }

  if (source.url) {
    return Promise.resolve([source.url]);
  }

  if (source.indexUrl) {
    return fetch(source.indexUrl, { signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(source.label + " index " + response.status);
        }
        return response.json();
      })
      .then((items) => {
        if (!Array.isArray(items)) return [] as string[];

        if (typeof source.indexItemToUrl === "function") {
          const toUrl = source.indexItemToUrl;

          return items.map((item) => toUrl(item)).filter((url) => !!url);
        }

        return [] as string[];
      })
      .catch((error) => {
        if (!signal.aborted) {
          console.warn("Failed to load " + source.label + " index:", error);
        }
        return [] as string[];
      });
  }

  if (typeof source.datePattern === "function") {
    const pattern = source.datePattern;

    return Promise.resolve(buildDateList(source.startDate, source.endDate).map((date) => pattern(date)));
  }

  return Promise.resolve([] as string[]);
}

function loadSource(source: Source, signal: AbortSignal): Promise<{ label: string; rows: Row[] }> {
  return resolveSourceUrls(source, signal).then((urls) => {
    if (!urls.length) {
      return { label: source.label, rows: [] as Row[] };
    }

    const warnOnFail = !source.datePattern;

    return Promise.all(urls.map((url) => fetchSourceUrl(url, source.label, warnOnFail, signal))).then((groups) => ({
      label: source.label,
      rows: groups.reduce((all, rows) => all.concat(rows), [] as Row[]),
    }));
  });
}

function prepareSourceRow(row: Row, sourceLabel: string): Row {
  if (sourceLabel === "MLB_LINEUPS") {
    const lineupRow = Object.assign({}, row);
    lineupRow.league = "MLB_LINEUPS";
    return lineupRow;
  }

  if (sourceLabel === "UFC") {
    const bet = String(row.bet || "").toLowerCase().trim();
    const fighterIndex = bet === "fighter_1" ? 1 : bet === "fighter_2" ? 2 : 0;

    if (!fighterIndex) return row;

    const ufcRow = Object.assign({}, row);
    const fighter = fighterIndex === 1 ? row.fighter_1 : row.fighter_2;

    ufcRow.sport = "mma";
    ufcRow.league = "UFC";
    ufcRow.game_date = row.match_date;
    ufcRow.matchup = [row.fighter_1, row.fighter_2].filter(Boolean).join(" vs ");
    ufcRow.market_type = "moneyline";
    ufcRow.bet_side = fighter;
    ufcRow.take_bet = fighter;
    ufcRow.dk_odds_american = fighterIndex === 1 ? row.moneyline_f1 : row.moneyline_f2;
    ufcRow.model_prob = fighterIndex === 1 ? row.model_prob_f1 : row.model_prob_f2;
    ufcRow.ev = fighterIndex === 1 ? row.ev_f1 : row.ev_f2;
    ufcRow.kelly = fighterIndex === 1 ? row.kelly_f1 : row.kelly_f2;
    ufcRow.edge = fighterIndex === 1 ? row.edge_f1 : row.edge_f2;
    ufcRow.bet_result = fighterIndex === 1 ? row.result_fighter_1 : row.result_fighter_2;

    return ufcRow;
  }

  return row;
}

export type LoadOutcome =
  | { kind: "no-sources" }
  | { kind: "loaded"; graded: NormalizedRow[] }
  | { kind: "failed" };

// Legacy loadHomepage(): loads every enabled source, keeps win/loss/push rows.
export async function loadCompletedBets(signal: AbortSignal): Promise<LoadOutcome> {
  const activeSources = SOURCES.filter((source) => source.enabled !== false);

  if (!activeSources.length) return { kind: "no-sources" };

  try {
    const results = await Promise.all(activeSources.map((source) => loadSource(source, signal)));

    const allRows: NormalizedRow[] = [];

    results.forEach((result) => {
      result.rows.forEach((row) => {
        const prepared = prepareSourceRow(row, result.label);
        allRows.push(normalizeRow(prepared, result.label));
      });
    });

    const graded = allRows.filter((row) => row.result === "win" || row.result === "loss" || row.result === "push");

    return { kind: "loaded", graded };
  } catch (error) {
    if (!signal.aborted) console.error("Homepage load failed:", error);
    return { kind: "failed" };
  }
}

// ---- pages/index.js: formatting and summaries ---------------------------

export function winRateClass(rate: number): string {
  if (rate >= 0.55) return "val-green";
  if (rate < 0.45) return "val-red";
  return "val-yellow";
}

export function formatProfit(value: any): string {
  const n = parseFloat(value);
  if (isNaN(n)) return "N/A";
  return (n > 0 ? "+" : "") + n.toFixed(2) + "u";
}

function cleanDate(value: any): string {
  return String(value || "").trim().split("_").join("-");
}

export function formatDateLong(value: any): string {
  const clean = cleanDate(value);
  const parts = clean.split("-");

  if (parts.length !== 3) return clean || "Unknown Date";

  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10);
  const day = parseInt(parts[2], 10);

  if (isNaN(year) || isNaN(month) || isNaN(day) || month < 1 || month > 12) {
    return clean || "Unknown Date";
  }

  const monthNames = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  return monthNames[month - 1] + " " + day + ", " + year;
}

export type Summary = {
  completed: string;
  record: string;
  winRate: string;
  modelProb: string;
  profit: string;
  recordClass: string;
  winRateClass: string;
  profitClass: string;
};

export function summarize(graded: NormalizedRow[]): Summary {
  const wins = graded.filter((row) => row.result === "win").length;
  const losses = graded.filter((row) => row.result === "loss").length;
  const pushes = graded.filter((row) => row.result === "push").length;

  const decisions = wins + losses;
  const winRate = decisions ? wins / decisions : null;

  const probabilityRows = graded.filter((row) => row.model_prob !== null);

  const avgProbability = probabilityRows.length
    ? probabilityRows.reduce((sum, row) => sum + (row.model_prob as number), 0) / probabilityRows.length
    : null;

  const profitRows = graded.filter((row) => row.profit_unit !== null);
  const totalProfit = profitRows.reduce((sum, row) => sum + (row.profit_unit as number), 0);

  return {
    completed: graded.length.toLocaleString(),
    record: wins + "-" + losses + "-" + pushes,
    winRate: winRate === null ? "N/A" : (winRate * 100).toFixed(1) + "%",
    modelProb: avgProbability === null ? "N/A" : (avgProbability * 100).toFixed(1) + "%",
    profit: profitRows.length ? formatProfit(totalProfit) : "N/A",
    recordClass: winRate === null ? "" : winRateClass(winRate),
    winRateClass: winRate === null ? "" : winRateClass(winRate),
    profitClass: profitRows.length ? (totalProfit >= 0 ? "val-green" : "val-red") : "",
  };
}

export type DayCard = {
  date: string;
  count: string;
  record: string;
  recordClass: string;
  rateText: string;
  rateClass: string;
  profitText: string;
  profitClass: string;
};

export function buildDayCards(graded: NormalizedRow[]): DayCard[] {
  const groups: Record<string, NormalizedRow[]> = {};

  graded.forEach((row) => {
    const key = cleanDate(row.game_date);

    if (!key) return;

    if (!groups[key]) {
      groups[key] = [];
    }

    groups[key].push(row);
  });

  return Object.keys(groups)
    .sort((a, b) => b.localeCompare(a))
    .slice(0, 30)
    .map((date) => {
      const rows = groups[date];

      const wins = rows.filter((row) => row.result === "win").length;
      const losses = rows.filter((row) => row.result === "loss").length;
      const pushes = rows.filter((row) => row.result === "push").length;

      const decisions = wins + losses;
      const rate = decisions ? wins / decisions : null;

      const profitRows = rows.filter((row) => row.profit_unit !== null);
      const profit = profitRows.reduce((sum, row) => sum + (row.profit_unit as number), 0);

      return {
        date,
        count: rows.length.toLocaleString(),
        record: wins + "-" + losses + "-" + pushes,
        recordClass: rate === null ? "" : winRateClass(rate),
        rateText: rate === null ? "N/A" : (rate * 100).toFixed(1) + "%",
        rateClass: rate === null ? "" : winRateClass(rate),
        profitText: profitRows.length ? formatProfit(profit) : "N/A",
        profitClass: profitRows.length ? (profit >= 0 ? "val-green" : "val-red") : "",
      };
    });
}
