/*
  KellyCalculator - native React port of legacy kelly_calculator.html +
  assets/js/pages/{kelly_calculator.js, kelly_calculator.2.js} + assets/js/shared/league_nav.js.

  Legacy behaviors found and preserved:
   1. config.js is loaded first (window.REPO_CONFIG drives which feeds load and how rows are parsed).
   2. Date picker defaults to today (local); clearing it resets to today; every change reloads all picks.
   3. Load: for each of 12 feeds (CFB, NHL, MLB, MLB_LINEUPS, NBA, WNBA, MLS, EPL, LALIGA, LIGUE1, SERIEA, BUNDESLIGA)
      REPO_CONFIG selectFiles are tried in order (win/ paths from raw.githubusercontent.com docs, other paths from repo root,
      no-store); first OK response is parsed; disabled/missing feeds and any feed error give no picks.
   4. Rows: cfg.normalizeRow, cfg.expandRows, cfg.filterFn / leagueColumn match, game_date must equal the selected date.
   5. Per pick: odds (NBA-specific columns, else bet_odds_american / dk_odds_american / american_odds / take_odds),
      Kelly (direct columns, NBA columns, or computed from model probability), EV (same pattern); picks with no positive
      Kelly are dropped; side text via cfg.buildBetText or a generic label.
   6. UFC: 61 HEAD requests (+/- 30 days) find the nearest event CSV; event date (or "No event") shown in the UFC Event box
      ("Loading..." until found); event CSV picks (fighter vs opponent, moneyline, kelly, ev).
   7. League filter nav (from shared league_nav.js): All, Football / MLB / Basketball / Soccer dropdown groups, NHL, UFC;
      leagues marked false in KELLY_LEAGUE_AVAILABILITY (NFL, CFL, NBA, College Basketball) are disabled/dashed;
      group toggle opens one menu at a time; picking from a menu does not close it; clicking outside the groups or
      pressing Escape closes menus; a group is highlighted when one of its leagues is selected.
   8. Selecting a league shows only that league's section (All shows every section, including empty ones).
   9. Bankroll input (live recalculation on input) and Kelly fraction buttons (Full 1, Half 0.5, Quarter 0.25;
      aria-pressed mirrors the active button).
  10. Sizing: bet = bankroll x kelly x fraction x scale, where scale shrinks all bets so total Kelly of the visible picks
      never exceeds 100%; totals bar shows total picks, total to bet and % of bankroll (dashes when empty).
  11. Account preferences: GET https://api.sportsmodelhub.com/api/account/preferences/ with credentials; when authenticated,
      bankroll and Kelly fraction are applied and the view re-renders; the CSRF token is kept; fraction click and bankroll
      "change" POST the new value (credentials, X-CSRFToken, JSON) only when signed in.
  12. Display: "Loading picks..." until the first render; picks grouped per sport with PICK/PICKS count, "No picks for this
      date" / "No picks for upcoming event"; cards show market tag, odds, matchup + time, bet, EV, Kelly, bet amount or
      "enter bankroll".
  13. Not present in legacy: URL params, localStorage, auto-refresh (nav.js is loaded by SiteShell).
  Not ported: legacy processPicks() (defined but never called).
  Difference: text from CSV is now rendered as text (legacy inserted it as HTML).
*/
import { useEffect, useMemo, useRef, useState } from "react";
import "../../../app/frontend/src/assets/js/shared/config.js";
import "../../../app/frontend/src/assets/css/pages/kelly_calculator.css";
import {
  DASH,
  KELLY_LEAGUE_AVAILABILITY,
  MID,
  SPORTS,
  emptyPicks,
  fetchAccountPreferences,
  formatDollar,
  formatPct,
  loadKellyPicks,
  saveAccountPreferences,
  todayDateInputValue,
  toDateStr,
  type AllPicks,
} from "../lib/kellyCalculatorData";

