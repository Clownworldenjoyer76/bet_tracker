/*
  PropEngine - native React port of legacy prop_engine.html + assets/js/pages/prop_engine.js.

  Legacy behaviors found and preserved:
   1. League pills NBA (basketball/nba, default), NHL (hockey/nhl), MLB (baseball/mlb). Clicking one makes it active,
      refills the Prop select for that league, reloads teams, and resets the main area to
      "Select a player and prop to begin analysis" with the sub line "NBA - NHL - MLB".
   2. Prop lists: NBA (Points, Rebounds, Assists, 3-Point %, PRA (Pts+Reb+Ast), Blocks, Steals),
      NHL (Goals, Assists, Points, Shots on Goal, Power Play Goals), MLB (Hits, RBI, Strikeouts, Home Runs),
      each with its stat keys and abbreviation.
   3. Teams load on start and on league change from the ESPN scoreboard for the HARD-CODED date 20260428
      (https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates=20260428).
      Status "Loading teams..." (yellow); team and player selects are reset; no events -> "No games today";
      otherwise teams are collected from the competitors (id, displayName, abbreviation), sorted by name,
      status "Select a team"; an error -> "Failed to load teams".
   4. Choosing a team (not the empty option) loads the roster (.../teams/{id}/roster): player select shows "Loading...",
      players come from data.athletes groups (items / athletes / the group itself if it has an id), only those with an id,
      sorted by displayName, shown as displayName || fullName || id, status "Select a player";
      a failure shows "Failed to load" in the select and "Failed to load players". Choosing the empty team option does nothing.
   5. Analyze runs from the Analyze button, when a player is chosen, and when the prop changes while a player is selected.
      Games = clamp(parseInt(value) || 15, 5, 82). No player or prop -> "Select a player and prop".
      An unknown player id returns silently. Status "Loading..." (yellow) and main "Loading...".
      Fetches https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{id}/overview.
      No data -> "Failed to load" / "Failed to load data". No usable game log -> "No data for {prop}" / "No game log data for {prop}".
      Otherwise status "{N} games - {prop}" (green) and the results render.
   6. Game log parsing: first statistics group, labels/names matched case-insensitively against the stat keys (+ abbreviation),
      PRA = points + rebounds + assists (all three required), date from the event, opponent abbreviation / atVs / "?", result;
      sorted newest first.
   7. Results: banner (headshot or placeholder, name, "pos - team - LEAGUE", "{prop} - Last {n} Games"), stat strip
      (Average, Last 3 Avg with HOT/COLD/AVG at +/-10%, Season High, Season Low), "Hit Rate by Line (Over)" with 7 lines from
      max(0, floor((avg-2)/0.5)*0.5) in 0.5 steps (bar green >= 65%, yellow >= 50%, red otherwise, percent and hits/total),
      and the Game Log table (date, opponent, W/L coloured, value coloured over/under the rounded average).
   8. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials (nav.js is loaded by SiteShell).
  Differences: requests are cancelled when superseded or when the page is left; ESPN text is rendered as React text
  (legacy inserted it into innerHTML).
*/
import { useEffect, useRef, useState } from "react";
import "../../../app/frontend/src/assets/css/pages/prop_engine.css";

const MID = String.fromCharCode(0xb7);
const DASH = String.fromCharCode(0x2014);
const UP = String.fromCharCode(0x25b2);
const DOWN = String.fromCharCode(0x25bc);
const RIGHT = String.fromCharCode(0x2192);
const PERSON = String.fromCodePoint(0x1f464);

const EMPTY_SUB_FULL = ["NBA", "NHL", "MLB", "Hit rates", "Trends", "Game log"].join(" " + MID + " ");
const EMPTY_SUB_LEAGUES = ["NBA", "NHL", "MLB"].join(" " + MID + " ");

type PropDef = { label: string; statKeys: string[]; abbr: string };

