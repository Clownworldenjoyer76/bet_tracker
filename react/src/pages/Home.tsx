import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import "../../../app/frontend/src/assets/js/shared/config.js";
import { loadAllLeagues, type Game } from "../lib/gamesTodayData";
import {
  buildDayCards,
  formatDateLong,
  loadCompletedBets,
  winRateClass,
  type NormalizedRow,
} from "../lib/betHistoryDailyData";
import "./home-page.css";

// Icons, colors, order, animations and disabled destinations match _home_left.html.
const leagues = [
  { key: "nfl", name: "NFL", color: "#3b82f6", glow: "rgba(59,130,246,.5)" },
  { key: "cfb", name: "College Football", color: "#f59e0b", glow: "rgba(245,158,11,.5)" },
  { key: "mlb", name: "MLB", color: "#ef4444", glow: "rgba(239,68,68,.5)" },
  { key: "nba", name: "NBA", color: "#f97316", glow: "rgba(249,115,22,.5)" },
  { key: "ncaam", name: "College Basketball", color: "#a855f7", glow: "rgba(168,85,247,.5)" },
  { key: "nhl", name: "NHL", color: "#38bdf8", glow: "rgba(56,189,248,.5)" },
  { key: "ufc", name: "UFC", color: "#ef4444", glow: "rgba(239,68,68,.5)" },
  { key: "soccer", name: "Soccer", color: "#22c55e", glow: "rgba(34,197,94,.5)" },
  { key: "wnba", name: "WNBA", color: "#ec4899", glow: "rgba(236,72,153,.5)" },
] as const;

type LeagueIconKey = typeof leagues[number]["key"];

function LeagueIcon({ kind }: { kind: LeagueIconKey }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {kind === "nfl" && <><path d="M3.5 20.5C3 12 8.5 4 20.5 3.5c.5 8.5-5 16.5-17 17z"/><path d="M9 15l6-6M9.8 12.8l1.4 1.4M11.3 11.3l1.4 1.4M12.8 9.8l1.4 1.4"/></>}
      {kind === "cfb" && <g transform="translate(24 0) scale(-1 1)"><path d="M3.5 20.5C3 12 8.5 4 20.5 3.5c.5 8.5-5 16.5-17 17z"/><path d="M9 15l6-6M9.8 12.8l1.4 1.4M11.3 11.3l1.4 1.4M12.8 9.8l1.4 1.4"/></g>}
      {kind === "mlb" && <><circle cx="12" cy="12" r="9"/><path d="M6.3 5.2c2.2 2 3.2 4.3 3.2 6.8s-1 4.8-3.2 6.8M17.7 5.2c-2.2 2-3.2 4.3-3.2 6.8s1 4.8 3.2 6.8"/></>}
      {kind === "nba" && <><circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18M5.3 5.3c2.7 2.7 2.7 10.7 0 13.4M18.7 5.3c-2.7 2.7-2.7 10.7 0 13.4"/></>}
      {kind === "ncaam" && <><rect x="4" y="3" width="16" height="10" rx="1"/><rect x="8.5" y="7" width="7" height="4"/><path d="M8 13h8M8.6 13l1.4 7M15.4 13L14 20M12 13v7M10 20h4"/></>}
      {kind === "nhl" && <><path d="M6 3l6 9M18 3l-6 9"/><ellipse cx="12" cy="15" rx="8" ry="3.2"/><path d="M4 15v3c0 1.8 3.6 3.2 8 3.2s8-1.4 8-3.2v-3"/></>}
      {kind === "ufc" && <><path d="M6.5 11.5V8a2 2 0 0 1 4 0V7a2 2 0 0 1 4 0v.5a2 2 0 0 1 3.5 1.3V15a6 6 0 0 1-6 6h-1.5a5 5 0 0 1-5-5z"/><path d="M10.5 8v3.5M14.5 7.5v4M6.5 16h11"/></>}
      {kind === "soccer" && <><circle cx="12" cy="12" r="9"/><path d="M12 7.8l3.4 2.5-1.3 4h-4.2l-1.3-4zM12 7.8V3.2M15.4 10.3l4.2-1.4M14.1 14.3l2.6 3.7M9.9 14.3L7.3 18M8.6 10.3L4.4 8.9"/></>}
      {kind === "wnba" && <><circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18M5.3 5.3c2.7 2.7 2.7 10.7 0 13.4M18.7 5.3c-2.7 2.7-2.7 10.7 0 13.4"/></>}
    </svg>
  );
}

function todayLocal(): string {
  const now = new Date();
  return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, "0"), String(now.getDate()).padStart(2, "0")].join("-");
}

