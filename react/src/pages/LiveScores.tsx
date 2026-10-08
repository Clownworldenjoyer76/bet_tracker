import { useEffect, useMemo, useState } from "react";
import "../../../app/frontend/src/assets/js/shared/config.js";
import "../../../app/frontend/src/assets/css/pages/live_scores.css";

type League = {
  key: string;
  label: string;
  enabled: boolean;
  sport: string;
  league: string;
  placeholder?: boolean;
};

type Team = {
  id: string;
  name: string;
  abbr: string;
  logo: string;
  score: string | null;
  winner: boolean;
};

type Game = {
  id: string;
  leagueKey: string;
  leagueLabel: string;
  date: string;
  status: any;
  away: Team;
  home: Team;
};

declare global {
  interface Window {
    isPageLeagueEnabled?: (
      page: string,
      league: string,
      fallback: boolean
    ) => boolean;
    PAGE_LEAGUES?: Record<string, Record<string, boolean>>;
  }
}

const CORE_API_ROOT = "https://sports.core.api.espn.com/v2";
const REFRESH_MS = 30000;

const LEAGUES: League[] = [
  { key: "NBA", label: "NBA", enabled: true, sport: "basketball", league: "nba" },
  { key: "NHL", label: "NHL", enabled: true, sport: "hockey", league: "nhl" },
  { key: "CFB", label: "CFB", enabled: true, sport: "football", league: "college-football" },
  { key: "WNBA", label: "WNBA", enabled: true, sport: "basketball", league: "wnba" },
  { key: "NCAAM", label: "NCAAM", enabled: false, sport: "basketball", league: "mens-college-basketball" },
  { key: "MLB", label: "MLB", enabled: true, sport: "baseball", league: "mlb" },
  { key: "EPL", label: "EPL", enabled: true, sport: "soccer", league: "eng.1" },
  { key: "MLS", label: "MLS", enabled: true, sport: "soccer", league: "usa.1" },
  { key: "LALIGA", label: "LA LIGA", enabled: true, sport: "soccer", league: "esp.1" },
  { key: "LIGUE1", label: "LIGUE 1", enabled: true, sport: "soccer", league: "fra.1" },
  { key: "SERIEA", label: "SERIE A", enabled: true, sport: "soccer", league: "ita.1" },
  { key: "BUNDESLIGA", label: "BUNDESLIGA", enabled: true, sport: "soccer", league: "ger.1" },
  { key: "UFC", label: "UFC", enabled: false, sport: "mma", league: "ufc", placeholder: true },
];

function enabled(league: League) {
  const fallback = league.enabled !== false;

  if (window.isPageLeagueEnabled) {
    return window.isPageLeagueEnabled("liveScores", league.key, fallback);
  }

  const configured = window.PAGE_LEAGUES?.liveScores?.[league.key];
  return configured === undefined ? fallback : configured !== false;
}

