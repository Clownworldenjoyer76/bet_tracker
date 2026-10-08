/*
  ThePicks - native React port of legacy the_picks.html + assets/js/shared/app.js + assets/js/pages/the_picks.js
  (the league configuration from assets/js/shared/config.js lives in src/lib/picksConfig.ts).

  Legacy behaviors found and preserved:
   1. Date picker (#p-date) starts at today (local); every change reloads the picks. Status shows "Loading..." while loading,
      then "{n} pick(s) - {date}".
   2. Leagues come from the config list, skipping any with enabled: false (NFL is disabled); one column per league in that order.
   3. Per league: loads the select CSV (first path that loads wins), plus the optional prediction and sportsbook CSVs, from
      https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/docs/. Rows are normalized / expanded per league,
      filtered to the league and to the chosen date; if none match the date the latest earlier date is found and treated as
      stale ("No Picks Today"). Select rows are merged over book and prediction rows (empty select values never overwrite),
      grouped by game and sorted by game time.
   4. Pick cards: time, league tag, matchup, pitchers (MLB), bet text, EV and edge dots (football cards hide the footer).
      MLB cards show "Lineups not available yet" when low_confidence is set. Clicking a card sends the pick_viewed analytics event
      and opens the game modal (football, soccer and the full projections / lines / picks layout).
   5. UFC: finds the next event from win/mma/ufc/03_select/_index.json (else probes today + 7 days with HEAD requests), shows the
      event date in the UFC Event box, loads that card CSV and shows fighter cards and a modal with implied / model probability, EV, Kelly, edge.
   6. League filter pills (All plus one per league): choosing one shows only that column (All shows every column, including empty ones).
      Columns without any pick are hidden until a pill is chosen. "NO PICKS FOR THIS DATE" replaces the columns when nothing loaded.
   7. The modal closes with the Close button or a click on the dark overlay.
   8. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials (nav.js is loaded by SiteShell).
  Differences: requests are cancelled or ignored when the date changes again or the page is left (legacy could add duplicate
  columns); CSV text is rendered as React text (legacy put it into innerHTML).
*/
import { useEffect, useState, type ReactNode } from "react";
import { PICKS_LEAGUES, REPO_CONFIG, type LeagueCfg, type Row } from "../lib/picksConfig";
import "../../../app/frontend/src/assets/css/pages/the_picks.css";

const MID = String.fromCharCode(0xb7);
const DASH = String.fromCharCode(0x2014);
const ELLIPSIS = String.fromCharCode(0x2026);
const DOT_FULL = String.fromCharCode(0x25cf);
const DOT_EMPTY = String.fromCharCode(0x25cb);
const NBSP = String.fromCharCode(0xa0);
// The legacy analytics code used this garbled dash (not a real em dash) when a team name is empty.
const LEGACY_ANALYTICS_DASH = String.fromCharCode(0xe2, 0x20ac, 0x201d);

const BASE_RAW = "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/docs/";
const UFC_MANIFEST_PATH = "win/mma/ufc/03_select/_index.json";

type CsvResult = { ok: boolean; rows: Row[]; source?: string };

type LeagueResult = {
  league: string;
  cfg?: LeagueCfg;
  error?: string;
  picks?: number;
  stale?: boolean;
  fromDate?: string | null;
  keys?: string[];
  grouped?: Record<string, Row[]>;
  rows?: Row[];
  eventDate?: string;
};

type ModalData =
  | { kind: "pick"; r: Row; picks: Row[]; cfg: LeagueCfg }
  | { kind: "ufc"; row: Row };

// --- Date --------------------------------------------------------------------

function todayLocal(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return y + "-" + m + "-" + day;
}

function replaceAllText(s: string, from: string, to: string): string {
  return s.split(from).join(to);
}

function toUnderscore(s: string): string {
  return replaceAllText((s || "").trim(), "-", "_");
}

function normDate(v: string): string {
  return toUnderscore(v || "");
}

// --- CSV ---------------------------------------------------------------------

function cleanCSVCell(v: string | undefined): string {
  let s = (v ?? "").trim();

  if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) {
    s = s.slice(1, -1);
  }

  return replaceAllText(s, '""', '"').trim();
}

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
      out.push(cur);
      cur = "";
      continue;
    }

    cur += ch;
  }

  out.push(cur);
  return out;
}

function parseCSV(text: string): Row[] {
  const raw = (text || "").replace(/^\uFEFF/, "").trim();
  if (!raw) return [];

  const lines = raw.split(/\r?\n/).filter((line) => line.trim() !== "");
  if (lines.length < 2) return [];

  const headers = parseCSVLine(lines[0]).map(cleanCSVCell);

  return lines.slice(1).map((line) => {
    const vals = parseCSVLine(line).map(cleanCSVCell);
    const obj: Row = {};
    headers.forEach((h, i) => {
      obj[h] = vals[i] ?? "";
    });
    return obj;
  });
}