const PROPS: Record<string, PropDef[]> = {
  nba: [
    { label: "Points", statKeys: ["points", "PTS"], abbr: "PTS" },
    { label: "Rebounds", statKeys: ["totalRebounds", "REB"], abbr: "REB" },
    { label: "Assists", statKeys: ["assists", "AST"], abbr: "AST" },
    { label: "3-Point %", statKeys: ["threePointPct", "3P%"], abbr: "3P%" },
    { label: "PRA (Pts+Reb+Ast)", statKeys: ["__pra__"], abbr: "PRA" },
    { label: "Blocks", statKeys: ["blocks", "BLK"], abbr: "BLK" },
    { label: "Steals", statKeys: ["steals", "STL"], abbr: "STL" },
  ],
  nhl: [
    { label: "Goals", statKeys: ["goals", "G"], abbr: "G" },
    { label: "Assists", statKeys: ["assists", "A"], abbr: "A" },
    { label: "Points", statKeys: ["points", "PTS"], abbr: "PTS" },
    { label: "Shots on Goal", statKeys: ["shotsTotal", "S"], abbr: "S" },
    { label: "Power Play Goals", statKeys: ["powerPlayGoals", "PPG"], abbr: "PPG" },
  ],
  mlb: [
    { label: "Hits", statKeys: ["hits", "H"], abbr: "H" },
    { label: "RBI", statKeys: ["rbi", "runsBattedIn", "RBI"], abbr: "RBI" },
    { label: "Strikeouts", statKeys: ["strikeouts", "strikeOuts", "SO"], abbr: "SO" },
    { label: "Home Runs", statKeys: ["homeRuns", "homerun", "HR"], abbr: "HR" },
  ],
};

const PILLS = [
  { label: "NBA", sport: "basketball", league: "nba" },
  { label: "NHL", sport: "hockey", league: "nhl" },
  { label: "MLB", sport: "baseball", league: "mlb" },
];

type Team = { id: string; name: string; abbr: string };
type AnyObj = any;

type Game = { date: Date | null; val: number; opp: string; result: string };

type MainView =
  | { kind: "empty"; sub: string }
  | { kind: "msg"; text: string }
  | {
      kind: "results";
      player: AnyObj;
      recent: Game[];
      propDef: PropDef;
      n: number;
      teamName: string | null;
      leagueKey: string;
    };

type Sel = {
  pill: number;
  teamId: string;
  playerId: string;
  propIdx: string;
  gameCount: string;
};

type PlayerMode = "default" | "loading" | "failed";

