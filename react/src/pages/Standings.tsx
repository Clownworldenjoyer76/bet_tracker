/*
  Standings - native React port of legacy standings.html + assets/js/standings/render.js
  (plus the league menu that assets/js/shared/league_nav.js built around the league pills).

  Legacy behaviors found and preserved:
   1. League list with enabled flags: NBA, NHL, WNBA, MLB, EPL, MLS, La Liga, Ligue 1, Serie A, Bundesliga are shown;
      NCAAM (rankings league) and UFC (placeholder) are disabled and hidden. Default league is NBA.
   2. League selector: grouped menu (Football, Basketball, Soccer groups, NHL, MLB, UFC) from the shared league nav;
      leagues not on this page are disabled. Choosing a league resets to the standings view and loads it.
   3. Standings load: status "Loading {label} standings..." (yellow); tries in order
      https://site.api.espn.com/apis/v2/sports/{sport}/{league}/standings, the same with ?season=2026, then for soccer
      cdn.espn.com/core/soccer/standings?xhr=1&league={league} and www.espn.com/soccer/standings/_/league/{league}?xhr=1,
      otherwise cdn.espn.com/core/{slug}/standings?xhr=1 and www.espn.com/{slug}/standings?xhr=1 (http -> https).
      The first successful response is used. All failing -> red "Failed to load {label} standings" and
      "Failed to load standings" plus the last error ("HTTP {status} - {url}").
   4. Response shapes handled: children / standings / content.standings / page.content.standings / standings.groups /
      sports[0].leagues[0].standings; groups come from children, groups, standings.groups or content.standings.groups;
      with no groups the entries (standings.entries or entries) are shown as one table, and "No data available"
      with status "No data" when there are none.
   5. Conference blocks with a header, division blocks (child entries) with a header, or a direct entries table.
      Tables: soccer GP W D L GD PTS, hockey GP W L OTL PTS STRK, baseball W L PCT GB STRK, others W L PCT GB STRK;
      stat values looked up by name; sorted by points (hockey), points then goal difference (soccer), wins (others);
      rank, logo and team name; playoff line after row 8 (NBA, NHL, WNBA), row 3 (MLB, when the league has no groups)
      or row 1 of each division (baseball), with a "PLAYOFF LINE" row.
   6. Rankings view (only for leagues with showRankings and not a placeholder; none are enabled now): Rankings pill toggles
      between standings and polls loaded from .../apis/site/v2/sports/{sport}/{league}/rankings (and ?season=2026);
      poll tables with #, Team, Record, Pts and Chg (up/down/same), status "{n} poll(s) loaded".
   7. Placeholder leagues show "{label} Coming Next" and a message instead of loading; no enabled leagues shows "No Leagues Enabled".
   8. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials (nav.js is loaded by SiteShell).
  Differences: requests are cancelled when superseded or when the page is left; ESPN text is rendered as React text
  (legacy escaped it into innerHTML).
*/
import { useEffect, useRef, useState, type ReactNode } from "react";
import LeagueNav from "../lib/leagueNav";
import "../../../app/frontend/src/assets/css/pages/standings.css";

const MID = String.fromCharCode(0xb7);
const DASH = String.fromCharCode(0x2014);
const UP = String.fromCharCode(0x25b2);
const DOWN = String.fromCharCode(0x25bc);

const CURRENT_SEASON = 2026;

type LeagueDef = {
  key: string;
  label: string;
  enabled: boolean;
  sport: string;
  league: string;
  cdnSlug: string;
  type: string;
  placeholder?: boolean;
  season: number;
  playoffSpots: number | null;
  showRankings: boolean;
};

