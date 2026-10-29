/*
  ModelValidation - native React port of legacy pages/model_validation.html + assets/js/pages/model_validation.2.js +
  assets/js/model-validation/{config,sources,csv,normalize,app}.js + assets/js/shared/{kelly-league-availability,league_nav}.js.

  Legacy behaviors preserved:
   1. Sources (raw.githubusercontent.com, main): NHL, MLB, MLB_LINEUPS, WNBA, SOCCER final CSVs; CFB (week_N_CFB_graded.csv)
      and UFC (YYYY_MM_DD_graded_ufc.csv) files listed through the GitHub contents API. Plain fetch, all in parallel.
   2. Same CSV parser, CFB/UFC row expansion and row normalization (league, market, side, line, probability, EV, Kelly,
      odds, date, result).
   3. Status bar: "Fetching graded model history from GitHub..." (yellow), then "N bets loaded / D decisions / F source
      file(s)" (green), a partial-failure message (yellow) or "No data loaded" (red).
   4. League nav (from shared league_nav.js with KELLY_LEAGUE_AVAILABILITY): All, Football group, NHL, MLB group
      (MLB, MLB With Lineups), Basketball group, Soccer group, UFC; unavailable leagues (NFL, CFL, NBA, College
      Basketball) are disabled/dashed; one menu open at a time; choosing a league keeps the menu open; outside click or
      Escape closes menus; a group is highlighted when one of its leagues is active.
   5. Market pills (All Markets, Moneyline, Spread / Line, Total) and Refresh (clears the results and reloads).
   6. Results: summary strip, calibration buckets, performance by market, most recent 100 graded bets.
   7. "What is Model Validation?" modal: opens from the subtitle link, closes on the X or a click on the backdrop.
  Not present in legacy: URL params, localStorage, auto-refresh (nav.js is loaded by SiteShell).
*/
import { useEffect, useState, type CSSProperties } from "react";
import "../../../app/frontend/src/assets/css/pages/model_validation.css";

// ---------------------------------------------------------------- config.js / sources.js
const REPO = "Clownworldenjoyer76/bet_tracker";
const BRANCH = "main";
const BASE = "https://raw.githubusercontent.com/" + REPO + "/" + BRANCH + "/";
const API_BASE = "https://api.github.com/repos/" + REPO + "/contents/";

const DASH = "\u2014";
const MID = "\u00b7";

type Row = Record<string, string | undefined>;
type IndexItem = { type?: string; name?: string; download_url?: string | null };

type Source = {
  label: string;
  enabled: boolean;
  url?: string;
  indexUrl?: string;
  indexItemToUrl?: (item: IndexItem) => string;
  adapter?: "cfb" | "ufc";
};

const SOURCES: Source[] = [
  { url: BASE + "docs/win/hockey/nhl/05_final_scores/graded/NHL_final.csv", label: "NHL", enabled: true },
  { url: BASE + "frontend/data/mlb/final/MLB_final.csv", label: "MLB", enabled: true },
  { url: BASE + "docs/win/basketball/05_final_scores/results/wnba/graded/WNBA_final.csv", label: "WNBA", enabled: true },
  { url: BASE + "docs/win/soccer/05_final_scores/results/graded/SOCCER_final.csv", label: "SOCCER", enabled: true },
  {
    indexUrl: API_BASE + "docs/win/football/cfb/04_final_results/graded?ref=" + BRANCH,
    indexItemToUrl: (item) => {
      if (!item || item.type !== "file") return "";
      if (!/^week_\d+_CFB_graded\.csv$/i.test(item.name || "")) return "";
      return item.download_url || "";
    },
    adapter: "cfb",
    label: "CFB",
    enabled: true,
  },
  {
    indexUrl: API_BASE + "frontend/data/ufc/graded?ref=" + BRANCH,
    indexItemToUrl: (item) => {
      if (!item || item.type !== "file") return "";
      if (!/^\d{4}_\d{2}_\d{2}_graded_ufc\.csv$/i.test(item.name || "")) return "";
      return item.download_url || "";
    },
    adapter: "ufc",
    label: "UFC",
    enabled: true,
  },
];

// ---------------------------------------------------------------- csv.js
function parseCSV(text: string): Row[] {
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
      obj[h] = (row[i] || "").trim();
    });
    return obj;
  });
}

