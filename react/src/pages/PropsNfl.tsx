/*
  PropsNfl - native React port of legacy props_nfl.html + assets/js/pages/props_nfl.js.

  Legacy behaviors found and preserved:
   1. Season select and Week select (Week 1 to Week 18). CHANGE REQUESTED BY THE USER: the starting season and week are read from
      docs/win/football/prop_engine/config/settings.yaml (season: / week:) in the same GitHub repo; they are not hard-coded.
      If that file cannot be read, the legacy defaults (first season, Week 1) are used and a warning is logged to the console.
      Changing either select clears the selected prop type and game and reloads the week.
   2. Loading a week fetches, in parallel with cache: "no-store" from
      https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main:
        docs/win/football/prop_engine/prop_picks_final/{season}/stage_2/week_{week}/{path}/week_{week}_{suffix}.csv
        for 7 prop types (passing, rushing, receiving, kicking, defense = Tackles, combo/pass_rush_yds, combo/rec_rush_yds),
        and docs/win/football/nfl/00_intake/schedule/weekly/week_{week}_NFL_weekly_schedule.csv.
      A failed or non-OK request gives no rows for that file. Rows are tagged with their prop_type.
      The schedule keeps rows with no season or with the selected season.
   3. Status text: "Loading {season} Week {week}...", then "{season} Week {week}", or
      "No data found for {season} Week {week}." when both schedule and props are empty.
   4. CSV parser: quoted fields, doubled quotes, newline rows with trailing CR removed, trimmed headers, blank rows dropped.
   5. Prop type buttons: "All Prop Types (N)" and "{label} (count)", counts ignore pick = no_bet and respect the selected game.
      Clicking one selects it (the selected game is kept).
   6. Game buttons: "All Games" (count of non-no_bet picks) and one per scheduled game
      ("away @ home", "{game_date} - {count} picks"). Clicking a game selects it AND clears the selected prop type.
      "All Games" clears the game only.
   7. Results: no_bet rows removed, filtered by game and prop type, sorted by pick_prob descending (missing = -1),
      title ("{game} - {prop}", game, prop or "Picks"), "{n} picks" count, "No qualifying picks." when empty.
      Each card shows player, prop label, game, pick (over/under colour), Sportsbook Line, Pick/Over/Under Prob (4 decimals),
      Projection, Low and High from the prop's own columns.
   8. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials (nav.js is loaded by SiteShell).
  Fix: the Prop Types and Game Props sections carry the extra class "active" because the site-wide dashboard.css
  hides every ".section" unless it is ".section.active" (all page CSS is bundled together in the React site).
  Differences: requests are cancelled when superseded or when the page is left; CSV text is rendered as React text
  (legacy escaped it into innerHTML); before the first load finishes the buttons and results are empty, as in legacy.
*/
import { useEffect, useRef, useState } from "react";
import "../../../app/frontend/src/assets/css/pages/props_nfl.css";

const MID = String.fromCharCode(0xb7);
const BULLET = String.fromCharCode(0x2022);

const RAW_ROOT = "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main";

const SETTINGS_URL = `${RAW_ROOT}/docs/win/football/prop_engine/config/settings.yaml`;

const AVAILABLE_SEASONS = [2026];
const AVAILABLE_WEEKS = Array.from({ length: 18 }, (_, i) => i + 1);

type PropType = {
  key: string;
  label: string;
  path: string;
  suffix: string;
  line: string;
  projection: string;
  low: string;
  high: string;
};