const LEAGUES: LeagueDef[] = [
  { key: "nba", label: "NBA", enabled: true, sport: "basketball", league: "nba", cdnSlug: "nba", type: "standings", season: CURRENT_SEASON, playoffSpots: 8, showRankings: false },
  { key: "nhl", label: "NHL", enabled: true, sport: "hockey", league: "nhl", cdnSlug: "nhl", type: "standings", season: CURRENT_SEASON, playoffSpots: 8, showRankings: false },
  { key: "wnba", label: "WNBA", enabled: true, sport: "basketball", league: "wnba", cdnSlug: "wnba", type: "standings", season: CURRENT_SEASON, playoffSpots: 8, showRankings: false },
  { key: "ncaam", label: "NCAAM", enabled: false, sport: "basketball", league: "mens-college-basketball", cdnSlug: "mens-college-basketball", type: "standings", season: CURRENT_SEASON, playoffSpots: null, showRankings: true },
  { key: "mlb", label: "MLB", enabled: true, sport: "baseball", league: "mlb", cdnSlug: "mlb", type: "standings", season: CURRENT_SEASON, playoffSpots: 3, showRankings: false },
  { key: "epl", label: "EPL", enabled: true, sport: "soccer", league: "eng.1", cdnSlug: "soccer", type: "standings", season: CURRENT_SEASON, playoffSpots: null, showRankings: false },
  { key: "mls", label: "MLS", enabled: true, sport: "soccer", league: "usa.1", cdnSlug: "soccer", type: "standings", season: CURRENT_SEASON, playoffSpots: null, showRankings: false },
  { key: "laliga", label: "LA LIGA", enabled: true, sport: "soccer", league: "esp.1", cdnSlug: "soccer", type: "standings", season: CURRENT_SEASON, playoffSpots: null, showRankings: false },
  { key: "ligue1", label: "LIGUE 1", enabled: true, sport: "soccer", league: "fra.1", cdnSlug: "soccer", type: "standings", season: CURRENT_SEASON, playoffSpots: null, showRankings: false },
  { key: "seriea", label: "SERIE A", enabled: true, sport: "soccer", league: "ita.1", cdnSlug: "soccer", type: "standings", season: CURRENT_SEASON, playoffSpots: null, showRankings: false },
  { key: "bundesliga", label: "BUNDESLIGA", enabled: true, sport: "soccer", league: "ger.1", cdnSlug: "soccer", type: "standings", season: CURRENT_SEASON, playoffSpots: null, showRankings: false },
  { key: "ufc", label: "UFC", enabled: false, sport: "mma", league: "ufc", cdnSlug: "ufc", type: "placeholder", placeholder: true, season: CURRENT_SEASON, playoffSpots: null, showRankings: false },
];

// ESPN payloads have many shapes, so they are handled loosely, as in the legacy script.
type AnyObj = any;

function getEnabledLeagues(): LeagueDef[] {
  return LEAGUES.filter((league) => league.enabled !== false);
}

function getDefaultLeagueKey(): string {
  const enabled = getEnabledLeagues();
  if (!enabled.length) return "";
  const preferred = enabled.find((league) => league.key === "nba");
  return preferred ? preferred.key : enabled[0].key;
}

function getLeague(key: string): LeagueDef | null {
  const enabled = getEnabledLeagues();
  if (!enabled.length) return null;
  return enabled.find((league) => league.key === key) || enabled[0];
}

