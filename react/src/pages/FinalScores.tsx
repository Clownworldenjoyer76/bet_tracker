/*
  FinalScores - native React port of legacy final_scores.html + final-scores/render.js.

  Legacy behaviors found and preserved:
   1. League list (13 leagues) filtered by window.isPageLeagueEnabled("finalScores", key, enabled) from shared config.js.
   2. Date input defaults to today (local); empty value falls back to today; changing it reloads scores.
   3. Per league: ESPN site scoreboard fetch; on any failure falls back to ESPN core API
      (events list, then $ref chain: event, competition, competitors, team, score, status), sorted by date.
   4. Only completed games shown (status.completed or state "post"); winner from scores, else winner flag.
   5. League pills (All + enabled leagues) filter visible league blocks; placeholder league (UFC) shows a placeholder block.
   6. Status bar: Loading... / "N completed games - date" / "N completed games - F league(s) failed - date" with yellow/green/red dot.
   7. Empty state "No completed games" when zero completed after a load; "No Leagues Enabled" block; "No score leagues enabled" status.
   8. Clicking a game opens a modal: ESPN summary fetch (failure tolerated) showing odds, scoring by period,
      team stats (sport whitelists, max 8), leaders. Close via CLOSE button, overlay click, Escape.
   9. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials.
*/
import { useEffect, useMemo, useState } from "react";
import "../../../app/frontend/src/assets/js/shared/config.js";
import "../../../app/frontend/src/assets/css/pages/final_scores.css";
import {
  DASH,
  DOT,
  LEAGUES,
  buildSummaryView,
  fetchJson,
  getWinnerFlags,
  isFinal,
  isLeagueEnabled,
  loadLeagueEvents,
  scoreText,
  summaryUrl,
  todayStr,
  toEspnDate,
  type Game,
  type SummaryView,
  type Team,
} from "../lib/finalScoresData";

type StatusState = { text: string; cls: string; dot: string };

type SummaryState =
  | { game: Game; status: "loading" }
  | { game: Game; status: "error"; message: string }
  | { game: Game; status: "done"; view: SummaryView };

function TeamRow({ team, winner }: { team: Team; winner: boolean }) {
  return (
    <div className="game-row">
      <span className="team-side">
        {team.logo ? (
          <img
            className="team-logo"
            src={team.logo}
            loading="lazy"
            alt={(team.abbr || team.name || "team") + " logo"}
          />
        ) : null}
        <span className={"team-abbr" + (winner ? " winner" : "")}>
          {team.abbr || team.name || DASH}
        </span>
      </span>
      <span className={"team-score" + (winner ? " winner" : "")}>{scoreText(team)}</span>
    </div>
  );
}

function GameCard({ game, onOpen }: { game: Game; onOpen: (game: Game) => void }) {
  const flags = getWinnerFlags(game);

  return (
    <div
      className="game-card"
      data-event={game.id || ""}
      data-sport={game.sport || ""}
      data-league={game.league || ""}
      data-league-key={game.leagueKey || ""}
      onClick={() => onOpen(game)}
    >
      <div className="game-status">FINAL</div>
      <TeamRow team={game.away} winner={flags.awayWins} />
      <TeamRow team={game.home} winner={flags.homeWins} />
    </div>
  );
}

