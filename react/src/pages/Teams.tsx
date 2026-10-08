/*
  Teams - native React port of legacy teams.html + assets/js/teams/render.js
  (plus the league menu that assets/js/shared/league_nav.js built around the league pills).

  Legacy behaviors found and preserved:
   1. League list with enabled flags: NBA, NHL, WNBA, MLB, EPL, MLS, La Liga, Ligue 1, Serie A and Bundesliga are shown;
      NCAAM and UFC (placeholder) are disabled and hidden. Default league is NBA.
   2. League selector: grouped menu from the shared league nav (leagues not on this page are disabled); the search box sits
      in the right-hand area of the same bar. Choosing a league clears the team cache and the search text and loads that league.
      A placeholder league shows "{label} Coming Next"; no enabled leagues shows "No Leagues Enabled".
   3. Team list: status "Loading {label} teams..." (yellow); fetches
      https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/teams?limit=500, follows every $ref
      (http -> https, 12 at a time, cached), builds teams (id, name, abbreviation, location, nickname, slug, logo), sorted by name.
      Success -> green "{count} teams - {label}" (also when the count is 0: "No teams found" box);
      failure -> red "Failed to load {label} teams" plus a "Failed to load teams" box with the error details.
   4. Search box: filters by name, abbreviation, location or nickname (case-insensitive, trimmed); "No teams found" when none match.
   5. Team cards: logo (or an empty placeholder), name, abbreviation (else location, else league label). Click opens the team modal.
   6. Team modal: logo, name, tags (league, abbreviation, location); tabs Overview, Roster, Schedule, Depth, History.
      Each panel loads on first view ("Loading..."); a failed panel shows "Failed to load" + details and retries on the next view.
      Overview: Team Snapshot grid (League, Team ID, Abbreviation, Location, Nickname, Slug, Primary/Alt Color) and an
      "OPEN TEAM PAGE" ESPN link (clubhouse link, else the first link). Roster: fetches
      .../seasons/2026/teams/{id}/athletes?limit=500, follows athlete refs and then position / team / country / college refs,
      sorted by jersey number then name, columns # Name Pos HT WT, injury dot; cached per league and team.
      Schedule and Depth show "not wired" notes; History lists the team details.
      The modal closes with the CLOSE button, a click on the dark overlay, or Escape.
   7. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials (nav.js is loaded by SiteShell).
  Differences: requests are cancelled or ignored when superseded or when the page is left; ESPN text is rendered as React text
  (legacy escaped it into innerHTML).
*/
import { useEffect, useRef, useState, type ReactNode } from "react";
import LeagueNav from "../lib/leagueNav";
import "../../../app/frontend/src/assets/css/pages/teams.css";

const MID = String.fromCharCode(0xb7);
const DASH = String.fromCharCode(0x2014);
const CROSS = String.fromCharCode(0x2715);
const ARROW = String.fromCharCode(0x2192);

const CURRENT_SEASON = 2026;
const CORE_API_ROOT = "https://sports.core.api.espn.com/v2";

type LeagueDef = {
  key: string;
  label: string;
  enabled: boolean;
  sport: string;
  league: string;
  type: string;
  placeholder?: boolean;
  season: number;
};