// ---------------------------------------------------------------- normalize.js
type NormRow = {
  source: string;
  league: string;
  league_sub: string;
  market: string;
  market_raw: string;
  bet_side: string;
  line: number | null;
  model_prob: number | null;
  ev: number | null;
  kelly: number | null;
  odds: number | null;
  game_date: string;
  result: string;
  win: boolean | null;
};

function parseNum(value: unknown): number | null {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  const n = parseFloat(value as string);
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
    const value = values[i];
    if (value !== null && value !== undefined && String(value).trim() !== "") {
      return String(value).trim();
    }
  }
  return "";
}

function normalizeProbability(value: unknown): number | null {
  let n = parseNum(value);
  if (n === null) return null;
  if (n > 1 && n <= 100) n = n / 100;
  return n;
}

function normalizeResult(value: unknown): string {
  const result = String(value || "").trim().toLowerCase();
  if (result === "win" || result === "w" || result === "1" || result === "true") return "win";
  if (result === "loss" || result === "l" || result === "0" || result === "false") return "loss";
  if (result === "push" || result === "p" || result === "tie" || result === "void") return "push";
  return "unknown";
}

function normalizeMarket(r: Row): string {
  const raw = firstText(r.market_type, r.market).toLowerCase();
  if (raw === "moneyline" || raw === "match_odds" || raw === "ml") return "moneyline";
  if (raw === "spread" || raw === "puck_line" || raw === "run_line" || raw === "line") return "spread";
  if (
    raw === "total" || raw === "over_total" || raw === "under_total" ||
    raw === "btts" || raw === "total25" || raw === "total35"
  ) return "total";
  return "other";
}

function sourceLeague(r: Row, sourceLabel: string): string {
  if (sourceLabel === "MLB_LINEUPS") return "MLB_LINEUPS";
  if (sourceLabel === "SOCCER") return "SOCCER";
  if (sourceLabel === "CFB") return "CFB";
  if (sourceLabel === "UFC") return "UFC";

  const league = firstText(r.league).toUpperCase();
  if (league === "NCAAB") return "NCAAM";
  return league || sourceLabel;
}

function sourceLeagueSub(r: Row, sourceLabel: string): string {
  if (sourceLabel === "SOCCER") return firstText(r.league, r.league_lower).toUpperCase();
  return sourceLeague(r, sourceLabel);
}

function truthySelected(value: unknown): boolean {
  const v = String(value === null || value === undefined ? "" : value).trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "y";
}

function cfbBetRow(row: Row, prefix: string, market: string): Row | null {
  if (!truthySelected(row[prefix + "_selected"])) return null;

  const selection = firstText(row[prefix + "_selection"]);
  const result = firstText(row[prefix + "_grade"]);

  const out: Row = Object.assign({}, row);
  out.sport = "football";
  out.league = "CFB";
  out.market_type = market;
  out.bet_side = selection.toLowerCase();
  out.take_bet = selection;
  out.line = firstText(row[prefix + "_line"]);
  out.dk_odds_american = firstText(row[prefix + "_odds_american"]);
  out.model_prob = firstText(row[prefix + "_model_probability"]);
  out.ev = firstText(row[prefix + "_ev"]);
  out.kelly = firstText(row[prefix + "_kelly"]);
  out.edge = firstText(row[prefix + "_edge"]);
  out.bet_result = result;
  return out;
}

function expandCFBRow(row: Row): Row[] {
  const out: Row[] = [];
  const ml = cfbBetRow(row, "ml", "moneyline");
  const spread = cfbBetRow(row, "spread", "spread");
  const total = cfbBetRow(row, "total", "total");
  if (ml) out.push(ml);
  if (spread) out.push(spread);
  if (total) out.push(total);
  return out;
}

function expandUFCRow(row: Row): Row[] {
  const bet = String(row.bet || "").trim().toLowerCase();
  const index = bet === "fighter_1" ? 1 : bet === "fighter_2" ? 2 : 0;
  if (!index) return [];

  const out: Row = Object.assign({}, row);
  const fighter = index === 1 ? row.fighter_1 : row.fighter_2;

  out.sport = "mma";
  out.league = "UFC";
  out.game_date = row.match_date;
  out.market_type = "moneyline";
  out.bet_side = fighter;
  out.take_bet = fighter;
  out.dk_odds_american = index === 1 ? row.moneyline_f1 : row.moneyline_f2;
  out.model_prob = index === 1 ? row.model_prob_f1 : row.model_prob_f2;
  out.ev = index === 1 ? row.ev_f1 : row.ev_f2;
  out.kelly = index === 1 ? row.kelly_f1 : row.kelly_f2;
  out.edge = index === 1 ? row.edge_f1 : row.edge_f2;
  out.bet_result = index === 1 ? row.result_fighter_1 : row.result_fighter_2;
  return [out];
}