function SummaryModal({
  state,
  onClose,
}: {
  state: SummaryState | null;
  onClose: () => void;
}) {
  if (!state) return null;

  const game = state.game;
  const flags = getWinnerFlags(game);

  let body;

  if (state.status === "loading") {
    body = (
      <div style={{ padding: 20, color: "var(--text-muted)", fontSize: 11 }}>Loading...</div>
    );
  } else if (state.status === "error") {
    body = (
      <div className="modal-error">
        Failed to load game summary
        <div className="error-details">{state.message}</div>
      </div>
    );
  } else {
    const view = state.view;

    body = (
      <>
        <div className="modal-top">
          <span className={"modal-league-tag tag-" + game.leagueKey}>
            {game.leagueLabel || game.leagueKey}
          </span>
          <span className="modal-final-tag">FINAL</span>
        </div>

        <div className="modal-matchup">
          {game.away.name || game.away.abbr || "Away"} @ {game.home.name || game.home.abbr || "Home"}
        </div>

        <div className="modal-scoreboard">
          <div className="modal-score-row">
            <span className={"modal-team" + (flags.awayWins ? " winner" : "")}>
              {game.away.abbr || game.away.name || DASH}
            </span>
            <span className={"modal-pts" + (flags.awayWins ? " winner" : "")}>
              {scoreText(game.away)}
            </span>
          </div>
          <div className="modal-score-row">
            <span className={"modal-team" + (flags.homeWins ? " winner" : "")}>
              {game.home.abbr || game.home.name || DASH}
            </span>
            <span className={"modal-pts" + (flags.homeWins ? " winner" : "")}>
              {scoreText(game.home)}
            </span>
          </div>
        </div>

        {view.odds ? (
          <div className="modal-section">
            <div className="modal-subtitle">Betting Lines</div>
            <div className="modal-row">Spread: {view.odds.spread}</div>
            <div className="modal-row">Total: {view.odds.total}</div>
          </div>
        ) : null}

        {view.lines.length ? (
          <div className="modal-section">
            <div className="modal-subtitle">Scoring by Period</div>
            {view.lines.map((line, i) => (
              <div className="modal-row" key={i}>
                {line}
              </div>
            ))}
          </div>
        ) : null}

        {view.stats.length ? (
          <div className="modal-section">
            <div className="modal-subtitle">Team Stats</div>
            {view.stats.map((row, i) => (
              <div className="modal-row" key={i}>
                <strong style={{ color: "var(--text-main)" }}>{row.team}</strong>
                <br />
                {row.text}
              </div>
            ))}
          </div>
        ) : null}

        {view.leaders.length ? (
          <div className="modal-section">
            <div className="modal-subtitle">Leaders</div>
            {view.leaders.map((line, i) => (
              <div className="modal-row" key={i}>
                {line}
              </div>
            ))}
          </div>
        ) : null}
      </>
    );
  }

  return (
    <div
      className="modal-overlay open"
      id="modal-overlay"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="modal-box">
        <button className="modal-close" id="modal-close" onClick={onClose}>
          CLOSE {String.fromCharCode(0x2715)}
        </button>
        <div className="modal-inner" id="modal-inner">
          {body}
        </div>
      </div>
    </div>
  );
}