const LEAGUES: LeagueDef[] = [
  { key: "nba", label: "NBA", enabled: true, sport: "basketball", league: "nba", type: "team-roster", season: CURRENT_SEASON },
  { key: "nhl", label: "NHL", enabled: true, sport: "hockey", league: "nhl", type: "team-roster", season: CURRENT_SEASON },
  { key: "wnba", label: "WNBA", enabled: true, sport: "basketball", league: "wnba", type: "team-roster", season: CURRENT_SEASON },
  { key: "ncaam", label: "NCAAM", enabled: false, sport: "basketball", league: "mens-college-basketball", type: "team-roster", season: CURRENT_SEASON },
  { key: "mlb", label: "MLB", enabled: true, sport: "baseball", league: "mlb", type: "team-roster", season: CURRENT_SEASON },
  { key: "epl", label: "EPL", enabled: true, sport: "soccer", league: "eng.1", type: "team-roster", season: CURRENT_SEASON },
  { key: "mls", label: "MLS", enabled: true, sport: "soccer", league: "usa.1", type: "team-roster", season: CURRENT_SEASON },
  { key: "laliga", label: "LA LIGA", enabled: true, sport: "soccer", league: "esp.1", type: "team-roster", season: CURRENT_SEASON },
  { key: "ligue1", label: "LIGUE 1", enabled: true, sport: "soccer", league: "fra.1", type: "team-roster", season: CURRENT_SEASON },
  { key: "seriea", label: "SERIE A", enabled: true, sport: "soccer", league: "ita.1", type: "team-roster", season: CURRENT_SEASON },
  { key: "bundesliga", label: "BUNDESLIGA", enabled: true, sport: "soccer", league: "ger.1", type: "team-roster", season: CURRENT_SEASON },
  { key: "ufc", label: "UFC", enabled: false, sport: "mma", league: "ufc", type: "placeholder", placeholder: true, season: CURRENT_SEASON },
];

const TEAM_TABS = [
  { key: "overview", label: "Overview" },
  { key: "roster", label: "Roster" },
  { key: "schedule", label: "Schedule" },
  { key: "depth", label: "Depth" },
  { key: "history", label: "History" },
];

// ESPN payloads are untyped JSON.
type AnyObj = any;

type Team = {
  id: string;
  uid: string;
  name: string;
  abbr: string;
  location: string;
  nickname: string;
  slug: string;
  logo: string;
  sport: string;
  league: string;
  leagueKey: string;
  leagueLabel: string;
  season: number;
  raw: AnyObj;
};

type MainView =
  | { kind: "blank" }
  | { kind: "teams" }
  | { kind: "error"; details: string }
  | { kind: "placeholder"; title: string; copy: string };

type PanelState = { status: "loading" | "ready" | "error"; players?: AnyObj[]; error?: string };

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

function valueOrDash(value: unknown): string {
  if (value === null || value === undefined || value === "") return DASH;
  return String(value);
}

