/*
  Players - native React port of legacy players.html + assets/js/players/render.js
  (plus the league menu that assets/js/shared/league_nav.js built around the league pills).

  Legacy behaviors found and preserved:
   1. League list with enabled flags: NBA, NHL, WNBA, MLB and MLS are shown; NCAAM, EPL, La Liga, Ligue 1, Serie A,
      Bundesliga and UFC (placeholder) are disabled and hidden. Default league is NBA.
   2. League selector: grouped menu from the shared league nav (leagues not on this page are disabled).
      Choosing a league clears the cached teams and player data and loads that league's team list.
      A placeholder league hides the team select and shows "{label} Coming Next"; no enabled leagues shows "No Leagues Enabled".
   3. Team list: status "Loading {label} teams..." (yellow); the team select is reset; fetches
      https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/teams?limit=500, follows every $ref
      (http -> https, 12 at a time, cached), builds teams (id, name, abbreviation, logo...), sorted by name.
      None -> red "No teams found for {label}" and "No teams found" with the URL; success -> "{label} - select a team"
      and "Select a team to view roster"; failure -> red "Failed to load {label} teams" and "Failed to load teams" + details.
   4. Choosing a team loads its roster (.../seasons/2026/teams/{id}/athletes?limit=500): status "Loading {team} roster...",
      athlete refs followed, then position / team / country / college refs of each athlete followed.
      Choosing the empty team option shows "Select a team to view roster".
   5. Roster grouping: soccer and MLB are grouped by position type (parent name or Goalkeepers/Defenders/Midfielders/Forwards,
      Pitchers/Catchers/Infielders/Outfielders, else "Roster"); other leagues are one list. Sorted by jersey number then name.
   6. Roster table: team header (logo, name, "{LEAGUE} - ESPN core roster"); columns # Name Pos Age HT WT (+ B/T for MLB,
      + Nation for MLS) + Status (injury badge, status, "Inactive" or a dash); group header rows; "No roster data available" when empty.
      Status "{team} - {count} players - click any player for profile" (green); failure -> red "Failed to load {team} roster" + details.
   7. Clicking a player row (with an id) opens the profile modal: headshot or placeholder, name, tags (position, jersey, team, league),
      tabs Overview, Game Log, Splits, News, Bio. Panels load on first view ("Loading..."). Overview shows the info grid
      (League, Team, Position, Jersey, Age, Height, Weight, Nation, Status) and Date of Birth / Birthplace when known;
      Game Log, Splits and News show the "not wired yet" notes; Bio lists the details. A failure shows "Failed to load player data".
      The modal closes with the CLOSE button, a click on the dark overlay, or Escape.
   8. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials (nav.js is loaded by SiteShell).
  Differences: requests are cancelled or ignored when superseded or when the page is left; ESPN text is rendered as React text
  (legacy escaped it into innerHTML).
*/
import { useEffect, useRef, useState, type ReactNode } from "react";
import LeagueNav from "../lib/leagueNav";
import "../../../app/frontend/src/assets/css/pages/players.css";

const MID = String.fromCharCode(0xb7);
const DASH = String.fromCharCode(0x2014);
const CROSS = String.fromCharCode(0x2715);
const PERSON = String.fromCodePoint(0x1f464);

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
  season?: number;
  columns: string[];
};

const BASE_COLS = ["#", "Name", "Pos", "Age", "HT", "WT"];

