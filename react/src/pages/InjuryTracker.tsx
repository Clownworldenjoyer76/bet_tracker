/*
  InjuryTracker - native React port of legacy injury_tracker.html + assets/js/pages/injury_tracker.js.

  Legacy behaviors found and preserved:
   1. config.js is loaded first (sets window.REPO_CONFIG used to find and parse today's pick CSVs).
   2. Initial status bar: "Loading injury feeds and today's picks..." (loading style, yellow dot).
   3. Today's picks: for every league in REPO_CONFIG with selectFiles, first CSV that loads is used
      (win/ paths come from raw.githubusercontent.com, no-store); rows normalized via cfg.normalizeRow,
      expanded via cfg.expandRows, filtered by league column and by today's date, text via cfg.buildBetText
      or a generic fallback.
   4. League-wide ESPN injuries fetched in parallel for all 15 leagues (always on, no offseason toggles); failures skipped.
   5. Picked-team verification: today's ESPN scoreboards resolve each picked team, then each team's own ESPN
      injury report is fetched and merged in (deduplicated); status line reports teams verified and injuries added.
   6. Impact section: summary strip (picks, picked teams with injuries, Out, Questionable/Doubtful - deduplicated),
      impact cards per picked game with pick chips and away/home injury rows sorted by status
      (Out, Doubtful, Questionable, Day-To-Day only); empty messages for no picks / no matched injuries.
   7. League filter controls: All, group dropdowns (Football, Basketball, Soccer) with "All <group>" + league items,
      direct NHL / MLB / UFC pills; active highlighting (including parent group); picking a filter closes menus and
      resets the visible limit to 50.
   8. Group menu toggles open/closed; one menu open at a time; clicking outside the menu groups or pressing Escape closes menus.
   9. Search box (trimmed, case-insensitive on player, team, injury, league label); resets visible limit to 50.
  10. Status select (Out+Doubtful+Questionable default, Out Only, Questionable+Doubtful, Day-To-Day, All); resets limit to 50.
  11. Browser table sorted by status rank, league, team, player; "Showing X of Y matching injuries";
      "No injuries match these filters" when empty; "Load 50 More" button shown only when more rows exist.
  12. Final status: "N injuries loaded - N current picks cross-referenced - N picked teams verified -
      N fallback injuries added - YYYY-MM-DD" (green dot).
  13. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials (nav.js is loaded by SiteShell).
*/
import { useEffect, useMemo, useState } from "react";
import "../../../app/frontend/src/assets/js/shared/config.js";
import "../../../app/frontend/src/assets/css/pages/injury_tracker.css";
import {
  DASH,
  MID,
  PAGE_SIZE,
  buildImpactGroups,
  filteredBrowserRows,
  impactSummary,
  loadInjuryData,
  sourceGroup,
  statusClass,
  statusRank,
  todayDash,
  type ImpactGroup,
  type Injury,
  type InjuryData,
  type StatusMode,
} from "../lib/injuryTrackerData";

type FilterType = "all" | "group" | "league";

const GROUP_LABELS: Record<string, string> = {
  football: "Football",
  basketball: "Basketball",
  soccer: "Soccer",
};

const GROUP_ITEMS: Record<string, { value: string; label: string }[]> = {
  football: [
    { value: "NFL", label: "NFL" },
    { value: "CFB", label: "College Football" },
    { value: "CFL", label: "CFL" },
  ],
  basketball: [
    { value: "NBA", label: "NBA" },
    { value: "NCAAM", label: "College Basketball" },
    { value: "WNBA", label: "WNBA" },
  ],
  soccer: [
    { value: "MLS", label: "MLS" },
    { value: "EPL", label: "EPL" },
    { value: "LALIGA", label: "La Liga" },
    { value: "LIGUE1", label: "Ligue 1" },
    { value: "SERIEA", label: "Serie A" },
    { value: "BUNDESLIGA", label: "Bundesliga" },
  ],
};

const GROUP_ORDER_BEFORE_NHL = ["football"];
const GROUP_ORDER_AFTER_MLB = ["basketball", "soccer"];

function ImpactInjuryRows({ rows }: { rows: Injury[] }) {
  const sorted = rows.slice().sort((a, b) => statusRank(a.status) - statusRank(b.status));

  return (
    <>
      {sorted.map((row, i) => (
        <div className="impact-injury-row" key={i}>
          <span className={"status-badge " + statusClass(row.status)}>{row.status}</span>
          <span className="impact-player">{row.player}</span>
          <span>{row.position}</span>
          <span className="impact-injury-type">{row.injury}</span>
        </div>
      ))}
    </>
  );
}