function expandSourceRows(rows: Row[], source: Source): Row[] {
  const out: Row[] = [];

  rows.forEach((row) => {
    let expanded: Row[];
    if (source.adapter === "cfb") expanded = expandCFBRow(row);
    else if (source.adapter === "ufc") expanded = expandUFCRow(row);
    else expanded = [row];

    expanded.forEach((item) => out.push(item));
  });

  return out;
}

function normalizeOdds(r: Row, betSide: string): number | null {
  let odds = firstNum(r.bet_odds_american, r.dk_odds_american, r.odds_american, r.american_odds);

  if (odds !== null) return odds;

  if (betSide === "home") {
    odds = firstNum(r.home_dk_moneyline_american, r.home_dk_spread_american, r.home_dk_puck_line_american, r.home_dk_run_line_american);
  } else if (betSide === "away") {
    odds = firstNum(r.away_dk_moneyline_american, r.away_dk_spread_american, r.away_dk_puck_line_american, r.away_dk_run_line_american);
  } else if (betSide === "over") {
    odds = firstNum(r.dk_total_over_american);
  } else if (betSide === "under") {
    odds = firstNum(r.dk_total_under_american);
  }

  if (odds !== null) return odds;

  const decimal = firstNum(r.odds, r.dk_odds_decimal, r.odds_decimal);
  if (decimal !== null && decimal > 1) {
    return decimal >= 2 ? Math.round((decimal - 1) * 100) : Math.round(-100 / (decimal - 1));
  }

  return null;
}

function normalizeModelProb(r: Row, betSide: string): number | null {
  const probability = normalizeProbability(firstText(r.bet_model_prob, r.model_prob));
  if (probability !== null) return probability;

  if (betSide === "home") return normalizeProbability(firstText(r.home_model_prob, r.home_prob));
  if (betSide === "away") return normalizeProbability(firstText(r.away_model_prob, r.away_prob));
  if (betSide === "over") return normalizeProbability(firstText(r.over_model_prob, r.over_prob));
  if (betSide === "under") return normalizeProbability(firstText(r.under_model_prob, r.under_prob));
  return null;
}

function normalizeRow(r: Row, sourceLabel: string): NormRow {
  const betSide = firstText(r.bet_side, r.side, r.take_bet, r.pick).toLowerCase();
  const result = normalizeResult(firstText(r.bet_result, r.result, r.outcome, r.win, r.won, r.correct));
  const modelProb = normalizeModelProb(r, betSide);

  return {
    source: sourceLabel,
    league: sourceLeague(r, sourceLabel),
    league_sub: sourceLeagueSub(r, sourceLabel),
    market: normalizeMarket(r),
    market_raw: firstText(r.market_type, r.market),
    bet_side: firstText(r.bet_side, r.side, r.take_bet, r.pick),
    line: firstNum(r.bet_line, r.line),
    model_prob: modelProb,
    ev: firstNum(r.bet_ev, r.ev, r.selected_ev, r.edge_pct),
    kelly: firstNum(r.bet_kelly, r.kelly),
    odds: normalizeOdds(r, betSide),
    game_date: firstText(r.game_date, r.match_date, r.date, r.score_game_date),
    result: result,
    win: result === "win" ? true : result === "loss" ? false : null,
  };
}

// ---------------------------------------------------------------- app.js (loading)
type FileResult = { ok: boolean; rows: Row[] };
type SourceResult = { label: string; rows: Row[]; failedFiles: number; totalFiles: number };

function fetchSourceUrl(url: string, label: string): Promise<FileResult> {
  return fetch(url)
    .then((res) => {
      if (!res.ok) throw new Error(label + " " + res.status + " " + MID + " " + url);
      return res.text();
    })
    .then((text) => ({ ok: true, rows: parseCSV(text) }))
    .catch((error) => {
      console.warn("Failed to load " + label + ":", error);
      return { ok: false, rows: [] };
    });
}

