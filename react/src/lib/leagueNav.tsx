/*
  Shared league selector (native React port of assets/js/shared/league_nav.js, used by Standings and Players).

  Legacy behaviors preserved:
   1. Order: All (only if the page has it), Football group, NHL, MLB, Basketball group, Soccer group, UFC.
   2. Groups: Football (NFL, College Football, CFL), Basketball (NBA, College Basketball, WNBA),
      Soccer (MLS, EPL, La Liga, Ligue 1, Serie A, Bundesliga).
   3. A league the page does not have is a disabled "not currently supported on this page" button;
      a group with no supported league is dimmed.
   4. Clicking a group toggle opens its submenu and closes the others; clicking outside the groups or pressing Escape closes menus.
      Choosing a league does not close the open submenu (same as legacy).
   5. A group toggle is highlighted when one of its leagues is active.
   6. Extra nodes (for example the Rankings pill) go in a right-aligned aux area.
  The host uses the id smh-league-controls (not league-controls) so the legacy league_nav.js, which nav.js can still
  load on a direct visit, never finds and rewrites this React-owned markup.
*/
import { useEffect, useState, type ReactNode } from "react";

type NavItem = { key: string; label: string };
type NavGroup = { key: string; label: string; leagues: NavItem[] };

const GROUPS: NavGroup[] = [
  {
    key: "football",
    label: "Football",
    leagues: [
      { key: "nfl", label: "NFL" },
      { key: "cfb", label: "College Football" },
      { key: "cfl", label: "CFL" },
    ],
  },
  {
    key: "basketball",
    label: "Basketball",
    leagues: [
      { key: "nba", label: "NBA" },
      { key: "ncaam", label: "College Basketball" },
      { key: "wnba", label: "WNBA" },
    ],
  },
  {
    key: "soccer",
    label: "Soccer",
    leagues: [
      { key: "mls", label: "MLS" },
      { key: "epl", label: "EPL" },
      { key: "laliga", label: "La Liga" },
      { key: "ligue1", label: "Ligue 1" },
      { key: "seriea", label: "Serie A" },
      { key: "bundesliga", label: "Bundesliga" },
    ],
  },
];

const NAV_CSS = `
      #smh-league-controls.shared-league-nav-host {
        display: flex !important;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        width: 100%;
        position: relative;
        z-index: 20;
      }

      #smh-league-controls .shared-league-nav-main {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }

      #smh-league-controls .shared-league-nav-aux {
        margin-left: auto;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }

      #smh-league-controls .control-group {
        position: relative;
        display: inline-flex;
        align-items: center;
      }

      #smh-league-controls .league-pill,
      #smh-league-controls .group-pill,
      #smh-league-controls .submenu-pill {
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

      #smh-league-controls .league-pill:hover,
      #smh-league-controls .group-pill:hover,
      #smh-league-controls .submenu-pill:hover {
        border-color: var(--accent-blue);
        color: var(--accent-blue);
      }

      #smh-league-controls .league-pill.active,
      #smh-league-controls .group-pill.active,
      #smh-league-controls .submenu-pill.active {
        border-color: var(--accent-green);
        color: var(--accent-green);
        background: rgba(0,255,132,0.06);
      }

      #smh-league-controls .group-pill::after {
        content: " \\25BE";
        color: var(--text-muted);
        font-size: 10px;
        letter-spacing: 0;
      }

      #smh-league-controls .group-pill:hover::after,
      #smh-league-controls .group-pill.active::after {
        color: var(--accent-green);
      }

      #smh-league-controls .control-group.open .group-pill {
        border-color: var(--accent-blue);
        color: var(--accent-blue);
        background: rgba(0,191,255,0.04);
      }

      #smh-league-controls .control-group.open .group-pill.active {
        border-color: var(--accent-green);
        color: var(--accent-green);
        background: rgba(0,255,132,0.06);
      }

      #smh-league-controls .submenu {
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

      #smh-league-controls .control-group.open .submenu {
        display: flex;
      }

      #smh-league-controls .submenu-pill {
        width: 100%;
        text-align: left;
        background: var(--bg-card);
      }

      #smh-league-controls .shared-league-unavailable {
        opacity: 0.38;
        cursor: not-allowed;
        border-style: dashed;
      }

      #smh-league-controls .shared-league-unavailable:hover {
        border-color: var(--border-soft);
        color: var(--text-muted);
        background: transparent;
      }

      #smh-league-controls .shared-group-unavailable {
        opacity: 0.62;
      }

      @media (max-width: 820px) {
        #smh-league-controls.shared-league-nav-host {
          align-items: stretch;
        }

        #smh-league-controls .shared-league-nav-main,
        #smh-league-controls .shared-league-nav-aux {
          width: 100%;
        }

        #smh-league-controls .control-group {
          width: 100%;
          flex-direction: column;
          align-items: stretch;
        }

        #smh-league-controls .league-pill,
        #smh-league-controls .group-pill {
          width: 100%;
          text-align: left;
        }

        #smh-league-controls .submenu {
          position: static;
          width: 100%;
          min-width: 0;
          margin-top: 6px;
          box-shadow: none;
          background: transparent;
        }

        #smh-league-controls .submenu-pill {
          padding-left: 22px;
        }

        #smh-league-controls .shared-league-nav-aux {
          margin-left: 0;
        }

        #smh-league-controls .shared-league-nav-aux > * {
          width: 100%;
          margin-left: 0 !important;
        }
      }
    `;