function ImpactCard({ group }: { group: ImpactGroup }) {
  return (
    <article className="impact-card">
      <div className="impact-card-top">
        <div className="impact-matchup">
          {group.away_team || "Away"} @ {group.home_team || "Home"}
        </div>
        <div className="impact-league">
          {group.leagueLabel}
          {group.game_time ? " " + MID + " " + group.game_time : ""}
        </div>
      </div>

      <div className="impact-picks">
        {group.picks.map((pick, i) => (
          <span className="pick-chip" key={i}>
            {pick.text || "Pick"}
          </span>
        ))}
      </div>

      {group.awayInjuries.length > 0 && (
        <div className="impact-team">
          <div className="impact-team-name">{group.away_team}</div>
          <ImpactInjuryRows rows={group.awayInjuries} />
        </div>
      )}

      {group.homeInjuries.length > 0 && (
        <div className="impact-team">
          <div className="impact-team-name">{group.home_team}</div>
          <ImpactInjuryRows rows={group.homeInjuries} />
        </div>
      )}
    </article>
  );
}

export default function InjuryTracker() {
  const [data, setData] = useState<InjuryData | null>(null);

  const [activeFilterType, setActiveFilterType] = useState<FilterType>("all");
  const [activeFilterValue, setActiveFilterValue] = useState("all");
  const [openGroup, setOpenGroup] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [statusMode, setStatusMode] = useState<StatusMode>("impact");
  const [visibleLimit, setVisibleLimit] = useState(PAGE_SIZE);

  // Load all feeds once; abort on unmount.
  useEffect(() => {
    const controller = new AbortController();

    loadInjuryData(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setData(result);
      })
      .catch((error) => {
        if (!controller.signal.aborted) console.error(error);
      });

    return () => controller.abort();
  }, []);

  // Close menus on outside click or Escape.
  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const target = event.target;

      if (!(target instanceof Element) || !target.closest(".control-group")) {
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

  const impactGroups = useMemo(
    () => (data ? buildImpactGroups(data.todayPicks, data.allInjuries) : []),
    [data]
  );

  const summary = useMemo(() => impactSummary(impactGroups), [impactGroups]);

  const searchQuery = search.trim();

  const rows = useMemo(
    () =>
      data
        ? filteredBrowserRows(data.allInjuries, activeFilterType, activeFilterValue, statusMode, searchQuery)
        : [],
    [data, activeFilterType, activeFilterValue, statusMode, searchQuery]
  );

  const shown = rows.slice(0, visibleLimit);

  const applyLeagueFilter = (type: FilterType, value: string) => {
    setActiveFilterType(type);
    setActiveFilterValue(value);
    setVisibleLimit(PAGE_SIZE);
    setOpenGroup(null);
  };

  const toggleGroup = (name: string) => {
    setOpenGroup((current) => (current === name ? null : name));
  };

  // ---- active highlighting (same rules as legacy setActiveControls)
  const leagueActive = (value: string) => activeFilterType === "league" && activeFilterValue === value;

  const groupToggleActive = (name: string) =>
    (activeFilterType === "group" && activeFilterValue === name) ||
    (activeFilterType === "league" && sourceGroup(activeFilterValue) === name);

  const pillClass = (base: string, active: boolean) => base + (active ? " active" : "");

  const renderGroup = (name: string) => (
    <div className={"control-group" + (openGroup === name ? " open" : "")} data-group={name} key={name}>
      <button
        type="button"
        className={pillClass("group-pill", groupToggleActive(name))}
        data-group-toggle={name}
        onClick={(event) => {
          event.stopPropagation();
          toggleGroup(name);
        }}
      >
        {GROUP_LABELS[name]}
      </button>

      <div className="submenu">
        <button
          type="button"
          className={pillClass("submenu-pill", activeFilterType === "group" && activeFilterValue === name)}
          data-filter-type="group"
          data-filter-value={name}
          onClick={(event) => {
            event.stopPropagation();
            applyLeagueFilter("group", name);
          }}
        >
          {"All " + GROUP_LABELS[name]}
        </button>

        {GROUP_ITEMS[name].map((item) => (
          <button
            type="button"
            key={item.value}
            className={pillClass("submenu-pill", leagueActive(item.value))}
            data-filter-type="league"
            data-filter-value={item.value}
            onClick={(event) => {
              event.stopPropagation();
              applyLeagueFilter("league", item.value);
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );

  const leaguePill = (value: string) => (
    <button
      type="button"
      className={pillClass("league-pill", leagueActive(value))}
      data-filter-type="league"
      data-filter-value={value}
      onClick={(event) => {
        event.stopPropagation();
        applyLeagueFilter("league", value);
      }}
    >
      {value}
    </button>
  );

  // ---- status bar
  const loading = data === null;

  const statusText = data
    ? data.allInjuries.length +
      " injuries loaded " +
      MID +
      " " +
      data.todayPicks.length +
      " current picks cross-referenced " +
      MID +
      " " +
      data.pickedTeamsResolved +
      " picked teams verified " +
      MID +
      " " +
      data.pickedTeamInjuriesAdded +
      " fallback injuries added " +
      MID +
      " " +
      data.dateDash
    : "Loading injury feeds and today's picks...";

  // ---- impact empty message
  let impactEmpty = "";

  if (data) {
    if (!data.todayPicks.length) {
      impactEmpty = "No current picks were loaded for " + todayDash() + ".";
    } else if (!impactGroups.length) {
      impactEmpty = "No reported impact injuries were matched to teams in today's picked games.";
    }
  }

  return (
    <>
      <div className="page-header">
        <div className="page-title">Injury Impact Tracker</div>
        <div className="page-subtitle">
          {"TODAY'S PICKS FIRST " + MID + " IMPACT INJURIES " + MID + " FULL LEAGUE BROWSER"}
        </div>
      </div>

      <div className="controls" id="league-controls">
        <button
          type="button"
          className={pillClass("league-pill", activeFilterType === "all")}
          data-filter-type="all"
          data-filter-value="all"
          onClick={(event) => {
            event.stopPropagation();
            applyLeagueFilter("all", "all");
          }}
        >
          All
        </button>

        {GROUP_ORDER_BEFORE_NHL.map(renderGroup)}

        {leaguePill("NHL")}
        {leaguePill("MLB")}

        {GROUP_ORDER_AFTER_MLB.map(renderGroup)}

        {leaguePill("UFC")}

        <input
          type="text"
          className="search-box"
          id="inj-search"
          placeholder="Search player or team..."
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setVisibleLimit(PAGE_SIZE);
          }}
        />
      </div>

      <div className={"status-bar" + (loading ? " loading" : "")} id="inj-status">
        <span className={"status-dot " + (loading ? "yellow" : "green")} id="status-dot"></span>
        <span id="status-text">{statusText}</span>
      </div>

      <section className="impact-wrap">
        <div className="section-kicker">Priority</div>

        <div className="section-title">Injuries Affecting Today's Picks</div>

        <div className="section-copy">
          Only injuries from teams participating in games on today's Picks page are promoted here.
        </div>

        <div className="summary-strip">
          <div className="summary-item">
            <span className="summary-val val-green" id="sum-picks">
              {data ? data.todayPicks.length : DASH}
            </span>
            <span className="summary-lbl">Today's Picks</span>
          </div>

          <div className="summary-item">
            <span className="summary-val val-blue" id="sum-teams">
              {data ? summary.affectedTeams : DASH}
            </span>
            <span className="summary-lbl">Picked Teams With Injuries</span>
          </div>

          <div className="summary-item">
            <span className="summary-val val-red" id="sum-out">
              {data ? summary.out : DASH}
            </span>
            <span className="summary-lbl">Out</span>
          </div>

          <div className="summary-item">
            <span className="summary-val val-yellow" id="sum-questionable">
              {data ? summary.questionable : DASH}
            </span>
            <span className="summary-lbl">Questionable / Doubtful</span>
          </div>
        </div>

        <div className="impact-grid" id="impact-grid">
          {impactGroups.map((group, i) => (
            <ImpactCard group={group} key={i} />
          ))}
        </div>

        <div className="impact-empty" id="impact-empty" style={{ display: impactEmpty ? "" : "none" }}>
          {impactEmpty}
        </div>
      </section>

      <section className="browser-wrap">
        <div className="section-kicker">Reference</div>

        <div className="section-title">All League Injuries</div>

        <div className="section-copy">
          The full feed remains available without dumping every injury record onto the page at once.
        </div>

        <div className="browser-toolbar">
          <span className="toolbar-label">Status</span>

          <select
            className="status-select"
            id="status-filter"
            value={statusMode}
            onChange={(event) => {
              setStatusMode(event.target.value as StatusMode);
              setVisibleLimit(PAGE_SIZE);
            }}
          >
            <option value="impact">Out + Doubtful + Questionable</option>
            <option value="out">Out Only</option>
            <option value="questionable">Questionable + Doubtful</option>
            <option value="dtd">Day-To-Day</option>
            <option value="all">All Statuses</option>
          </select>

          <span className="result-count" id="result-count">
            {data ? "Showing " + shown.length + " of " + rows.length + " matching injuries" : DASH}
          </span>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>League</th>
                <th>Team</th>
                <th>Player</th>
                <th>Pos</th>
                <th>Status</th>
                <th>Injury</th>
              </tr>
            </thead>

            <tbody id="inj-tbody">
              {shown.map((row, i) => (
                <tr key={i}>
                  <td className="td-league">{row.leagueLabel}</td>
                  <td className="td-team">{row.team}</td>
                  <td className="td-player">{row.player}</td>
                  <td className="td-pos">{row.position}</td>
                  <td>
                    <span className={"status-badge " + statusClass(row.status)}>{row.status}</span>
                  </td>
                  <td className="td-injury">{row.injury}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="empty-state" id="inj-empty" style={{ display: data && !rows.length ? "" : "none" }}>
            No injuries match these filters
          </div>
        </div>

        <button
          type="button"
          className="load-more"
          id="load-more"
          style={{ display: rows.length > visibleLimit ? "block" : "none" }}
          onClick={() => setVisibleLimit((limit) => limit + PAGE_SIZE)}
        >
          Load 50 More
        </button>
      </section>
    </>
  );
}