function txt(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

function normalizeUrl(url: unknown): string {
  if (!url) return "";
  return String(url).replace(/^http:\/\//i, "https://");
}

function buildStandingsUrls(league: LeagueDef): string[] {
  const encodedLeague = encodeURIComponent(league.league);
  const sport = encodeURIComponent(league.sport);
  const siteUrl =
    "https://site.api.espn.com/apis/v2/sports/" + sport + "/" + encodedLeague + "/standings";

  const urls = [siteUrl, siteUrl + "?season=" + encodeURIComponent(league.season || CURRENT_SEASON)];

  if (league.sport === "soccer") {
    urls.push("https://cdn.espn.com/core/soccer/standings?xhr=1&league=" + encodedLeague);
    urls.push("https://www.espn.com/soccer/standings/_/league/" + encodedLeague + "?xhr=1");
  } else {
    urls.push(
      "https://cdn.espn.com/core/" +
        encodeURIComponent(league.cdnSlug || league.league) +
        "/standings?xhr=1"
    );
    urls.push(
      "https://www.espn.com/" +
        encodeURIComponent(league.cdnSlug || league.league) +
        "/standings?xhr=1"
    );
  }

  return urls;
}

function buildRankingsUrls(league: LeagueDef): string[] {
  const encodedLeague = encodeURIComponent(league.league);
  const sport = encodeURIComponent(league.sport);

  return [
    "https://site.api.espn.com/apis/site/v2/sports/" + sport + "/" + encodedLeague + "/rankings",
    "https://site.api.espn.com/apis/site/v2/sports/" +
      sport + "/" + encodedLeague + "/rankings?season=" +
      encodeURIComponent(league.season || CURRENT_SEASON),
  ];
}

async function fetchJson(url: string, signal: AbortSignal): Promise<AnyObj> {
  const finalUrl = normalizeUrl(url);
  const response = await fetch(finalUrl, { signal });

  if (!response.ok) {
    throw new Error("HTTP " + response.status + " " + MID + " " + finalUrl);
  }

  return response.json();
}

async function fetchFirstJson(urls: string[], signal: AbortSignal): Promise<{ url: string; data: AnyObj }> {
  let lastError: unknown = null;

  for (let i = 0; i < urls.length; i++) {
    try {
      return { url: urls[i], data: await fetchJson(urls[i], signal) };
    } catch (e) {
      if (signal.aborted) throw e;
      lastError = e;
    }
  }

  throw lastError || new Error("No usable standings endpoint");
}

function getStat(stats: AnyObj[] | null | undefined, names: string[] | string): AnyObj {
  if (!stats) return DASH;

  const nameList = Array.isArray(names) ? names : [names];

  for (let i = 0; i < stats.length; i++) {
    const stat = stats[i];
    const statName = String(stat.name || stat.shortDisplayName || stat.displayName || "").toLowerCase();

    for (let j = 0; j < nameList.length; j++) {
      if (statName === String(nameList[j]).toLowerCase()) {
        return stat.displayValue !== undefined
          ? stat.displayValue
          : stat.value !== undefined
          ? stat.value
          : DASH;
      }
    }
  }

  return DASH;
}

function getNumericStat(entry: AnyObj, names: string[]): number {
  const raw = getStat(entry.stats || [], names);
  const parsed = parseFloat(String(raw).replace(/[^\d.-]/g, ""));
  return isNaN(parsed) ? 0 : parsed;
}

function sortEntries(entries: AnyObj[], league: LeagueDef | null): AnyObj[] {
  return entries.slice().sort((a, b) => {
    if (league && league.sport === "hockey") {
      return getNumericStat(b, ["points", "pts"]) - getNumericStat(a, ["points", "pts"]);
    }

    if (league && league.sport === "soccer") {
      const ptsDiff = getNumericStat(b, ["points", "pts"]) - getNumericStat(a, ["points", "pts"]);
      if (ptsDiff !== 0) return ptsDiff;

      const gdDiff =
        getNumericStat(b, ["pointdifferential", "differential", "goaldifference", "gd"]) -
        getNumericStat(a, ["pointdifferential", "differential", "goaldifference", "gd"]);

      if (gdDiff !== 0) return gdDiff;
    }

    return getNumericStat(b, ["wins", "w"]) - getNumericStat(a, ["wins", "w"]);
  });
}

type Col = { label: string; names: string[] };

function getColumnsForLeague(league: LeagueDef | null): Col[] {
  if (!league) {
    return [
      { label: "W", names: ["wins", "w"] },
      { label: "L", names: ["losses", "l"] },
      { label: "PCT", names: ["winpercent", "pct", "win%"] },
    ];
  }

  if (league.sport === "soccer") {
    return [
      { label: "GP", names: ["gamesplayed", "gp", "played"] },
      { label: "W", names: ["wins", "w"] },
      { label: "D", names: ["ties", "draws", "d"] },
      { label: "L", names: ["losses", "l"] },
      { label: "GD", names: ["pointdifferential", "differential", "goaldifference", "gd"] },
      { label: "PTS", names: ["points", "pts"] },
    ];
  }

  if (league.sport === "hockey") {
    return [
      { label: "GP", names: ["gamesplayed", "gp"] },
      { label: "W", names: ["wins", "w"] },
      { label: "L", names: ["losses", "l"] },
      { label: "OTL", names: ["otlosses", "otl"] },
      { label: "PTS", names: ["points", "pts"] },
      { label: "STRK", names: ["streak"] },
    ];
  }

  if (league.sport === "baseball") {
    return [
      { label: "W", names: ["wins", "w"] },
      { label: "L", names: ["losses", "l"] },
      { label: "PCT", names: ["winpercent", "pct"] },
      { label: "GB", names: ["gamesbehind", "gb"] },
      { label: "STRK", names: ["streak"] },
    ];
  }

  return [
    { label: "W", names: ["wins", "w"] },
    { label: "L", names: ["losses", "l"] },
    { label: "PCT", names: ["winpercent", "pct", "win%"] },
    { label: "GB", names: ["gamesbehind", "gb"] },
    { label: "STRK", names: ["streak"] },
  ];
}

function getTeamLogo(team: AnyObj): string {
  if (!team) return "";

  if (Array.isArray(team.logos) && team.logos.length) {
    return normalizeUrl(team.logos[0].href || team.logos[0].url || "");
  }

  if (team.logo) return normalizeUrl(team.logo);

  return "";
}

function getTeamName(team: AnyObj): string {
  if (!team) return DASH;

  return team.shortDisplayName || team.displayName || team.name || team.abbreviation || DASH;
}

function extractStandingsPayload(data: AnyObj): AnyObj {
  if (!data) return null;

  if (data.children || data.standings) {
    return data;
  }

  if (data.content && data.content.standings) {
    return data.content.standings;
  }

  if (data.page && data.page.content && data.page.content.standings) {
    return data.page.content.standings;
  }

  if (data.standings && data.standings.groups) {
    return data.standings;
  }

  if (data.sports && data.sports[0] && data.sports[0].leagues && data.sports[0].leagues[0]) {
    const league = data.sports[0].leagues[0];
    if (league.standings) return league.standings;
  }

  return data;
}

function getGroupsFromPayload(payload: AnyObj): AnyObj[] {
  if (!payload) return [];

  if (Array.isArray(payload.children)) return payload.children;
  if (Array.isArray(payload.groups)) return payload.groups;
  if (payload.standings && Array.isArray(payload.standings.groups)) return payload.standings.groups;
  if (
    payload.content &&
    payload.content.standings &&
    Array.isArray(payload.content.standings.groups)
  ) {
    return payload.content.standings.groups;
  }

  return [];
}

function getEntriesFromNode(node: AnyObj): AnyObj[] {
  if (!node) return [];

  if (node.standings && Array.isArray(node.standings.entries)) {
    return node.standings.entries;
  }

  if (Array.isArray(node.entries)) {
    return node.entries;
  }

  return [];
}

function getChildrenFromNode(node: AnyObj): AnyObj[] {
  if (!node) return [];

  if (Array.isArray(node.children)) return node.children;
  if (Array.isArray(node.groups)) return node.groups;

  return [];
}

function getNodeName(node: AnyObj): string {
  if (!node) return "";

  return node.name || node.displayName || node.shortDisplayName || node.abbreviation || "";
}

type TableData = { entries: AnyObj[]; cutoff: number | null };
type DivisionView = { name: string; table: TableData };
type ConferenceView = {
  name: string;
  divisions: DivisionView[];
  table: TableData | null;
};

type MainView =
  | { kind: "none" }
  | { kind: "placeholder"; title: string; copy: string }
  | { kind: "error"; text: string; details: string }
  | { kind: "single"; league: LeagueDef; table: TableData }
  | { kind: "groups"; league: LeagueDef; conferences: ConferenceView[] }
  | { kind: "rankings"; league: LeagueDef; polls: AnyObj[] };

function StandingsTable({
  table,
  league,
}: {
  table: TableData;
  league: LeagueDef | null;
}) {
  const cols = getColumnsForLeague(league);
  const cutoff = table.cutoff;
  const sorted = sortEntries(table.entries, league);

  return (
    <div className="table-scroll">
      <table className="standings-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Team</th>
            {cols.map((col) => (
              <th key={col.label}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((entry, idx) => {
            const team = entry.team || {};
            const stats = entry.stats || [];
            const logo = getTeamLogo(team);

            return (
              <tr key={idx} className={cutoff && idx === cutoff - 1 ? "playoff-cutoff" : undefined}>
                <td className="rank-cell">{idx + 1}</td>
                <td>
                  <div className="team-cell">
                    {logo ? (
                      <img
                        className="team-logo-sm"
                        src={logo}
                        loading="lazy"
                        alt={getTeamName(team) + " logo"}
                      />
                    ) : null}
                    <span className="team-name-cell">{getTeamName(team)}</span>
                  </div>
                </td>
                {cols.map((col) => (
                  <td key={col.label}>{txt(getStat(stats, col.names))}</td>
                ))}
              </tr>
            );
          })}
          {cutoff ? (
            <tr>
              <td colSpan={cols.length + 2} className="playoff-label">
                {DASH + " PLAYOFF LINE " + DASH}
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

function buildGroupsView(groups: AnyObj[], league: LeagueDef): ConferenceView[] {
  return groups.map((group) => {
    const conf: ConferenceView = { name: getNodeName(group), divisions: [], table: null };
    const children = getChildrenFromNode(group);

    if (children.length) {
      children.forEach((child) => {
        const childEntries = getEntriesFromNode(child);
        if (!childEntries.length) return;

        conf.divisions.push({
          name: getNodeName(child),
          table: { entries: childEntries, cutoff: league.sport === "baseball" ? 1 : null },
        });
      });
    } else {
      const entries = getEntriesFromNode(group);

      if (entries.length) {
        conf.table = { entries, cutoff: league.playoffSpots || null };
      }
    }

    return conf;
  });
}

function RankingsView({ polls }: { polls: AnyObj[] }) {
  return (
    <div className="rankings-wrap">
      {polls.map((poll, pi) => {
        const pollName = poll.name || poll.shortName || "Poll";
        const updated = poll.lastUpdated
          ? new Date(poll.lastUpdated).toLocaleDateString("en-US", { month: "short", day: "numeric" })
          : "";
        const ranks: AnyObj[] = poll.ranks || [];

        return (
          <div className="poll-block" key={pi}>
            <div className="poll-header">
              {pollName}
              {updated ? (
                <>
                  {" "}
                  <span style={{ fontSize: "10px", color: "var(--text-muted)", fontWeight: 400 }}>
                    {MID + " Updated " + updated}
                  </span>
                </>
              ) : null}
            </div>
            {!ranks.length ? (
              <div className="no-data">No data</div>
            ) : (
              <div className="table-scroll">
                <table className="rankings-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Team</th>
                      <th>Record</th>
                      <th>Pts</th>
                      <th>Chg</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ranks.map((entry, ri) => {
                      const team = entry.team || {};
                      const logo = getTeamLogo(team);
                      const record = entry.recordSummary || "";
                      const points = entry.points !== undefined ? entry.points : DASH;
                      const prevRank = entry.previousRank || 0;
                      const curRank = entry.current || entry.rank || 0;
                      let change: ReactNode = null;

                      if (prevRank && curRank) {
                        const diff = prevRank - curRank;

                        if (diff > 0) {
                          change = <span className="rank-chg-up">{UP + diff}</span>;
                        } else if (diff < 0) {
                          change = <span className="rank-chg-down">{DOWN + Math.abs(diff)}</span>;
                        } else {
                          change = <span className="rank-chg-same">{DASH}</span>;
                        }
                      }

                      return (
                        <tr key={ri}>
                          <td>
                            <span className="rank-num">{txt(curRank)}</span>
                          </td>
                          <td>
                            <div className="team-cell">
                              {logo ? (
                                <img
                                  className="team-logo-sm"
                                  src={logo}
                                  loading="lazy"
                                  alt={getTeamName(team) + " logo"}
                                />
                              ) : null}
                              <span className="team-name-cell">{getTeamName(team)}</span>
                            </div>
                          </td>
                          <td>{txt(record)}</td>
                          <td>{txt(points)}</td>
                          <td>{change}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function Standings() {
  const [leagueKey, setLeagueKey] = useState<string>(getDefaultLeagueKey());
  const [view, setView] = useState<"standings" | "rankings">("standings");
  const [status, setStatusState] = useState<{ text: string; dot: string }>({
    text: "Loading...",
    dot: "yellow",
  });
  const [main, setMain] = useState<MainView>({ kind: "none" });
  const [emptyVisible, setEmptyVisible] = useState<boolean>(false);

  const leagueRef = useRef<LeagueDef | null>(getLeague(getDefaultLeagueKey()));
  const viewRef = useRef<"standings" | "rankings">("standings");
  const ctlRef = useRef<AbortController | null>(null);

  const setStatus = (text: string, dot?: string) => setStatusState({ text, dot: dot || "" });

  const newController = (): AbortController => {
    if (ctlRef.current) ctlRef.current.abort();
    const ctl = new AbortController();
    ctlRef.current = ctl;
    return ctl;
  };

  const showNoEnabledLeagues = () => {
    setEmptyVisible(false);
    setStatus("No standings leagues enabled", "yellow");
    setMain({
      kind: "placeholder",
      title: "No Leagues Enabled",
      copy: "Enable at least one league in docs/js/standings/render.js to show standings coverage.",
    });
  };

  const showPlaceholderLeague = (league: LeagueDef) => {
    setEmptyVisible(false);
    setStatus(league.label + " standings placeholder", "yellow");
    setMain({
      kind: "placeholder",
      title: league.label + " Coming Next",
      copy:
        league.label +
        " does not use a normal team standings table, so it is parked as a placeholder while the team-based leagues are wired first.",
    });
  };

  const loadStandings = async (league: LeagueDef) => {
    const ctl = newController();

    setMain({ kind: "none" });
    setEmptyVisible(false);
    setStatus("Loading " + league.label + " standings...", "yellow");

    try {
      const result = await fetchFirstJson(buildStandingsUrls(league), ctl.signal);
      if (ctl.signal.aborted) return;

      const payload = extractStandingsPayload(result.data);
      const groups = getGroupsFromPayload(payload);

      setMain({ kind: "none" });
      setEmptyVisible(false);

      if (!groups.length) {
        const entries = getEntriesFromNode(payload && payload.standings ? payload.standings : payload);

        if (!entries.length) {
          setEmptyVisible(true);
          setStatus("No data", "");
          return;
        }

        setMain({
          kind: "single",
          league,
          table: { entries, cutoff: league.playoffSpots || null },
        });
        setStatus(league.label + " standings loaded", "green");
        return;
      }

      setMain({ kind: "groups", league, conferences: buildGroupsView(groups, league) });
      setStatus(league.label + " standings loaded", "green");
    } catch (e) {
      if (ctl.signal.aborted) return;
      setStatus("Failed to load " + league.label + " standings", "red");
      setEmptyVisible(false);
      setMain({
        kind: "error",
        text: "Failed to load standings",
        details: (e as Error).message || "",
      });
    }
  };

  const loadRankings = async (league: LeagueDef) => {
    const ctl = newController();

    setMain({ kind: "none" });
    setEmptyVisible(false);
    setStatus("Loading " + league.label + " rankings...", "yellow");

    try {
      const result = await fetchFirstJson(buildRankingsUrls(league), ctl.signal);
      if (ctl.signal.aborted) return;

      const data = result.data;
      let polls: AnyObj[] = [];
      if (data) {
        if (Array.isArray(data.rankings)) polls = data.rankings;
        else if (data.content && Array.isArray(data.content.rankings)) polls = data.content.rankings;
        else if (data.page && data.page.content && Array.isArray(data.page.content.rankings)) {
          polls = data.page.content.rankings;
        }
      }

      if (!polls.length) {
        setEmptyVisible(true);
        setStatus("No rankings available", "");
        return;
      }

      setMain({ kind: "rankings", league, polls });
      setStatus(polls.length + " poll" + (polls.length > 1 ? "s" : "") + " loaded", "green");
    } catch (e) {
      if (ctl.signal.aborted) return;
      setStatus("Failed to load rankings", "red");
      setMain({
        kind: "error",
        text: "Failed to load rankings",
        details: (e as Error).message || "",
      });
    }
  };

  const activateLeague = (key: string) => {
    const league = getLeague(key);

    if (!league) {
      showNoEnabledLeagues();
      return;
    }

    leagueRef.current = league;
    viewRef.current = "standings";
    setLeagueKey(league.key);
    setView("standings");

    if (league.type === "placeholder") {
      if (ctlRef.current) ctlRef.current.abort();
      showPlaceholderLeague(league);
      return;
    }

    loadStandings(league);
  };

  const toggleRankings = () => {
    const league = leagueRef.current;
    if (!league || !league.showRankings) return;

    if (viewRef.current === "rankings") {
      viewRef.current = "standings";
      setView("standings");
      loadStandings(league);
    } else {
      viewRef.current = "rankings";
      setView("rankings");
      loadRankings(league);
    }
  };

  useEffect(() => {
    const league = leagueRef.current;
    if (!league) {
      showNoEnabledLeagues();
    } else {
      activateLeague(league.key);
    }
    return () => {
      if (ctlRef.current) ctlRef.current.abort();
    };
  }, []);

  const activeLeague = getLeague(leagueKey);
  const rankingsHidden = !(
    activeLeague &&
    activeLeague.showRankings &&
    activeLeague.type !== "placeholder"
  );

  const rankingsPill = (
    <div
      className={
        "view-pill" +
        (rankingsHidden ? " hidden" : "") +
        (!rankingsHidden && view === "rankings" ? " active" : "")
      }
      id="rankings-pill"
      onClick={() => {
        if (!rankingsHidden) toggleRankings();
      }}
    >
      Rankings
    </div>
  );

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Standings</div>
          <div className="page-subtitle">{"ESPN " + MID + " CURRENT SEASON"}</div>
        </div>
      </div>

      <LeagueNav
        present={getEnabledLeagues().map((l) => l.key)}
        activeKey={leagueKey}
        onSelect={activateLeague}
        pillAs="div"
        className="controls"
        aux={rankingsPill}
      />

      <div className="status-bar" id="standings-status">
        <span className={"status-dot " + status.dot} id="status-dot"></span>
        <span id="status-text">{status.text}</span>
      </div>

      <div className="main" id="standings-main">
        {main.kind === "placeholder" ? (
          <div className="placeholder-state">
            <div className="placeholder-title">{main.title}</div>
            <div className="placeholder-copy">{main.copy}</div>
          </div>
        ) : main.kind === "error" ? (
          <div className="empty-state">
            {main.text}
            <div className="error-details">{main.details}</div>
          </div>
        ) : main.kind === "single" ? (
          <div className="conference-block">
            <StandingsTable table={main.table} league={main.league} />
          </div>
        ) : main.kind === "groups" ? (
          <div className="conferences-wrap">
            {main.conferences.map((conf, ci) => (
              <div className="conference-block" key={ci}>
                {conf.name ? <div className="conference-header">{conf.name}</div> : null}
                {conf.divisions.map((div, di) => (
                  <div className="division-block" key={di}>
                    {div.name ? <div className="division-header">{div.name}</div> : null}
                    <StandingsTable table={div.table} league={main.league} />
                  </div>
                ))}
                {conf.table ? <StandingsTable table={conf.table} league={main.league} /> : null}
              </div>
            ))}
          </div>
        ) : main.kind === "rankings" ? (
          <RankingsView polls={main.polls} />
        ) : null}
      </div>
      <div className="empty-state" id="standings-empty" style={{ display: emptyVisible ? "" : "none" }}>
        No data available
      </div>
    </>
  );
}
