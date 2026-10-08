// Native React conversion of the Bet History page.
// CSS dependencies (unchanged, still in the legacy tree / shared):
//   app\frontend\src\assets\css\pages\bet_history.css  (legacy tree)
//   src\pages\history-react-fix.css
//   global CSS imported by src\main.tsx (matstheme.css, site-polish.css from the legacy tree)
import { useCallback, useEffect, useRef, useState } from "react";
import "../../../app/frontend/src/assets/css/pages/bet_history.css";
import "./history-react-fix.css";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type CsvRow = Record<string, string | undefined>;
type ResultKind = "win" | "loss" | "push" | "unknown";
type MarketKind = "moneyline" | "spread" | "total" | "other";

interface HistoryRow {
  source: string;
  league: string;
  league_sub: string;
  game_date: string;
  game_time: string;
  matchup: string;
  market: MarketKind;
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
  result: ResultKind;
}

interface HistorySource {
  label: string;
  enabled?: boolean;
  url?: string;
  urls?: string[];
  indexUrl?: string;
  indexItemToUrl?: (item: unknown) => string;
  datePattern?: (date: string) => string;
  startDate?: string;
  endDate?: string;
}

interface LoadedSource {
  label: string;
  rows: CsvRow[];
}

interface LeagueItem {
  key: string;
  label: string;
}

interface LeagueGroup {
  key: string;
  label: string;
  leagues: LeagueItem[];
}

interface PillData {
  league: string;
  sub?: string;
}

interface SmhWindow {
  SMHTrack?: (eventName: string, properties?: Record<string, unknown>) => void;
  __smhAnalyticsQueue?: Array<[string, Record<string, unknown>]>;
}

/* ------------------------------------------------------------------ */
/* Configuration (mirrors public\assets\js\bet-history\sources.js and   */
/* public\assets\js\shared\kelly-league-availability.js)                */
/* ------------------------------------------------------------------ */

const SOURCES: HistorySource[] = [
  { url: "history-data/MLB.csv", label: "MLB", enabled: true },
  { url: "history-data/MLB_LINEUPS.csv", label: "MLB_LINEUPS", enabled: true },
  { url: "history-data/WNBA.csv", label: "WNBA", enabled: true },
  { url: "history-data/NHL.csv", label: "NHL", enabled: true },
  { url: "history-data/SOCCER.csv", label: "SOCCER", enabled: true },
  { url: "history-data/UFC.csv", label: "UFC", enabled: true },
];