async function fetchCSV(path: string, signal: AbortSignal): Promise<CsvResult> {
  try {
    const resolvedPath = path.startsWith("win/") ? BASE_RAW + path : path;
    const r = await fetch(resolvedPath, { signal });
    if (!r.ok) return { ok: false, rows: [] };
    return { ok: true, rows: parseCSV(await r.text()), source: path };
  } catch {
    return { ok: false, rows: [] };
  }
}

function resolvePaths(
  value: ((date: string) => string | string[]) | undefined,
  dateFormatted: string
): string[] {
  if (!value) return [];

  const resolved = typeof value === "function" ? value(dateFormatted) : value;

  if (Array.isArray(resolved)) return resolved.filter(Boolean);
  if (resolved) return [resolved];
  return [];
}

// Try paths in order. First one that loads wins; the rest are skipped.
async function fetchMultiCSV(paths: string[], signal: AbortSignal): Promise<CsvResult> {
  const list = Array.isArray(paths) ? paths.filter(Boolean) : [];

  for (const p of list) {
    const res = await fetchCSV(p, signal);
    if (res.ok) return { ok: true, rows: res.rows, source: p };
  }

  if (list.length && !signal.aborted) console.warn("[picks] No data file loaded. Tried:", list);
  return { ok: false, rows: [] };
}

// --- Row Matching -------------------------------------------------------------

function rowMatchesLeague(row: Row, cfg: LeagueCfg, target: string): boolean {
  if (cfg.filterFn) return true;
  if (cfg.leagueColumn) return (row[cfg.leagueColumn] || "").trim().toUpperCase() === target;
  if (cfg.marketColumn) return (row[cfg.marketColumn] || "").trim().toUpperCase() === target;
  const league = (row.league || "").trim().toUpperCase();
  const market = (row.market || "").trim().toUpperCase();
  return league === target || market === target;
}

function filterRows(
  allRows: Row[],
  dateFormatted: string,
  leagueName: string,
  cfg: LeagueCfg
): { rows: Row[]; stale: boolean; fromDate: string | null } {
  const target = leagueName.toUpperCase();

  const leagueRows = allRows.filter((r) => {
    if (cfg.filterFn) return cfg.filterFn(r, null, target);
    return rowMatchesLeague(r, cfg, target);
  });

  const dated = leagueRows.filter((r) => normDate(r.game_date) === dateFormatted);
  if (dated.length > 0) return { rows: dated, stale: false, fromDate: dateFormatted };

  if (leagueRows.length === 0) return { rows: [], stale: false, fromDate: null };
  leagueRows.sort((a, b) => normDate(b.game_date).localeCompare(normDate(a.game_date)));
  const latestDate = normDate(leagueRows[0].game_date);
  const fallback = leagueRows.filter((r) => normDate(r.game_date) === latestDate);
  return { rows: fallback, stale: true, fromDate: latestDate };
}

// --- Join Keys ----------------------------------------------------------------

function makeKey(row: Row, cfg?: LeagueCfg): string {
  if (cfg && cfg.joinKey) {
    return (row[cfg.joinKey] || "").trim();
  }
  return (row.game_date || "").trim() + "|" + (row.home_team || "").trim() + "|" + (row.away_team || "").trim();
}

function buildMap(rows: Row[], cfg: LeagueCfg): Record<string, Row> {
  const map: Record<string, Row> = {};
  rows.forEach((r) => {
    const k = makeKey(r, cfg);
    if (k) map[k] = r;
  });
  return map;
}

function mergeRows(selectRows: Row[], predMap: Record<string, Row>, bookMap: Record<string, Row>, cfg: LeagueCfg): Row[] {
  return selectRows.map((sel) => {
    const key = makeKey(sel, cfg);
    const pred = predMap[key] || {};
    const book = bookMap[key] || {};
    // Layer pred -> book -> sel, but DON'T let an empty select value overwrite a real value from book/pred.
    const merged: Row = { ...pred, ...book };
    Object.keys(sel).forEach((k) => {
      const v = sel[k];
      if (v !== "" && v !== null && v !== undefined) merged[k] = v;
    });
    merged.__key = key;
    if (!merged.game_time && pred.game_time) merged.game_time = pred.game_time;
    return merged;
  });
}

// --- Bet Text -----------------------------------------------------------------

function formatLine(line: string): string {
  const n = parseFloat(line);
  if (isNaN(n)) return line;
  return n > 0 ? "+" + n : String(n);
}

function cleanOdds(odds: unknown): string {
  if (odds === null || odds === undefined || odds === "") return "";
  const n = parseFloat(String(odds));
  if (isNaN(n)) return String(odds);
  return n > 0 ? "+" + n : String(n);
}

function wrapOdds(odds: unknown): string {
  const cleaned = cleanOdds(odds);
  return cleaned ? " (" + cleaned + ")" : "";
}