const ARROW = String.fromCharCode(0x25be);

// CSS the legacy shared league_nav.js injected into the page (style id shared-league-nav-style).
const LEAGUE_NAV_CSS = `
#league-controls.shared-league-nav-host {
  display: flex !important;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
  position: relative;
  z-index: 20;
}

#league-controls .shared-league-nav-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

#league-controls .shared-league-nav-aux {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

#league-controls .control-group {
  position: relative;
  display: inline-flex;
  align-items: center;
}

#league-controls .league-pill,
#league-controls .group-pill,
#league-controls .submenu-pill {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 4px 12px;
  border: 1px solid var(--border-soft);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
  text-transform: uppercase;
  line-height: 1.2;
  white-space: nowrap;
}

#league-controls .league-pill:hover,
#league-controls .group-pill:hover,
#league-controls .submenu-pill:hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

#league-controls .league-pill.active,
#league-controls .group-pill.active,
#league-controls .submenu-pill.active {
  border-color: var(--accent-green);
  color: var(--accent-green);
  background: rgba(0,255,132,0.06);
}

#league-controls .group-pill::after {
  content: " ${ARROW}";
  color: var(--text-muted);
  font-size: 10px;
  letter-spacing: 0;
}

#league-controls .group-pill:hover::after,
#league-controls .group-pill.active::after {
  color: var(--accent-green);
}

#league-controls .control-group.open .group-pill {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
  background: rgba(0,191,255,0.04);
}

#league-controls .control-group.open .group-pill.active {
  border-color: var(--accent-green);
  color: var(--accent-green);
  background: rgba(0,255,132,0.06);
}

#league-controls .submenu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 190px;
  display: none;
  flex-direction: column;
  gap: 6px;
  padding: 8px;
  background: var(--background);
  border: 1px solid var(--border-soft);
  box-shadow: 0 18px 44px rgba(0,0,0,0.45);
  z-index: 50;
}

#league-controls .control-group.open .submenu {
  display: flex;
}

#league-controls .submenu-pill {
  width: 100%;
  text-align: left;
  background: var(--bg-card);
}

#league-controls .shared-league-unavailable {
  opacity: 0.38;
  cursor: not-allowed;
  border-style: dashed;
}

#league-controls .shared-league-unavailable:hover {
  border-color: var(--border-soft);
  color: var(--text-muted);
  background: transparent;
}

#league-controls .shared-group-unavailable {
  opacity: 0.62;
}

@media (max-width: 820px) {
  #league-controls.shared-league-nav-host {
    align-items: stretch;
  }

  #league-controls .shared-league-nav-main,
  #league-controls .shared-league-nav-aux {
    width: 100%;
  }

  #league-controls .control-group {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  #league-controls .league-pill,
  #league-controls .group-pill {
    width: 100%;
    text-align: left;
  }

  #league-controls .submenu {
    position: static;
    width: 100%;
    min-width: 0;
    margin-top: 6px;
    box-shadow: none;
    background: transparent;
  }

  #league-controls .submenu-pill {
    padding-left: 22px;
  }

  #league-controls .shared-league-nav-aux {
    margin-left: 0;
  }

  #league-controls .shared-league-nav-aux > * {
    width: 100%;
    margin-left: 0 !important;
  }
}
`;

const FRACTIONS = [
  { value: 1, label: "Full" },
  { value: 0.5, label: "Half" },
  { value: 0.25, label: "Quarter" },
];

type LeagueItem = { key: string; label: string };

const FOOTBALL: LeagueItem[] = [
  { key: "nfl", label: "NFL" },
  { key: "cfb", label: "College Football" },
  { key: "cfl", label: "CFL" },
];

const MLB: LeagueItem[] = [
  { key: "mlb", label: "MLB" },
  { key: "mlb_lineups", label: "MLB " + MID + " With Lineups" },
];