export type LeagueNavProps = {
  /** League keys that exist (are enabled) on the page. */
  present: string[];
  activeKey: string;
  onSelect: (key: string) => void;
  /** Element used for the league pills: Standings used div pills, Players used button pills. */
  pillAs: "div" | "button";
  /** Extra class names for the host element (Standings uses "controls"). */
  className?: string;
  /** Extra nodes shown in the right-aligned aux area. */
  aux?: ReactNode;
};

export default function LeagueNav({
  present,
  activeKey,
  onSelect,
  pillAs,
  className,
  aux,
}: LeagueNavProps) {
  const [openGroup, setOpenGroup] = useState<string | null>(null);

  useEffect(() => {
    const onDocClick = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (!target.closest("#smh-league-controls .control-group")) {
        setOpenGroup(null);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpenGroup(null);
    };
    document.addEventListener("click", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("click", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const has = (key: string) => present.indexOf(key) !== -1;

  const renderLeague = (item: NavItem, asSubmenu: boolean) => {
    if (!has(item.key)) {
      return (
        <button
          key={item.key}
          type="button"
          disabled
          className={
            "league-pill shared-league-unavailable" +
            (asSubmenu ? " submenu-pill" : "")
          }
          title={item.label + " is not currently supported on this page."}
        >
          {item.label}
        </button>
      );
    }

    const cls =
      "league-pill shared-league-option" +
      (asSubmenu ? " submenu-pill" : "") +
      (item.key === activeKey ? " active" : "");

    if (pillAs === "div") {
      return (
        <div
          key={item.key}
          className={cls}
          data-league={item.key}
          onClick={() => onSelect(item.key)}
        >
          {item.label}
        </div>
      );
    }

    return (
      <button
        key={item.key}
        type="button"
        className={cls}
        data-league={item.key}
        onClick={() => onSelect(item.key)}
      >
        {item.label}
      </button>
    );
  };

  const renderGroup = (group: NavGroup) => {
    const supported = group.leagues.filter((l) => has(l.key)).length;
    const groupActive = group.leagues.some(
      (l) => has(l.key) && l.key === activeKey
    );
    const isOpen = openGroup === group.key;

    return (
      <div
        key={group.key}
        className={
          "control-group" +
          (supported ? "" : " shared-group-unavailable") +
          (isOpen ? " open" : "")
        }
        data-group={group.key}
      >
        <button
          type="button"
          className={"group-pill" + (groupActive ? " active" : "")}
          data-group-toggle={group.key}
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setOpenGroup((cur) => (cur === group.key ? null : group.key));
          }}
        >
          {group.label}
        </button>
        <div className="submenu">
          {group.leagues.map((l) => renderLeague(l, true))}
        </div>
      </div>
    );
  };

  return (
    <>
      <style>{NAV_CSS}</style>
      <div
        id="smh-league-controls"
        className={"shared-league-nav-host" + (className ? " " + className : "")}
        data-shared-league-nav-ready="true"
      >
        <div className="shared-league-nav-main">
          {has("all") ? renderLeague({ key: "all", label: "All" }, false) : null}
          {renderGroup(GROUPS[0])}
          {renderLeague({ key: "nhl", label: "NHL" }, false)}
          {renderLeague({ key: "mlb", label: "MLB" }, false)}
          {renderGroup(GROUPS[1])}
          {renderGroup(GROUPS[2])}
          {renderLeague({ key: "ufc", label: "UFC" }, false)}
        </div>
        {aux ? <div className="shared-league-nav-aux">{aux}</div> : null}
      </div>
    </>
  );
}