const LEAGUE_AVAILABILITY: Record<string, boolean> = {
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

// data-league / data-league-sub values of the pills present in the legacy bet_history.html
const PILL_DATA: Record<string, PillData> = {
  all: { league: "all" },
  cfb: { league: "CFB" },
  nhl: { league: "NHL" },
  mlb: { league: "MLB" },
  mlb_lineups: { league: "MLB_LINEUPS" },
  wnba: { league: "WNBA" },
  mls: { league: "SOCCER", sub: "MLS" },
  epl: { league: "SOCCER", sub: "EPL" },
  laliga: { league: "SOCCER", sub: "LALIGA" },
  ligue1: { league: "SOCCER", sub: "LIGUE1" },
  seriea: { league: "SOCCER", sub: "SERIEA" },
  bundesliga: { league: "SOCCER", sub: "BUNDESLIGA" },
  ufc: { league: "UFC" },
};

const GROUP_FOOTBALL: LeagueGroup = {
  key: "football",
  label: "Football",
  leagues: [
    { key: "nfl", label: "NFL" },
    { key: "cfb", label: "College Football" },
    { key: "cfl", label: "CFL" },
  ],
};

const GROUP_MLB: LeagueGroup = {
  key: "mlb",
  label: "MLB",
  leagues: [
    { key: "mlb", label: "MLB" },
    { key: "mlb_lineups", label: "MLB \u00b7 With Lineups" },
  ],
};

const GROUP_BASKETBALL: LeagueGroup = {
  key: "basketball",
  label: "Basketball",
  leagues: [
    { key: "nba", label: "NBA" },
    { key: "ncaam", label: "College Basketball" },
    { key: "wnba", label: "WNBA" },
  ],
};

const GROUP_SOCCER: LeagueGroup = {
  key: "soccer",
  label: "Soccer",
  leagues: [
    { key: "mls", label: "MLS" },
    { key: "epl", label: "EPL" },
    { key: "laliga", label: "La Liga" },
    { key: "ligue1", label: "Ligue 1" },
    { key: "seriea", label: "Serie A" },
    { key: "bundesliga", label: "Bundesliga" },
  ],
};

const MARKET_PILLS: LeagueItem[] = [
  { key: "all", label: "All Markets" },
  { key: "moneyline", label: "Moneyline" },
  { key: "spread", label: "Spread / Line" },
  { key: "total", label: "Total" },
];

const RESULT_PILLS: LeagueItem[] = [
  { key: "all", label: "All Results" },
  { key: "win", label: "Wins" },
  { key: "loss", label: "Losses" },
  { key: "push", label: "Push" },
];

const SORT_OPTIONS: LeagueItem[] = [
  { key: "newest", label: "Newest First" },
  { key: "oldest", label: "Oldest First" },
  { key: "best_profit", label: "Best P/L" },
  { key: "worst_profit", label: "Worst P/L" },
  { key: "highest_ev", label: "Highest EV" },
  { key: "lowest_ev", label: "Lowest EV" },
  { key: "league", label: "League A-Z" },
];

// Same CSS text the legacy league_nav.js injected into <head> as #shared-league-nav-style.
const LEAGUE_NAV_CSS = `
      #league-controls.shared-league-nav-host {
        display: flex !important;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        width: 100%;
        position: relative;
        z-index: 20;
      }

      #league-controls .shared-league-nav-main {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }

      #league-controls .shared-league-nav-aux {
        margin-left: auto;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }

      #league-controls .control-group {
        position: relative;
        display: inline-flex;
        align-items: center;
      }

      #league-controls .league-pill,
      #league-controls .group-pill,
      #league-controls .submenu-pill {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.08em;
        padding: 4px 12px;
        border: 1px solid var(--border-soft);
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
        transition: all 0.15s;
        text-transform: uppercase;
        line-height: 1.2;
        white-space: nowrap;
      }

      #league-controls .league-pill:hover,
      #league-controls .group-pill:hover,
      #league-controls .submenu-pill:hover {
        border-color: var(--accent-blue);
        color: var(--accent-blue);
      }

      #league-controls .league-pill.active,
      #league-controls .group-pill.active,
      #league-controls .submenu-pill.active {
        border-color: var(--accent-green);
        color: var(--accent-green);
        background: rgba(0,255,132,0.06);
      }

      #league-controls .group-pill::after {
        content: " \u25be";
        color: var(--text-muted);
        font-size: 10px;
        letter-spacing: 0;
      }

      #league-controls .group-pill:hover::after,
      #league-controls .group-pill.active::after {
        color: var(--accent-green);
      }

      #league-controls .control-group.open .group-pill {
        border-color: var(--accent-blue);
        color: var(--accent-blue);
        background: rgba(0,191,255,0.04);
      }

      #league-controls .control-group.open .group-pill.active {
        border-color: var(--accent-green);
        color: var(--accent-green);
        background: rgba(0,255,132,0.06);
      }

      #league-controls .submenu {
        position: absolute;
        top: calc(100% + 6px);
        left: 0;
        min-width: 190px;
        display: none;
        flex-direction: column;
        gap: 6px;
        padding: 8px;
        background: #121923;
        border: 1px solid var(--text-muted);
        box-shadow: 0 18px 44px rgba(0,0,0,0.75);
        z-index: 50;
      }

      #league-controls .control-group.open .submenu {
        display: flex;
      }

      #league-controls .submenu-pill {
        width: 100%;
        text-align: left;
        background: var(--bg-card);
      }

      #league-controls .shared-league-unavailable {
        opacity: 0.38;
        cursor: not-allowed;
        border-style: dashed;
      }

      #league-controls .shared-league-unavailable:hover {
        border-color: var(--border-soft);
        color: var(--text-muted);
        background: transparent;
      }

      #league-controls .shared-group-unavailable {
        opacity: 0.62;
      }

      @media (max-width: 820px) {
        #league-controls.shared-league-nav-host {
          align-items: stretch;
        }

        #league-controls .shared-league-nav-main,
        #league-controls .shared-league-nav-aux {
          width: 100%;
        }

        #league-controls .control-group {
          width: 100%;
          flex-direction: column;
          align-items: stretch;
        }

        #league-controls .league-pill,
        #league-controls .group-pill {
          width: 100%;
          text-align: left;
        }

        #league-controls .submenu {
          position: static;
          width: 100%;
          min-width: 0;
          margin-top: 6px;
          box-shadow: none;
          background: transparent;
        }

        #league-controls .submenu-pill {
          padding-left: 22px;
        }

        #league-controls .shared-league-nav-aux {
          margin-left: 0;
        }

        #league-controls .shared-league-nav-aux > * {
          width: 100%;
          margin-left: 0 !important;
        }
      }
    `;

/* ------------------------------------------------------------------ */
/* csv.js                                                              */
/* ------------------------------------------------------------------ */

function parseCSV(text: string): CsvRow[] {
  const rows: string[][] = [];
  let current: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const char = text.charAt(i);
    const next = text.charAt(i + 1);

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

  const headerRow = rows[0];
  if (rows.length < 2 || !headerRow) return [];

  const headers = headerRow.map((h) => h.trim().toLowerCase().replace(/"/g, ""));

  return rows.slice(1).map((row) => {
    const obj: CsvRow = {};

    headers.forEach((h, i) => {
      obj[h] = (row[i] || "").trim().replace(/^"|"$/g, "");
    });

    return obj;
  });
}

/* ------------------------------------------------------------------ */
/* normalize.js                                                        */
/* ------------------------------------------------------------------ */

function parseNum(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = parseFloat(String(value));
  return isNaN(n) ? null : n;
}

function firstNum(...values: unknown[]): number | null {
  for (let i = 0; i < values.length; i++) {
    const n = parseNum(values[i]);
    if (n !== null) return n;
  }
  return null;
}

function firstText(...values: unknown[]): string {
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v !== null && v !== undefined && String(v).trim() !== "") {
      return String(v).trim();
    }
  }
  return "";
}

function normalizeResult(r: CsvRow): ResultKind {
  const resultCol = ["bet_result", "result", "outcome", "win", "won", "correct"].find(
    (c) => r[c] !== undefined && r[c] !== ""
  );

  const resultVal = resultCol ? String(r[resultCol]).toLowerCase().trim() : "";

  if (resultVal === "win" || resultVal === "w" || resultVal === "1" || resultVal === "true") return "win";
  if (resultVal === "loss" || resultVal === "l" || resultVal === "0" || resultVal === "false") return "loss";
  if (resultVal === "push" || resultVal === "p" || resultVal === "void" || resultVal === "tie") return "push";

  return "unknown";
}

function normalizeMarket(r: CsvRow): MarketKind {
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

  let mktRaw = r["market_type"] || "";

  if (!mktRaw) {
    const candidate = (r["market"] || "").toUpperCase().trim();
    if (leagueNames.indexOf(candidate) === -1) mktRaw = r["market"] || "";
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
  ) {
    return "total";
  }

  return "other";
}

function normalizeLeague(r: CsvRow, sourceLabel: string): string {
  const leagueRaw = (r["league"] || "").toUpperCase().trim();

  if (sourceLabel === "SOCCER") return "SOCCER";
  if (leagueRaw === "NCAAB") return "NCAAM";
  if (leagueRaw) return leagueRaw;

  return sourceLabel;
}

function formatLineValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "";

  const n = parseNum(value);
  if (n === null) return String(value);

  return n > 0 ? "+" + n : String(n);
}

function normalizeLine(r: CsvRow, market: MarketKind, betSide: string): string {
  const line = firstText(r["bet_line"], r["line"]);

  if (line) return line;

  if (market === "spread") {
    if (betSide === "home") {
      return firstText(r["home_spread"], r["home_puck_line"], r["home_run_line"]);
    }

    if (betSide === "away") {
      return firstText(r["away_spread"], r["away_puck_line"], r["away_run_line"]);
    }
  }

  if (market === "total") {
    return firstText(r["total"], r["dk_total"]);
  }

  return "";
}