const BASKETBALL: LeagueItem[] = [
  { key: "nba", label: "NBA" },
  { key: "ncaam", label: "College Basketball" },
  { key: "wnba", label: "WNBA" },
];

const SOCCER: LeagueItem[] = [
  { key: "mls", label: "MLS" },
  { key: "epl", label: "EPL" },
  { key: "laliga", label: "La Liga" },
  { key: "ligue1", label: "Ligue 1" },
  { key: "seriea", label: "Serie A" },
  { key: "bundesliga", label: "Bundesliga" },
];

function isSupported(key: string): boolean {
  return KELLY_LEAGUE_AVAILABILITY[key] === true;
}

export default function KellyCalculator() {
  const [date, setDate] = useState(todayDateInputValue);
  const [fraction, setFraction] = useState(1);
  const [bankroll, setBankroll] = useState("");
  const [selectedLeague, setSelectedLeague] = useState("all");
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const [picks, setPicks] = useState<AllPicks>(emptyPicks);
  const [rendered, setRendered] = useState(false);
  const [ufcEvent, setUfcEvent] = useState("Loading...");

  const bankrollRef = useRef<HTMLInputElement | null>(null);
  const signedInRef = useRef(false);
  const csrfRef = useRef<string | null>(null);

  // Load all picks whenever the date changes; abort the previous load.
  useEffect(() => {
    const controller = new AbortController();

    loadKellyPicks(toDateStr(date), controller.signal, (text) => {
      if (!controller.signal.aborted) setUfcEvent(text);
    })
      .then((result) => {
        if (controller.signal.aborted) return;

        setPicks(result);
        setRendered(true);
      })
      .catch((error) => {
        if (!controller.signal.aborted) console.error(error);
      });

    return () => controller.abort();
  }, [date]);

  // Account preferences (bankroll + Kelly fraction) for signed-in users.
  useEffect(() => {
    const controller = new AbortController();

    fetchAccountPreferences(controller.signal).then((prefs) => {
      if (!prefs || controller.signal.aborted) return;

      signedInRef.current = true;
      csrfRef.current = prefs.csrfToken;

      if (prefs.bankroll !== null && prefs.bankroll !== undefined) {
        setBankroll(String(prefs.bankroll));
      }

      if (prefs.kelly_fraction !== null && prefs.kelly_fraction !== undefined) {
        const parsed = parseFloat(String(prefs.kelly_fraction));

        if (FRACTIONS.some((f) => f.value === parsed)) setFraction(parsed);
      }

      setRendered(true);
    });

    return () => controller.abort();
  }, []);

  const savePreferences = (patch: Record<string, unknown>) => {
    if (!signedInRef.current || !csrfRef.current) return;

    saveAccountPreferences(patch, csrfRef.current).then((nextToken) => {
      if (nextToken) csrfRef.current = nextToken;
    });
  };

  // Bankroll "change" (commit) event saves the value; "input" updates are handled by React state.
  useEffect(() => {
    const input = bankrollRef.current;

    if (!input) return;

    const onChange = () => {
      const value = input.value.trim();

      if (!signedInRef.current || !csrfRef.current) return;

      saveAccountPreferences({ bankroll: value === "" ? null : value }, csrfRef.current).then((nextToken) => {
        if (nextToken) csrfRef.current = nextToken;
      });
    };

    input.addEventListener("change", onChange);

    return () => input.removeEventListener("change", onChange);
  }, []);

  // Close league menus on outside click or Escape.
  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const target = event.target;

      if (!(target instanceof Element) || !target.closest("#league-controls .control-group")) {
        setOpenGroup(null);
      }
    };

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpenGroup(null);
    };

    document.addEventListener("click", onClick);
    document.addEventListener("keydown", onKey);

    return () => {
      document.removeEventListener("click", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  // ---- calculations (legacy render())
  const view = useMemo(() => {
    const bankrollValue = parseFloat(bankroll) || 0;
    const sports = selectedLeague === "all" ? SPORTS : SPORTS.filter((s) => s.key === selectedLeague);

    const allPicksList = sports.flatMap((s) => picks[s.key]);
    const totalKelly = allPicksList.reduce((sum, p) => sum + p.kelly * fraction, 0);
    const scale = totalKelly > 1.0 ? 1.0 / totalKelly : 1.0;

    let totalPicks = 0;
    let totalBet = 0;

    const sections = sports.map(({ key, label }) => {
      const list = picks[key];

      totalPicks += list.length;

      const cards = list.map((p) => {
        const betAmt = bankrollValue > 0 ? bankrollValue * p.kelly * fraction * scale : 0;

        totalBet += betAmt;

        return { p, betAmt };
      });

      return { key, label, cards };
    });

    return { bankrollValue, sections, totalPicks, totalBet };
  }, [bankroll, fraction, picks, selectedLeague]);

  const { bankrollValue, sections, totalPicks, totalBet } = view;

  const showTotals = rendered;
  const totalPicksText = showTotals ? String(totalPicks || DASH) : DASH;
  const totalBetText = showTotals && bankrollValue > 0 && totalBet > 0 ? formatDollar(totalBet) : DASH;
  const totalPctText = showTotals && bankrollValue > 0 && totalBet > 0 ? formatPct(totalBet / bankrollValue) : DASH;

  // ---- league nav helpers
  const leagueButton = (item: LeagueItem, asSubmenu: boolean) => {
    if (!isSupported(item.key)) {
      return (
        <button
          type="button"
          key={item.key}
          disabled
          className={"league-pill shared-league-unavailable" + (asSubmenu ? " submenu-pill" : "")}
          data-shared-league-key={item.key}
          title={item.label + " is not currently supported on this page."}
        >
          {item.label}
        </button>
      );
    }

    const active = selectedLeague === item.key;

    return (
      <button
        type="button"
        key={item.key}
        className={"league-pill shared-league-option" + (asSubmenu ? " submenu-pill" : "") + (active ? " active" : "")}
        data-league-key={item.key}
        onClick={() => setSelectedLeague(item.key)}
      >
        {item.label}
      </button>
    );
  };

  const group = (name: string, label: string, items: LeagueItem[]) => {
    const supported = items.filter((item) => isSupported(item.key)).length;
    const groupActive = items.some((item) => isSupported(item.key) && selectedLeague === item.key);

    return (
      <div
        key={name}
        className={
          "control-group" + (supported ? "" : " shared-group-unavailable") + (openGroup === name ? " open" : "")
        }
        data-group={name}
      >
        <button
          type="button"
          className={"group-pill" + (groupActive ? " active" : "")}
          data-group-toggle={name}
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setOpenGroup((current) => (current === name ? null : name));
          }}
        >
          {label}
        </button>

        <div className="submenu">{items.map((item) => leagueButton(item, true))}</div>
      </div>
    );
  };

  return (
    <>
      <style id="shared-league-nav-style">{LEAGUE_NAV_CSS}</style>

      <div className="picks-header">
        <h1 className="picks-title">KELLY CALCULATOR</h1>
      </div>

      <div
        className="league-filter-controls shared-league-nav-host"
        id="league-controls"
        data-shared-league-nav-ready="true"
      >
        <div className="shared-league-nav-main">
          <button
            type="button"
            className={"league-pill shared-league-option" + (selectedLeague === "all" ? " active" : "")}
            data-league-key="all"
            onClick={() => setSelectedLeague("all")}
          >
            All
          </button>

          {group("football", "Football", FOOTBALL)}

          {leagueButton({ key: "nhl", label: "NHL" }, false)}

          {group("mlb", "MLB", MLB)}

          {group("basketball", "Basketball", BASKETBALL)}

          {group("soccer", "Soccer", SOCCER)}

          {leagueButton({ key: "ufc", label: "UFC" }, false)}
        </div>
      </div>

      <div className="picks-controls">
        <div className="ctrl-group">
          <label className="ctrl-label" htmlFor="date-picker">
            Date
          </label>
          <input
            type="date"
            id="date-picker"
            value={date}
            onChange={(event) => setDate(event.target.value || todayDateInputValue())}
          />
        </div>

        <div className="ctrl-group">
          <span className="ctrl-label" id="kelly-ufc-event-label">
            UFC Event
          </span>
          <div id="kelly-ufc-event" role="status" aria-live="polite" aria-labelledby="kelly-ufc-event-label">
            {ufcEvent}
          </div>
        </div>

        <div className="ctrl-group">
          <label className="ctrl-label" htmlFor="bankroll">
            Bankroll
          </label>
          <div className="bankroll-wrap">
            <span className="dollar">$</span>
            <input
              type="number"
              id="bankroll"
              ref={bankrollRef}
              placeholder="10000"
              min="0"
              step="100"
              autoComplete="off"
              data-private="true"
              value={bankroll}
              onChange={(event) => setBankroll(event.target.value)}
            />
          </div>
        </div>

        <div className="ctrl-group">
          <span className="ctrl-label" id="kelly-fraction-label">
            Kelly Fraction
          </span>
          <div
            className="fraction-btns"
            role="group"
            aria-labelledby="kelly-fraction-label"
            data-a11y-enhanced="true"
          >
            {FRACTIONS.map((f) => (
              <button
                type="button"
                key={f.value}
                data-frac={String(f.value)}
                className={fraction === f.value ? "active" : undefined}
                aria-pressed={fraction === f.value ? "true" : "false"}
                onClick={() => {
                  setFraction(f.value);
                  savePreferences({ kelly_fraction: f.value });
                }}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="totals-bar">
        <div className="total-item">
          <span className="t-label">Total Picks</span>
          <div className="t-val" id="total-picks">
            {totalPicksText}
          </div>
        </div>
        <div className="total-item">
          <span className="t-label">Total to Bet</span>
          <div className="t-val" id="total-bet">
            {totalBetText}
          </div>
        </div>
        <div className="total-item">
          <span className="t-label">% of Bankroll</span>
          <div className="t-val" id="total-pct">
            {totalPctText}
          </div>
        </div>
      </div>

      <div className="picks-body" id="picks-container">
        {!rendered ? (
          <div className="loading-state">Loading picks...</div>
        ) : (
          sections.map(({ key, label, cards }) => (
            <div className="sport-section" key={key}>
              <div className="sport-section-header">
                <span className={"sport-section-title " + key}>{label}</span>
                <span className="pick-count">
                  {cards.length} PICK{cards.length !== 1 ? "S" : ""}
                </span>
              </div>

              {cards.length === 0 ? (
                <div className="no-picks">No picks{key === "ufc" ? " for upcoming event" : " for this date"}</div>
              ) : (
                <div className="picks-grid">
                  {cards.map(({ p, betAmt }, i) => (
                    <div className="pick-card" key={i}>
                      <div className="pick-card-top">
                        <span className={"pick-market-tag " + p.market_type}>{p.market_type.replace("_", " ")}</span>
                        <span className="pick-odds">{p.odds}</span>
                      </div>
                      <div className="pick-matchup">
                        {p.matchup}
                        {p.time ? " " + MID + " " + p.time : ""}
                      </div>
                      <div className="pick-bet">{String(p.side)}</div>
                      <div className="pick-footer">
                        <span className="pick-ev">EV {p.ev !== null ? formatPct(p.ev) : DASH}</span>
                        <span className="pick-kelly">K {formatPct(p.kelly)}</span>
                        {bankrollValue > 0 ? (
                          <span className="pick-amount">{formatDollar(betAmt)}</span>
                        ) : (
                          <span className="pick-amount zero">enter bankroll</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </>
  );
}