function normalizeRefUrl(url: unknown): string {
  if (!url) return "";
  return String(url).replace(/^http:\/\//i, "https://");
}

function isRefItem(item: AnyObj): boolean {
  return !!(item && typeof item === "object" && item.$ref);
}

function getRefUrl(item: AnyObj): string {
  if (!item) return "";
  if (typeof item === "string") return normalizeRefUrl(item);
  if (item.$ref) return normalizeRefUrl(item.$ref);
  return "";
}

function coreLeagueBase(league: { sport: string; league: string }): string {
  return CORE_API_ROOT + "/sports/" + league.sport + "/leagues/" + league.league;
}

function coreTeamsUrl(league: LeagueDef): string {
  return coreLeagueBase(league) + "/teams?limit=500";
}

function coreRosterUrl(league: { sport: string; league: string; season: number }, teamId: string): string {
  return (
    coreLeagueBase(league) +
    "/seasons/" +
    encodeURIComponent(league.season || CURRENT_SEASON) +
    "/teams/" +
    encodeURIComponent(teamId) +
    "/athletes?limit=500"
  );
}

async function fetchJson(url: string, signal?: AbortSignal): Promise<AnyObj> {
  const finalUrl = normalizeRefUrl(url);
  const response = await fetch(finalUrl, signal ? { signal } : undefined);

  if (!response.ok) {
    throw new Error("HTTP " + response.status + " " + MID + " " + finalUrl);
  }

  return response.json();
}

function normalizeTeams(rawTeams: AnyObj[], league: LeagueDef): Team[] {
  const teams = Array.isArray(rawTeams) ? rawTeams : [];

  return teams
    .map((t) => {
      const logos = Array.isArray(t.logos) ? t.logos : [];
      let logo = "";

      if (logos.length) {
        logo = normalizeRefUrl(logos[0].href || logos[0].url || "");
      }

      return {
        id: t.id || t.uid || t.abbreviation || "",
        uid: t.uid || "",
        name: t.displayName || t.name || t.shortDisplayName || t.abbreviation || "Unknown Team",
        abbr: t.abbreviation || "",
        location: t.location || "",
        nickname: t.nickname || "",
        slug: t.slug || "",
        logo: logo,
        sport: league.sport,
        league: league.league,
        leagueKey: league.key,
        leagueLabel: league.label,
        season: league.season || CURRENT_SEASON,
        raw: t,
      } as Team;
    })
    .filter((team) => team.id && team.name)
    .sort((a, b) => a.name.localeCompare(b.name));
}

function getPlayerName(player: AnyObj): string {
  if (!player) return DASH;

  return (
    player.displayName ||
    player.fullName ||
    player.shortName ||
    player.name ||
    [player.firstName, player.lastName].filter(Boolean).join(" ") ||
    DASH
  );
}

function getPosition(player: AnyObj): string {
  if (!player || !player.position) return DASH;

  if (typeof player.position === "string") return player.position;

  return (
    player.position.abbreviation ||
    player.position.name ||
    player.position.displayName ||
    player.position.shortDisplayName ||
    DASH
  );
}

function formatHeight(player: AnyObj): string {
  if (!player) return DASH;

  if (player.displayHeight) return player.displayHeight;

  const height = player.height;

  if (!height) return DASH;

  if (typeof height === "string") return height;

  const inches = Number(height);

  if (!inches || isNaN(inches)) return DASH;

  const feet = Math.floor(inches / 12);
  const rem = inches % 12;

  return feet + "'" + rem + '"';
}

function formatWeight(player: AnyObj): string {
  if (!player) return DASH;

  if (player.displayWeight) return player.displayWeight;

  const weight = player.weight;

  if (!weight) return DASH;

  if (typeof weight === "string") return weight;

  return String(weight) + " lbs";
}

function sortPlayers(a: AnyObj, b: AnyObj): number {
  const aNum = parseInt(a.jersey || a.uniformNumber || "999", 10);
  const bNum = parseInt(b.jersey || b.uniformNumber || "999", 10);

  if (!isNaN(aNum) && !isNaN(bNum) && aNum !== bNum) {
    return aNum - bNum;
  }

  return getPlayerName(a).localeCompare(getPlayerName(b));
}

function InfoRows({ rows }: { rows: string[][] }): ReactNode {
  return (
    <div className="info-grid">
      {rows.map((row, i) => (
        <div className="info-item" key={i}>
          <div className="info-label">{row[0]}</div>
          <div className="info-val">{valueOrDash(row[1])}</div>
        </div>
      ))}
    </div>
  );
}

function OverviewPanel({ team, leagueLabel }: { team: Team; leagueLabel: string }) {
  const raw = team.raw || {};

  const rows: string[][] = [
    ["League", team.leagueLabel || leagueLabel],
    ["Team ID", team.id || DASH],
    ["Abbreviation", team.abbr || DASH],
    ["Location", team.location || DASH],
    ["Nickname", team.nickname || DASH],
    ["Slug", team.slug || DASH],
  ];

  if (raw.color) rows.push(["Primary Color", "#" + raw.color]);
  if (raw.alternateColor) rows.push(["Alt Color", "#" + raw.alternateColor]);

  let web: AnyObj = null;

  if (raw.links && Array.isArray(raw.links) && raw.links.length) {
    web =
      raw.links.find((link: AnyObj) => link && link.rel && link.rel.indexOf("clubhouse") !== -1) || raw.links[0];
  }

  return (
    <>
      <div className="modal-subtitle">Team Snapshot</div>
      <InfoRows rows={rows} />
      {web && web.href ? (
        <>
          <div className="modal-subtitle">ESPN</div>
          <a
            href={normalizeRefUrl(web.href)}
            target="_blank"
            rel="noopener"
            style={{ fontSize: "11px", color: "var(--accent-green)", textDecoration: "none" }}
          >
            {"OPEN TEAM PAGE " + ARROW}
          </a>
        </>
      ) : null}
    </>
  );
}

function RosterPanel({ players }: { players: AnyObj[] }) {
  const list = Array.isArray(players) ? players.slice() : [];

  if (!list.length) {
    return <div className="no-data">No roster data</div>;
  }

  list.sort(sortPlayers);

  return (
    <div style={{ overflowX: "auto" }}>
      <table className="roster-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Name</th>
            <th>Pos</th>
            <th>HT</th>
            <th>WT</th>
          </tr>
        </thead>
        <tbody>
          {list.map((player, i) => {
            const num = player.jersey || player.uniformNumber;
            const jersey = num ? "#" + num : DASH;
            const hasInj = !!(player.injuries && player.injuries.length);

            return (
              <tr key={i}>
                <td>{jersey}</td>
                <td>
                  <span className="p-name">{getPlayerName(player)}</span>
                  {hasInj ? <span className="inj-dot" title={player.injuries[0].status || "Injured"}></span> : null}
                </td>
                <td>{getPosition(player)}</td>
                <td>{formatHeight(player)}</td>
                <td>{formatWeight(player)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function HistoryPanel({ team, leagueLabel }: { team: Team; leagueLabel: string }) {
  const raw = team.raw || {};

  const rows: string[][] = [
    ["Name", team.name || DASH],
    ["League", team.leagueLabel || leagueLabel],
    ["Team ID", team.id || DASH],
    ["UID", team.uid || DASH],
    ["Abbreviation", team.abbr || DASH],
    ["Location", team.location || DASH],
    ["Nickname", team.nickname || DASH],
    ["Slug", team.slug || DASH],
  ];

  if (raw.color) rows.push(["Primary Color", "#" + raw.color]);
  if (raw.alternateColor) rows.push(["Alt Color", "#" + raw.alternateColor]);

  return (
    <>
      {rows.map((row, i) => (
        <div className="bio-row" key={i}>
          <span className="bio-label">{row[0]}</span>
          <span className="bio-val">{valueOrDash(row[1])}</span>
        </div>
      ))}
    </>
  );
}

export default function Teams() {
  const [leagueKey, setLeagueKey] = useState<string>(getDefaultLeagueKey());
  const leagueRef = useRef<LeagueDef | null>(getLeague(getDefaultLeagueKey()));
  const [allTeams, setAllTeams] = useState<Team[]>([]);
  const [searchText, setSearchText] = useState<string>("");
  const [status, setStatusState] = useState<{ text: string; dot: string }>({ text: "Loading...", dot: "yellow" });
  const [main, setMain] = useState<MainView>({ kind: "blank" });

  const [modalTeam, setModalTeam] = useState<Team | null>(null);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [panels, setPanels] = useState<Record<string, PanelState>>({});
  const panelsRef = useRef<Record<string, PanelState>>({});
  const modalSeq = useRef<number>(0);
  const rosterCtl = useRef<AbortController | null>(null);

  const refCache = useRef<Record<string, Promise<AnyObj> | undefined>>({});
  const rosterCache = useRef<Record<string, AnyObj[]>>({});
  const loadSeq = useRef<number>(0);
  const ctlRef = useRef<AbortController | null>(null);
  const unmounted = useRef<boolean>(false);

  const setStatus = (text: string, dot?: string) => setStatusState({ text, dot: dot || "" });

  const fetchRef = (item: AnyObj): Promise<AnyObj> => {
    const url = getRefUrl(item);

    if (!url) {
      return Promise.resolve(item);
    }

    const cached = refCache.current[url];
    if (cached) {
      return cached;
    }

    const p = fetchJson(url).catch((error: unknown) => {
      delete refCache.current[url];
      throw error;
    });
    refCache.current[url] = p;
    return p;
  };

  const fetchRefs = async (items: AnyObj, limit: number, isStale: () => boolean): Promise<AnyObj[]> => {
    const list: AnyObj[] = Array.isArray(items) ? items.slice(0, limit || items.length) : [];
    const results: AnyObj[] = [];
    const concurrency = 12;
    let index = 0;

    const worker = async () => {
      while (index < list.length) {
        if (isStale()) return;
        const currentIndex = index++;
        const item = list[currentIndex];

        try {
          results[currentIndex] = isRefItem(item) ? await fetchRef(item) : item;
        } catch (e) {
          results[currentIndex] = null;
        }
      }
    };

    const workers: Promise<void>[] = [];
    const workerCount = Math.min(concurrency, list.length);

    for (let i = 0; i < workerCount; i++) {
      workers.push(worker());
    }

    await Promise.all(workers);

    return results.filter(Boolean);
  };

  const hydrateAthleteRefs = async (player: AnyObj): Promise<AnyObj> => {
    if (!player || typeof player !== "object") return player;

    const tasks: Promise<void>[] = [];
    const fields = ["position", "team", "country", "college"];

    fields.forEach((field) => {
      if (isRefItem(player[field])) {
        tasks.push(
          fetchRef(player[field])
            .then((value) => {
              player[field] = value;
            })
            .catch(() => {})
        );
      }
    });

    await Promise.all(tasks);

    return player;
  };

  const startRequest = (): { ctl: AbortController; isStale: () => boolean } => {
    if (ctlRef.current) ctlRef.current.abort();
    const ctl = new AbortController();
    ctlRef.current = ctl;
    const seq = ++loadSeq.current;
    return { ctl, isStale: () => unmounted.current || loadSeq.current !== seq };
  };

  const showNoEnabledLeagues = () => {
    setStatus("No team leagues enabled", "yellow");
    setMain({
      kind: "placeholder",
      title: "No Leagues Enabled",
      copy: "Enable at least one league in docs/js/teams/render.js to show team coverage.",
    });
  };

  const showPlaceholderLeague = (league: LeagueDef) => {
    setStatus(league.label + " team coverage placeholder", "yellow");
    setMain({
      kind: "placeholder",
      title: league.label + " Coming Next",
      copy:
        "This page is currently built around teams and rosters. " +
        league.label +
        " does not fit the same team model, so it is parked as a placeholder while the team-based leagues are wired first.",
    });
  };

  const loadTeams = async (league: LeagueDef) => {
    const req = startRequest();

    setStatus("Loading " + league.label + " teams...", "yellow");
    setAllTeams([]);
    setMain({ kind: "blank" });

    const url = coreTeamsUrl(league);

    try {
      const data = await fetchJson(url, req.ctl.signal);
      const teamItems = Array.isArray(data.items) ? data.items : [];
      const hydratedTeams = await fetchRefs(teamItems, 500, req.isStale);
      if (req.isStale()) return;

      const list = normalizeTeams(hydratedTeams, league);

      setAllTeams(list);
      setMain({ kind: "teams" });
      setStatus(list.length + " teams " + MID + " " + league.label, "green");
    } catch (e) {
      if (req.isStale()) return;
      setStatus("Failed to load " + league.label + " teams", "red");
      setMain({ kind: "error", details: (e as Error).message || url });
    }
  };

  const activateLeague = (key: string) => {
    const league = getLeague(key);

    if (!league) {
      showNoEnabledLeagues();
      return;
    }

    leagueRef.current = league;
    setLeagueKey(league.key);
    setAllTeams([]);
    setSearchText("");

    if (league.type === "placeholder") {
      startRequest();
      showPlaceholderLeague(league);
      return;
    }

    loadTeams(league);
  };

  const loadRoster = async (team: Team, isStale: () => boolean, signal: AbortSignal): Promise<AnyObj[] | null> => {
    const cacheKey = team.leagueKey + ":" + team.id;
    const cachedRoster = rosterCache.current[cacheKey];

    if (cachedRoster) {
      return cachedRoster;
    }

    const url = coreRosterUrl({ sport: team.sport, league: team.league, season: team.season }, team.id);
    const data = await fetchJson(url, signal);
    const athleteItems = Array.isArray(data.items) ? data.items : [];
    const athletes = await fetchRefs(athleteItems, 500, isStale);
    if (isStale()) return null;

    await Promise.all(athletes.map((player) => hydrateAthleteRefs(player)));
    if (isStale()) return null;

    athletes.forEach((player) => {
      if (!player.team) player.team = team.raw || team;
      player.__team = team;
    });

    rosterCache.current[cacheKey] = athletes;

    return athletes;
  };

  const loadPanel = async (team: Team, tab: string, seq: number) => {
    const current = panelsRef.current[tab];
    if (current && (current.status === "ready" || current.status === "loading")) return;

    const isStale = () => unmounted.current || modalSeq.current !== seq;

    const setPanel = (state: PanelState) => {
      if (isStale()) return;
      panelsRef.current = { ...panelsRef.current, [tab]: state };
      setPanels(panelsRef.current);
    };

    setPanel({ status: "loading" });

    try {
      if (tab === "roster") {
        const ctl = rosterCtl.current || new AbortController();
        const players = await loadRoster(team, isStale, ctl.signal);
        if (players === null) return;
        setPanel({ status: "ready", players });
      } else {
        setPanel({ status: "ready" });
      }
    } catch (e) {
      if (isStale()) return;
      setPanel({ status: "error", error: (e as Error).message || "" });
    }
  };

  const openTeamModal = (team: Team) => {
    const seq = ++modalSeq.current;
    if (rosterCtl.current) rosterCtl.current.abort();
    rosterCtl.current = new AbortController();
    panelsRef.current = {};
    setPanels({});
    setActiveTab("overview");
    setModalTeam(team);
    setModalOpen(true);
    loadPanel(team, "overview", seq);
  };

  const closeTeamModal = () => setModalOpen(false);

  const selectTab = (tab: string) => {
    setActiveTab(tab);
    if (modalTeam) loadPanel(modalTeam, tab, modalSeq.current);
  };

  useEffect(() => {
    unmounted.current = false;

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setModalOpen(false);
    };
    document.addEventListener("keydown", onKey);

    const league = leagueRef.current;
    if (!league) {
      showNoEnabledLeagues();
    } else {
      activateLeague(league.key);
    }

    return () => {
      unmounted.current = true;
      document.removeEventListener("keydown", onKey);
      if (ctlRef.current) ctlRef.current.abort();
      if (rosterCtl.current) rosterCtl.current.abort();
    };
  }, []);

  const activeLeague = getLeague(leagueKey);
  const activeLabel = activeLeague ? activeLeague.label : "";

  const query = searchText.trim().toLowerCase();
  let teams = allTeams.slice();

  if (query) {
    teams = teams.filter(
      (team) =>
        String(team.name || "").toLowerCase().indexOf(query) !== -1 ||
        String(team.abbr || "").toLowerCase().indexOf(query) !== -1 ||
        String(team.location || "").toLowerCase().indexOf(query) !== -1 ||
        String(team.nickname || "").toLowerCase().indexOf(query) !== -1
    );
  }

  let mainNode: ReactNode = null;
  if (main.kind === "teams" && teams.length) {
    mainNode = (
      <div className="team-grid">
        {teams.map((team, i) => (
          <div className="team-card" key={team.id + ":" + i} onClick={() => openTeamModal(team)}>
            {team.logo ? (
              <img className="team-logo" src={team.logo} loading="lazy" alt={team.name + " logo"} />
            ) : (
              <div className="team-logo-placeholder"></div>
            )}
            <div className="team-info">
              <div className="team-name">{team.name}</div>
              <div className="team-abbr">{team.abbr || team.location || activeLabel}</div>
            </div>
          </div>
        ))}
      </div>
    );
  } else if (main.kind === "error") {
    mainNode = (
      <div className="empty-state">
        Failed to load teams
        <div className="error-details">{main.details}</div>
      </div>
    );
  } else if (main.kind === "placeholder") {
    mainNode = (
      <div className="placeholder-state">
        <div className="placeholder-title">{main.title}</div>
        <div className="placeholder-copy">{main.copy}</div>
      </div>
    );
  }

  const emptyShown = main.kind === "teams" && teams.length === 0;

  const modalSubtitle = modalTeam ? (
    <div className="modal-team-sub">
      <span>{modalTeam.leagueLabel || activeLabel}</span>
      {modalTeam.abbr ? <span>{modalTeam.abbr}</span> : null}
      {modalTeam.location ? <span>{modalTeam.location}</span> : null}
    </div>
  ) : null;

  const renderPanel = (tab: string): ReactNode => {
    if (!modalTeam) return null;
    const state = panels[tab];

    if (!state || state.status === "loading") {
      return <div className="modal-loading">Loading...</div>;
    }

    if (state.status === "error") {
      return (
        <div className="modal-error">
          Failed to load
          <div className="error-details">{state.error || ""}</div>
        </div>
      );
    }

    if (tab === "overview") return <OverviewPanel team={modalTeam} leagueLabel={activeLabel} />;
    if (tab === "roster") return <RosterPanel players={state.players || []} />;
    if (tab === "schedule") return <div className="no-data">Schedule is not wired on this ESPN Core version yet</div>;
    if (tab === "depth") return <div className="no-data">Depth chart is not wired on this ESPN Core version yet</div>;
    if (tab === "history") return <HistoryPanel team={modalTeam} leagueLabel={activeLabel} />;

    return <div className="no-data">No data</div>;
  };

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Teams</div>
          <div className="page-subtitle">{"ESPN CORE " + MID + " TEAM INFO & ROSTERS"}</div>
        </div>
      </div>

      <LeagueNav
        present={getEnabledLeagues().map((l) => l.key)}
        activeKey={leagueKey}
        onSelect={activateLeague}
        pillAs="div"
        className="controls"
        aux={
          <input
            type="text"
            className="search-box"
            id="team-search"
            placeholder="Search team..."
            value={searchText}
            onChange={(e) => {
              setSearchText(e.target.value);
              // Legacy re-rendered the list on every keystroke (replacing any error or placeholder box).
              setMain({ kind: "teams" });
            }}
          />
        }
      />

      <div className="status-bar" id="teams-status">
        <span className={"status-dot " + status.dot} id="status-dot"></span>
        <span id="status-text">{status.text}</span>
      </div>

      <div className="main" id="teams-main">
        {mainNode}
      </div>
      <div className="empty-state" id="teams-empty" style={{ display: emptyShown ? "" : "none" }}>
        No teams found
      </div>

      <div
        className={"modal-overlay" + (modalOpen ? " open" : "")}
        id="modal-overlay"
        onClick={(e) => {
          if (e.target === e.currentTarget) closeTeamModal();
        }}
      >
        <div className="modal-box">
          <button className="modal-close" id="modal-close" onClick={closeTeamModal}>
            {"CLOSE " + CROSS}
          </button>
          <div className="modal-team-header" id="modal-team-header">
            {modalTeam ? (
              <>
                {modalTeam.logo ? <img className="modal-logo" src={modalTeam.logo} alt={modalTeam.name + " logo"} /> : null}
                <div>
                  <div className="modal-team-name">{modalTeam.name}</div>
                  {modalSubtitle}
                </div>
              </>
            ) : null}
          </div>
          <div className="modal-tabs" id="modal-tabs">
            {modalTeam
              ? TEAM_TABS.map((tab) => (
                  <div
                    key={tab.key}
                    className={"modal-tab" + (tab.key === activeTab ? " active" : "")}
                    data-tab={tab.key}
                    onClick={() => selectTab(tab.key)}
                  >
                    {tab.label}
                  </div>
                ))
              : null}
          </div>
          <div id="modal-panels">
            {modalTeam
              ? TEAM_TABS.map((tab) => (
                  <div key={tab.key} className={"modal-panel" + (tab.key === activeTab ? " active" : "")} id={"panel-" + tab.key}>
                    {renderPanel(tab.key)}
                  </div>
                ))
              : null}
          </div>
        </div>
      </div>
    </>
  );
}