function GamesList() {
  const [games, setGames] = useState<Game[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [today] = useState(todayLocal);
  const [heading] = useState(() => "Games on " + new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }));
  const [tz] = useState(() => {
    try {
      const part = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", timeZoneName: "short" }).formatToParts(new Date()).find(item => item.type === "timeZoneName");
      return part?.value || "ET";
    } catch { return "ET"; }
  });

  useEffect(() => {
    const controller = new AbortController();
    loadAllLeagues(today, controller.signal)
      .then(results => {
        if (controller.signal.aborted) return;
        setGames(results.flatMap(result => result.games).sort((a, b) => a.sortTime - b.sortTime));
      })
      .catch(error => {
        if (controller.signal.aborted) return;
        console.error(error);
        setFailed(true);
      });
    return () => controller.abort();
  }, [today]);

  return (
    <section className="hl-panel" id="hl-today" aria-label="Games today">
      <div className="hl-head"><div className="hl-title" id="hl-games-date">{heading}</div></div>
      <div className="hl-games" id="hl-games">
        {failed ? <div className="hl-state">Could not load games</div> : games === null ? <div className="hl-state loading">Loading games</div> : games.length === 0 ? <div className="hl-state">No games today</div> : games.map((game, index) => {
          const c = game.card || {};
          const leagueConfig = (window as typeof window & { REPO_CONFIG?: Record<string, { displayName?: string }> }).REPO_CONFIG || {};
          const abbr = leagueConfig[game.league]?.displayName || game.league;
          return (
            <div className="hl-row" key={`${game.league}-${game.sortTime}-${index}`}>
              <span className="hl-badge">{abbr}</span>
              <span className="hl-time">{c.time ? c.time + " " + tz : "TBD"}</span>
              <span className="hl-match">{game.sport === "mma" ? game.title : <>{c.away}<span className="hl-at">@</span>{c.home}</>}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

type DaySelection = { date: string; rows: NormalizedRow[] };

function HomeHistory() {
  const [graded, setGraded] = useState<NormalizedRow[] | null>(null);
  const [statusText, setStatusText] = useState("Loading completed bet history...");
  const [statusState, setStatusState] = useState("");
  const [limit, setLimit] = useState(7);
  const [selection, setSelection] = useState<DaySelection | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const priorFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setStatusText("Loading completed bets from all enabled sports and markets...");
    loadCompletedBets(controller.signal).then(outcome => {
      if (controller.signal.aborted) return;
      if (outcome.kind === "loaded") {
        setGraded(outcome.graded);
        setStatusText(outcome.graded.length.toLocaleString() + " completed bets loaded across all enabled sports and markets.");
        setStatusState("green");
      } else {
        setGraded([]);
        setStatusText(outcome.kind === "no-sources" ? "No completed-bet sources are enabled." : "Completed bet history failed to load.");
        setStatusState("red");
      }
    });
    return () => controller.abort();
  }, []);

  const days = useMemo(() => graded ? buildDayCards(graded) : [], [graded]);
  const sevenDays = days.slice(0, 7);
  const sevenStats = useMemo(() => {
    if (!sevenDays.length) return null;
    let bets = 0, wins = 0, losses = 0, pushes = 0;
    sevenDays.forEach(day => {
      bets += Number(day.count.replace(/,/g, "")) || 0;
      const [w, l, p] = day.record.split("-").map(Number);
      wins += w || 0;
      losses += l || 0;
      pushes += p || 0;
    });
    const rate = wins + losses ? wins / (wins + losses) : null;
    return {
      bets: bets.toLocaleString(),
      record: `${wins}-${losses}-${pushes}`,
      rate: rate === null ? "N/A" : (rate * 100).toFixed(1) + "%",
      color: rate === null ? "" : winRateClass(rate),
      range: sevenDays.length ? `${formatDateLong(sevenDays[sevenDays.length - 1].date).replace(/^([A-Za-z]{3})[a-z]* (\d+),.*$/, "$1 $2")} – ${formatDateLong(sevenDays[0].date).replace(/^([A-Za-z]{3})[a-z]* (\d+),.*$/, "$1 $2")}` : "",
    };
  }, [days]);

  function showDate(date: string) {
    if (!graded) return;
    if (!selection) priorFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setSelection({ date, rows: graded.filter(row => String(row.game_date).replace(/_/g, "-") === date) });
  }

  function closeDate() {
    setSelection(null);
    window.requestAnimationFrame(() => priorFocus.current?.focus());
  }

  const visibleDays = days.slice(0, limit);
  const currentIndex = selection ? visibleDays.findIndex(day => day.date === selection.date) : -1;
  function stepDate(delta: number) {
    const next = visibleDays[currentIndex + delta];
    if (next) showDate(next.date);
  }

  useEffect(() => {
    if (!selection) return;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); closeDate(); return; }
      if (event.key === "ArrowLeft" && currentIndex + 1 < visibleDays.length) { event.preventDefault(); stepDate(1); return; }
      if (event.key === "ArrowRight" && currentIndex > 0) { event.preventDefault(); stepDate(-1); return; }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )).filter(el => el.getClientRects().length > 0);
      if (!focusable.length) return;
      if (event.shiftKey && document.activeElement === focusable[0]) { event.preventDefault(); focusable[focusable.length - 1].focus(); }
      if (!event.shiftKey && document.activeElement === focusable[focusable.length - 1]) { event.preventDefault(); focusable[0].focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = oldOverflow; document.removeEventListener("keydown", onKey); };
  }, [selection, currentIndex, days, limit]);

  return (
    <>
      <section className="home-history" aria-label="Completed bet history">
        <div className="section-header"><div className="section-title">Completed Bet History</div><div className="section-note">Last 7 completed dates, all sports, all markets</div></div>
        <div className="status-line"><span className={`status-dot ${statusState}`} aria-hidden="true"/><span>{statusText}</span></div>
        {sevenStats && <div className="hist-summary">
          <div className="hs-head"><span className="hs-title">Last {sevenDays.length} days</span><span className="hs-range">{sevenStats.range}</span></div>
          <div className="hs-stats">
            <div><div className="day-stat-label">Total Bets</div><div className="day-stat-value">{sevenStats.bets}</div></div>
            <div><div className="day-stat-label">W-L-P Record</div><div className={`day-stat-value ${sevenStats.color}`}>{sevenStats.record}</div></div>
            <div><div className="day-stat-label">Win Rate</div><div className={`day-stat-value ${sevenStats.color}`}>{sevenStats.rate}</div></div>
          </div>
        </div>}
        <div className="history-grid" id="history-grid">
          {graded === null ? Array.from({ length: 4 }, (_, index) => <div className="hist-skel" key={index}/>) : days.length === 0 ? <div className="empty-state">No completed bet history available</div> : days.slice(0, limit).map(day => <article
            className="day-card" key={day.date} role="button" tabIndex={0}
            aria-label={`View picks for ${formatDateLong(day.date)}`}
            onClick={() => showDate(day.date)}
            onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); showDate(day.date); } }}
          >
            <div className="date-label">Date</div><div className="date-value">{formatDateLong(day.date)}</div>
            <div className="day-stats">
              <div className="day-stat"><div className="day-stat-label">Bets For That Day</div><div className="day-stat-value">{day.count}</div></div>
              <div className="day-stat"><div className="day-stat-label">W-L-P Record</div><div className={`day-stat-value ${day.recordClass}`}>{day.record}</div></div>
              <div className="day-stat"><div className="day-stat-label">Win Rate</div><div className={`day-stat-value ${day.rateClass}`}>{day.rateText}</div></div>
              <div className="day-stat"><div className="day-stat-label">Profit / Loss</div><div className={`day-stat-value ${day.profitClass}`}>{day.profitText}</div></div>
            </div>
          </article>)}
        </div>
        {days.length > limit && <button type="button" className="hist-more" onClick={() => setLimit(n => n + 7)}>Load more</button>}
      </section>
      {selection && <div className="home-pk-overlay open" onMouseDown={event => { if (event.target === event.currentTarget) closeDate(); }}>
        <div className="home-pk-panel" role="dialog" aria-modal="true" aria-label={`Picks for ${formatDateLong(selection.date)}`} ref={dialogRef}>
          <div className="home-pk-head">
            <button type="button" className="home-pk-nav" aria-label="Previous date" disabled={currentIndex < 0 || currentIndex + 1 >= visibleDays.length} onClick={() => stepDate(1)}>‹</button>
            <div className="home-pk-title">Picks<span>{formatDateLong(selection.date)}</span></div>
            <button type="button" className="home-pk-nav" aria-label="Next date" disabled={currentIndex <= 0} onClick={() => stepDate(-1)}>›</button>
            <button type="button" className="home-pk-x" ref={closeRef} aria-label="Close" onClick={closeDate}>×</button>
          </div>
          <div className="home-pk-results">
            <table aria-label={`Graded bets for ${formatDateLong(selection.date)}`}><thead><tr><th>League</th><th>Matchup</th><th>Pick</th><th>Result</th><th>Profit</th></tr></thead><tbody>
              {selection.rows.map((bet, index) => <tr key={`${bet.source}-${bet.game_date}-${index}`}><td>{bet.league}</td><td>{bet.matchup || "—"}</td><td>{bet.pick || bet.bet_side || "—"}</td><td>{bet.result}</td><td>{bet.profit_display || "—"}</td></tr>)}
            </tbody></table>
          </div>
        </div>
      </div>}
    </>
  );
}

export default function Home() {
  return (
    <main className="smh-home" aria-label="SportsModelHub homepage">
      <div className="smh-home-content">
        <div className="smh-home-left">
          {/* The original Announcements, Membership and Advertisement sections were conditional on Django-rendered content.
              No React data contract for those values was present in the supplied sources; no empty boxes are inserted. */}
          <section className="hl-panel" id="hl-leagues" aria-label="Leagues">
            <div className="hl-head"><div className="hl-title">Leagues</div><div className="hl-note">League pages coming soon</div></div>
            <nav className="hl-tiles" aria-label="Sports leagues">
              {leagues.map((league, index) => {
                const style = { "--c": league.color, "--cg": league.glow, animationDelay: `${index * 0.04 + 0.02}s` } as CSSProperties;
                return <a key={league.key} className="hl-tile" href="#" title={`${league.name} - coming soon`} data-league={league.key} style={style} onClick={event => event.preventDefault()}><LeagueIcon kind={league.key}/><span>{league.name}</span></a>;
              })}
            </nav>
          </section>
          <GamesList />
        </div>
        <HomeHistory />
      </div>
    </main>
  );
}