const PROP_TYPES: PropType[] = [
  {
    key: "passing",
    label: "Passing Yards",
    path: "passing",
    suffix: "passing",
    line: "actual_prop_total_passing_yards",
    projection: "prop_engine_passing_yards",
    low: "prop_engine_passing_yards_low",
    high: "prop_engine_passing_yards_high",
  },
  {
    key: "rushing",
    label: "Rushing Yards",
    path: "rushing",
    suffix: "rushing",
    line: "actual_prop_total_rushing_yards",
    projection: "prop_engine_rushing_yards",
    low: "prop_engine_rushing_yards_low",
    high: "prop_engine_rushing_yards_high",
  },
  {
    key: "receiving",
    label: "Receiving Yards",
    path: "receiving",
    suffix: "receiving",
    line: "actual_prop_total_receiving_yards",
    projection: "prop_engine_receiving_yards",
    low: "prop_engine_receiving_yards_low",
    high: "prop_engine_receiving_yards_high",
  },
  {
    key: "kicking",
    label: "Kicking Points",
    path: "kicking",
    suffix: "kicking",
    line: "actual_prop_total_kicking_points",
    projection: "prop_engine_kicking_points",
    low: "prop_engine_kicking_points_low",
    high: "prop_engine_kicking_points_high",
  },
  {
    key: "defense",
    label: "Tackles",
    path: "defense",
    suffix: "defense",
    line: "actual_prop_total_tackles",
    projection: "prop_engine_tackles",
    low: "prop_engine_tackles_low",
    high: "prop_engine_tackles_high",
  },
  {
    key: "pass_rush",
    label: "Passing/Rushing Yards",
    path: "combo/pass_rush_yds",
    suffix: "pass_rush_yds",
    line: "actual_prop_total_passing_plus_rushing_yards",
    projection: "prop_engine_pr",
    low: "prop_engine_pr_low",
    high: "prop_engine_pr_high",
  },
  {
    key: "rec_rush",
    label: "Rushing/Receiving Yards",
    path: "combo/rec_rush_yds",
    suffix: "rec_rush_yds",
    line: "actual_prop_total_rushing_plus_receiving_yards",
    projection: "prop_engine_rr",
    low: "prop_engine_rr_low",
    high: "prop_engine_rr_high",
  },
];

type Row = Record<string, string>;

function parseCsv(text: string): Row[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];

    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          quoted = false;
        }
      } else {
        field += ch;
      }
    } else {
      if (ch === '"') {
        quoted = true;
      } else if (ch === ",") {
        row.push(field);
        field = "";
      } else if (ch === "\n") {
        row.push(field.replace(/\r$/, ""));
        rows.push(row);
        row = [];
        field = "";
      } else {
        field += ch;
      }
    }
  }

  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }

  if (!rows.length) return [];

  const headers = rows[0].map((h) => h.trim());

  return rows
    .slice(1)
    .filter((r) => r.some((v) => String(v).trim() !== ""))
    .map((r) => {
      const obj: Row = {};
      headers.forEach((h, index) => {
        obj[h] = r[index] ?? "";
      });
      return obj;
    });
}

async function fetchCsv(url: string, signal: AbortSignal): Promise<Row[]> {
  const response = await fetch(url, { cache: "no-store", signal });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return parseCsv(await response.text());
}

function stage2Url(season: number, week: number, config: PropType): string {
  return (
    `${RAW_ROOT}/docs/win/football/prop_engine/prop_picks_final/` +
    `${season}/stage_2/week_${week}/${config.path}/` +
    `week_${week}_${config.suffix}.csv`
  );
}

function scheduleUrl(week: number): string {
  return (
    `${RAW_ROOT}/docs/win/football/nfl/00_intake/schedule/weekly/` +
    `week_${week}_NFL_weekly_schedule.csv`
  );
}