function normalizeOdds(r: CsvRow, betSide: string): number | null {
  let oddsAmerican = firstNum(
    r["bet_odds_american"],
    r["dk_odds_american"],
    r["odds_american"],
    r["american_odds"]
  );

  if (oddsAmerican === null) {
    if (betSide === "home") {
      oddsAmerican = firstNum(
        r["home_dk_moneyline_american"],
        r["home_dk_spread_american"],
        r["home_dk_puck_line_american"],
        r["home_dk_run_line_american"],
        r["dk_home_puck_line"]
      );
    } else if (betSide === "away") {
      oddsAmerican = firstNum(
        r["away_dk_moneyline_american"],
        r["away_dk_spread_american"],
        r["away_dk_puck_line_american"],
        r["away_dk_run_line_american"],
        r["dk_away_puck_line"]
      );
    } else if (betSide === "over") {
      oddsAmerican = firstNum(r["dk_total_over_american"]);
    } else if (betSide === "under") {
      oddsAmerican = firstNum(r["dk_total_under_american"]);
    }
  }

  if (oddsAmerican === null) {
    const dec = firstNum(r["odds"], r["dk_odds_decimal"]);

    if (dec !== null) {
      oddsAmerican = dec >= 2 ? Math.round((dec - 1) * 100) : Math.round(-100 / (dec - 1));
    }
  }

  return oddsAmerican;
}

function normalizeOddsDisplay(r: CsvRow, betSide: string): string {
  if (String(r["sport"] || "").toLowerCase() === "soccer" || firstText(r["odds"])) {
    const soccerOdds = firstText(r["odds"]);
    if (soccerOdds) return soccerOdds;
  }

  const odds = normalizeOdds(r, betSide);

  if (odds === null) return "";

  return odds > 0 ? "+" + odds : String(odds);
}

function normalizeModelProb(r: CsvRow, betSide: string): number | null {
  let modelProb = firstNum(r["bet_model_prob"], r["model_prob"]);

  if (modelProb === null) {
    if (betSide === "home") {
      modelProb = firstNum(r["home_model_prob"], r["home_prob"]);
    } else if (betSide === "away") {
      modelProb = firstNum(r["away_model_prob"], r["away_prob"]);
    } else if (betSide === "over") {
      modelProb = firstNum(r["over_model_prob"], r["over_prob"]);
    } else if (betSide === "under") {
      modelProb = firstNum(r["under_model_prob"], r["under_prob"]);
    }
  }

  if (modelProb !== null && modelProb > 1) modelProb = modelProb / 100;

  return modelProb;
}

function normalizeMatchup(r: CsvRow): string {
  const away = firstText(r["away_team"], r["score_away_team"]);
  const home = firstText(r["home_team"], r["score_home_team"]);

  if (away || home) {
    return (away || "Away") + " @ " + (home || "Home");
  }

  return firstText(r["matchup"], r["game"], r["event"], r["home_away"]);
}

function soccerTotalFromMarket(market: unknown, takeBet: unknown): string {
  const raw = String(market || takeBet || "").toLowerCase();

  const totalMatch = raw.match(/total(\d{2,3})/);
  if (totalMatch) return String(parseInt(totalMatch[1] || "", 10) / 10);

  const takeMatch = raw.match(/(?:over|under)(\d{2,3})/);
  if (takeMatch) return String(parseInt(takeMatch[1] || "", 10) / 10);

  return "";
}