const LEAGUES: LeagueDef[] = [
  { key: "nba", label: "NBA", enabled: true, sport: "basketball", league: "nba", type: "team-roster", season: CURRENT_SEASON, columns: BASE_COLS },
  { key: "nhl", label: "NHL", enabled: true, sport: "hockey", league: "nhl", type: "team-roster", season: CURRENT_SEASON, columns: BASE_COLS },
  { key: "wnba", label: "WNBA", enabled: true, sport: "basketball", league: "wnba", type: "team-roster", season: CURRENT_SEASON, columns: BASE_COLS },
  { key: "ncaam", label: "NCAAM", enabled: false, sport: "basketball", league: "mens-college-basketball", type: "team-roster", season: CURRENT_SEASON, columns: BASE_COLS },
  { key: "mlb", label: "MLB", enabled: true, sport: "baseball", league: "mlb", type: "team-roster", season: CURRENT_SEASON, columns: BASE_COLS.concat(["B/T"]) },
  { key: "epl", label: "EPL", enabled: false, sport: "soccer", league: "eng.1", type: "team-roster", season: CURRENT_SEASON, columns: BASE_COLS.concat(["Nation"]) },
  { key: "mls", label: "MLS", enabled: true, sport: "soccer", league: "usa.1", type: "team-roster", season: CURRENT_SEASON, columns: BASE_COLS.concat(["Nation"]) },
  { key: "laliga", label: "LA LIGA", enabled: false, sport: "soccer", league: "esp.1", type: "team-roster", season: CURRENT_SEASON, columns: BASE_COLS.concat(["Nation"]) },
  { key: "ligue1", label: "LIGUE 1", enabled: false, sport: "soccer", league: "fra.1", type: "team-roster", season: CURRENT_SEASON, columns: BASE_COLS.concat(["Nation"]) },
  { key: "seriea", label: "SERIE A", enabled: false, sport: "soccer", league: "ita.1", type: "team-roster", season: CURRENT_SEASON, columns: BASE_COLS.concat(["Nation"]) },
  { key: "bundesliga", label: "BUNDESLIGA", enabled: false, sport: "soccer", league: "ger.1", type: "team-roster", season: CURRENT_SEASON, columns: BASE_COLS.concat(["Nation"]) },
  { key: "ufc", label: "UFC", enabled: false, sport: "mma", league: "ufc", type: "placeholder", placeholder: true, columns: ["Name", "Division", "Record", "Status"] },
];

const PLAYER_TABS = [
  { key: "overview", label: "Overview" },
  { key: "gamelog", label: "Game Log" },
  { key: "splits", label: "Splits" },
  { key: "news", label: "News" },
  { key: "bio", label: "Bio" },
];

// ESPN payloads are loosely shaped, so they are handled loosely, as in the legacy script.
type AnyObj = any;

type Team = {
  id: string;
  uid: string;
  name: string;
  abbreviation: string;
  location: string;
  nickname: string;
  slug: string;
  logo: string;
  raw: AnyObj;
};

type Group = { label: string; players: AnyObj[] };

type MainView =
  | { kind: "empty"; text: string }
  | { kind: "placeholder"; title: string; copy: string }
  | { kind: "error"; text: string; details: string }
  | { kind: "roster"; team: Team; league: LeagueDef; groups: Group[] };

type PanelState = { status: "loading" | "ready" | "error"; error?: string };

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
  return enabled.find((lg) => lg.key === key) || enabled[0];
}

