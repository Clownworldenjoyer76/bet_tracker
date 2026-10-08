/*
  GamesToday - native React port of legacy games_today.html + games-today/{main,render,modal}.js.

  Legacy behaviors found and preserved:
   1. Missing window.REPO_CONFIG: status "Missing config." and nothing loads.
   2. Date input defaults to today (local); empty value falls back to today; changing it reloads all leagues.
   3. Load: status "Loading..." (loading style), games area cleared; error: status "Error loading games." + ERROR LOADING GAMES.
   4. loadAllLeagues: leagues enabled via REPO_CONFIG + window.isPageLeagueEnabled("gamesToday", ...), CSVs fetched
      (win/ paths from raw.githubusercontent.com, cache-busted, no-store), games sorted by time (shared module).
   5. Each successful render: filter pills rebuilt (All active + one per league); pills show/hide league sections.
   6. League sections with header and cards, "No games" for empty leagues; zero games total replaces everything
      with NO GAMES FOR THIS DATE; status "N game(s) - date".
   7. Card: date/time, league, away/home, ML / run-line / puck-line / spread (no spread row for soccer/mma), total, projection.
   8. Card click or Enter/Space opens the details modal and sends the game_details_opened analytics event
      (window.SMHTrack, or queued on window.__smhAnalyticsQueue).
   9. Modal: league tag, date/time, title, only non-empty detail rows; Close button, backdrop click, Escape (inside dialog),
      Tab focus trap, focus moves to Close on open and returns to the opener on close.
  10. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials (nav.js is loaded by SiteShell).
*/
import { useEffect, useMemo, useRef, useState } from "react";
import "../../../app/frontend/src/assets/js/shared/config.js";
import "../../../app/frontend/src/assets/css/matstheme.css";
import "../../../app/frontend/src/assets/css/pages/games_today.css";
import "../../../app/frontend/src/assets/css/site-polish.css";
import {
  MID,
  isPresent,
  loadAllLeagues,
  type Game,
  type LeagueResult,
} from "../lib/gamesTodayData";

declare global {
  interface Window {
    SMHTrack?: (event: string, props?: Record<string, unknown>) => void;
    __smhAnalyticsQueue?: unknown[];
  }
}

const DASH = String.fromCharCode(0x2014);
const ELLIPSIS = String.fromCharCode(0x2026);

function todayLocal(): string {
  const d = new Date();

  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
}

function spreadLabelFor(sport: string | undefined): string {
  if (sport === "baseball") return "RUN LINE";
  if (sport === "hockey") return "PUCK LINE";
  if (sport === "soccer") return "";
  if (sport === "mma") return "";
  return "SPREAD";
}

function LineRow({ label, value }: { label: string; value: string | undefined }) {
  if (!isPresent(label) || !isPresent(value)) return null;

  return (
    <div className="gt-card-line-row">
      <span className="gt-card-line-label">{label}</span>
      <span className="gt-card-line-val">{value}</span>
    </div>
  );
}

function ArrayLineRow({ label, values }: { label: string; values: string[] | undefined }) {
  const clean = (values || []).filter(isPresent);
  if (!isPresent(label) || !clean.length) return null;

  return (
    <div className="gt-card-line-row">
      <span className="gt-card-line-label">{label}</span>
      <span className="gt-card-line-val">{clean.join(" / ")}</span>
    </div>
  );
}

function GameCard({
  game,
  selectedDate,
  onOpen,
}: {
  game: Game;
  selectedDate: string;
  onOpen: (game: Game) => void;
}) {
  const c = game.card || {};

  const open = () => {
    const props = {
      league: game.league || game.displayLeague,
      sport: game.sport,
      matchup: game.title || `${c.away || DASH} @ ${c.home || DASH}`,
      selected_date: c.date || selectedDate,
    };

    if (window.SMHTrack) {
      window.SMHTrack("game_details_opened", props);
    } else {
      window.__smhAnalyticsQueue = window.__smhAnalyticsQueue || [];
      window.__smhAnalyticsQueue.push(["game_details_opened", props]);
    }

    onOpen(game);
  };

  return (
    <div
      className="gt-card"
      role="button"
      tabIndex={0}
      aria-label={
        "Open game details: " +
        (game.title || [c.away, c.home].filter(Boolean).join(" at ") || game.displayLeague || "game")
      }
      onClick={open}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          open();
        }
      }}
    >
      <div className="gt-card-top">
        <span className="gt-card-time">{[c.date, c.time].filter(Boolean).join(` ${MID} `)}</span>
        <span className="gt-card-league">{game.displayLeague}</span>
      </div>

      <div className="gt-card-matchup">
        <div className="gt-card-team-row">
          <span className="gt-card-team away">{c.away || ""}</span>
        </div>
        <div className="gt-card-team-row">
          <span className="gt-card-team home">{c.home || ""}</span>
        </div>
      </div>

      <div className="gt-card-divider"></div>

      <div className="gt-card-lines">
        <ArrayLineRow label="ML" values={c.moneyline} />
        <ArrayLineRow label={spreadLabelFor(game.sport)} values={c.spread} />
        <LineRow label="TOTAL" value={c.total} />
      </div>

      {isPresent(c.projection) ? (
        <>
          <div className="gt-card-divider"></div>
          <div className="gt-card-proj">
            <span className="gt-card-proj-label">PROJ</span>
            <span className="gt-card-proj-val">{c.projection}</span>
          </div>
        </>
      ) : null}
    </div>
  );
}