export default function FinalScores() {
  const leagues = useMemo(() => LEAGUES.filter(isLeagueEnabled), []);

  const [date, setDate] = useState<string>(todayStr());
  const [activeLeague, setActiveLeague] = useState<string>("all");
  const [games, setGames] = useState<Record<string, Game[]> | null>(null);
  const [status, setStatus] = useState<StatusState>({ text: "Loading...", cls: "", dot: "yellow" });
  const [selectedGame, setSelectedGame] = useState<Game | null>(null);
  const [summary, setSummary] = useState<SummaryState | null>(null);

  // Load scores for the selected date; aborts on date change / unmount.
  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    const effectiveDate = date || todayStr();
    const espnDate = toEspnDate(effectiveDate);

    const load = async () => {
      setStatus({ text: "Loading...", cls: "loading", dot: "yellow" });

      const scoreLeagues = leagues.filter((cfg) => cfg.type !== "placeholder");

      if (!scoreLeagues.length) {
        setGames((prev) => prev || {});
        setStatus({ text: "No score leagues enabled", cls: "", dot: "yellow" });
        return;
      }

      const results = await Promise.all(
        scoreLeagues.map(async (cfg) => {
          try {
            const events = await loadLeagueEvents(cfg, espnDate, signal);
            return { key: cfg.key, ok: true, events };
          } catch (e) {
            return { key: cfg.key, ok: false, events: [] as Game[] };
          }
        })
      );

      if (signal.aborted) return;

      setGames((prev) => {
        const next: Record<string, Game[]> = { ...(prev || {}) };
        results.forEach((result) => {
          next[result.key] = result.events;
        });
        leagues.forEach((cfg) => {
          if (cfg.type === "placeholder" && !next[cfg.key]) next[cfg.key] = [];
        });
        return next;
      });

      const total = results.reduce((sum, r) => sum + r.events.filter(isFinal).length, 0);
      const failed = results.filter((r) => !r.ok).length;

      if (failed) {
        setStatus({
          text: total + " completed games" + DOT + failed + " league(s) failed" + DOT + effectiveDate,
          cls: "",
          dot: "red",
        });
      } else {
        setStatus({ text: total + " completed games" + DOT + effectiveDate, cls: "", dot: "green" });
      }
    };

    load();

    return () => {
      controller.abort();
    };
  }, [date, leagues]);

  // Load the game summary for the open modal; aborts on close / switch / unmount.
  useEffect(() => {
    if (!selectedGame) {
      setSummary(null);
      return;
    }

    const game = selectedGame;
    const controller = new AbortController();
    const signal = controller.signal;

    setSummary({ game, status: "loading" });

    const run = async () => {
      try {
        let data: any = null;

        try {
          data = await fetchJson(summaryUrl(game), signal);
        } catch (summaryError) {
          if (signal.aborted) return;
          data = null;
        }

        if (signal.aborted) return;

        setSummary({ game, status: "done", view: buildSummaryView(game, data) });
      } catch (e) {
        if (signal.aborted) return;
        setSummary({
          game,
          status: "error",
          message: e instanceof Error ? e.message || "" : String(e),
        });
      }
    };

    run();

    return () => {
      controller.abort();
    };
  }, [selectedGame]);

  // Escape closes the modal.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelectedGame(null);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  const totalCompleted = useMemo(() => {
    if (!games) return 0;
    return leagues.reduce(
      (sum, cfg) => (cfg.type === "placeholder" ? sum : sum + (games[cfg.key] || []).filter(isFinal).length),
      0
    );
  }, [games, leagues]);

  const modalState =
    selectedGame && summary && summary.game === selectedGame
      ? summary
      : selectedGame
        ? ({ game: selectedGame, status: "loading" } as SummaryState)
        : null;

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Final Scores</div>
          <div className="page-subtitle">ALL LEAGUES</div>
        </div>
      </div>

      <div className="controls" id="league-controls">
        <div
          className={"league-pill" + (activeLeague === "all" ? " active" : "")}
          data-league="all"
          onClick={() => setActiveLeague("all")}
        >
          All
        </div>

        {leagues.map((cfg) => (
          <div
            key={cfg.key}
            className={
              "league-pill" +
              (cfg.placeholder ? " placeholder" : "") +
              (activeLeague === cfg.key ? " active" : "")
            }
            data-league={cfg.key}
            onClick={() => setActiveLeague(cfg.key)}
          >
            {cfg.label}
          </div>
        ))}

        <input
          type="date"
          className="date-input"
          id="score-date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
        />
      </div>

      <div className={"status-bar " + status.cls} id="scores-status">
        <span className={"status-dot " + status.dot} id="status-dot"></span>
        <span id="status-text">{status.text}</span>
      </div>

      <div className="main" id="scores-main">
        {games && !leagues.length ? (
          <div className="placeholder-state">
            <div className="placeholder-title">No Leagues Enabled</div>
            <div className="placeholder-copy">
              Enable at least one league in assets/js/shared/config.js under PAGE_LEAGUES.finalScores.
            </div>
          </div>
        ) : null}

        {games
          ? leagues
              .filter((cfg) => activeLeague === "all" || activeLeague === cfg.key)
              .map((cfg) => {
                const completed = (games[cfg.key] || []).filter(isFinal);

                return (
                  <div className="league-block" data-league={cfg.key} key={cfg.key}>
                    <div className={"league-header lh-" + cfg.key}>{cfg.label}</div>

                    {cfg.type === "placeholder" ? (
                      <div className="placeholder-state">
                        <div className="placeholder-title">{cfg.label} Coming Next</div>
                        <div className="placeholder-copy">
                          {cfg.label} does not use the same team final-score model, so it is parked as a placeholder.
                        </div>
                      </div>
                    ) : completed.length ? (
                      <div className="games-grid">
                        {completed.map((game, i) => (
                          <GameCard key={cfg.key + "-" + (game.id || i)} game={game} onOpen={setSelectedGame} />
                        ))}
                      </div>
                    ) : (
                      <div className="no-games">No completed games</div>
                    )}
                  </div>
                );
              })
          : null}
      </div>

      {games && leagues.length > 0 && totalCompleted === 0 ? (
        <div className="empty-state" id="scores-empty">
          No completed games
        </div>
      ) : null}

      <SummaryModal state={modalState} onClose={() => setSelectedGame(null)} />
    </>
  );
}