function normalizePick(r: CsvRow, market: MarketKind, betSide: string, line: string): string {
  let label = "";

  if (betSide === "home") {
    label = firstText(r["home_team"], r["score_home_team"], "Home");
  } else if (betSide === "away") {
    label = firstText(r["away_team"], r["score_away_team"], "Away");
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
    label = firstText(r["take_bet"], r["bet_side"], r["side"], r["pick"]);
  }

  if (String(r["sport"] || "").toLowerCase() === "soccer") {
    const soccerMarket = String(firstText(r["market_type"], r["market"])).toLowerCase();
    const soccerLine = soccerTotalFromMarket(soccerMarket, r["take_bet"]);

    if (soccerMarket === "match_odds") {
      return label;
    }

    if (soccerMarket === "btts") {
      return "BTTS " + label;
    }

    if (soccerLine && (betSide === "over" || betSide === "under")) {
      return label + " " + soccerLine;
    }

    return firstText(r["take_bet"], label);
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

function normalizeProfitDisplay(value: unknown): string {
  const n = parseNum(value);

  if (n === null) return "";

  return n > 0 ? "+" + n.toFixed(2) : n.toFixed(2);
}

function normalizeRow(r: CsvRow, sourceLabel: string): HistoryRow {
  const betSide = String(firstText(r["bet_side"], r["side"], r["take_bet"], r["pick"])).toLowerCase().trim();

  const league = normalizeLeague(r, sourceLabel);
  const leagueSub = (r["league"] || "").toUpperCase().trim();
  const market = normalizeMarket(r);
  const line = normalizeLine(r, market, betSide);
  const odds = normalizeOdds(r, betSide);
  const profitUnit = firstNum(r["profit_unit"], r["profit"], r["pnl"], r["units"], r["profit_loss"]);

  return {
    source: sourceLabel,
    league: league,
    league_sub: leagueSub,

    game_date: firstText(r["game_date"], r["match_date"], r["date"], r["score_game_date"]),
    game_time: firstText(r["game_time"], r["match_time"], r["score_match_time"]),
    matchup: normalizeMatchup(r),

    market: market,
    market_raw: firstText(r["market_type"], r["market"]),
    bet_side: firstText(r["bet_side"], r["side"], r["take_bet"], r["pick"]),
    pick: normalizePick(r, market, betSide, line),

    line: parseNum(line),
    odds: odds,
    odds_display: normalizeOddsDisplay(r, betSide),

    model_prob: normalizeModelProb(r, betSide),
    ev: firstNum(r["bet_ev"], r["ev"], r["selected_ev"], r["edge_pct"]),
    kelly: firstNum(r["bet_kelly"], r["kelly"]),
    edge: firstNum(r["bet_edge_vs_market"], r["edge_vs_market"], r["edge"]),

    profit_unit: profitUnit,
    profit_kelly: firstNum(r["profit_kelly"]),
    profit_display: normalizeProfitDisplay(profitUnit),

    result: normalizeResult(r),
  };
}

/* ------------------------------------------------------------------ */
/* app.js (data loading)                                               */
/* ------------------------------------------------------------------ */

function padTwo(n: number): string {
  return n < 10 ? "0" + n : "" + n;
}

function todayFileDate(): string {
  const d = new Date();
  return d.getFullYear() + "_" + padTwo(d.getMonth() + 1) + "_" + padTwo(d.getDate());
}

function normalizeFileDate(value: unknown): string {
  return String(value || "").trim().split("-").join("_");
}

function dateFromFileDate(value: unknown): Date | null {
  const parts = normalizeFileDate(value)
    .split("_")
    .map((v) => parseInt(v, 10));

  if (parts.length !== 3 || parts.some((v) => isNaN(v))) {
    return null;
  }

  return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
}

function fileDateFromDate(d: Date): string {
  return d.getFullYear() + "_" + padTwo(d.getMonth() + 1) + "_" + padTwo(d.getDate());
}

function buildDateList(startDate: string | undefined, endDate: string | undefined): string[] {
  const start = dateFromFileDate(startDate);
  const end = dateFromFileDate(endDate || todayFileDate());
  const dates: string[] = [];

  if (!start || !end || start > end) return dates;

  const cur = new Date(start.getTime());
  while (cur <= end) {
    dates.push(fileDateFromDate(cur));
    cur.setDate(cur.getDate() + 1);
  }

  return dates;
}

function fetchSourceUrl(url: string, label: string, warnOnFail: boolean, signal: AbortSignal): Promise<CsvRow[]> {
  return fetch(url, { signal: signal })
    .then((res) => {
      if (!res.ok) throw new Error(label + " " + res.status);
      return res.text();
    })
    .then((text) => parseCSV(text))
    .catch((err: unknown) => {
      if (warnOnFail && !signal.aborted) console.warn("Failed to load " + label + ":", err);
      return [] as CsvRow[];
    });
}

function resolveSourceUrls(src: HistorySource, signal: AbortSignal): Promise<string[]> {
  if (Array.isArray(src.urls)) return Promise.resolve(src.urls);
  if (src.url) return Promise.resolve([src.url]);

  if (src.indexUrl) {
    const label = src.label;
    const toUrl = src.indexItemToUrl;
    const pattern = src.datePattern;

    return fetch(src.indexUrl, { signal: signal })
      .then((res) => {
        if (!res.ok) throw new Error(label + " index " + res.status);
        return res.json() as Promise<unknown>;
      })
      .then((items) => {
        if (!Array.isArray(items)) return [] as string[];

        const list: unknown[] = items;

        if (typeof toUrl === "function") {
          return list.map((item) => toUrl(item)).filter((url) => !!url);
        }

        if (typeof pattern !== "function") return [] as string[];

        return list.map((date) => pattern(normalizeFileDate(date)));
      })
      .catch((err: unknown) => {
        if (!signal.aborted) console.warn("Failed to load " + label + " index:", err);
        return [] as string[];
      });
  }

  const datePattern = src.datePattern;
  if (typeof datePattern === "function") {
    return Promise.resolve(buildDateList(src.startDate, src.endDate).map((date) => datePattern(date)));
  }

  return Promise.resolve([] as string[]);
}

function loadSource(src: HistorySource, signal: AbortSignal): Promise<LoadedSource> {
  return resolveSourceUrls(src, signal).then((urls) => {
    if (!urls.length) {
      return { label: src.label, rows: [] as CsvRow[] };
    }

    const warnOnFail = !src.datePattern;

    return Promise.all(urls.map((url) => fetchSourceUrl(url, src.label, warnOnFail, signal))).then((groups) => ({
      label: src.label,
      rows: groups.reduce((out: CsvRow[], rows) => out.concat(rows), [] as CsvRow[]),
    }));
  });
}

function prepareSourceRow(row: CsvRow, sourceLabel: string): CsvRow {
  if (sourceLabel === "MLB_LINEUPS") {
    const lineupRow: CsvRow = { ...row };
    lineupRow["league"] = "MLB_LINEUPS";
    return lineupRow;
  }

  if (sourceLabel === "UFC") {
    const bet = String(row["bet"] || "").toLowerCase().trim();
    const fighterIndex = bet === "fighter_1" ? 1 : bet === "fighter_2" ? 2 : 0;

    if (!fighterIndex) return row;

    const ufcRow: CsvRow = { ...row };
    const fighter = fighterIndex === 1 ? row["fighter_1"] : row["fighter_2"];

    ufcRow["sport"] = "mma";
    ufcRow["league"] = "UFC";
    ufcRow["game_date"] = row["match_date"];
    ufcRow["matchup"] = [row["fighter_1"], row["fighter_2"]].filter(Boolean).join(" vs ");
    ufcRow["market_type"] = "moneyline";
    ufcRow["bet_side"] = fighter;
    ufcRow["take_bet"] = fighter;
    ufcRow["dk_odds_american"] = fighterIndex === 1 ? row["moneyline_f1"] : row["moneyline_f2"];
    ufcRow["model_prob"] = fighterIndex === 1 ? row["model_prob_f1"] : row["model_prob_f2"];
    ufcRow["ev"] = fighterIndex === 1 ? row["ev_f1"] : row["ev_f2"];
    ufcRow["kelly"] = fighterIndex === 1 ? row["kelly_f1"] : row["kelly_f2"];
    ufcRow["edge"] = fighterIndex === 1 ? row["edge_f1"] : row["edge_f2"];
    ufcRow["bet_result"] = fighterIndex === 1 ? row["result_fighter_1"] : row["result_fighter_2"];

    return ufcRow;
  }

  return row;
}

function isGraded(r: HistoryRow): boolean {
  return r.result === "win" || r.result === "loss" || r.result === "push";
}

/* ------------------------------------------------------------------ */
/* app.js (analytics)                                                  */
/* ------------------------------------------------------------------ */

function trackHistoryFilter(
  filterType: string,
  filterValue: string,
  league: string,
  betType: string,
  result: string
): void {
  const props: Record<string, unknown> = {
    filter_type: filterType,
    filter_value: filterValue,
    league: league || "all",
    bet_type: betType || "all",
    result: result || "all",
  };

  const w = window as unknown as SmhWindow;

  if (w.SMHTrack) {
    w.SMHTrack("bet_history_filtered", props);
  } else {
    w.__smhAnalyticsQueue = w.__smhAnalyticsQueue || [];
    w.__smhAnalyticsQueue.push(["bet_history_filtered", props]);
  }
}

/* ------------------------------------------------------------------ */
/* render.js (formatting, sorting, grouping)                           */
/* ------------------------------------------------------------------ */

function formatDateDisplay(date: string): string {
  if (!date) return "\u2014";
  return String(date).split("_").join("-");
}

function formatDateLong(date: string): string {
  if (!date) return "\u2014";

  const clean = String(date).split("_").join("-").trim();
  const parts = clean.split("-");

  if (parts.length !== 3) return clean;

  const year = parseInt(parts[0] || "", 10);
  const month = parseInt(parts[1] || "", 10);
  const day = parseInt(parts[2] || "", 10);

  if (isNaN(year) || isNaN(month) || isNaN(day)) return clean;

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

  if (month < 1 || month > 12) return clean;

  return String(monthNames[month - 1]) + " " + day + ", " + year;
}

function formatOdds(odds: number | null, oddsDisplay: string): string {
  if (oddsDisplay.trim() !== "") {
    return oddsDisplay;
  }

  if (odds === null) return "\u2014";

  const n = parseFloat(String(odds));
  if (isNaN(n)) return String(odds);

  return n > 0 ? "+" + n : String(n);
}

function formatProfit(value: number | null): string {
  if (value === null) return "\u2014";

  const n = parseFloat(String(value));
  if (isNaN(n)) return String(value);

  return n > 0 ? "+" + n.toFixed(2) + "u" : n.toFixed(2) + "u";
}

function formatPercent(value: number | null): string {
  if (value === null) return "\u2014";

  let n = parseFloat(String(value));
  if (isNaN(n)) return "\u2014";

  if (Math.abs(n) <= 1) n = n * 100;

  return n.toFixed(1) + "%";
}

function formatEV(value: number | null): string {
  if (value === null) return "\u2014";

  const n = parseFloat(String(value));
  if (isNaN(n)) return "\u2014";

  return n > 0 ? "+" + n.toFixed(2) : n.toFixed(2);
}

function formatKelly(value: number | null): string {
  if (value === null) return "\u2014";

  const n = parseFloat(String(value));
  if (isNaN(n)) return "\u2014";

  if (Math.abs(n) <= 1) return (n * 100).toFixed(1) + "%";

  return n.toFixed(2);
}

function formatMarketLabel(market: string): string {
  if (!market) return "\u2014";

  if (market === "moneyline") return "Moneyline";
  if (market === "spread") return "Spread / Line";
  if (market === "total") return "Total";

  return String(market).charAt(0).toUpperCase() + String(market).slice(1);
}

function valueClass(value: number | null): string {
  const n = parseFloat(String(value));

  if (isNaN(n) || n === 0) return "";
  return n > 0 ? "val-green" : "val-red";
}

function probabilityClass(value: number | null): string {
  let n = parseFloat(String(value));

  if (isNaN(n)) return "";
  if (n > 1) n = n / 100;

  if (n >= 0.65) return "val-green";
  if (n >= 0.5) return "val-yellow";
  return "val-red";
}

function profitClass(value: number | null): string {
  const n = parseFloat(String(value));

  if (isNaN(n) || n === 0) return "profit-flat";
  return n > 0 ? "val-green" : "val-red";
}

function outcomeClass(result: ResultKind): string {
  if (result === "win") return "outcome-w";
  if (result === "loss") return "outcome-l";
  return "outcome-p";
}

function outcomeText(result: ResultKind): string {
  if (result === "win") return "WIN";
  if (result === "loss") return "LOSS";
  if (result === "push") return "PUSH";
  return "\u2014";
}

function leagueDisplayName(r: HistoryRow): string {
  if (r.league === "SOCCER" && r.league_sub && r.league_sub !== "SOCCER") {
    return r.league + " \u00b7 " + r.league_sub;
  }

  return r.league || "\u2014";
}

function historySearchText(r: HistoryRow): string {
  return [
    formatDateDisplay(r.game_date),
    formatDateLong(r.game_date),
    leagueDisplayName(r),
    r.matchup || "",
    r.pick || "",
    r.bet_side || "",
    r.market || "",
    r.market_raw || "",
    formatOdds(r.odds, r.odds_display),
    outcomeText(r.result),
    formatProfit(r.profit_unit),
    r.model_prob !== null ? formatPercent(r.model_prob) : "",
    r.ev !== null ? String(r.ev) : "",
    r.kelly !== null ? String(r.kelly) : "",
    r.source || "",
  ]
    .join(" ")
    .toLowerCase();
}

function applyHistorySearch(rows: HistoryRow[], search: string): HistoryRow[] {
  const q = String(search || "").trim().toLowerCase();

  if (!q) return rows;

  return rows.filter((r) => historySearchText(r).indexOf(q) !== -1);
}

function compareNumberWithMissing(
  a: HistoryRow,
  b: HistoryRow,
  getter: (r: HistoryRow) => number | null,
  direction: "asc" | "desc"
): number {
  const av = getter(a);
  const bv = getter(b);

  if (av === null && bv === null) return 0;
  if (av === null) return 1;
  if (bv === null) return -1;

  return direction === "asc" ? av - bv : bv - av;
}

function sortHistoryRows(rows: HistoryRow[], historySort: string): HistoryRow[] {
  const sorted = rows.slice();

  sorted.sort((a, b) => {
    if (historySort === "oldest") {
      return String(a.game_date).localeCompare(String(b.game_date));
    }

    if (historySort === "best_profit") {
      return compareNumberWithMissing(a, b, (r) => r.profit_unit, "desc");
    }

    if (historySort === "worst_profit") {
      return compareNumberWithMissing(a, b, (r) => r.profit_unit, "asc");
    }

    if (historySort === "highest_ev") {
      return compareNumberWithMissing(a, b, (r) => r.ev, "desc");
    }

    if (historySort === "lowest_ev") {
      return compareNumberWithMissing(a, b, (r) => r.ev, "asc");
    }

    if (historySort === "league") {
      const leagueCompare = leagueDisplayName(a).localeCompare(leagueDisplayName(b));
      if (leagueCompare !== 0) return leagueCompare;
      return String(b.game_date).localeCompare(String(a.game_date));
    }

    return String(b.game_date).localeCompare(String(a.game_date));
  });

  return sorted;
}

interface DateGroup {
  date: string;
  longDate: string;
  rows: HistoryRow[];
}

function groupRowsByDate(rows: HistoryRow[]): DateGroup[] {
  const groups: DateGroup[] = [];
  const groupMap = new Map<string, DateGroup>();

  rows.forEach((r) => {
    const dateKey = formatDateDisplay(r.game_date);
    let group = groupMap.get(dateKey);

    if (!group) {
      group = {
        date: dateKey,
        longDate: formatDateLong(r.game_date),
        rows: [],
      };
      groupMap.set(dateKey, group);
      groups.push(group);
    }

    group.rows.push(r);
  });

  return groups;
}

function groupRecordText(rows: HistoryRow[]): string {
  const wins = rows.filter((r) => r.result === "win").length;
  const losses = rows.filter((r) => r.result === "loss").length;
  const pushes = rows.filter((r) => r.result === "push").length;

  return wins + "-" + losses + "-" + pushes;
}

function isLeagueSupported(key: string): boolean {
  if (Object.prototype.hasOwnProperty.call(LEAGUE_AVAILABILITY, key)) {
    return LEAGUE_AVAILABILITY[key] === true;
  }

  return Object.prototype.hasOwnProperty.call(PILL_DATA, key);
}

function rateColor(rate: number): string {
  return rate >= 0.55 ? "var(--accent-green)" : rate < 0.45 ? "var(--accent-red)" : "var(--accent-yellow)";
}

function rateClass(rate: number): string {
  return rate >= 0.55 ? "val-green" : rate < 0.45 ? "val-red" : "val-yellow";
}

/* ------------------------------------------------------------------ */
/* render.js (React components)                                        */
/* ------------------------------------------------------------------ */

function BreakdownCard(props: { title: string; rows: HistoryRow[] }) {
  const rows = props.rows;
  const wins = rows.filter((r) => r.result === "win").length;
  const losses = rows.filter((r) => r.result === "loss").length;
  const decisions = wins + losses;
  const rate = decisions ? wins / decisions : 0;

  const evRows = rows.filter((r) => r.ev !== null);
  const ev = evRows.reduce((s, r) => s + (r.ev ?? 0), 0);

  const profitRows = rows.filter((r) => r.profit_unit !== null);
  const profit = profitRows.reduce((s, r) => s + (r.profit_unit ?? 0), 0);

  return (
    <div className="breakdown-card">
      <div className="breakdown-title">{props.title}</div>
      <div className="stat-row">
        <span className="stat-label">Bets</span>
        <span className="stat-value">{rows.length}</span>
      </div>
      <div className="stat-row">
        <span className="stat-label">W-L</span>
        <span className="stat-value">{wins + "-" + losses}</span>
      </div>
      <div className="stat-row">
        <span className="stat-label">Win Rate</span>
        <span className="stat-value" style={{ color: rateColor(rate) }}>
          {(rate * 100).toFixed(1) + "%"}
        </span>
      </div>
      <div className="stat-row">
        <span className="stat-label">P/L</span>
        <span
          className="stat-value"
          style={{ color: profit >= 0 ? "var(--accent-green)" : "var(--accent-red)" }}
        >
          {profitRows.length ? formatProfit(profit) : "\u2014"}
        </span>
      </div>
      <div className="stat-row">
        <span className="stat-label">Total EV</span>
        <span className="stat-value" style={{ color: ev >= 0 ? "var(--accent-green)" : "var(--accent-red)" }}>
          {evRows.length ? ev.toFixed(2) : "\u2014"}
        </span>
      </div>
    </div>
  );
}

function DetailItem(props: { label: string; value: string; cls: string }) {
  return (
    <div className="history-detail-item">
      <div className="history-detail-label">{props.label}</div>
      <div className={"history-detail-value " + props.cls}>{props.value}</div>
    </div>
  );
}

function HistoryCard(props: { r: HistoryRow }) {
  const r = props.r;
  const outCls = outcomeClass(r.result);
  const outTxt = outcomeText(r.result);
  const profitCls = profitClass(r.profit_unit);

  return (
    <div className="history-card">
      <div className="history-card-top">
        <div className="history-card-meta">
          <span className="history-league-pill">{leagueDisplayName(r)}</span>
        </div>
        <span className={"history-result-badge " + outCls}>{outTxt}</span>
      </div>
      <div className="history-card-matchup">{r.matchup || "\u2014"}</div>
      <div className="history-card-pick">{r.pick || r.bet_side || "\u2014"}</div>
      <div className="history-card-stats">
        <div>
          <div className="history-card-stat-label">Odds</div>
          <div className="history-card-stat-value">{formatOdds(r.odds, r.odds_display)}</div>
        </div>
        <div>
          <div className="history-card-stat-label">P/L</div>
          <div className="history-card-stat-value">
            <span className={profitCls}>{formatProfit(r.profit_unit)}</span>
          </div>
        </div>
      </div>
      <details className="history-details">
        <summary>Details</summary>
        <div className="history-details-grid">
          <DetailItem label="Market" value={formatMarketLabel(r.market)} cls="" />
          <DetailItem label="Raw Market" value={r.market_raw || "\u2014"} cls="" />
          <DetailItem label="Model Prob" value={formatPercent(r.model_prob)} cls={probabilityClass(r.model_prob)} />
          <DetailItem label="EV" value={formatEV(r.ev)} cls={valueClass(r.ev)} />
          <DetailItem label="Kelly" value={formatKelly(r.kelly)} cls={valueClass(r.kelly)} />
          <DetailItem label="Source" value={r.source || "\u2014"} cls="" />
        </div>
      </details>
    </div>
  );
}

function HistoryResults(props: { displayRows: HistoryRow[]; matchCount: number }) {
  const displayRows = props.displayRows;
  const groups = groupRowsByDate(displayRows);

  return (
    <>
      <div className="bets-table-wrap">
        <table className="bets-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>League</th>
              <th>Game / Matchup</th>
              <th>Pick</th>
              <th>Odds</th>
              <th>Result</th>
              <th>P/L Units</th>
            </tr>
          </thead>
          <tbody>
            {displayRows.map((r, i) => (
              <tr key={i}>
                <td>
                  <span className="history-date">{formatDateDisplay(r.game_date)}</span>
                </td>
                <td>
                  <span className="history-league-pill">{leagueDisplayName(r)}</span>
                </td>
                <td>
                  <span className="history-matchup">{r.matchup || "\u2014"}</span>
                </td>
                <td>
                  <span className="history-pick">{r.pick || r.bet_side || "\u2014"}</span>
                </td>
                <td>
                  <span className="history-odds">{formatOdds(r.odds, r.odds_display)}</span>
                </td>
                <td>
                  <span className={"history-result-badge " + outcomeClass(r.result)}>{outcomeText(r.result)}</span>
                </td>
                <td>
                  <span className={"history-profit-badge " + profitClass(r.profit_unit)}>
                    {formatProfit(r.profit_unit)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="history-card-list">
        {groups.map((group) => (
          <div className="history-date-group" key={group.date}>
            <div className="history-date-header">
              <span>{group.longDate}</span>
              <span className="history-date-count">
                {group.rows.length + " bet" + (group.rows.length === 1 ? "" : "s")}
              </span>
              <span className="history-date-record">{"W/L/P: " + groupRecordText(group.rows)}</span>
            </div>
            <div className="history-card-grid">
              {group.rows.map((r, i) => (
                <HistoryCard r={r} key={i} />
              ))}
            </div>
          </div>
        ))}
      </div>
      {props.matchCount > 500 ? (
        <div className="history-limit-note">
          {"Showing first 500 of " + props.matchCount + " matching completed bets"}
        </div>
      ) : null}
    </>
  );
}

function HistoryMain(props: {
  graded: HistoryRow[];
  search: string;
  sort: string;
  tick: number;
  onSearch: (value: string) => void;
  onSort: (value: string) => void;
}) {
  const graded = props.graded;

  if (!graded.length) {
    return <div className="empty-state">No completed bets match the current filter</div>;
  }

  const wins = graded.filter((r) => r.result === "win").length;
  const losses = graded.filter((r) => r.result === "loss").length;
  const pushes = graded.filter((r) => r.result === "push").length;
  const decisions = wins + losses;
  const winRate = decisions ? wins / decisions : 0;

  const avgProbRows = graded.filter((r) => r.model_prob !== null);
  const avgProb = avgProbRows.length
    ? avgProbRows.reduce((s, r) => s + (r.model_prob ?? 0), 0) / avgProbRows.length
    : 0;

  const evRows = graded.filter((r) => r.ev !== null);
  const totalEV = evRows.reduce((s, r) => s + (r.ev ?? 0), 0);

  const profitRows = graded.filter((r) => r.profit_unit !== null);
  const totalProfit = profitRows.reduce((s, r) => s + (r.profit_unit ?? 0), 0);

  const strip = [
    { val: String(graded.length), lbl: "Completed Bets", cls: "" },
    {
      val: wins + "-" + losses + (pushes ? "-" + pushes : ""),
      lbl: "W-L-P Record",
      cls: rateClass(winRate),
    },
    { val: (winRate * 100).toFixed(1) + "%", lbl: "Win Rate", cls: rateClass(winRate) },
    {
      val: avgProbRows.length ? (avgProb * 100).toFixed(1) + "%" : "\u2014",
      lbl: "Avg Model Prob",
      cls: "val-blue",
    },
    {
      val: profitRows.length ? formatProfit(totalProfit) : "\u2014",
      lbl: "Profit / Loss",
      cls: totalProfit >= 0 ? "val-green" : "val-red",
    },
    {
      val: evRows.length ? totalEV.toFixed(2) : "\u2014",
      lbl: "Total EV",
      cls: totalEV >= 0 ? "val-green" : "val-red",
    },
  ];

  const leagues: string[] = [];
  graded.forEach((r) => {
    if (leagues.indexOf(r.league) === -1) leagues.push(r.league);
  });
  leagues.sort();

  const markets: MarketKind[] = ["moneyline", "spread", "total", "other"];
  const marketCards = markets
    .map((market) => ({ market: market, rows: graded.filter((r) => r.market === market) }))
    .filter((m) => m.rows.length > 0);

  const sortedRows = sortHistoryRows(graded, props.sort);
  const searchedRows = applyHistorySearch(sortedRows, props.search);
  const displayRows = searchedRows.slice(0, 500);

  return (
    <>
      <div className="summary-strip">
        {strip.map((s) => (
          <div className="summary-item" key={s.lbl}>
            <div className={"summary-val " + s.cls}>{s.val}</div>
            <div className="summary-lbl">{s.lbl}</div>
          </div>
        ))}
      </div>

      <div className="section">
        <div className="section-title">Performance by League</div>
        <div className="breakdown-grid">
          {leagues.map((league) => (
            <BreakdownCard key={league} title={league} rows={graded.filter((r) => r.league === league)} />
          ))}
        </div>
      </div>

      {marketCards.length ? (
        <div className="section">
          <div className="section-title">Performance by Market</div>
          <div className="breakdown-grid">
            {marketCards.map((m) => (
              <BreakdownCard key={m.market} title={formatMarketLabel(m.market)} rows={m.rows} />
            ))}
          </div>
        </div>
      ) : null}

      <div className="section" id="completed-history-section">
        <div className="section-title">Completed Bet History</div>
        <div className="history-tools">
          <input
            className="history-search"
            type="search"
            placeholder="Search completed bets..."
            value={props.search}
            onChange={(e) => props.onSearch(e.target.value)}
          />
          <select className="history-sort" value={props.sort} onChange={(e) => props.onSort(e.target.value)}>
            {SORT_OPTIONS.map((o) => (
              <option key={o.key} value={o.key}>
                {o.label}
              </option>
            ))}
          </select>
          <div className="history-count" id="history-count">
            {searchedRows.length + " shown"}
          </div>
        </div>
        <div id="completed-history-results" key={props.tick + "|" + props.search + "|" + props.sort}>
          {searchedRows.length ? (
            <HistoryResults displayRows={displayRows} matchCount={searchedRows.length} />
          ) : (
            <div className="history-empty-results">No bets match your search</div>
          )}
        </div>
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function BetHistory() {
  const [rows, setRows] = useState<HistoryRow[]>([]);
  const [status, setStatus] = useState<{ text: string; dot: string }>({
    text: "Loading bet history...",
    dot: "yellow",
  });
  const [mainVisible, setMainVisible] = useState(false);
  const [renderTick, setRenderTick] = useState(0);

  const [activePillKey, setActivePillKey] = useState("all");
  const [activeLeague, setActiveLeague] = useState("all");
  const [activeLeagueSub, setActiveLeagueSub] = useState("all");
  const [activeMarket, setActiveMarket] = useState("all");
  const [activeResult, setActiveResult] = useState("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("newest");
  const [openGroup, setOpenGroup] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const groupRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const loadAll = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();

    const controller = new AbortController();
    abortRef.current = controller;

    const activeSources = SOURCES.filter((src) => src.enabled !== false);

    if (!activeSources.length) {
      setRows([]);
      setStatus({ text: "No leagues are currently enabled.", dot: "red" });
      setMainVisible(true);
      setRenderTick((t) => t + 1);
      return;
    }

    const labels = activeSources.map((s) => s.label).join(", ");

    setStatus({ text: "Fetching data from GitHub: " + labels + "...", dot: "yellow" });
    setMainVisible(false);

    void Promise.all(activeSources.map((src) => loadSource(src, controller.signal))).then((results) => {
      if (controller.signal.aborted) return;

      const next: HistoryRow[] = [];

      results.forEach((result) => {
        result.rows.forEach((row) => {
          next.push(normalizeRow(prepareSourceRow(row, result.label), result.label));
        });
      });

      const graded = next.filter(isGraded).length;

      setRows(next);
      setStatus({
        text: next.length + " bets loaded \u00b7 " + graded + " graded \u00b7 active: " + labels,
        dot: "green",
      });
      setMainVisible(true);
      setRenderTick((t) => t + 1);
    });
  }, []);

  useEffect(() => {
    loadAll();

    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, [loadAll]);

  useEffect(() => {
    const onDocumentClick = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) return;

      const inside = Object.values(groupRefs.current).some((el) => el !== null && el.contains(target));

      if (!inside) setOpenGroup(null);
    };

    const onDocumentKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpenGroup(null);
    };

    document.addEventListener("click", onDocumentClick);
    document.addEventListener("keydown", onDocumentKeyDown);

    return () => {
      document.removeEventListener("click", onDocumentClick);
      document.removeEventListener("keydown", onDocumentKeyDown);
    };
  }, []);

  const activePillLeague = (): string => {
    const data = PILL_DATA[activePillKey];
    return data ? data.sub || data.league || "all" : activeLeague;
  };

  const rerenderIfRows = () => {
    if (rows.length) {
      setMainVisible(true);
      setRenderTick((t) => t + 1);
    }
  };

  const onLeagueClick = (key: string) => {
    const data = PILL_DATA[key];
    if (!data) return;

    setActivePillKey(key);
    setActiveLeague(data.league);
    setActiveLeagueSub(data.sub || "all");
    setOpenGroup(null);

    const value = data.sub || data.league || "all";
    trackHistoryFilter("league", value, value, activeMarket, activeResult);

    rerenderIfRows();
  };

  const onMarketClick = (market: string) => {
    setActiveMarket(market);
    trackHistoryFilter("market", market, activePillLeague(), market, activeResult);
    rerenderIfRows();
  };

  const onResultClick = (result: string) => {
    setActiveResult(result);
    trackHistoryFilter("result", result, activePillLeague(), activeMarket, result);
    rerenderIfRows();
  };

  const renderLeague = (item: LeagueItem, asSubmenu: boolean) => {
    const data = PILL_DATA[item.key];

    if (!isLeagueSupported(item.key) || !data) {
      return (
        <button
          key={item.key}
          type="button"
          disabled
          className={"league-pill shared-league-unavailable" + (asSubmenu ? " submenu-pill" : "")}
          data-shared-league-key={item.key}
          title={item.label + " is not currently supported on this page."}
        >
          {item.label}
        </button>
      );
    }

    return (
      <button
        key={item.key}
        type="button"
        className={
          "league-pill shared-league-option" + (asSubmenu ? " submenu-pill" : "") + (activePillKey === item.key ? " active" : "")
        }
        data-league-key={item.key}
        data-league={data.league}
        data-league-sub={data.sub}
        onClick={() => onLeagueClick(item.key)}
      >
        {item.label}
      </button>
    );
  };

  const renderGroup = (group: LeagueGroup) => {
    const supportedCount = group.leagues.filter((l) => isLeagueSupported(l.key)).length;
    const hasActive = group.leagues.some((l) => l.key === activePillKey);

    return (
      <div
        key={group.key}
        className={
          "control-group" + (openGroup === group.key ? " open" : "") + (supportedCount ? "" : " shared-group-unavailable")
        }
        data-group={group.key}
        ref={(el) => {
          groupRefs.current[group.key] = el;
        }}
      >
        <button
          type="button"
          className={"group-pill" + (hasActive ? " active" : "")}
          data-group-toggle={group.key}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setOpenGroup(openGroup === group.key ? null : group.key);
          }}
        >
          {group.label}
        </button>
        <div
          className="submenu"
          onClick={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
        >
          {group.leagues.map((l) => renderLeague(l, true))}
        </div>
      </div>
    );
  };

  const filtered = rows.filter((r) => {
    if (activeLeague !== "all" && r.league !== activeLeague) return false;
    if (activeMarket !== "all" && r.market !== activeMarket) return false;
    if (activeResult !== "all" && r.result !== activeResult) return false;

    if (activeLeague === "SOCCER" && activeLeagueSub !== "all" && r.league_sub !== activeLeagueSub) {
      return false;
    }

    return true;
  });

  const graded = filtered.filter(isGraded);

  return (
    <div className={"history-react-page" + (openGroup ? " history-dropdown-open" : "")}>
      <div style={{ display: "contents" }}>
        <style id="shared-league-nav-style">{LEAGUE_NAV_CSS}</style>

        <div className="page-header">
          <div>
            <div className="page-title">Bet History</div>
            <div className="page-subtitle">
              GRADED BETS &middot; RESULTS &middot; MODEL PROBABILITY &middot; EV &middot; ODDS
            </div>
          </div>
        </div>

        <div className="controls shared-league-nav-host" id="league-controls" data-shared-league-nav-ready="true">
          <div className="shared-league-nav-main">
            <button
              type="button"
              className={"league-pill shared-league-option" + (activePillKey === "all" ? " active" : "")}
              data-league-key="all"
              data-league="all"
              onClick={() => onLeagueClick("all")}
            >
              All
            </button>
            {renderGroup(GROUP_FOOTBALL)}
            {renderLeague({ key: "nhl", label: "NHL" }, false)}
            {renderGroup(GROUP_MLB)}
            {renderGroup(GROUP_BASKETBALL)}
            {renderGroup(GROUP_SOCCER)}
            {renderLeague({ key: "ufc", label: "UFC" }, false)}
          </div>
        </div>

        <div className="controls">
          {MARKET_PILLS.map((m) => (
            <div
              key={m.key}
              className={"market-pill" + (activeMarket === m.key ? " active" : "")}
              data-market={m.key}
              onClick={() => onMarketClick(m.key)}
            >
              {m.label}
            </div>
          ))}

          {RESULT_PILLS.map((m) => (
            <div
              key={m.key}
              className={"result-pill" + (activeResult === m.key ? " active" : "")}
              data-result={m.key}
              onClick={() => onResultClick(m.key)}
            >
              {m.label}
            </div>
          ))}

          <button className="refresh-btn" onClick={loadAll}>
            &#8635; Refresh
          </button>
        </div>

        <div className="status-bar" id="history-status">
          <span className={"status-dot " + status.dot} id="status-dot"></span>
          <span id="status-text">{status.text}</span>
        </div>

        <div className="main" id="history-main">
          {mainVisible ? (
            <HistoryMain
              graded={graded}
              search={search}
              sort={sort}
              tick={renderTick}
              onSearch={setSearch}
              onSort={setSort}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