function GameModal({ game, onClose }: { game: Game | null; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);

  // Focus management: move focus to Close on open, return it to the opener on close.
  useEffect(() => {
    if (!game) return;

    const returnFocus = document.activeElement as HTMLElement | null;
    const openFrame = requestAnimationFrame(() => {
      closeRef.current?.focus();
    });

    return () => {
      cancelAnimationFrame(openFrame);

      if (returnFocus && document.contains(returnFocus)) {
        requestAnimationFrame(() => returnFocus.focus());
      }
    };
  }, [game]);

  if (!game) return null;

  const rows = (game.modal || []).filter(([, value]) => isPresent(value));

  return (
    <div
      className="gt-modal open"
      id="gt-modal"
      role="dialog"
      aria-modal="true"
      aria-hidden="false"
      aria-label="Game details"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          onClose();
          return;
        }

        if (event.key !== "Tab") return;

        const closeButton = closeRef.current;

        if (!closeButton) {
          event.preventDefault();
          return;
        }

        // Close is the only focusable element in the dialog, so it is both first and last.
        if (document.activeElement === closeButton) {
          event.preventDefault();
          closeButton.focus();
        }
      }}
    >
      <div className="gt-modal-card">
        <div id="gt-modal-content">
          <div className="gt-modal-header">
            <span className="gt-modal-league-tag">{game.displayLeague}</span>
            <span className="gt-modal-time">
              {[game.card?.date, game.card?.time].filter(Boolean).join(` ${MID} `)}
            </span>
          </div>

          <h2 className="gt-modal-title">{game.title}</h2>

          <div className="gt-modal-section-label">GAME DETAILS</div>
          <div className="gt-modal-lines">
            {rows.map(([label, value], i) => (
              <div className="gt-line-row" key={i}>
                <span className="gt-line-label">{label}</span>
                <span className="gt-line-val">{value}</span>
              </div>
            ))}
          </div>
        </div>

        <button type="button" className="gt-modal-close-btn" ref={closeRef} onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}

export default function GamesToday() {
  const [date, setDate] = useState<string>(todayLocal());
  // null until the first successful load, like the legacy page (no filter pills before then).
  const [results, setResults] = useState<LeagueResult[] | null>(null);
  const [renderedDate, setRenderedDate] = useState<string>("");
  const [activeLeague, setActiveLeague] = useState<string>("all");
  const [selectedGame, setSelectedGame] = useState<Game | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<boolean>(false);
  const [missingConfig, setMissingConfig] = useState<boolean>(false);

  // Load all leagues for the selected date; aborts on date change / unmount.
  useEffect(() => {
    if (!(window as any).REPO_CONFIG) {
      setMissingConfig(true);
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const signal = controller.signal;
    const dateStr = date || todayLocal();

    setMissingConfig(false);
    setLoading(true);
    setError(false);

    loadAllLeagues(dateStr, signal)
      .then((next) => {
        if (signal.aborted) return;
        setResults(next);
        setRenderedDate(dateStr);
        setActiveLeague("all");
        setLoading(false);
      })
      .catch((err: unknown) => {
        console.error(err);
        if (signal.aborted) return;
        setError(true);
        setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [date]);

  const totalGames = useMemo(
    () => (results || []).reduce((total, result) => total + (result.games ? result.games.length : 0), 0),
    [results]
  );

  let statusText = "";
  if (missingConfig) statusText = "Missing config.";
  else if (loading) statusText = "Loading" + ELLIPSIS;
  else if (error) statusText = "Error loading games.";
  else if (results) statusText = `${totalGames} game${totalGames === 1 ? "" : "s"} ${MID} ${renderedDate}`;

  const showGames = !loading && !error && !missingConfig && results !== null;

  return (
    <>
      <div className="gt-header">
        <h1 className="gt-title">GAMES TODAY</h1>
        <div
          id="gt-status"
          className={"status" + (loading && !missingConfig ? " loading" : "")}
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          {statusText}
        </div>
      </div>

      <div className="gt-controls">
        <div className="gt-date-wrap">
          <label className="gt-date-label" htmlFor="gt-date">
            Date
          </label>
          <input id="gt-date" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </div>

        <div id="gt-filters">
          {results !== null ? (
            <>
              <button
                type="button"
                className={"filter-pill" + (activeLeague === "all" ? " active" : "")}
                data-league="all"
                onClick={() => setActiveLeague("all")}
              >
                All
              </button>

              {results.map((result) => (
                <button
                  type="button"
                  className={"filter-pill" + (activeLeague === result.league ? " active" : "")}
                  data-league={result.league}
                  key={result.league}
                  onClick={() => setActiveLeague(result.league)}
                >
                  {result.displayName}
                </button>
              ))}
            </>
          ) : null}
        </div>
      </div>

      <div id="gt-games">
        {error ? <div className="gt-empty-state">ERROR LOADING GAMES</div> : null}

        {showGames && totalGames === 0 ? (
          <div className="gt-empty-state">NO GAMES FOR THIS DATE</div>
        ) : null}

        {showGames && totalGames > 0
          ? (results || []).map((result) => (
              <section
                className="gt-league-section"
                data-league={result.league}
                key={result.league}
                style={{ display: activeLeague === "all" || activeLeague === result.league ? "" : "none" }}
              >
                <div className="gt-league-header">{result.displayName}</div>

                <div className="gt-league-games">
                  {!result.games || result.games.length === 0 ? (
                    <div className="gt-col-state empty">No games</div>
                  ) : (
                    result.games.map((game, i) => (
                      <GameCard
                        key={`${game.league}-${i}`}
                        game={game}
                        selectedDate={date}
                        onOpen={setSelectedGame}
                      />
                    ))
                  )}
                </div>
              </section>
            ))
          : null}
      </div>

      <GameModal game={selectedGame} onClose={() => setSelectedGame(null)} />
    </>
  );
}