function buildBetText(p: Row, r: Row, cfg: LeagueCfg): string {
  if (cfg.buildBetText) return cfg.buildBetText(p, r);

  const market = (p.market_type || "").toLowerCase();
  const side = (p.bet_side || "").toLowerCase();
  const line = p.bet_line || p.line || "";
  const odds = p.bet_odds_american || p.dk_odds_american || p.take_odds || "";

  let label = "";
  let american = odds;

  if (side === "home") label = r.home_team || "Home";
  if (side === "away") label = r.away_team || "Away";
  if (side === "over") label = "Over";
  if (side === "under") label = "Under";

  if (["spread", "puck_line", "run_line"].includes(market)) {
    if (side === "home")
      american =
        p.bet_odds_american ||
        p.dk_odds_american ||
        p.take_odds ||
        r.home_dk_spread_american ||
        r.home_dk_puck_line_american ||
        r.home_dk_run_line_american ||
        odds;
    if (side === "away")
      american =
        p.bet_odds_american ||
        p.dk_odds_american ||
        p.take_odds ||
        r.away_dk_spread_american ||
        r.away_dk_puck_line_american ||
        r.away_dk_run_line_american ||
        odds;
    return (label + " " + formatLine(line) + wrapOdds(american)).trim();
  }

  if (market === "total") {
    if (side === "over")
      american = p.bet_odds_american || p.dk_odds_american || p.take_odds || r.dk_total_over_american || odds;
    if (side === "under")
      american = p.bet_odds_american || p.dk_odds_american || p.take_odds || r.dk_total_under_american || odds;
    return (label + " " + formatLine(line) + wrapOdds(american)).trim();
  }

  if (market === "moneyline") {
    if (side === "home")
      american = p.bet_odds_american || p.dk_odds_american || p.take_odds || r.home_dk_moneyline_american || odds;
    if (side === "away")
      american = p.bet_odds_american || p.dk_odds_american || p.take_odds || r.away_dk_moneyline_american || odds;
    return (label + wrapOdds(american)).trim();
  }

  return (side + " " + formatLine(line) + " " + cleanOdds(odds)).trim();
}

// --- Edge / EV / Kelly --------------------------------------------------------

function getEv(p: Row): number {
  return parseFloat(String(p.ev || p.bet_ev || p.selected_ev || 0));
}

function getKelly(p: Row): number {
  return parseFloat(String(p.kelly || p.bet_kelly || 0));
}

function extractEdge(p: Row): number {
  // Select files write a per-pick edge for the chosen side; that is the single source of truth.
  if (p.edge !== undefined && p.edge !== "") {
    return parseFloat(p.edge);
  }
  if (p.bet_edge_vs_market !== undefined && p.bet_edge_vs_market !== "") {
    return parseFloat(p.bet_edge_vs_market);
  }
  return parseFloat(String(p.ev || p.selected_ev || 0));
}

function statDecimals(cfg: LeagueCfg | undefined, fallback: number): number {
  const n = parseInt(String(cfg && cfg.statDecimals), 10);
  return Number.isFinite(n) ? n : fallback;
}

function formatPercentValue(n: unknown, decimals: number, signed: boolean): string {
  const v = parseFloat(String(n));
  if (isNaN(v)) return DASH;
  const prefix = signed && v >= 0 ? "+" : "";
  return prefix + (v * 100).toFixed(decimals) + "%";
}

function EdgeDots({ edge, cfg }: { edge: number; cfg?: LeagueCfg }) {
  const filled =
    edge >= 0.15 ? 5 : edge >= 0.1 ? 4 : edge >= 0.07 ? 3 : edge >= 0.04 ? 2 : edge >= 0.001 ? 1 : 0;
  const cls = ["e0", "e1", "e2", "e3", "e4", "e5"][filled];
  const dots = DOT_FULL.repeat(filled) + DOT_EMPTY.repeat(5 - filled);
  const dec = statDecimals(cfg, 1);
  return (
    <span className={"edge-dots " + cls} title={"Edge " + (edge * 100).toFixed(dec) + "%"}>
      {dots}
    </span>
  );
}

// --- Time Sort ----------------------------------------------------------------

function parseTime(t: string | undefined): number {
  if (!t) return 9999;

  const s = String(t).trim();

  const ampm = s.match(/(\d+):(\d+)\s*(AM|PM)/i);
  if (ampm) {
    let h = parseInt(ampm[1], 10);
    const min = parseInt(ampm[2], 10);
    if (ampm[3].toUpperCase() === "PM" && h !== 12) h += 12;
    if (ampm[3].toUpperCase() === "AM" && h === 12) h = 0;
    return h * 60 + min;
  }

  const military = s.match(/^(\d{1,2}):(\d{2})/);
  if (military) {
    const h = parseInt(military[1], 10);
    const min = parseInt(military[2], 10);
    if (!isNaN(h) && !isNaN(min)) return h * 60 + min;
  }

  return 9999;
}