async function fetchJSON(url: string, signal: AbortSignal): Promise<AnyObj | null> {
  try {
    const r = await fetch(url, { signal });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

function extractStatByLabels(
  labels: string[],
  names: string[],
  statsArr: AnyObj[],
  keys: string[]
): number | null {
  for (let k = 0; k < keys.length; k++) {
    const key = keys[k].toLowerCase();
    for (let i = 0; i < labels.length; i++) {
      if ((labels[i] || "").toLowerCase() === key) {
        const v = parseFloat(statsArr[i]);
        return isNaN(v) ? null : v;
      }
    }
    for (let j = 0; j < (names || []).length; j++) {
      if ((names[j] || "").toLowerCase() === key) {
        const v2 = parseFloat(statsArr[j]);
        return isNaN(v2) ? null : v2;
      }
    }
  }
  return null;
}

function parseGamelog(data: AnyObj, propDef: PropDef): Game[] {
  const gl = data.gameLog || {};
  const sg = (gl.statistics || [])[0];
  if (!sg) return [];

  const labels: string[] = sg.labels || [];
  const names: string[] = sg.names || [];
  const sgEvts: AnyObj[] = sg.events || [];
  const evDict = gl.events || {};
  const games: Game[] = [];

  sgEvts.forEach((entry) => {
    const statsArr: AnyObj[] = entry.stats || [];
    let val: number | null = null;

    if (propDef.statKeys[0] === "__pra__") {
      const pts = extractStatByLabels(labels, names, statsArr, ["points", "pts", "PTS"]);
      const reb = extractStatByLabels(labels, names, statsArr, ["totalRebounds", "rebounds", "REB"]);
      const ast = extractStatByLabels(labels, names, statsArr, ["assists", "AST"]);
      if (pts !== null && reb !== null && ast !== null) val = pts + reb + ast;
    } else {
      val = extractStatByLabels(labels, names, statsArr, propDef.statKeys.concat([propDef.abbr]));
    }

    if (val !== null) {
      const ev = evDict[entry.eventId] || {};
      games.push({
        date: ev.gameDate ? new Date(ev.gameDate) : null,
        val: val,
        opp: ev.opponent ? ev.opponent.abbreviation || "?" : ev.atVs || "?",
        result: ev.gameResult || "",
      });
    }
  });

  return games.sort(
    (a, b) => (b.date ? b.date.getTime() : 0) - (a.date ? a.date.getTime() : 0)
  );
}

function calcHitRate(games: Game[], line: number) {
  const hits = games.filter((g) => g.val > line).length;
  return { rate: games.length ? hits / games.length : 0, hits: hits, total: games.length };
}

function rateColor(r: number): string {
  return r >= 0.65
    ? "var(--accent-green)"
    : r >= 0.5
    ? "var(--accent-yellow)"
    : "var(--accent-red)";
}

function Results({ view }: { view: Extract<MainView, { kind: "results" }> }) {
  const { player, recent, propDef, n, teamName, leagueKey } = view;

  const vals = recent.map((g) => g.val);
  const avg = vals.reduce((s, v) => s + v, 0) / vals.length;
  const max = Math.max.apply(null, vals);
  const min = Math.min.apply(null, vals);
  const avg3 = vals.slice(0, 3).reduce((s, v) => s + v, 0) / Math.min(3, vals.length);
  const trendCls = avg3 > avg * 1.1 ? "trend-hot" : avg3 < avg * 0.9 ? "trend-cold" : "trend-mid";
  const trendTxt =
    avg3 > avg * 1.1 ? UP + " HOT" : avg3 < avg * 0.9 ? DOWN + " COLD" : RIGHT + " AVG";

  const hs: string = player.headshot ? player.headshot.href || "" : "";
  const pos: string = player.position ? player.position.abbreviation || "" : "";

  const strip: { val: string | number; lbl: string; trend: boolean }[] = [
    { val: avg.toFixed(1), lbl: propDef.abbr + " Average", trend: false },
    { val: avg3.toFixed(1), lbl: "Last 3 Avg", trend: true },
    { val: max, lbl: "Season High", trend: false },
    { val: min, lbl: "Season Low", trend: false },
  ];

  const step = 0.5;
  const lo = Math.max(0, Math.floor((avg - 2) / step) * step);
  const hitRows = [];
  for (let i = 0; i < 7; i++) {
    const line = +(lo + i * step).toFixed(1);
    const hr = calcHitRate(recent, line);
    hitRows.push(
      <div className="hit-row" key={i}>
        <span className="hit-line-label">{line}</span>
        <div className="hit-bar-track">
          <div
            className="hit-bar-fill"
            style={{ width: hr.rate * 100 + "%", background: rateColor(hr.rate) }}
          ></div>
        </div>
        <span className="hit-pct" style={{ color: rateColor(hr.rate) }}>
          {(hr.rate * 100).toFixed(0) + "%"}
        </span>
        <span className="hit-count">{hr.hits + "/" + hr.total}</span>
      </div>
    );
  }

  const midLine = +avg.toFixed(1);

  return (
    <>
      <div className="player-banner">
        {hs ? (
          <img className="player-headshot" src={hs} />
        ) : (
          <div className="player-headshot-ph">{PERSON}</div>
        )}
        <div>
          <div className="player-banner-name">{player.displayName || ""}</div>
          <div className="player-banner-meta">
            {(pos || "") +
              (teamName ? " " + MID + " " + teamName : "") +
              " " + MID + " " +
              leagueKey.toUpperCase()}
          </div>
          <div className="player-banner-prop">
            {propDef.label + " " + MID + " Last " + n + " Games"}
          </div>
        </div>
      </div>

      <div className="stat-strip">
        {strip.map((s, i) => (
          <div className="stat-strip-item" key={i}>
            <div className="stat-val">{s.val}</div>
            <div className="stat-lbl">{s.lbl}</div>
            {s.trend ? <span className={"stat-trend " + trendCls}>{trendTxt}</span> : null}
          </div>
        ))}
      </div>

      <div className="results-grid">
        <div className="hit-section">
          <div className="section-title">Hit Rate by Line (Over)</div>
          {hitRows}
        </div>

        <div className="log-section">
          <div className="section-title">Game Log</div>
          <table className="log-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Opp</th>
                <th>W/L</th>
                <th>{propDef.abbr}</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((g, i) => {
                const ds = g.date
                  ? g.date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
                  : DASH;
                const cls = g.val > midLine ? "cell-over" : g.val < midLine ? "cell-under" : "";
                const rc =
                  g.result === "W"
                    ? { color: "var(--accent-green)" }
                    : g.result === "L"
                    ? { color: "var(--accent-red)" }
                    : undefined;
                return (
                  <tr key={i}>
                    <td>{ds}</td>
                    <td>{g.opp || DASH}</td>
                    <td style={rc}>{g.result || DASH}</td>
                    <td className={cls}>{g.val}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

export default function PropEngine() {
  const [sel, setSelState] = useState<Sel>({
    pill: 0,
    teamId: "",
    playerId: "",
    propIdx: "0",
    gameCount: "15",
  });
  const selRef = useRef<Sel>(sel);
  const [teams, setTeamsState] = useState<Team[]>([]);
  const teamsRef = useRef<Team[]>([]);
  const [players, setPlayersState] = useState<AnyObj[]>([]);
  const playersRef = useRef<AnyObj[]>([]);
  const [playerMode, setPlayerMode] = useState<PlayerMode>("default");
  const [status, setStatusState] = useState<{ text: string; dot: string }>({
    text: "Select a league, team, and player",
    dot: "",
  });
  const [main, setMain] = useState<MainView>({ kind: "empty", sub: EMPTY_SUB_FULL });

  const teamsCtl = useRef<AbortController | null>(null);
  const playersCtl = useRef<AbortController | null>(null);
  const analyzeCtl = useRef<AbortController | null>(null);

  const updateSel = (patch: Partial<Sel>) => {
    selRef.current = { ...selRef.current, ...patch };
    setSelState(selRef.current);
  };
  const setTeams = (v: Team[]) => {
    teamsRef.current = v;
    setTeamsState(v);
  };
  const setPlayers = (v: AnyObj[]) => {
    playersRef.current = v;
    setPlayersState(v);
  };
  const setStatus = (text: string, dot?: string) => setStatusState({ text, dot: dot || "" });

  const loadTeams = async (pillIdx: number) => {
    const pill = PILLS[pillIdx];
    if (teamsCtl.current) teamsCtl.current.abort();
    if (playersCtl.current) playersCtl.current.abort();
    if (analyzeCtl.current) analyzeCtl.current.abort();
    const ctl = new AbortController();
    teamsCtl.current = ctl;

    setStatus("Loading teams...", "yellow");
    updateSel({ teamId: "", playerId: "" });
    setPlayerMode("default");
    setTeams([]);
    setPlayers([]);

    try {
      const url =
        "https://site.api.espn.com/apis/site/v2/sports/" +
        pill.sport + "/" + pill.league + "/scoreboard?dates=20260428";
      const data = await fetchJSON(url, ctl.signal);
      if (ctl.signal.aborted) return;
      const events: AnyObj[] = (data && data.events) || [];

      if (!events.length) {
        setStatus("No games today", "");
        return;
      }

      const teamMap: Record<string, Team> = {};
      events.forEach((e) => {
        const comp = e.competitions && e.competitions[0];
        if (!comp) return;
        (comp.competitors || []).forEach((c: AnyObj) => {
          const t = c.team;
          if (t && t.id && t.displayName && !teamMap[t.id]) {
            teamMap[t.id] = { id: t.id, name: t.displayName, abbr: t.abbreviation || "" };
          }
        });
      });

      const list = Object.values(teamMap).sort((a, b) => a.name.localeCompare(b.name));
      setTeams(list);
      setStatus("Select a team", "");
    } catch (e) {
      if (ctl.signal.aborted) return;
      console.error("loadTeams failed:", e);
      setStatus("Failed to load teams", "");
    }
  };

  const loadPlayers = async (teamId: string) => {
    const pill = PILLS[selRef.current.pill];
    if (playersCtl.current) playersCtl.current.abort();
    const ctl = new AbortController();
    playersCtl.current = ctl;

    setPlayerMode("loading");
    updateSel({ playerId: "" });
    setPlayers([]);

    try {
      const url =
        "https://site.api.espn.com/apis/site/v2/sports/" +
        pill.sport + "/" + pill.league + "/teams/" + teamId + "/roster";
      const data = await fetchJSON(url, ctl.signal);
      if (ctl.signal.aborted) return;

      if (!data) throw new Error("Failed to fetch roster");

      const list: AnyObj[] = [];
      (data.athletes || []).forEach((g: AnyObj) => {
        (g.items || g.athletes || (g.id ? [g] : [])).forEach((p: AnyObj) => {
          if (p.id) list.push(p);
        });
      });

      list.sort((a, b) => (a.displayName || "").localeCompare(b.displayName || ""));
      setPlayers(list);
      setPlayerMode("default");
      setStatus("Select a player", "");
    } catch (e) {
      if (ctl.signal.aborted) return;
      console.error("loadPlayers failed:", e);
      setPlayerMode("failed");
      setStatus("Failed to load players", "");
    }
  };

  const analyze = async (playerId: string, propIdxStr: string, countStr: string) => {
    const pill = PILLS[selRef.current.pill];
    const propIdx = parseInt(propIdxStr);
    const n = Math.max(5, Math.min(82, parseInt(countStr) || 15));
    const propDef = (PROPS[pill.league] || [])[propIdx];

    if (!playerId || !propDef) {
      setStatus("Select a player and prop", "");
      return;
    }

    const player = playersRef.current.find((p) => String(p.id) === playerId);
    if (!player) return;

    if (analyzeCtl.current) analyzeCtl.current.abort();
    const ctl = new AbortController();
    analyzeCtl.current = ctl;

    setStatus("Loading...", "yellow");
    setMain({ kind: "msg", text: "Loading..." });

    try {
      const url =
        "https://site.web.api.espn.com/apis/common/v3/sports/" +
        pill.sport + "/" + pill.league + "/athletes/" + playerId + "/overview";
      const data = await fetchJSON(url, ctl.signal);
      if (ctl.signal.aborted) return;

      if (!data) throw new Error("No data");

      const games = parseGamelog(data, propDef);

      if (!games.length) {
        setStatus("No data for " + propDef.label, "");
        setMain({ kind: "msg", text: "No game log data for " + propDef.label });
        return;
      }

      setStatus(games.length + " games " + MID + " " + propDef.label, "green");

      const recent = games.slice(0, n);
      if (!recent.length) {
        setMain({ kind: "msg", text: "No data for " + propDef.label });
        return;
      }
      const team = teamsRef.current.find((t) => String(t.id) === selRef.current.teamId);
      setMain({
        kind: "results",
        player: player,
        recent: recent,
        propDef: propDef,
        n: n,
        teamName: team ? team.name : null,
        leagueKey: pill.league,
      });
    } catch (e) {
      if (ctl.signal.aborted) return;
      console.error("analyze failed:", e);
      setStatus("Failed to load", "");
      setMain({ kind: "msg", text: "Failed to load data" });
    }
  };

  useEffect(() => {
    loadTeams(0);
    return () => {
      if (teamsCtl.current) teamsCtl.current.abort();
      if (playersCtl.current) playersCtl.current.abort();
      if (analyzeCtl.current) analyzeCtl.current.abort();
    };
  }, []);

  const pillIdx = sel.pill;
  const league = PILLS[pillIdx].league;
  const propList = PROPS[league] || [];

  const onPill = (i: number) => {
    updateSel({ pill: i, propIdx: "0" });
    loadTeams(i);
    setMain({ kind: "empty", sub: EMPTY_SUB_LEAGUES });
  };

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Prop Engine</div>
          <div className="page-subtitle">
            {["HIT RATES", "TRENDS", "OVER/UNDER ANALYSIS"].join(" " + MID + " ")}
          </div>
        </div>
      </div>

      <div className="controls-wrap">
        <div className="controls-row">
          <span className="controls-label">League</span>
          {PILLS.map((p, i) => (
            <div
              key={p.league}
              className={"league-pill" + (i === pillIdx ? " active" : "")}
              data-sport={p.sport}
              data-league={p.league}
              onClick={() => onPill(i)}
            >
              {p.label}
            </div>
          ))}
        </div>
        <div className="controls-row">
          <span className="controls-label">Team</span>
          <select
            className="ctrl-select"
            id="team-select"
            value={sel.teamId}
            onChange={(e) => {
              const v = e.target.value;
              updateSel({ teamId: v });
              if (v) loadPlayers(v);
            }}
          >
            <option value="">{DASH + " Select Team " + DASH}</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
          <span className="controls-label" style={{ marginLeft: "8px" }}>
            Player
          </span>
          <select
            className="ctrl-select"
            id="player-select"
            value={sel.playerId}
            onChange={(e) => {
              const v = e.target.value;
              updateSel({ playerId: v });
              if (v) analyze(v, selRef.current.propIdx, selRef.current.gameCount);
            }}
          >
            {playerMode === "loading" ? (
              <option value="">Loading...</option>
            ) : playerMode === "failed" ? (
              <option value="">Failed to load</option>
            ) : (
              <>
                <option value="">{DASH + " Select Player " + DASH}</option>
                {players.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.displayName || p.fullName || p.id}
                  </option>
                ))}
              </>
            )}
          </select>
        </div>
        <div className="controls-row">
          <span className="controls-label">Prop</span>
          <select
            className="ctrl-select"
            id="prop-select"
            value={sel.propIdx}
            onChange={(e) => {
              const v = e.target.value;
              updateSel({ propIdx: v });
              if (selRef.current.playerId) {
                analyze(selRef.current.playerId, v, selRef.current.gameCount);
              }
            }}
          >
            {propList.map((p, i) => (
              <option key={i} value={String(i)}>
                {p.label}
              </option>
            ))}
          </select>
          <span className="controls-label" style={{ marginLeft: "8px" }}>
            Games
          </span>
          <input
            className="ctrl-num"
            id="game-count"
            type="number"
            min="5"
            max="82"
            value={sel.gameCount}
            title="Last N games"
            onChange={(e) => updateSel({ gameCount: e.target.value })}
          />
          <button
            className="analyze-btn"
            id="analyze-btn"
            onClick={() =>
              analyze(selRef.current.playerId, selRef.current.propIdx, selRef.current.gameCount)
            }
          >
            Analyze
          </button>
        </div>
      </div>

      <div className="status-bar" id="prop-status">
        <span className={"status-dot " + status.dot} id="status-dot"></span>
        <span id="status-text">{status.text}</span>
      </div>

      <div className="main" id="prop-main">
        {main.kind === "empty" ? (
          <div className="empty-state">
            Select a player and prop to begin analysis
            <div className="empty-sub">{main.sub}</div>
          </div>
        ) : main.kind === "msg" ? (
          <div className="empty-state">{main.text}</div>
        ) : (
          <Results view={main} />
        )}
      </div>
    </>
  );
}