function normalizeUrl(value: unknown) {
  return String(value || "").replace(/^http:\/\//i, "https://");
}

async function fetchJson(url: string) {
  const response = await fetch(normalizeUrl(url));
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function fetchRef(item: any): Promise<any> {
  if (!item?.$ref) return item;
  return fetchJson(item.$ref);
}

function normalizeScore(score: any): string | null {
  if (score === null || score === undefined || score === "") return null;

  if (typeof score === "object") {
    for (const key of ["displayValue", "value", "score", "points", "total"]) {
      if (score[key] !== undefined && score[key] !== null && score[key] !== "") {
        const value = normalizeScore(score[key]);
        if (value !== null) return value;
      }
    }
    return null;
  }

  return String(score);
}

function siteTeam(item: any): Team {
  const team = item?.team || {};
  const logo =
    team.logos?.[0]?.href ||
    team.logos?.[0]?.url ||
    team.logo ||
    "";

  return {
    id: team.id || item?.id || "",
    name: team.displayName || team.name || team.shortDisplayName || "—",
    abbr: team.abbreviation || team.shortDisplayName || team.name || "—",
    logo: normalizeUrl(logo),
    score: normalizeScore(item?.score),
    winner: item?.winner === true,
  };
}

function normalizeSiteEvents(cfg: League, events: any[]): Game[] {
  return events.flatMap((event) => {
    const competition = event?.competitions?.[0];
    const competitors = competition?.competitors || [];

    const away = competitors.find((team: any) => team.homeAway === "away");
    const home = competitors.find((team: any) => team.homeAway === "home");

    if (!away || !home) return [];

    return [{
      id: event.id || "",
      leagueKey: cfg.key,
      leagueLabel: cfg.label,
      date: event.date || competition?.date || "",
      status: event.status || competition?.status || {},
      away: siteTeam(away),
      home: siteTeam(home),
    }];
  });
}

function todayParam() {
  const now = new Date();

  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("");
}

async function loadCoreEvents(cfg: League): Promise<Game[]> {
  const url =
    `${CORE_API_ROOT}/sports/${encodeURIComponent(cfg.sport)}` +
    `/leagues/${encodeURIComponent(cfg.league)}` +
    `/events?dates=${todayParam()}&limit=200`;

  const data = await fetchJson(url);
  const refs = Array.isArray(data.items) ? data.items : [];

  const events = await Promise.all(
    refs.map(async (item: any): Promise<Game | null> => {
      try {
        const event = await fetchRef(item);

        const competition = await fetchRef(
          event?.competitions?.[0] || event?.competition
        );

        if (!competition) return null;

        const competitors = await Promise.all(
          (competition.competitors || []).map(async (raw: any) => {
            const competitor = await fetchRef(raw);

            if (competitor?.team?.$ref) {
              competitor.team = await fetchRef(competitor.team);
            }

            if (competitor?.score?.$ref) {
              competitor.score = await fetchRef(competitor.score);
            }

            return competitor;
          })
        );

        let away = competitors.find(
          (team: any) => String(team?.homeAway).toLowerCase() === "away"
        );

        let home = competitors.find(
          (team: any) => String(team?.homeAway).toLowerCase() === "home"
        );

        if ((!away || !home) && competitors.length >= 2) {
          away = competitors[0];
          home = competitors[1];
        }

        if (!away || !home) return null;

        const status = await fetchRef(
          event?.status || competition?.status || {}
        );

        return {
          id: event.id || competition.id || "",
          leagueKey: cfg.key,
          leagueLabel: cfg.label,
          date: event.date || competition.date || "",
          status,
          away: siteTeam(away),
          home: siteTeam(home),
        };
      } catch {
        return null;
      }
    })
  );

  return events.filter((game): game is Game => game !== null);
}

async function loadLeague(cfg: League) {
  const url =
    `https://site.api.espn.com/apis/site/v2/sports/` +
    `${encodeURIComponent(cfg.sport)}/${encodeURIComponent(cfg.league)}/scoreboard`;

  try {
    const data = await fetchJson(url);
    return normalizeSiteEvents(cfg, data.events || []);
  } catch {
    return loadCoreEvents(cfg);
  }
}

function statusType(game: Game) {
  return game.status?.type || game.status || {};
}

function isLive(game: Game) {
  const type = statusType(game);
  return type.completed !== true &&
    String(type.state || game.status?.state || "").toLowerCase() === "in";
}

function isFinal(game: Game) {
  const type = statusType(game);
  return type.completed === true || game.status?.completed === true;
}

function startTime(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "";

  return date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}

function statusLabel(game: Game) {
  const type = statusType(game);

  return (
    type.shortDetail ||
    type.detail ||
    type.description ||
    game.status?.shortDetail ||
    game.status?.detail ||
    game.status?.description ||
    startTime(game.date)
  );
}

function TeamRow({
  team,
  winner,
}: {
  team: Team;
  winner: boolean;
}) {
  return (
    <div className="game-row">
      <span className="team-side">
        {team.logo ? (
          <img
            className="team-logo"
            src={team.logo}
            loading="lazy"
            alt={`${team.abbr || team.name} logo`}
          />
        ) : null}

        <span className={`team-abbr${winner ? " winner" : ""}`}>
          {team.abbr || team.name}
        </span>
      </span>

      <span
        className={`team-score${team.score === null ? " no-score" : ""}${
          winner ? " winner" : ""
        }`}
      >
        {team.score ?? "—"}
      </span>
    </div>
  );
}

function GameCard({ game }: { game: Game }) {
  const live = isLive(game);
  const final = isFinal(game);

  let awayWins = game.away.winner;
  let homeWins = game.home.winner;

  if (final && game.away.score !== null && game.home.score !== null) {
    const away = Number(game.away.score);
    const home = Number(game.home.score);

    if (!Number.isNaN(away) && !Number.isNaN(home)) {
      awayWins = away > home;
      homeWins = home > away;
    }
  }

  return (
    <div className={`game-card${live ? " live" : ""}`}>
      <div
        className={
          live
            ? "game-status is-live"
            : final
              ? "game-status is-final"
              : "game-status"
        }
      >
        {statusLabel(game)}
      </div>

      <TeamRow team={game.away} winner={awayWins} />
      <TeamRow team={game.home} winner={homeWins} />
    </div>
  );
}

export default function LiveScores() {
  const leagues = useMemo(() => LEAGUES.filter(enabled), []);
  const [activeLeague, setActiveLeague] = useState("all");
  const [games, setGames] = useState<Record<string, Game[]>>({});
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(0);
  const [updated, setUpdated] = useState("");

  useEffect(() => {
    let cancelled = false;

    const refresh = async () => {
      if (!cancelled) setLoading(true);

      const scoreLeagues = leagues.filter((league) => !league.placeholder);

      const results = await Promise.all(
        scoreLeagues.map(async (league) => {
          try {
            return {
              league,
              games: await loadLeague(league),
              ok: true,
            };
          } catch {
            return {
              league,
              games: [] as Game[],
              ok: false,
            };
          }
        })
      );

      if (cancelled) return;

      const next: Record<string, Game[]> = {};

      for (const result of results) {
        next[result.league.key] = result.games;
      }

      for (const league of leagues) {
        if (league.placeholder) next[league.key] = [];
      }

      setGames(next);
      setFailed(results.filter((result) => !result.ok).length);
      setUpdated(
        new Date().toLocaleTimeString("en-US", {
          hour: "numeric",
          minute: "2-digit",
        })
      );
      setLoading(false);
    };

    refresh();
    const timer = window.setInterval(refresh, REFRESH_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [leagues]);

  const total = Object.values(games).reduce(
    (sum, leagueGames) => sum + leagueGames.length,
    0
  );

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Live Scores</div>
          <div className="page-subtitle">
            ALL LEAGUES · AUTO-REFRESH 30S
          </div>
        </div>

        <div className="refresh-badge">
          {updated ? `UPDATED ${updated}` : "—"}
        </div>
      </div>

      <div className="controls" id="league-controls">
        <button
          type="button"
          className={`league-pill${activeLeague === "all" ? " active" : ""}`}
          onClick={() => setActiveLeague("all")}
        >
          All
        </button>

        {leagues.map((league) => (
          <button
            type="button"
            key={league.key}
            className={`league-pill${
              activeLeague === league.key ? " active" : ""
            }${league.placeholder ? " placeholder" : ""}`}
            onClick={() => setActiveLeague(league.key)}
          >
            {league.label}
          </button>
        ))}
      </div>

      <div className={`status-bar${loading ? " loading" : ""}`}>
        <span
          className={`status-dot ${
            loading ? "yellow" : failed ? "red" : "green"
          }`}
        />

        <span>
          {loading
            ? "Refreshing..."
            : failed
              ? `${total} games loaded · ${failed} league(s) failed · last updated ${updated}`
              : `${total} games loaded · last updated ${updated}`}
        </span>
      </div>

      <div className="main">
        {leagues
          .filter(
            (league) =>
              activeLeague === "all" || activeLeague === league.key
          )
          .map((league) => (
            <div
              className="league-block"
              data-league={league.key}
              key={league.key}
            >
              <div className={`league-header lh-${league.key}`}>
                {league.label}
              </div>

              {league.placeholder ? (
                <div className="placeholder-state">
                  <div className="placeholder-title">
                    {league.label} Coming Next
                  </div>
                  <div className="placeholder-copy">
                    {league.label} does not use the same team-score model,
                    so it is parked as a placeholder.
                  </div>
                </div>
              ) : games[league.key]?.length ? (
                <div className="games-grid">
                  {games[league.key].map((game) => (
                    <GameCard
                      game={game}
                      key={`${league.key}-${game.id}`}
                    />
                  ))}
                </div>
              ) : (
                !loading && <div className="no-games">No games today</div>
              )}
            </div>
          ))}
      </div>
    </>
  );
}
