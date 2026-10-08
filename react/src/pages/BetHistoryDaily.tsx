/*
  BetHistoryDaily - native React port of legacy bet_history_daily.html +
  assets/js/bet-history/{config,sources,csv,normalize}.js + assets/js/pages/index.js
  (the public/ copies, which are the ones the page loaded via /assets/js/...).

  Legacy behaviors found and preserved:
   1. Six completed-bet CSV sources (MLB, MLB_LINEUPS, WNBA, NHL, SOCCER, UFC) from relative history-data/{name}.csv;
      sources with enabled === false are skipped; each URL fetched with a plain fetch; a failed fetch logs a console.warn
      and gives no rows. The source resolver still supports urls[], url, indexUrl + indexItemToUrl and datePattern forms.
   2. CSV parsing (quotes, escaped quotes, CRLF/LF, lower-cased trimmed headers) and row normalisation
      (league, market, line, odds, model probability, matchup, pick text, profit units, result win/loss/push/unknown).
   3. Source-specific row preparation: MLB_LINEUPS rows get league "MLB_LINEUPS"; UFC rows are mapped to the picked fighter
      (fighter_1 / fighter_2 columns) as a moneyline bet.
   4. Only win / loss / push rows are kept ("graded").
   5. Summary strip: Completed Bets, W-L-P Record, Win Rate, Avg Model Prob, Profit / Loss (N/A when not computable;
      win rate coloured green >= 55%, red < 45%, yellow otherwise, applied to record and win rate; model prob always blue;
      profit green when >= 0, red when negative).
   6. History grid: rows grouped by game date, newest 30 dates, one card per day with long date, bet count, W-L-P record,
      win rate and profit / loss (same colour rules). Empty result: "No completed bet history available".
   7. Status line: "Loading completed bet history..." initially, then "Loading completed bets from all enabled sports and
      markets..."; on success green "N completed bets loaded across all enabled sports and markets."; no enabled sources:
      red "No completed-bet sources are enabled."; load failure: red "Completed bet history failed to load." (summary and
      history are shown empty in both cases).
   8. Page wrapper div.history-react-page and the history-react-fix.css import are kept as in the old wrapper.
   9. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials (nav.js is loaded by SiteShell).
  Not used: the app/ copy of sources.js (different content: GitHub raw URLs); the old wrapper loaded /assets/js/bet-history/sources.js,
  i.e. the public copy. config.js globals (REPO, BRANCH, BASE) are not used by the public sources and are not ported.
  Difference: no replaceAll - split/join is used (same result).
*/
import { useEffect, useMemo, useState } from "react";
import "../../../app/frontend/src/assets/css/pages/index.css";
import "./history-react-fix.css";
import {
  buildDayCards,
  formatDateLong,
  loadCompletedBets,
  summarize,
  type NormalizedRow,
} from "../lib/betHistoryDailyData";

function valClass(base: string, extra: string) {
  return extra ? base + " " + extra : base;
}

export default function BetHistoryDaily() {
  const [graded, setGraded] = useState<NormalizedRow[] | null>(null);
  const [statusText, setStatusText] = useState("Loading completed bet history...");
  const [statusState, setStatusState] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    const run = async () => {
      setStatusText("Loading completed bets from all enabled sports and markets...");
      setStatusState("");

      const outcome = await loadCompletedBets(controller.signal);

      if (controller.signal.aborted) return;

      if (outcome.kind === "no-sources") {
        setGraded([]);
        setStatusText("No completed-bet sources are enabled.");
        setStatusState("red");
      } else if (outcome.kind === "failed") {
        setGraded([]);
        setStatusText("Completed bet history failed to load.");
        setStatusState("red");
      } else {
        setGraded(outcome.graded);
        setStatusText(
          outcome.graded.length.toLocaleString() +
            " completed bets loaded across all enabled sports and markets."
        );
        setStatusState("green");
      }
    };

    run();

    return () => controller.abort();
  }, []);

  const summary = useMemo(() => (graded ? summarize(graded) : null), [graded]);
  const dayCards = useMemo(() => (graded ? buildDayCards(graded) : null), [graded]);

  return (
    <div className="history-react-page">
      <main className="main">
        <section className="summary-strip" aria-label="Overall completed bet performance">
          <div className="summary-item">
            <div className={valClass("summary-val", "")} id="summary-completed">
              {summary ? summary.completed : "N/A"}
            </div>
            <div className="summary-lbl">Completed Bets</div>
          </div>

          <div className="summary-item">
            <div className={valClass("summary-val", summary ? summary.recordClass : "")} id="summary-record">
              {summary ? summary.record : "N/A"}
            </div>
            <div className="summary-lbl">W-L-P Record</div>
          </div>

          <div className="summary-item">
            <div className={valClass("summary-val", summary ? summary.winRateClass : "")} id="summary-win-rate">
              {summary ? summary.winRate : "N/A"}
            </div>
            <div className="summary-lbl">Win Rate</div>
          </div>

          <div className="summary-item">
            <div className="summary-val val-blue" id="summary-model-prob">
              {summary ? summary.modelProb : "N/A"}
            </div>
            <div className="summary-lbl">Avg Model Prob</div>
          </div>

          <div className="summary-item">
            <div className={valClass("summary-val", summary ? summary.profitClass : "")} id="summary-profit">
              {summary ? summary.profit : "N/A"}
            </div>
            <div className="summary-lbl">Profit / Loss</div>
          </div>
        </section>

        <section className="section">
          <div className="section-header">
            <div className="section-title">Completed Bet History</div>
            <div className="section-note">Last 30 completed dates, all sports, all markets</div>
          </div>

          <div className="status-line">
            <span className={valClass("status-dot", statusState)} id="status-dot" />
            <span id="status-text">{statusText}</span>
          </div>

          <div className="history-grid" id="history-grid">
            {dayCards === null ? (
              <div className="empty-state">Loading completed bet history...</div>
            ) : dayCards.length === 0 ? (
              <div className="empty-state">No completed bet history available</div>
            ) : (
              dayCards.map((card) => (
                <article className="day-card" key={card.date}>
                  <div className="date-label">Date</div>
                  <div className="date-value">{formatDateLong(card.date)}</div>
                  <div className="day-stats">
                    <div className="day-stat">
                      <div className="day-stat-label">Bets For That Day</div>
                      <div className="day-stat-value">{card.count}</div>
                    </div>
                    <div className="day-stat">
                      <div className="day-stat-label">W-L-P Record</div>
                      <div className={valClass("day-stat-value", card.recordClass)}>{card.record}</div>
                    </div>
                    <div className="day-stat">
                      <div className="day-stat-label">Win Rate</div>
                      <div className={valClass("day-stat-value", card.rateClass)}>{card.rateText}</div>
                    </div>
                    <div className="day-stat">
                      <div className="day-stat-label">Profit / Loss</div>
                      <div className={valClass("day-stat-value", card.profitClass)}>{card.profitText}</div>
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