function numeric(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function formatProb(value: unknown): string {
  const n = numeric(value);
  return n === null ? "" : n.toFixed(4);
}

function txt(value: unknown): string {
  return String(value ?? "");
}

function parseSettings(text: string): { season: number; week: number } | null {
  const s = /^\s*season\s*:\s*(\d+)\s*(?:#.*)?$/m.exec(text);
  const w = /^\s*week\s*:\s*(\d+)\s*(?:#.*)?$/m.exec(text);
  if (!s || !w) return null;
  const season = Number(s[1]);
  const week = Number(w[1]);
  if (!(season > 0) || !(week > 0)) return null;
  return { season, week };
}

export default function PropsNfl() {
  const [season, setSeason] = useState<number>(AVAILABLE_SEASONS[0]);
  const [week, setWeek] = useState<number>(1);
  const [schedule, setSchedule] = useState<Row[]>([]);
  const [props, setProps] = useState<Row[]>([]);
  const [selectedProp, setSelectedProp] = useState<string | null>(null);
  const [selectedGame, setSelectedGame] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("");
  const [loaded, setLoaded] = useState<boolean>(false);

  const ctlRef = useRef<AbortController | null>(null);

  const loadWeek = async (seasonValue: number, weekValue: number) => {
    if (ctlRef.current) ctlRef.current.abort();
    const ctl = new AbortController();
    ctlRef.current = ctl;

    setStatus(`Loading ${seasonValue} Week ${weekValue}...`);

    const schedulePromise = fetchCsv(scheduleUrl(weekValue), ctl.signal).catch(
      (): Row[] => []
    );

    const propPromises = PROP_TYPES.map(async (config) => {
      try {
        const rows = await fetchCsv(stage2Url(seasonValue, weekValue, config), ctl.signal);
        return rows.map((row) => ({ ...row, prop_type: config.key }));
      } catch (_) {
        return [] as Row[];
      }
    });

    const [sched, propGroups] = await Promise.all([schedulePromise, Promise.all(propPromises)]);

    if (ctl.signal.aborted) return;

    const filteredSchedule = sched.filter(
      (row) => !row.season || String(row.season) === String(seasonValue)
    );
    const allProps = propGroups.flat();

    setSchedule(filteredSchedule);
    setProps(allProps);
    setLoaded(true);

    if (!filteredSchedule.length && !allProps.length) {
      setStatus(`No data found for ${seasonValue} Week ${weekValue}.`);
    } else {
      setStatus(`${seasonValue} Week ${weekValue}`);
    }
  };

  useEffect(() => {
    const settingsCtl = new AbortController();
    setStatus("Loading settings...");

    (async () => {
      let start = { season: AVAILABLE_SEASONS[0], week: 1 };
      try {
        const response = await fetch(SETTINGS_URL, { cache: "no-store", signal: settingsCtl.signal });
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        const parsed = parseSettings(await response.text());
        if (!parsed) throw new Error("season/week not found in settings.yaml");
        start = parsed;
      } catch (e) {
        if (settingsCtl.signal.aborted) return;
        console.warn("props_nfl: could not read settings.yaml, using first season and Week 1", e);
      }
      if (settingsCtl.signal.aborted) return;
      setSeason(start.season);
      setWeek(start.week);
      loadWeek(start.season, start.week);
    })();

    return () => {
      settingsCtl.abort();
      if (ctlRef.current) ctlRef.current.abort();
    };
  }, []);

  const seasonOptions = AVAILABLE_SEASONS.indexOf(season) === -1
    ? AVAILABLE_SEASONS.concat([season]).sort((a, b) => a - b)
    : AVAILABLE_SEASONS;
  const weekOptions = AVAILABLE_WEEKS.indexOf(week) === -1
    ? AVAILABLE_WEEKS.concat([week]).sort((a, b) => a - b)
    : AVAILABLE_WEEKS;

  const gameLabel = (gameId: unknown): string => {
    const game = schedule.find((g) => String(g.game_id) === String(gameId));
    if (!game) return String(gameId);
    return `${game.away_team} @ ${game.home_team}`;
  };

  // Prop type buttons
  const gameFilteredRows = props.filter((row) => {
    if (row.pick === "no_bet") return false;
    if (!selectedGame) return true;
    return String(row.game_id) === selectedGame;
  });

  // Results
  let rows = props.filter((row) => row.pick !== "no_bet");
  if (selectedGame) {
    rows = rows.filter((row) => String(row.game_id) === selectedGame);
  }
  let selectedPropConfig: PropType | undefined;
  if (selectedProp) {
    selectedPropConfig = PROP_TYPES.find((p) => p.key === selectedProp);
    rows = rows.filter((row) => row.prop_type === selectedProp);
  }

  let title: string;
  if (selectedGame && selectedPropConfig) {
    title = `${gameLabel(selectedGame)} ${MID} ${selectedPropConfig.label}`;
  } else if (selectedGame) {
    title = gameLabel(selectedGame);
  } else if (selectedPropConfig) {
    title = selectedPropConfig.label;
  } else {
    title = "Picks";
  }

  rows = rows
    .slice()
    .sort((a, b) => (numeric(b.pick_prob) ?? -1) - (numeric(a.pick_prob) ?? -1));

  const allGamesCount = props.filter((row) => row.pick !== "no_bet").length;

  return (
    <>
      <header className="page-header">
        <div className="page-title">NFL Props</div>
        <div className="page-subtitle">
          {["MODEL PICKS", "PLAYER PROJECTIONS", "OVER/UNDER PROBABILITIES"].join(
            " " + MID + " "
          )}
        </div>
      </header>

      <main className="main">
        <div className="selector-row">
          <div className="selector-block">
            <label className="selector-label" htmlFor="seasonSelect">
              Season
            </label>
            <select
              id="seasonSelect"
              className="selector"
              value={String(season)}
              onChange={(event) => {
                const v = Number(event.target.value);
                setSeason(v);
                setSelectedProp(null);
                setSelectedGame(null);
                loadWeek(v, week);
              }}
            >
              {seasonOptions.map((s) => (
                <option key={s} value={String(s)}>
                  {String(s)}
                </option>
              ))}
            </select>
          </div>

          <div className="selector-block">
            <label className="selector-label" htmlFor="weekSelect">
              Week
            </label>
            <select
              id="weekSelect"
              className="selector"
              value={String(week)}
              onChange={(event) => {
                const v = Number(event.target.value);
                setWeek(v);
                setSelectedProp(null);
                setSelectedGame(null);
                loadWeek(season, v);
              }}
            >
              {weekOptions.map((w) => (
                <option key={w} value={String(w)}>
                  {`Week ${w}`}
                </option>
              ))}
            </select>
          </div>

          <div id="status">{status}</div>
        </div>

        <section className="section active">
          <div className="section-title">Prop Types</div>
          <div id="propButtons" className="button-grid">
            {loaded ? (
              <>
                <button
                  className={selectedProp === null ? "active" : ""}
                  onClick={() => setSelectedProp(null)}
                >
                  {`All Prop Types (${gameFilteredRows.length})`}
                </button>
                {PROP_TYPES.map((config) => {
                  const count = gameFilteredRows.filter(
                    (row) => row.prop_type === config.key
                  ).length;
                  return (
                    <button
                      key={config.key}
                      className={selectedProp === config.key ? "active" : ""}
                      onClick={() => setSelectedProp(config.key)}
                    >
                      {`${config.label} (${count})`}
                    </button>
                  );
                })}
              </>
            ) : null}
          </div>
        </section>

        <section className="section active">
          <div className="section-title">Game Props</div>
          <div id="gameButtons">
            {loaded ? (
              <>
                <button
                  className={"game-button" + (selectedGame === null ? " active" : "")}
                  onClick={() => setSelectedGame(null)}
                >
                  <span className="teams">All Games</span>
                  <span className="meta">{`${allGamesCount} picks`}</span>
                </button>
                {schedule.map((game, i) => {
                  const gameId = String(game.game_id);
                  const count = props.filter(
                    (row) => String(row.game_id) === gameId && row.pick !== "no_bet"
                  ).length;
                  return (
                    <button
                      key={i}
                      className={"game-button" + (selectedGame === gameId ? " active" : "")}
                      onClick={() => {
                        setSelectedGame(gameId);
                        setSelectedProp(null);
                      }}
                    >
                      <span className="teams">{`${game.away_team} @ ${game.home_team}`}</span>
                      <span className="meta">{`${game.game_date || ""} ${BULLET} ${count} picks`}</span>
                    </button>
                  );
                })}
              </>
            ) : null}
          </div>
        </section>

        <section className="results-section">
          <div className="results-header">
            <div className="results-title" id="resultsTitle">
              {title}
            </div>
            <div id="resultCount">{loaded ? `${rows.length} picks` : ""}</div>
          </div>
          <div id="results">
            {!loaded ? null : !rows.length ? (
              <div className="empty">No qualifying picks.</div>
            ) : (
              <div className="pick-grid">
                {rows.map((row, i) => {
                  const config = PROP_TYPES.find((p) => p.key === row.prop_type) as PropType;
                  const pickClass = row.pick === "over" ? "pick-over" : "pick-under";
                  return (
                    <article className="pick-card-nfl" key={i}>
                      <div className="pick-card-head">
                        <div>
                          <div className="pick-player">{txt(row.player_name)}</div>
                          <div className="pick-prop">{txt(config.label || row.prop_type)}</div>
                          <div className="pick-game">{gameLabel(row.game_id)}</div>
                        </div>
                        <div className={"pick-choice " + pickClass}>{txt(row.pick)}</div>
                      </div>
                      <div className="pick-metrics">
                        <div className="pick-metric">
                          <div className="pick-metric-label">Sportsbook Line</div>
                          <div className="pick-metric-value">{txt(row[config.line])}</div>
                        </div>
                        <div className="pick-metric">
                          <div className="pick-metric-label">Pick Prob</div>
                          <div className="pick-metric-value prob">{formatProb(row.pick_prob)}</div>
                        </div>
                        <div className="pick-metric">
                          <div className="pick-metric-label">Over Prob</div>
                          <div className="pick-metric-value">{formatProb(row.over_prob)}</div>
                        </div>
                        <div className="pick-metric">
                          <div className="pick-metric-label">Under Prob</div>
                          <div className="pick-metric-value">{formatProb(row.under_prob)}</div>
                        </div>
                        <div className="pick-metric">
                          <div className="pick-metric-label">Projection</div>
                          <div className="pick-metric-value">{txt(row[config.projection])}</div>
                        </div>
                        <div className="pick-metric">
                          <div className="pick-metric-label">Low</div>
                          <div className="pick-metric-value">{txt(row[config.low])}</div>
                        </div>
                        <div className="pick-metric">
                          <div className="pick-metric-label">High</div>
                          <div className="pick-metric-value">{txt(row[config.high])}</div>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        </section>
      </main>
    </>
  );
}