// --- UFC: Find Nearest Event --------------------------------------------------

function ymdToFileDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return y + "_" + m + "_" + day;
}

async function findUFCEventDate(signal: AbortSignal): Promise<string | null> {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayStr = ymdToFileDate(today);

  // 1) Preferred path: read the manifest. Schema: ["YYYY_MM_DD", ...]
  try {
    const r = await fetch(BASE_RAW + UFC_MANIFEST_PATH, { cache: "no-store", signal });
    if (r.ok) {
      const dates = await r.json();
      if (Array.isArray(dates) && dates.length) {
        const sorted = [...dates].sort();
        const upcoming = sorted.find((d) => d >= todayStr);
        if (upcoming) return upcoming;
        // Nothing upcoming - show the most recent past event so the page is not empty between fight cards.
        return sorted[sorted.length - 1];
      }
    }
  } catch {
    /* fall through to probe */
  }

  // 2) Fallback: small probe (today + 7 days).
  const candidates: { date: string; offset: number }[] = [];
  for (let offset = 0; offset <= 7; offset++) {
    const d = new Date(today);
    d.setDate(today.getDate() + offset);
    candidates.push({ date: ymdToFileDate(d), offset });
  }

  const results = await Promise.all(
    candidates.map(async ({ date, offset }) => {
      const url = BASE_RAW + "win/mma/ufc/03_select/" + date + "_ufc_select.csv";
      try {
        const r = await fetch(url, { method: "HEAD", signal });
        return r.ok ? { date, offset } : null;
      } catch {
        return null;
      }
    })
  );

  const valid = results
    .filter((x): x is { date: string; offset: number } => !!x)
    .sort((a, b) => a.offset - b.offset);
  return valid.length ? valid[0].date : null;
}

// --- UFC: Load ----------------------------------------------------------------

async function loadUFC(signal: AbortSignal, setEventText: (text: string) => void): Promise<LeagueResult> {
  const cfg = REPO_CONFIG["UFC"];
  const eventDate = await findUFCEventDate(signal);

  if (signal.aborted) return { league: "UFC", cfg, picks: 0, error: "Cancelled" };

  // Update event selector
  setEventText(eventDate ? replaceAllText(eventDate, "_", "-") : "No upcoming event");

  if (!eventDate) return { league: "UFC", cfg, picks: 0, error: "No event found" };

  const url = BASE_RAW + "win/mma/ufc/03_select/" + eventDate + "_ufc_select.csv";
  const res = await fetchCSV(url, signal);

  if (!res.ok || res.rows.length === 0) return { league: "UFC", cfg, picks: 0 };

  return { league: "UFC", cfg, eventDate, rows: res.rows, picks: res.rows.length };
}

// --- League Loader ------------------------------------------------------------

async function loadLeague(
  league: string,
  dateFormatted: string,
  signal: AbortSignal,
  setEventText: (text: string) => void
): Promise<LeagueResult> {
  const cfg = REPO_CONFIG[league];
  if (!cfg) return { league, error: "No config" };

  // UFC uses its own loader
  if (cfg.isUFC) return loadUFC(signal, setEventText);

  const emptyRes: Promise<CsvResult> = Promise.resolve({ ok: false, rows: [] });

  const selectPaths = resolvePaths(cfg.selectFiles, dateFormatted);
  const predPaths = resolvePaths(cfg.predFile, dateFormatted);
  const bookPaths = resolvePaths(cfg.bookFile, dateFormatted);

  const [selectRes, predRes, bookRes] = await Promise.all([
    fetchMultiCSV(selectPaths, signal),
    predPaths.length ? fetchMultiCSV(predPaths, signal) : emptyRes,
    bookPaths.length ? fetchMultiCSV(bookPaths, signal) : emptyRes,
  ]);

  if (!selectRes.ok) return { league, cfg, error: "File not found", picks: 0 };

  // Allow leagues with non-canonical column names (e.g. soccer's match_date) to remap into the standard shape.
  const normalize = cfg.normalizeRow ? (r: Row) => (cfg.normalizeRow as (row: Row) => Row)(r) : (r: Row) => r;
  const normalizedSelect = selectRes.rows.flatMap((r) => {
    const normalized = normalize(r);

    if (cfg.expandRows) {
      return cfg.expandRows(normalized);
    }

    return [normalized];
  });

  const { rows: selectRows, stale, fromDate } = filterRows(normalizedSelect, dateFormatted, league, cfg);
  if (selectRows.length === 0) return { league, cfg, picks: 0, stale, fromDate };

  const predMap = buildMap(predRes.rows, cfg);
  const bookMap = buildMap(bookRes.rows, cfg);
  const merged = mergeRows(selectRows, predMap, bookMap, cfg);

  const grouped: Record<string, Row[]> = {};
  merged.forEach((r) => {
    if (!grouped[r.__key]) grouped[r.__key] = [];
    grouped[r.__key].push(r);
  });

  const keys = Object.keys(grouped).sort((a, b) => parseTime(grouped[a][0].game_time) - parseTime(grouped[b][0].game_time));

  return { league, cfg, keys, grouped, stale, fromDate, picks: merged.length };
}