function resolveSourceUrls(source: Source): Promise<{ ok: boolean; urls: string[] }> {
  if (source.url) return Promise.resolve({ ok: true, urls: [source.url] });

  if (source.indexUrl) {
    return fetch(source.indexUrl)
      .then((res) => {
        if (!res.ok) throw new Error(source.label + " index " + res.status);
        return res.json();
      })
      .then((items: unknown) => {
        if (!Array.isArray(items)) return { ok: true, urls: [] };

        const urls = (items as IndexItem[])
          .map((item) => (typeof source.indexItemToUrl === "function" ? source.indexItemToUrl(item) : ""))
          .filter((url) => !!url);

        return { ok: true, urls };
      })
      .catch((error) => {
        console.warn("Failed to load " + source.label + " index:", error);
        return { ok: false, urls: [] };
      });
  }

  return Promise.resolve({ ok: true, urls: [] });
}

function loadSource(source: Source): Promise<SourceResult> {
  return resolveSourceUrls(source).then((resolved) => {
    if (!resolved.ok) {
      return { label: source.label, rows: [], failedFiles: 1, totalFiles: 0 };
    }

    if (!resolved.urls.length) {
      return { label: source.label, rows: [], failedFiles: 0, totalFiles: 0 };
    }

    return Promise.all(resolved.urls.map((url) => fetchSourceUrl(url, source.label))).then((groups) => {
      let rawRows: Row[] = [];
      let failed = 0;

      groups.forEach((group) => {
        if (!group.ok) failed++;
        rawRows = rawRows.concat(group.rows);
      });

      return {
        label: source.label,
        rows: expandSourceRows(rawRows, source),
        failedFiles: failed,
        totalFiles: resolved.urls.length,
      };
    });
  });
}

// ---------------------------------------------------------------- app.js (formatting)
function safePct(value: number | null): string {
  return value === null || value === undefined ? DASH : (value * 100).toFixed(1) + "%";
}

function formatOdds(value: number | null): string {
  if (value === null || value === undefined) return DASH;
  return value > 0 ? "+" + value : String(value);
}

function formatEV(value: number | null): string {
  if (value === null || value === undefined) return DASH;
  return value.toFixed(2);
}