function txt(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

function valueOrDash(value: unknown): unknown {
  if (value === null || value === undefined || value === "") return DASH;
  return value;
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

function coreLeagueBase(league: LeagueDef): string {
  return CORE_API_ROOT + "/sports/" + league.sport + "/leagues/" + league.league;
}

function coreTeamsUrl(league: LeagueDef): string {
  return coreLeagueBase(league) + "/teams?limit=500";
}

function coreRosterUrl(league: LeagueDef, teamId: string): string {
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

function normalizeTeams(rawTeams: AnyObj[]): Team[] {
  const teams = Array.isArray(rawTeams) ? rawTeams : [];

  return teams
    .map((t) => {
      const logos = Array.isArray(t.logos) ? t.logos : [];
      let logo = "";

      if (logos.length) {
        logo = logos[0].href || logos[0].url || "";
      }

      return {
        id: t.id || t.uid || t.abbreviation || "",
        uid: t.uid || "",
        name: t.displayName || t.name || t.shortDisplayName || t.abbreviation || "Unknown Team",
        abbreviation: t.abbreviation || "",
        location: t.location || "",
        nickname: t.nickname || "",
        slug: t.slug || "",
        logo: logo,
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

function getBatsThrows(player: AnyObj): string {
  let batsVal = DASH;
  let throwsVal = DASH;

  if (player.bats) {
    batsVal =
      typeof player.bats === "string"
        ? player.bats
        : player.bats.abbreviation || player.bats.displayValue || player.bats.name || DASH;
  }

  if (player.throws) {
    throwsVal =
      typeof player.throws === "string"
        ? player.throws
        : player.throws.abbreviation || player.throws.displayValue || player.throws.name || DASH;
  }

  if (batsVal === DASH && throwsVal === DASH) return DASH;

  return batsVal + "/" + throwsVal;
}

function getNation(player: AnyObj): string {
  if (!player) return DASH;

  if (player.citizenship) return player.citizenship;
  if (player.nationality) return player.nationality;

  if (player.country) {
    if (typeof player.country === "string") return player.country;

    return player.country.abbreviation || player.country.displayName || player.country.name || DASH;
  }

  if (player.birthPlace && player.birthPlace.country) return player.birthPlace.country;
  if (player.birthCountry) return player.birthCountry;

  return DASH;
}

// Status: an injury badge, plain text, or a dash. "text" is what the legacy stripTags() of the status cell gave.
function getPlayerStatus(player: AnyObj): { badge: boolean; text: string } {
  if (!player) return { badge: false, text: DASH };

  if (player.injuries && player.injuries.length) {
    return {
      badge: true,
      text: txt(player.injuries[0].status || player.injuries[0].type || "Injured"),
    };
  }

  if (player.status) {
    if (typeof player.status === "string") return { badge: false, text: txt(player.status) };

    return {
      badge: false,
      text: txt(player.status.name || player.status.type || player.status.displayName || DASH),
    };
  }

  if (player.active === false) return { badge: false, text: "Inactive" };

  return { badge: false, text: DASH };
}

function getPlayerTeam(player: AnyObj): string {
  if (!player) return DASH;

  if (player.__team && player.__team.name) return player.__team.name;

  if (!player.team) return DASH;

  if (typeof player.team === "string") return player.team;

  return (
    player.team.displayName ||
    player.team.name ||
    player.team.abbreviation ||
    player.team.shortDisplayName ||
    DASH
  );
}

function formatDate(value: AnyObj): string {
  if (!value) return DASH;

  const d = new Date(value);

  if (isNaN(d.getTime())) return value;

  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatBirthPlace(place: AnyObj): string {
  if (!place) return DASH;

  if (typeof place === "string") return place;

  return [place.city, place.state, place.country].filter(Boolean).join(", ") || DASH;
}

function sortPlayers(a: AnyObj, b: AnyObj): number {
  const aNum = parseInt(a.jersey || a.uniformNumber || "999", 10);
  const bNum = parseInt(b.jersey || b.uniformNumber || "999", 10);

  if (!isNaN(aNum) && !isNaN(bNum) && aNum !== bNum) {
    return aNum - bNum;
  }

  return getPlayerName(a).localeCompare(getPlayerName(b));
}

function getPositionGroup(player: AnyObj, league: LeagueDef): string {
  const position = player && player.position ? player.position : null;
  let parent = "";

  if (position && typeof position === "object") {
    parent =
      position.parent && typeof position.parent === "object"
        ? position.parent.displayName || position.parent.name || ""
        : "";
  }

  if (parent) return parent;

  const pos = getPosition(player);

  if (league.sport === "soccer") {
    if (/goalkeeper|^gk$/i.test(pos)) return "Goalkeepers";
    if (/defender|^d$|^cb$|^lb$|^rb$/i.test(pos)) return "Defenders";
    if (/midfielder|^m$|^cm$|^dm$|^am$/i.test(pos)) return "Midfielders";
    if (/forward|striker|^f$|^st$|^fw$/i.test(pos)) return "Forwards";
  }

  if (league.key === "mlb") {
    if (/pitcher|^p$/i.test(pos)) return "Pitchers";
    if (/catcher|^c$/i.test(pos)) return "Catchers";
    if (/first|second|third|shortstop|infield|^1b$|^2b$|^3b$|^ss$/i.test(pos)) return "Infielders";
    if (/outfield|left|center|right|^lf$|^cf$|^rf$|^of$/i.test(pos)) return "Outfielders";
  }

  return "Roster";
}

function groupPlayersByPositionType(players: AnyObj[], league: LeagueDef): Group[] {
  const buckets: Record<string, AnyObj[]> = {};
  const order: string[] = [];

  players.forEach((player) => {
    const label = getPositionGroup(player, league);

    if (!buckets[label]) {
      buckets[label] = [];
      order.push(label);
    }

    buckets[label].push(player);
  });

  return order.map((label) => ({ label: label, players: buckets[label].sort(sortPlayers) }));
}

function normalizeRosterGroups(players: AnyObj[], league: LeagueDef): Group[] {
  const list = Array.isArray(players) ? players : [];

  if (!list.length) {
    return [];
  }

  if (league.sport === "soccer") {
    return groupPlayersByPositionType(list, league);
  }

  if (league.key === "mlb") {
    return groupPlayersByPositionType(list, league);
  }

  return [{ label: "", players: list.sort(sortPlayers) }];
}

function getPlayerCell(player: AnyObj, col: string): ReactNode {
  if (!player) return DASH;

  if (col === "#") return txt(valueOrDash(player.jersey || player.uniformNumber));

  if (col === "Name") return <span className="player-name-cell">{getPlayerName(player)}</span>;

  if (col === "Pos") return getPosition(player);

  if (col === "Age") return txt(valueOrDash(player.age));

  if (col === "HT") return txt(valueOrDash(formatHeight(player)));

  if (col === "WT") return txt(valueOrDash(formatWeight(player)));

  if (col === "B/T") return getBatsThrows(player);

  if (col === "Nation") return getNation(player);

  if (col === "Division") {
    return txt(valueOrDash(player.division || player.weightClass || player.weightclass));
  }

  if (col === "Record") return txt(valueOrDash(player.record || player.displayRecord));

  if (col === "Status") return renderStatus(player);

  return DASH;
}

function renderStatus(player: AnyObj): ReactNode {
  const s = getPlayerStatus(player);
  return s.badge ? <span className="inj-badge">{s.text}</span> : s.text;
}

function statusText(player: AnyObj): string {
  return getPlayerStatus(player).text || DASH;
}

function PanelContent({
  tab,
  player,
  league,
}: {
  tab: string;
  player: AnyObj;
  league: LeagueDef;
}) {
  if (tab === "overview") {
    const rows: [string, unknown][] = [
      ["League", league.label],
      ["Team", getPlayerTeam(player)],
      ["Position", getPosition(player)],
      ["Jersey", player.jersey ? "#" + player.jersey : DASH],
      ["Age", player.age || DASH],
      ["Height", formatHeight(player)],
      ["Weight", formatWeight(player)],
      ["Nation", getNation(player)],
      ["Status", statusText(player)],
    ];

    return (
      <>
        <div className="modal-subtitle">Player Snapshot</div>
        <div className="info-grid">
          {rows.map((row, i) => (
            <div className="info-item" key={i}>
              <div className="info-label">{row[0]}</div>
              <div className="info-val">{txt(valueOrDash(row[1]))}</div>
            </div>
          ))}
        </div>
        {player.dateOfBirth ? (
          <>
            <div className="modal-subtitle" style={{ marginTop: "12px" }}>
              Bio
            </div>
            <div className="bio-row">
              <span className="bio-label">Date of Birth</span>
              <span className="bio-val">{formatDate(player.dateOfBirth)}</span>
            </div>
          </>
        ) : null}
        {player.birthPlace ? (
          <div className="bio-row">
            <span className="bio-label">Birthplace</span>
            <span className="bio-val">{formatBirthPlace(player.birthPlace)}</span>
          </div>
        ) : null}
      </>
    );
  }

  if (tab === "gamelog") {
    return <div className="no-data">Game log data is not wired on the ESPN core roster route yet</div>;
  }

  if (tab === "splits") {
    return <div className="no-data">Splits data is not wired on the ESPN core roster route yet</div>;
  }

  if (tab === "news") {
    return <div className="no-data">News data is not wired on the ESPN core roster route yet</div>;
  }

  const rows: [string, unknown][] = [
    ["Name", getPlayerName(player)],
    ["League", league.label],
    ["Team", getPlayerTeam(player)],
    ["Position", getPosition(player)],
    ["Jersey", player.jersey ? "#" + player.jersey : DASH],
    ["Age", player.age || DASH],
    ["Height", formatHeight(player)],
    ["Weight", formatWeight(player)],
    ["Nation", getNation(player)],
    ["Date of Birth", player.dateOfBirth ? formatDate(player.dateOfBirth) : DASH],
    ["Birthplace", player.birthPlace ? formatBirthPlace(player.birthPlace) : DASH],
    ["Status", statusText(player)],
  ];

  return (
    <>
      {rows.map((row, i) => (
        <div className="bio-row" key={i}>
          <span className="bio-label">{row[0]}</span>
          <span className="bio-val">{txt(valueOrDash(row[1]))}</span>
        </div>
      ))}
    </>
  );
}

export default function Players() {
  const [leagueKey, setLeagueKey] = useState<string>(getDefaultLeagueKey());
  const leagueRef = useRef<LeagueDef | null>(getLeague(getDefaultLeagueKey()));
  const [teams, setTeamsState] = useState<Team[]>([]);
  const teamsRef = useRef<Team[]>([]);
  const [teamId, setTeamId] = useState<string>("");
  const [wrapHidden, setWrapHidden] = useState<boolean>(false);
  const [status, setStatusState] = useState<{ text: string; dot: string }>({
    text: "Loading players page...",
    dot: "yellow",
  });
  const [main, setMain] = useState<MainView>({ kind: "empty", text: "Select a team to view roster" });

  const [modalPlayer, setModalPlayer] = useState<AnyObj | null>(null);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [panels, setPanels] = useState<Record<string, PanelState>>({});
  const panelsRef = useRef<Record<string, PanelState>>({});
  const modalSeq = useRef<number>(0);

  const refCache = useRef<Record<string, Promise<AnyObj> | undefined>>({});
  const playerDataCache = useRef<Record<string, AnyObj>>({});
  const loadSeq = useRef<number>(0);
  const ctlRef = useRef<AbortController | null>(null);
  const unmounted = useRef<boolean>(false);

  const setStatus = (text: string, dot?: string) => setStatusState({ text, dot: dot || "" });
  const setTeams = (v: Team[]) => {
    teamsRef.current = v;
    setTeamsState(v);
  };

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

  const hydrateEntityRefs = async (entity: AnyObj): Promise<AnyObj> => {
    if (!entity || typeof entity !== "object") return entity;

    const tasks: Promise<void>[] = [];
    const fields = ["position", "team", "country", "college"];

    fields.forEach((field) => {
      if (isRefItem(entity[field])) {
        tasks.push(
          fetchRef(entity[field])
            .then((value) => {
              entity[field] = value;
            })
            .catch(() => {})
        );
      }
    });

    await Promise.all(tasks);

    return entity;
  };

  const startRequest = (): { seq: number; ctl: AbortController; isStale: () => boolean } => {
    if (ctlRef.current) ctlRef.current.abort();
    const ctl = new AbortController();
    ctlRef.current = ctl;
    const seq = ++loadSeq.current;
    return { seq, ctl, isStale: () => unmounted.current || loadSeq.current !== seq };
  };

  const showNoEnabledLeagues = () => {
    setWrapHidden(true);
    setTeamId("");
    setStatus("No player leagues enabled", "yellow");
    setMain({
      kind: "placeholder",
      title: "No Leagues Enabled",
      copy: "Enable at least one league in docs/js/players/render.js to show player coverage.",
    });
  };

  const showPlaceholderLeague = (league: LeagueDef) => {
    setWrapHidden(true);
    setTeamId("");
    setStatus(league.label + " player coverage placeholder", "yellow");
    setMain({
      kind: "placeholder",
      title: league.label + " Coming Next",
      copy:
        "This page is currently built around team rosters. " +
        league.label +
        " needs a separate fighter-directory model, so it is intentionally parked as a placeholder while the team-based leagues are wired first.",
    });
  };

  const loadTeamList = async (league: LeagueDef) => {
    const req = startRequest();

    setStatus("Loading " + league.label + " teams...", "yellow");
    setTeamId("");
    setTeams([]);

    const url = coreTeamsUrl(league);

    try {
      const data = await fetchJson(url, req.ctl.signal);
      const teamItems = Array.isArray(data.items) ? data.items : [];
      const hydratedTeams = await fetchRefs(teamItems, 500, req.isStale);
      if (req.isStale()) return;

      const list = normalizeTeams(hydratedTeams);

      if (!list.length) {
        setStatus("No teams found for " + league.label, "red");
        setMain({ kind: "error", text: "No teams found", details: url });
        return;
      }

      setTeams(list);
      setStatus(league.label + " " + MID + " select a team", "");
      setMain({ kind: "empty", text: "Select a team to view roster" });
    } catch (e) {
      if (req.isStale()) return;
      setStatus("Failed to load " + league.label + " teams", "red");
      setMain({
        kind: "error",
        text: "Failed to load teams",
        details: (e as Error).message || url,
      });
    }
  };

  const loadRoster = async (id: string) => {
    const league = leagueRef.current;
    const team = teamsRef.current.find((t) => String(t.id) === String(id));

    if (!team || !league) return;

    const req = startRequest();

    setStatus("Loading " + team.name + " roster...", "yellow");

    const url = coreRosterUrl(league, id);

    try {
      const data = await fetchJson(url, req.ctl.signal);
      const athleteItems = Array.isArray(data.items) ? data.items : [];
      const athletes = await fetchRefs(athleteItems, 500, req.isStale);
      if (req.isStale()) return;

      await Promise.all(athletes.map((player) => hydrateEntityRefs(player)));
      if (req.isStale()) return;

      athletes.forEach((player) => {
        if (!player.team) player.team = team.raw || team;
        player.__team = team;
        player.__league = league;
      });

      const groupMap = normalizeRosterGroups(athletes, league);
      const count = groupMap.reduce((total, grp) => total + grp.players.length, 0);

      setMain({ kind: "roster", team, league, groups: groupMap });
      setStatus(
        team.name + " " + MID + " " + count + " players " + MID + " click any player for profile",
        "green"
      );
    } catch (e) {
      if (req.isStale()) return;
      setStatus("Failed to load " + team.name + " roster", "red");
      setMain({
        kind: "error",
        text: "Failed to load roster",
        details: (e as Error).message || url,
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
    setLeagueKey(league.key);
    setTeams([]);
    playerDataCache.current = {};

    if (league.type === "placeholder") {
      startRequest();
      showPlaceholderLeague(league);
      return;
    }

    setWrapHidden(false);
    loadTeamList(league);
  };

  const closePlayerModal = () => setModalOpen(false);

  const loadPlayerPanel = async (tab: string, player: AnyObj, seq: number) => {
    const league = leagueRef.current;
    if (!league) return;
    if (panelsRef.current[tab] && panelsRef.current[tab].status === "ready") return;

    const setPanel = (state: PanelState) => {
      if (modalSeq.current !== seq || unmounted.current) return;
      panelsRef.current = { ...panelsRef.current, [tab]: state };
      setPanels(panelsRef.current);
    };

    setPanel({ status: "loading" });

    try {
      const cacheKey = league.key + ":" + player.id;
      let data = playerDataCache.current[cacheKey];

      if (!data) {
        data = await hydrateEntityRefs(player);
        playerDataCache.current[cacheKey] = data;
      }

      setPanel({ status: "ready" });
    } catch (e) {
      setPanel({ status: "error", error: (e as Error).message || "" });
    }
  };

  const openPlayerModal = (player: AnyObj) => {
    const seq = ++modalSeq.current;
    panelsRef.current = {};
    setPanels({});
    setActiveTab("overview");
    setModalPlayer(player);
    setModalOpen(true);
    loadPlayerPanel("overview", player, seq);
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
    };
  }, []);

  const activeLeague = getLeague(leagueKey);

  // Modal header
  let headerNode: ReactNode = null;
  if (modalPlayer && activeLeague) {
    const player = modalPlayer;
    let headshot: unknown = "";

    if (player.headshot) {
      headshot = player.headshot.href || player.headshot;
    } else if (player.images && player.images.length) {
      headshot = player.images[0].href || player.images[0].url || "";
    }

    const headshotUrl = normalizeRefUrl(headshot);
    const pos = getPosition(player);
    const jersey = player.jersey ? "#" + player.jersey : "";
    const team = getPlayerTeam(player);

    headerNode = (
      <>
        {headshotUrl ? (
          <img className="modal-headshot" src={headshotUrl} alt={getPlayerName(player)} />
        ) : (
          <div className="modal-headshot-placeholder">{PERSON}</div>
        )}
        <div>
          <div className="modal-player-name">{getPlayerName(player)}</div>
          <div className="modal-player-meta">
            {pos && pos !== DASH ? <span className="tag">{pos}</span> : null}
            {jersey ? <span>{jersey}</span> : null}
            {team && team !== DASH ? <span>{team}</span> : null}
            <span>{activeLeague.label}</span>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Players</div>
          <div className="page-subtitle">
            {["ROSTER BY TEAM", "CLICK PLAYER FOR PROFILE"].join(" " + MID + " ")}
          </div>
        </div>
      </div>

      <div className="controls">
        <LeagueNav
          present={getEnabledLeagues().map((l) => l.key)}
          activeKey={leagueKey}
          onSelect={activateLeague}
          pillAs="button"
        />
        <div className={"team-select-wrap" + (wrapHidden ? " hidden" : "")} id="team-select-wrap">
          <span className="team-select-label">Team</span>
          <select
            className="team-select"
            id="team-select"
            value={teamId}
            onChange={(e) => {
              const v = e.target.value;
              setTeamId(v);
              if (v) {
                loadRoster(v);
              } else {
                setMain({ kind: "empty", text: "Select a team to view roster" });
              }
            }}
          >
            <option value="">{DASH + " Select Team " + DASH}</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="status-bar" id="players-status">
        <span className={"status-dot " + status.dot} id="status-dot"></span>
        <span id="status-text">{status.text}</span>
      </div>

      <div className="main" id="players-main">
        {main.kind === "empty" ? (
          <div className="empty-state">{main.text}</div>
        ) : main.kind === "placeholder" ? (
          <div className="placeholder-state">
            <div className="placeholder-title">{main.title}</div>
            <div className="placeholder-copy">{main.copy}</div>
          </div>
        ) : main.kind === "error" ? (
          <div className="empty-state">
            {main.text}
            <div className="error-details">{main.details}</div>
          </div>
        ) : (
          <>
            <div className="roster-header">
              {main.team.logo ? (
                <img className="roster-logo" src={main.team.logo} alt={main.team.name + " logo"} />
              ) : null}
              <div>
                <div className="roster-team-name">{main.team.name}</div>
                <div className="roster-team-meta">{main.league.label + " " + MID + " ESPN core roster"}</div>
              </div>
            </div>
            {!main.groups.length ? (
              <div className="empty-state">No roster data available</div>
            ) : (
              <div className="players-wrap">
                <table className="players-table">
                  <thead>
                    <tr>
                      {(main.league.columns || ["#", "Name", "Pos", "Age"]).map((c) => (
                        <th key={c}>{c}</th>
                      ))}
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {main.groups.map((group, gi) => {
                      const rowCols = main.league.columns || ["#", "Name", "Pos", "Age"];
                      return [
                        group.label ? (
                          <tr className="roster-group-row" key={"g" + gi}>
                            <td colSpan={rowCols.length + 1}>
                              <div className="roster-group-header">{group.label}</div>
                            </td>
                          </tr>
                        ) : null,
                        ...group.players.map((player, pi) => (
                          <tr
                            className="player-row"
                            key={"p" + gi + "-" + pi}
                            onClick={player && player.id ? () => openPlayerModal(player) : undefined}
                          >
                            {rowCols.map((col) => (
                              <td key={col}>{getPlayerCell(player, col)}</td>
                            ))}
                            <td>{renderStatus(player)}</td>
                          </tr>
                        )),
                      ];
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      <div
        className={"modal-overlay" + (modalOpen ? " open" : "")}
        id="modal-overlay"
        onClick={(e) => {
          if (e.target === e.currentTarget) closePlayerModal();
        }}
      >
        <div className="modal-box">
          <button className="modal-close" id="modal-close" onClick={closePlayerModal}>
            {"CLOSE " + CROSS}
          </button>
          <div className="modal-player-header" id="modal-player-header">
            {headerNode}
          </div>
          <div className="modal-tabs" id="modal-tabs">
            {modalPlayer
              ? PLAYER_TABS.map((tab) => (
                  <div
                    key={tab.key}
                    className={"modal-tab" + (tab.key === activeTab ? " active" : "")}
                    data-tab={tab.key}
                    onClick={() => {
                      setActiveTab(tab.key);
                      loadPlayerPanel(tab.key, modalPlayer, modalSeq.current);
                    }}
                  >
                    {tab.label}
                  </div>
                ))
              : null}
          </div>
          <div id="modal-panels">
            {modalPlayer && activeLeague
              ? PLAYER_TABS.map((tab) => {
                  const ps = panels[tab.key];
                  return (
                    <div
                      key={tab.key}
                      className={"modal-panel" + (tab.key === activeTab ? " active" : "")}
                      id={"ppanel-" + tab.key}
                    >
                      {!ps || ps.status === "loading" ? (
                        <div className="modal-loading">Loading...</div>
                      ) : ps.status === "error" ? (
                        <div className="modal-error">
                          Failed to load player data
                          <div className="error-details">{ps.error || ""}</div>
                        </div>
                      ) : (
                        <PanelContent tab={tab.key} player={modalPlayer} league={activeLeague} />
                      )}
                    </div>
                  );
                })
              : null}
          </div>
        </div>
      </div>
    </>
  );
}