// --- Analytics ----------------------------------------------------------------

type Analytics = { capture: (eventName: string, properties?: Record<string, unknown>) => void };

function getAnalytics(): Analytics | undefined {
  return (window as unknown as { SMHAnalytics?: Analytics }).SMHAnalytics;
}

// --- Cards --------------------------------------------------------------------

function PickCard({ p, r, cfg, onClick }: { p: Row; r: Row; cfg: LeagueCfg; onClick: () => void }) {
  const betText = buildBetText(p, r, cfg);
  const edge = extractEdge(p);
  const ev = getEv(p);
  const isBaseball = !!cfg.isBaseball;
  const dec = statDecimals(cfg, 1);

  // MLB-only: warn when lineup info is not yet available for this game.
  const lowConf = isBaseball && (p.low_confidence === "1" || (p.low_confidence as unknown) === 1);

  return (
    <div className={"pick-card" + (cfg.isFootball ? " football-pick" : "")} onClick={onClick}>
      {lowConf ? <div className="card-warning">Lineups not available yet</div> : null}
      <div className="card-top">
        <span className="card-time">{r.game_time || DASH}</span>
        <span className="card-league-tag">{cfg.displayName}</span>
      </div>
      <div className="card-matchup">
        <span className="card-team">{r.away_team || DASH}</span>
        <span className="card-at">@</span>
        <span className="card-team">{r.home_team || DASH}</span>
      </div>
      {isBaseball && (r.away_pitcher || r.home_pitcher) ? (
        <div className="card-pitchers">{(r.away_pitcher || "?") + " vs " + (r.home_pitcher || "?")}</div>
      ) : null}
      <div className="card-bet">{betText}</div>
      <div className="card-footer">
        <span className={"card-ev " + (ev >= 0 ? "pos" : "neg")}>{formatPercentValue(ev, dec, true)}</span>
        <EdgeDots edge={edge} cfg={cfg} />
      </div>
    </div>
  );
}

function UfcCard({ row, onClick }: { row: Row; onClick: () => void }) {
  const fighter = row.fighter || DASH;
  const opponent = row.opponent || DASH;
  const ml = row.moneyline || DASH;
  const ev = parseFloat(String(row.ev || 0));
  const edge = parseFloat(String(row.edge || 0));

  return (
    <div className="pick-card" onClick={onClick}>
      <div className="card-top">
        <span className="card-time">MMA</span>
        <span className="card-league-tag">UFC</span>
      </div>
      <div className="card-matchup">
        <span className="card-team">{fighter}</span>
        <span className="card-at">vs</span>
        <span className="card-team">{opponent}</span>
      </div>
      <div className="card-bet">{fighter + " " + ml}</div>
      <div className="card-footer">
        <span className={"card-ev " + (ev >= 0 ? "pos" : "neg")}>{formatPercentValue(ev, 1, true)}</span>
        <EdgeDots edge={edge} />
      </div>
    </div>
  );
}

// --- Modals -------------------------------------------------------------------