// ---------------------------------------------------------------- league nav (league_nav.js + availability)
const KELLY_LEAGUE_AVAILABILITY: Record<string, boolean> = {
  nfl: false,
  cfb: true,
  cfl: false,
  nhl: true,
  mlb: true,
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

type LeagueItem = { key: string; label: string; league?: string; sub?: string };

const FOOTBALL: LeagueItem[] = [
  { key: "nfl", label: "NFL" },
  { key: "cfb", label: "College Football", league: "CFB" },
  { key: "cfl", label: "CFL" },
];
const MLB_ITEMS: LeagueItem[] = [
  { key: "mlb", label: "MLB", league: "MLB" },
];
const BASKETBALL: LeagueItem[] = [
  { key: "nba", label: "NBA" },
  { key: "ncaam", label: "College Basketball" },
  { key: "wnba", label: "WNBA", league: "WNBA" },
];
const SOCCER: LeagueItem[] = [
  { key: "mls", label: "MLS", league: "SOCCER", sub: "MLS" },
  { key: "epl", label: "EPL", league: "SOCCER", sub: "EPL" },
  { key: "laliga", label: "La Liga", league: "SOCCER", sub: "LALIGA" },
  { key: "ligue1", label: "Ligue 1", league: "SOCCER", sub: "LIGUE1" },
  { key: "seriea", label: "Serie A", league: "SOCCER", sub: "SERIEA" },
  { key: "bundesliga", label: "Bundesliga", league: "SOCCER", sub: "BUNDESLIGA" },
];
const ALL_ITEM: LeagueItem = { key: "all", label: "All", league: "all" };
const NHL_ITEM: LeagueItem = { key: "nhl", label: "NHL", league: "NHL" };
const UFC_ITEM: LeagueItem = { key: "ufc", label: "UFC", league: "UFC" };

const MARKETS = [
  { key: "all", label: "All Markets" },
  { key: "moneyline", label: "Moneyline" },
  { key: "spread", label: "Spread / Line" },
  { key: "total", label: "Total" },
];

function isSupported(key: string): boolean {
  return KELLY_LEAGUE_AVAILABILITY[key] === true;
}

// CSS the legacy shared league_nav.js injected into <head> (style id shared-league-nav-style).
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
        content: " \\25BE";
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
        background: var(--background);
        border: 1px solid var(--border-soft);
        box-shadow: 0 18px 44px rgba(0,0,0,0.45);
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

const WIN_GREEN = "var(--accent-green)";
const LOSS_RED = "var(--accent-red)";
const MUTED_10: CSSProperties = { fontSize: "10px", color: "var(--text-muted)" };

// ---------------------------------------------------------------- results view (app.js render())
function Results({ rows, activeLeague }: { rows: NormRow[]; activeLeague: string }) {
  const graded = rows.filter((row) => row.win === true || row.win === false);

  if (!graded.length) {
    return <div className="empty-state">No graded bets match the current filter</div>;
  }

  const wins = graded.filter((row) => row.win === true).length;
  const losses = graded.length - wins;
  const winRate = wins / graded.length;

  const probabilityRows = graded.filter(
    (row) => row.model_prob !== null && row.model_prob >= 0 && row.model_prob <= 1
  );
  const avgProb = probabilityRows.length
    ? probabilityRows.reduce((sum, row) => sum + (row.model_prob as number), 0) / probabilityRows.length
    : null;

  const evRows = graded.filter((row) => row.ev !== null);
  const totalEV = evRows.reduce((sum, row) => sum + (row.ev as number), 0);

  const rateCls = winRate >= 0.55 ? "val-green" : winRate < 0.45 ? "val-red" : "val-yellow";
  const summary = [
    { val: String(graded.length), lbl: "Graded Bets", cls: "" },
    { val: wins + "-" + losses, lbl: "W-L Record", cls: rateCls },
    { val: (winRate * 100).toFixed(1) + "%", lbl: "Win Rate", cls: rateCls },
    { val: avgProb === null ? DASH : (avgProb * 100).toFixed(1) + "%", lbl: "Avg Model Prob", cls: "val-blue" },
    { val: evRows.length ? totalEV.toFixed(2) : DASH, lbl: "Total EV", cls: totalEV >= 0 ? "val-green" : "val-red" },
  ];

  const buckets: [number, number, string][] = [
    [0, 0.45, "< 45%"],
    [0.45, 0.55, "45\u201355%"],
    [0.55, 0.65, "55\u201365%"],
    [0.65, 0.75, "65\u201375%"],
    [0.75, 1.000001, "> 75%"],
  ];

  const calRows = buckets.map((bucket) => {
    const bucketRows = probabilityRows.filter(
      (row) => (row.model_prob as number) >= bucket[0] && (row.model_prob as number) < bucket[1]
    );
    if (!bucketRows.length) return null;

    const bucketWins = bucketRows.filter((row) => row.win === true).length;
    const predAvg = bucketRows.reduce((sum, row) => sum + (row.model_prob as number), 0) / bucketRows.length;
    const actual = bucketWins / bucketRows.length;
    const diff = actual - predAvg;
    const diffStr = (diff >= 0 ? "+" : "") + (diff * 100).toFixed(1) + "%";
    const diffCls = diff > 0.05 ? "val-green" : diff < -0.05 ? "val-red" : "";

    return (
      <div className="cal-row" key={bucket[2]}>
        <span className="cal-bucket">{bucket[2]}</span>
        <div className="cal-bar-wrap">
          <div className="cal-bar-pred" style={{ width: predAvg * 100 + "%" }}></div>
          <div className="cal-bar-act" style={{ width: actual * 100 + "%" }}></div>
        </div>
        <span className="cal-pct">
          <span style={{ color: "var(--accent-blue)" }}>{(predAvg * 100).toFixed(0) + "%"}</span>
          {" pred " + MID + " "}
          <span style={{ color: "var(--accent-green)" }}>{(actual * 100).toFixed(0) + "%"}</span>
          {" act " + MID + " "}
          <span className={diffCls}>{diffStr}</span>
        </span>
        <span style={{ ...MUTED_10, minWidth: "40px", textAlign: "right" }}>{bucketRows.length + " bets"}</span>
      </div>
    );
  });

  const marketCards = ["moneyline", "spread", "total"].map((market) => {
    const marketRows = graded.filter((row) => row.market === market);
    if (!marketRows.length) return null;

    const marketWins = marketRows.filter((row) => row.win === true).length;
    const marketRate = marketWins / marketRows.length;
    const marketEVRows = marketRows.filter((row) => row.ev !== null);
    const marketEV = marketEVRows.reduce((sum, row) => sum + (row.ev as number), 0);

    const spreadLabels: Record<string, string> = { NHL: "Puck Line", MLB: "Run Line", MLB_LINEUPS: "Run Line", CFB: "Spread" };
    const label =
      market === "spread"
        ? spreadLabels[activeLeague] || "Spread / Line"
        : market.charAt(0).toUpperCase() + market.slice(1);

    return (
      <div className="mkt-card" key={market}>
        <div className="mkt-card-title">{label}</div>
        <div className="mkt-stat-row">
          <span className="mkt-stat-label">Bets</span>
          <span className="mkt-stat-val">{marketRows.length}</span>
        </div>
        <div className="mkt-stat-row">
          <span className="mkt-stat-label">W-L</span>
          <span className="mkt-stat-val">{marketWins + "-" + (marketRows.length - marketWins)}</span>
        </div>
        <div className="mkt-stat-row">
          <span className="mkt-stat-label">Win Rate</span>
          <span
            className="mkt-stat-val"
            style={{
              color: marketRate >= 0.55 ? WIN_GREEN : marketRate < 0.45 ? LOSS_RED : "var(--accent-yellow)",
            }}
          >
            {(marketRate * 100).toFixed(1) + "%"}
          </span>
        </div>
        <div className="mkt-stat-row">
          <span className="mkt-stat-label">Total EV</span>
          <span className="mkt-stat-val" style={{ color: marketEV >= 0 ? WIN_GREEN : LOSS_RED }}>
            {marketEVRows.length ? marketEV.toFixed(2) : DASH}
          </span>
        </div>
      </div>
    );
  });
  const hasMarketCards = marketCards.some((card) => card !== null);

  const recent = graded
    .slice()
    .sort((a, b) => String(b.game_date).localeCompare(String(a.game_date)))
    .slice(0, 100);

  return (
    <>
      <div className="summary-strip">
        {summary.map((item) => (
          <div className="summary-item" key={item.lbl}>
            <div className={"summary-val " + item.cls}>{item.val}</div>
            <div className="summary-lbl">{item.lbl}</div>
          </div>
        ))}
      </div>

      <div className="calibration-section">
        <div className="section-title">
          {"Model Calibration " + MID + " Predicted Probability vs Actual Win Rate"}
        </div>
        {calRows}
      </div>

      {hasMarketCards ? (
        <div className="ev-section">
          <div className="section-title">Performance by Market</div>
          <div className="market-breakdown">{marketCards}</div>
        </div>
      ) : null}

      <div className="bets-section">
        <div className="section-title">Graded Bets</div>
        <div style={{ overflowX: "auto" }}>
          <table className="bets-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>League</th>
                <th>Market</th>
                <th>Side/Line</th>
                <th>Odds</th>
                <th>Model%</th>
                <th>EV</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((row, i) => {
                const outcomeClass = row.win ? "outcome-w" : "outcome-l";
                const outcomeText = row.win ? "WIN" : "LOSS";
                const probClass =
                  row.model_prob === null
                    ? ""
                    : row.model_prob >= 0.65
                      ? "prob-high"
                      : row.model_prob >= 0.5
                        ? "prob-mid"
                        : "prob-low";
                const evClass = row.ev === null ? "" : row.ev >= 0 ? "val-green" : "val-red";
                const leagueText =
                  row.league === "SOCCER" && row.league_sub && row.league_sub !== "SOCCER"
                    ? row.league + " " + MID + " " + row.league_sub
                    : row.league;
                let sideLine = row.bet_side || DASH;
                if (row.line !== null) sideLine += " " + (row.line > 0 ? "+" + row.line : String(row.line));

                return (
                  <tr key={i}>
                    <td>{row.game_date || DASH}</td>
                    <td>{leagueText || DASH}</td>
                    <td>{row.market_raw || row.market || DASH}</td>
                    <td>{sideLine}</td>
                    <td>{formatOdds(row.odds)}</td>
                    <td className={probClass}>{safePct(row.model_prob)}</td>
                    <td className={evClass}>{formatEV(row.ev)}</td>
                    <td className={outcomeClass}>{outcomeText}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {graded.length > 100 ? (
          <div style={{ ...MUTED_10, padding: "8px 0", textAlign: "center" }}>
            {"Showing most recent 100 of " + graded.length + " graded bets"}
          </div>
        ) : null}
      </div>
    </>
  );
}

// ---------------------------------------------------------------- page
type Status = { text: string; dot: string };

export default function ModelValidation() {
  const [allRows, setAllRows] = useState<NormRow[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [status, setStatus] = useState<Status>({ text: "Loading data...", dot: "yellow" });
  const [activeKey, setActiveKey] = useState("all");
  const [activeLeague, setActiveLeague] = useState("all");
  const [activeLeagueSub, setActiveLeagueSub] = useState("all");
  const [activeMarket, setActiveMarket] = useState("all");
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const loadAll = () => {
    const activeSources = SOURCES.filter((source) => source.enabled !== false);

    setStatus({ text: "Fetching graded model history from GitHub...", dot: "yellow" });
    setShowResults(false);

    Promise.all(activeSources.map(loadSource)).then((results) => {
      const rows: NormRow[] = [];
      let failedFiles = 0;
      let totalFiles = 0;

      results.forEach((result) => {
        failedFiles += result.failedFiles;
        totalFiles += result.totalFiles;

        result.rows.forEach((row) => {
          rows.push(normalizeRow(row, result.label));
        });
      });

      const decisions = rows.filter((row) => row.win === true || row.win === false).length;

      if (!rows.length && failedFiles) {
        setStatus({ text: "No data loaded " + MID + " " + failedFiles + " source file/index request(s) failed", dot: "red" });
      } else if (failedFiles) {
        setStatus({
          text:
            rows.length + " bets loaded " + MID + " " + decisions + " decisions " + MID + " " + failedFiles +
            " of " + totalFiles + " file request(s) failed",
          dot: "yellow",
        });
      } else {
        setStatus({
          text: rows.length + " bets loaded " + MID + " " + decisions + " decisions " + MID + " " + totalFiles + " source file(s)",
          dot: "green",
        });
      }

      setAllRows(rows);
      setShowResults(true);
    });
  };

  // Initial load (legacy app.js called loadAll() once on page load).
  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Close league menus on outside click or Escape (legacy league_nav.js).
  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Element) || !target.closest("#league-controls .control-group")) {
        setOpenGroup(null);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpenGroup(null);
    };
    document.addEventListener("click", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("click", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const selectLeague = (item: LeagueItem) => {
    setActiveKey(item.key);
    setActiveLeague(item.league || "all");
    setActiveLeagueSub(item.sub || "all");
    if (allRows.length) setShowResults(true);
  };

  const selectMarket = (key: string) => {
    setActiveMarket(key);
    if (allRows.length) setShowResults(true);
  };

  const filtered = allRows.filter((row) => {
    if (activeLeague !== "all" && row.league !== activeLeague) return false;
    if (activeLeague === "SOCCER" && activeLeagueSub !== "all" && row.league_sub !== activeLeagueSub) return false;
    if (activeMarket !== "all" && row.market !== activeMarket) return false;
    return true;
  });

  const leagueButton = (item: LeagueItem, asSubmenu: boolean) => {
    if (!isSupported(item.key) && item.key !== "all") {
      return (
        <button
          type="button"
          key={item.key}
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
        type="button"
        key={item.key}
        className={
          "league-pill" + (asSubmenu ? " submenu-pill" : "") + " shared-league-option" +
          (activeKey === item.key ? " active" : "")
        }
        data-league-key={item.key}
        data-league={item.league}
        data-league-sub={item.sub}
        onClick={() => selectLeague(item)}
      >
        {item.label}
      </button>
    );
  };

  const group = (name: string, label: string, items: LeagueItem[]) => {
    const supported = items.filter((item) => isSupported(item.key)).length;
    const groupActive = items.some((item) => isSupported(item.key) && activeKey === item.key);

    return (
      <div
        key={name}
        className={"control-group" + (supported ? "" : " shared-group-unavailable") + (openGroup === name ? " open" : "")}
        data-group={name}
      >
        <button
          type="button"
          className={"group-pill" + (groupActive ? " active" : "")}
          data-group-toggle={name}
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setOpenGroup((current) => (current === name ? null : name));
          }}
        >
          {label}
        </button>
        <div className="submenu">{items.map((item) => leagueButton(item, true))}</div>
      </div>
    );
  };

  return (
    <>
      <style id="shared-league-nav-style">{LEAGUE_NAV_CSS}</style>

      <div className="page-header">
        <div>
          <div className="page-title">Model Validation</div>
          <div className="page-subtitle">
            {"MODEL PROB vs ACTUAL OUTCOME " + MID + " CALIBRATION " + MID + " EV TRACKING " + MID + " "}
            <span className="info-trigger" onClick={() => setModalOpen(true)}>
              What is Model Validation?
            </span>
          </div>
        </div>
      </div>

      <div className="controls shared-league-nav-host" id="league-controls" data-shared-league-nav-ready="true">
        <div className="shared-league-nav-main">
          {leagueButton(ALL_ITEM, false)}
          {group("football", "Football", FOOTBALL)}
          {leagueButton(NHL_ITEM, false)}
          {group("mlb", "MLB", MLB_ITEMS)}
          {group("basketball", "Basketball", BASKETBALL)}
          {group("soccer", "Soccer", SOCCER)}
          {leagueButton(UFC_ITEM, false)}
        </div>
      </div>

      <div className="controls">
        {MARKETS.map((market) => (
          <div
            key={market.key}
            className={"market-pill" + (activeMarket === market.key ? " active" : "")}
            data-market={market.key}
            onClick={() => selectMarket(market.key)}
          >
            {market.label}
          </div>
        ))}
        <button className="refresh-btn" onClick={loadAll}>
          {"\u21bb Refresh"}
        </button>
      </div>

      <div className="status-bar" id="val-status">
        <span className={"status-dot " + status.dot} id="status-dot"></span>
        <span id="status-text">{status.text}</span>
      </div>

      <div className="main" id="val-main">
        {showResults ? <Results rows={filtered} activeLeague={activeLeague} /> : null}
      </div>

      <div
        className="cal-overlay"
        id="cal-modal"
        style={modalOpen ? { display: "flex" } : undefined}
        onClick={(event) => {
          if (event.target === event.currentTarget) setModalOpen(false);
        }}
      >
        <div className="cal-box">
          <div className="cal-header">
            <div className="cal-title">What is Model Validation?</div>
            <button className="cal-close" onClick={() => setModalOpen(false)}>
              {"\u2715"}
            </button>
          </div>
          <div className="cal-body">
            <div className="cal-graphic">
              <div className="cal-demo">
                <div className="cal-demo-title">Perfectly Calibrated</div>
                <DemoRow pct={45} act={46} cls="act-good" color="var(--accent-green)" note={"+1% \u2713"} />
                <DemoRow pct={60} act={61} cls="act-good" color="var(--accent-green)" note={"+1% \u2713"} />
                <DemoRow pct={75} act={74} cls="act-good" color="var(--accent-green)" note={"-1% \u2713"} />
              </div>
              <div className="cal-demo">
                <div className="cal-demo-title">Overconfident Model</div>
                <DemoRow pct={45} act={30} cls="act-over" color="var(--accent-red)" note={"-15% \u2717"} />
                <DemoRow pct={60} act={44} cls="act-over" color="var(--accent-red)" note={"-16% \u2717"} />
                <DemoRow pct={75} act={55} cls="act-over" color="var(--accent-red)" note={"-20% \u2717"} />
              </div>
            </div>

            <div className="cal-legend">
              <span>
                <span className="legend-dot" style={{ background: "rgba(0,191,255,0.5)" }}></span>Predicted probability (blue bar)
              </span>
              <span>
                <span className="legend-dot" style={{ background: "var(--accent-green)" }}></span>Actual win rate (green bar)
              </span>
            </div>

            <div className="cal-text">
              <p>
                The model assigns a probability to each bet before the game is played. For example, <strong>"this team has a <span className="hl-blue">65%</span> chance to cover."</strong>
              </p>
              <p>
                Calibration measures whether those predictions are accurate in reality. If the model says <span className="hl-blue">65%</span> and teams actually win <span className="hl-green">65%</span>{" of the time in that bucket \u2014 the model is "}<strong>perfectly calibrated.</strong>
              </p>
              <p>
                If it predicts <span className="hl-blue">65%</span> but they only win <span className="hl-red">50%</span>, the model is <strong className="hl-red">overconfident</strong>. If they win <span className="hl-yellow">75%</span>, it's <strong className="hl-yellow">underestimating.</strong>
              </p>
              <p>
                The bars show <span className="hl-blue">predicted probability in blue</span> and <span className="hl-green">actual win rate in green</span>{". If these align closely across all buckets, the model's confidence levels are trustworthy \u2014 not just that it wins bets."}
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function DemoRow({ pct, act, cls, color, note }: { pct: number; act: number; cls: string; color: string; note: string }) {
  return (
    <div className="cal-demo-row">
      <span className="cal-demo-lbl">{pct + "%"}</span>
      <div className="cal-demo-bar">
        <div className="cal-demo-pred" style={{ width: pct + "%" }}></div>
        <div className={"cal-demo-act " + cls} style={{ width: act + "%" }}></div>
      </div>
      <span className="cal-demo-note" style={{ color }}>
        {note}
      </span>
    </div>
  );
}
