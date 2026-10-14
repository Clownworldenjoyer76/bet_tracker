import { useEffect, useRef, useState } from "react";
import type { NormalizedRow } from "../lib/betHistoryDailyData";
import Account from "./Account";
import Login from "./Login";
import GamesToday from "./GamesToday";
import BetHistoryDaily from "./BetHistoryDaily";
import { accountBootstrap } from "../lib/accountUi";
import "./home-page.css";

const leagues = [
  ["NFL", "/nfl_dashboard.html"],
  ["College Football", "/ncaaf_dashboard.html"],
  ["MLB", "/mlb_dashboard.html"],
  ["NBA", "/nba_dashboard.html"],
  ["College Basketball", "/ncaam_dashboard.html"],
  ["NHL", "/nhl_dashboard.html"],
  ["UFC", "/ufc_dashboard.html"],
  ["Soccer", "/soccer_dashboard.html"],
  ["WNBA", "/wnba_dashboard.html"],
] as const;

export default function Home() {
  const session = accountBootstrap();
  const [selectedDay, setSelectedDay] = useState<{ day: string; rows: NormalizedRow[] } | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const priorFocus = useRef<HTMLElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  function openDay(day: string, rows: NormalizedRow[]) {
    priorFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setSelectedDay({ day, rows });
  }
  function closeDay() {
    setSelectedDay(null);
    window.requestAnimationFrame(() => priorFocus.current?.focus());
  }
  useEffect(() => {
    if (!selectedDay) return;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDay();
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const controls = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )).filter((item) => item.getClientRects().length > 0);
      if (!controls.length) return;
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = originalOverflow; document.removeEventListener("keydown", onKey); };
  }, [selectedDay]);

  return (
    <main className="smh-home" aria-label="SportsModelHub homepage">
      <div className="smh-home-grid">
        <aside className="smh-home-account" aria-label="Account and membership">
          {session.authenticated ? <Account /> : <Login />}
        </aside>
        <div className="smh-home-content">
          <section className="smh-home-panel" id="home-leagues" aria-labelledby="home-leagues-heading">
            <div className="smh-home-panel-heading"><h2 id="home-leagues-heading">Leagues</h2><span>Sports dashboards</span></div>
            <nav className="smh-home-leagues" aria-label="Sports leagues">
              {leagues.map(([name, href]) => (
                <a href={href} className="smh-home-league" key={href}>{name} <span aria-hidden="true">â†’</span></a>
              ))}
            </nav>
          </section>
          <section className="smh-home-panel smh-home-games" id="home-games" aria-labelledby="home-games-heading">
            <div className="smh-home-panel-heading"><h2 id="home-games-heading">Games today</h2><a href="/games_today.html">Full games dashboard â†’</a></div>
            <GamesToday />
          </section>
          <section className="smh-home-panel smh-home-history" id="home-history" aria-labelledby="home-history-heading">
            <div className="smh-home-panel-heading"><h2 id="home-history-heading">Completed Bet History</h2><a href="/bet_history_daily.html">Full history â†’</a></div>
            <BetHistoryDaily onDateSelect={openDay} />
            <p className="smh-home-subtle">Select a completed date to view its picks, or open the <a href="/the_picks.html">full Picks page</a>.</p>
          </section>
        </div>
      </div>
      {selectedDay ? (
        <div className="smh-home-picks-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) closeDay(); }}>
          <div className="smh-home-picks-dialog" role="dialog" aria-modal="true" aria-label={`Graded bets for ${selectedDay.day}`} ref={dialogRef}>
            <header className="smh-home-picks-dialog-head">
              <h2>Completed Bets â€” {selectedDay.day}</h2>
              <button type="button" ref={closeRef} onClick={closeDay} aria-label="Close historical picks">Close</button>
            </header>
            <div className="smh-home-picks-dialog-body">
              <p className="smh-home-subtle">Results recorded for this completed date. <a href="/the_picks.html">Open the full Picks page</a>.</p>
              <div className="smh-home-history-results">
                <table aria-label="Graded bets for selected date">
                  <thead><tr><th>League</th><th>Matchup</th><th>Pick</th><th>Result</th><th>Profit</th></tr></thead>
                  <tbody>
                    {selectedDay.rows.map((bet, index) => (
                      <tr key={`${bet.source}-${bet.game_date}-${index}`}>
                        <td>{bet.league}</td><td>{bet.matchup || "â€”"}</td>
                        <td>{bet.pick || bet.bet_side || "â€”"}</td>
                        <td>{bet.result}</td><td>{bet.profit_display || "â€”"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