function PickModalContent({ r, picks, cfg }: { r: Row; picks: Row[]; cfg: LeagueCfg }): ReactNode {
  if (cfg.isFootball) {
    return (
      <>
        <div className="modal-header">
          <span className="modal-league-tag">{cfg.displayName}</span>
          <span className="modal-game-time">{r.game_time || ""}</span>
        </div>

        <h2 className="modal-title">
          {r.away_team || DASH} <span className="modal-at">@</span> {r.home_team || DASH}
        </h2>

        <div className="modal-picks-section">
          <div className="modal-picks-label">PICKS</div>
          <div className="modal-picks">
            {picks.map((p, i) => (
              <div className="modal-pick-row" key={i}>
                <div className="modal-bet">{buildBetText(p, r, cfg)}</div>
              </div>
            ))}
          </div>
        </div>
      </>
    );
  }

  // Soccer: simpler modal - no projections / spreads / totals exist for these markets.
  if (cfg.isSoccer) {
    return (
      <>
        <div className="modal-header">
          <span className="modal-league-tag">{cfg.displayName}</span>
          <span className="modal-game-time">{r.game_time || ""}</span>
        </div>
        <h2 className="modal-title">
          {r.home_team || DASH} <span className="modal-at">vs</span> {r.away_team || DASH}
        </h2>
        <div className="modal-picks-section">
          <div className="modal-picks-label">PICKS</div>
          <div className="modal-picks">
            {picks.map((p, i) => {
              const ev = getEv(p);
              const kelly = getKelly(p);
              const edge = extractEdge(p);
              const dec = statDecimals(cfg, 2);
              return (
                <div className="modal-pick-row" key={i}>
                  <div className="modal-bet">{buildBetText(p, r, cfg)}</div>
                  <div className="modal-pick-stats">
                    <span className={"modal-ev " + (ev >= 0 ? "pos" : "neg")}>{formatPercentValue(ev, dec, true) + " EV"}</span>
                    <span className="modal-kelly">{"Kelly " + formatPercentValue(kelly, dec, false)}</span>
                    <EdgeDots edge={edge} cfg={cfg} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </>
    );
  }

  const isHockey = !!cfg.isHockey;
  const isBaseball = !!cfg.isBaseball;

  const projAway = isHockey ? r.away_projected_goals : isBaseball ? r.away_projected_runs : r.away_projected_points;
  const projHome = isHockey ? r.home_projected_goals : isBaseball ? r.home_projected_runs : r.home_projected_points;
  const projTotal = isHockey ? r.total_projected_goals : isBaseball ? r.total_projected_runs : r.total_projected_points;

  const spreadKey = isHockey ? "puck_line" : isBaseball ? "run_line" : "spread";
  const spreadAway = r["away_" + spreadKey] || r.away_spread || DASH;
  const spreadHome = r["home_" + spreadKey] || r.home_spread || DASH;
  const spreadAwayOdds = r["away_dk_" + spreadKey + "_american"] || r.away_dk_spread_american || DASH;
  const spreadHomeOdds = r["home_dk_" + spreadKey + "_american"] || r.home_dk_spread_american || DASH;

  return (
    <>
      <div className="modal-header">
        <span className="modal-league-tag">{cfg.displayName}</span>
        <span className="modal-game-time">{r.game_time || ""}</span>
      </div>
      <h2 className="modal-title">
        {r.away_team || DASH} <span className="modal-at">@</span> {r.home_team || DASH}
      </h2>
      {isBaseball && (r.away_pitcher || r.home_pitcher) ? (
        <div className="modal-pitchers">
          <span className="modal-pitcher-label">SP</span>
          {r.away_pitcher || "?"} <span className="modal-pitcher-vs">vs</span> {r.home_pitcher || "?"}
        </div>
      ) : null}
      <div className="modal-proj">
        <span>
          {"Proj " + (r.away_team || "Away") + ": "}
          <strong>{projAway || DASH}</strong>
        </span>
        <span>
          {"Proj " + (r.home_team || "Home") + ": "}
          <strong>{projHome || DASH}</strong>
        </span>
        <span>
          {"Total: "}
          <strong>{projTotal || DASH}</strong>
        </span>
      </div>
      <div className="modal-lines">
        <div className="modal-line-row">
          <span className="line-label">ML</span>
          <span>{(r.away_dk_moneyline_american || DASH) + " / " + (r.home_dk_moneyline_american || DASH)}</span>
        </div>
        <div className="modal-line-row">
          <span className="line-label">{spreadKey.replace("_", " ").toUpperCase()}</span>
          <span>{spreadAway + " (" + spreadAwayOdds + ") / " + spreadHome + " (" + spreadHomeOdds + ")"}</span>
        </div>
        <div className="modal-line-row">
          <span className="line-label">TOTAL</span>
          <span>
            {(r.total || DASH) +
              " " +
              NBSP +
              " O " +
              (r.dk_total_over_american || DASH) +
              " / U " +
              (r.dk_total_under_american || DASH)}
          </span>
        </div>
      </div>
      <div className="modal-picks-section">
        <div className="modal-picks-label">PICKS</div>
        <div className="modal-picks">
          {picks.map((p, i) => {
            const ev = getEv(p);
            const kelly = getKelly(p);
            const edge = extractEdge(p);
            const dec = statDecimals(cfg, 2);
            return (
              <div className="modal-pick-row" key={i}>
                <div className="modal-bet">{buildBetText(p, r, cfg)}</div>
                <div className="modal-pick-stats">
                  <span className={"modal-ev " + (ev >= 0 ? "pos" : "neg")}>{formatPercentValue(ev, dec, true) + " EV"}</span>
                  <span className="modal-kelly">{"Kelly " + formatPercentValue(kelly, dec, false)}</span>
                  <EdgeDots edge={edge} cfg={cfg} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

function UfcModalContent({ row }: { row: Row }): ReactNode {
  const fighter = row.fighter || DASH;
  const opponent = row.opponent || DASH;
  const ml = row.moneyline || DASH;
  const impliedProb = parseFloat(String(row.implied_prob || 0));
  const modelProb = parseFloat(String(row.model_prob || 0));
  const edge = parseFloat(String(row.edge || 0));
  const ev = parseFloat(String(row.ev || 0));
  const kelly = parseFloat(String(row.kelly || 0));

  const fmt = (n: number, dec = 1): string => (isNaN(n) ? DASH : (n * 100).toFixed(dec) + "%");

  return (
    <>
      <div className="modal-header">
        <span className="modal-league-tag">UFC</span>
        <span className="modal-game-time">{row.match_date ? replaceAllText(row.match_date, "_", "-") : ""}</span>
      </div>
      <h2 className="modal-title">
        {fighter} <span className="modal-at">vs</span> {opponent}
      </h2>
      <div className="modal-proj">
        <span>
          {"Moneyline: "}
          <strong>{ml}</strong>
        </span>
        <span>
          {"Implied: "}
          <strong>{fmt(impliedProb)}</strong>
        </span>
        <span>
          {"Model: "}
          <strong>{fmt(modelProb)}</strong>
        </span>
      </div>
      <div className="modal-picks-section">
        <div className="modal-picks-label">EDGE ANALYSIS</div>
        <div className="modal-picks">
          <div className="modal-pick-row">
            <div className="modal-bet">{fighter + " to Win"}</div>
            <div className="modal-pick-stats">
              <span className={"modal-ev " + (ev >= 0 ? "pos" : "neg")}>{formatPercentValue(ev, 2, true) + " EV"}</span>
              <span className="modal-kelly">{"Kelly " + formatPercentValue(kelly, 2, false)}</span>
              <span className="modal-kelly">{"Edge " + formatPercentValue(edge, 2, false)}</span>
              <EdgeDots edge={edge} />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// --- Page ---------------------------------------------------------------------

export default function ThePicks() {
  const [dateStr, setDateStr] = useState<string>(todayLocal);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusText, setStatusText] = useState<string>("");
  const [results, setResults] = useState<LeagueResult[] | null>(null);
  const [ufcText, setUfcText] = useState<string>("Loading...");
  // The active filter pill, and whether it has been applied to the columns (legacy applied it only to columns that already existed).
  const [pill, setPill] = useState<string>("all");
  const [pillApplied, setPillApplied] = useState<boolean>(false);
  const [modal, setModal] = useState<ModalData | null>(null);
  const [modalOpen, setModalOpen] = useState<boolean>(false);

  // Honor `enabled: false` on a league config so it disappears from the page (header + filter pill + data load).
  const leagues = PICKS_LEAGUES.filter((l) => {
    const cfg = REPO_CONFIG[l];
    return cfg && cfg.enabled !== false;
  });

  useEffect(() => {
    const ctl = new AbortController();
    let cancelled = false;
    const dateFormatted = toUnderscore(dateStr);

    setLoading(true);
    setStatusText("Loading" + ELLIPSIS);
    setResults(null);
    setPill("all");
    setPillApplied(false);

    const setEventText = (text: string) => {
      if (!cancelled) setUfcText(text);
    };

    (async () => {
      const res = await Promise.all(leagues.map((l) => loadLeague(l, dateFormatted, ctl.signal, setEventText)));
      if (cancelled) return;

      let totalPicks = 0;
      res.forEach((result) => {
        totalPicks += countCards(result);
      });

      setResults(res);
      setStatusText(totalPicks + " pick" + (totalPicks !== 1 ? "s" : "") + " " + MID + " " + dateStr);
      setLoading(false);
    })();

    return () => {
      cancelled = true;
      ctl.abort();
    };
    // leagues is derived from constants and never changes
  }, [dateStr]);

  const openModal = (data: ModalData) => {
    setModal(data);
    setModalOpen(true);
  };

  const onPickClick = (result: LeagueResult, p: Row, r: Row, picks: Row[]) => {
    const analytics = getAnalytics();

    if (analytics) {
      const probability = [p.model_prob, p.bet_model_prob, p.bet_adjusted_model_prob, p.selected_model_prob, p.model_probability].find(
        (value) => value !== undefined && value !== null && value !== ""
      );

      analytics.capture("pick_viewed", {
        league: result.league,
        sport: result.cfg && result.cfg.sport,
        matchup:
          result.cfg && result.cfg.isSoccer
            ? (r.home_team || LEGACY_ANALYTICS_DASH) + " vs " + (r.away_team || LEGACY_ANALYTICS_DASH)
            : (r.away_team || LEGACY_ANALYTICS_DASH) + " @ " + (r.home_team || LEGACY_ANALYTICS_DASH),
        bet_type: p.market_type || p.market,
        model_probability: probability,
        edge: extractEdge(p),
        selected_date: dateStr ? dateStr : r.game_date,
      });
    }

    openModal({ kind: "pick", r, picks, cfg: result.cfg as LeagueCfg });
  };

  const onUfcClick = (row: Row) => {
    const analytics = getAnalytics();

    if (analytics) {
      const fighter = row.fighter || DASH;
      const opponent = row.opponent || DASH;
      analytics.capture("pick_viewed", {
        league: "UFC",
        sport: "mma",
        matchup: fighter + " vs " + opponent,
        bet_type: "moneyline",
        model_probability: row.model_prob,
        edge: row.edge,
        selected_date: row.match_date,
      });
    }

    openModal({ kind: "ufc", row });
  };

  const renderColumn = (result: LeagueResult): ReactNode => {
    const count = countCards(result);
    // Columns without a pick are hidden until a filter pill is chosen; a chosen pill shows "All" or just its own column.
    const visible = pillApplied ? pill === "all" || result.league === pill : count > 0;
    const style = visible ? undefined : { display: "none" };

    // UFC uses its own renderer
    if (result.league === "UFC") {
      return (
        <div className="league-column" data-league="UFC" key="UFC" style={style}>
          <div className="league-header">UFC</div>
          {result.error || !result.rows || result.rows.length === 0 ? (
            <div className="col-state empty">No UFC Picks</div>
          ) : (
            <div className="league-cards">
              {result.rows.map((row, i) => (
                <UfcCard row={row} key={i} onClick={() => onUfcClick(row)} />
              ))}
            </div>
          )}
        </div>
      );
    }

    const header = (result.cfg && result.cfg.displayName) || result.league;

    let body: ReactNode;
    if (result.error || result.stale || !result.keys || result.keys.length === 0 || !result.grouped || !result.cfg) {
      body = <div className="col-state empty">No Picks Today</div>;
    } else {
      const grouped = result.grouped;
      const cards: ReactNode[] = [];
      result.keys.forEach((key) => {
        const picks = grouped[key];
        const r = picks[0];
        picks.forEach((p, i) => {
          cards.push(
            <PickCard
              key={key + ":" + i}
              p={p}
              r={r}
              cfg={result.cfg as LeagueCfg}
              onClick={() => onPickClick(result, p, r, picks)}
            />
          );
        });
      });
      body = <div className="league-cards">{cards}</div>;
    }

    return (
      <div className="league-column" data-league={result.league} key={result.league} style={style}>
        <div className="league-header">{header}</div>
        {body}
      </div>
    );
  };

  let gamesNode: ReactNode = null;
  if (results) {
    const total = results.reduce((sum, result) => sum + countCards(result), 0);
    gamesNode =
      total === 0 ? <div className="empty-state">NO PICKS FOR THIS DATE</div> : results.map((result) => renderColumn(result));
  }

  const choosePill = (sel: string) => {
    setPill(sel);
    if (results) setPillApplied(true);
  };

  return (
    <>
      <div className="picks-header">
        <h1 className="picks-title">PICKS</h1>
        <div id="status" className={"status" + (loading ? " loading" : "")}>
          {statusText}
        </div>
      </div>

      <div className="picks-controls">
        <div className="date-wrap">
          <span className="date-label">Date</span>
          <input id="p-date" type="date" value={dateStr} onChange={(e) => setDateStr(e.target.value || "")} />
        </div>
        <div className="ufc-event-wrap">
          <span className="ufc-event-label">UFC Event</span>
          <div id="ufc-event-selector">{ufcText}</div>
        </div>
        <div id="league-filters">
          <div
            className={"filter-pill" + (pill === "all" ? " active" : "")}
            data-league="all"
            onClick={() => choosePill("all")}
          >
            All
          </div>
          {leagues.map((l) => {
            const cfg = REPO_CONFIG[l];
            return (
              <div
                key={l}
                className={"filter-pill" + (pill === l ? " active" : "")}
                data-league={l}
                onClick={() => choosePill(l)}
              >
                {(cfg && cfg.displayName) || l}
              </div>
            );
          })}
        </div>
      </div>

      <div id="games">{gamesNode}</div>

      <div
        id="modal"
        className={"modal" + (modalOpen ? " open" : "")}
        onClick={(e) => {
          if (e.target === e.currentTarget) setModalOpen(false);
        }}
      >
        <div className="modal-card" onClick={(e) => e.stopPropagation()}>
          <div id="modal-content">
            {modal ? (
              modal.kind === "ufc" ? (
                <UfcModalContent row={modal.row} />
              ) : (
                <PickModalContent r={modal.r} picks={modal.picks} cfg={modal.cfg} />
              )
            ) : null}
          </div>
          <button className="modal-close-btn" onClick={() => setModalOpen(false)}>
            Close
          </button>
        </div>
      </div>
    </>
  );
}

// Number of cards a league column shows (same rules as the column renderers).
function countCards(result: LeagueResult): number {
  if (result.league === "UFC") {
    return result.error || !result.rows || result.rows.length === 0 ? 0 : result.rows.length;
  }

  if (result.error || result.stale || !result.keys || result.keys.length === 0 || !result.grouped) return 0;

  const grouped = result.grouped;
  let count = 0;
  result.keys.forEach((key) => {
    count += grouped[key].length;
  });
  return count;
}
