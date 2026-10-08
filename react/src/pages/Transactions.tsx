import { useEffect, useMemo, useState, type MouseEvent as ReactMouseEvent } from "react";

import "../../../app/frontend/src/assets/css/pages/transactions.css";

type FilterType = "all" | "group" | "league";
type GroupKey = "football" | "basketball" | "soccer";
type TransactionTypeKey =
  | "signed"
  | "trade"
  | "il"
  | "reinstated"
  | "recalled"
  | "optioned"
  | "claimed"
  | "waived"
  | "released"
  | "other";

type SourceConfig = {
  key: string;
  label: string;
  group: string;
  sport: string;
  league: string;
};

type TransactionType = {
  key: TransactionTypeKey;
  label: string;
};

type TransactionRow = {
  league: string;
  label: string;
  group: string;
  date: string;
  team: string;
  teamName: string;
  desc: string;
  types: TransactionType[];
};

type EspnTransaction = {
  date?: string;
  description?: string;
  team?: {
    abbreviation?: string;
    displayName?: string;
    name?: string;
  };
};

type EspnTransactionsResponse = {
  transactions?: EspnTransaction[];
};

type StatusState = {
  text: string;
  className: string;
  dotClassName: string;
};

const SOURCES: readonly SourceConfig[] = [
  { key: "NHL", label: "NHL", group: "hockey", sport: "hockey", league: "nhl" },
  { key: "MLB", label: "MLB", group: "baseball", sport: "baseball", league: "mlb" },
  { key: "NBA", label: "NBA", group: "basketball", sport: "basketball", league: "nba" },
  {
    key: "NCAAM",
    label: "College Basketball",
    group: "basketball",
    sport: "basketball",
    league: "mens-college-basketball",
  },
  { key: "WNBA", label: "WNBA", group: "basketball", sport: "basketball", league: "wnba" },
  { key: "MLS", label: "MLS", group: "soccer", sport: "soccer", league: "usa.1" },
  { key: "EPL", label: "EPL", group: "soccer", sport: "soccer", league: "eng.1" },
  { key: "LALIGA", label: "La Liga", group: "soccer", sport: "soccer", league: "esp.1" },
  { key: "LIGUE1", label: "Ligue 1", group: "soccer", sport: "soccer", league: "fra.1" },
  { key: "SERIEA", label: "Serie A", group: "soccer", sport: "soccer", league: "ita.1" },
  {
    key: "BUNDESLIGA",
    label: "Bundesliga",
    group: "soccer",
    sport: "soccer",
    league: "ger.1",
  },
  { key: "UFC", label: "UFC", group: "mma", sport: "mma", league: "ufc" },
  { key: "NFL", label: "NFL", group: "football", sport: "football", league: "nfl" },
  {
    key: "CFB",
    label: "College Football",
    group: "football",
    sport: "football",
    league: "college-football",
  },
  { key: "CFL", label: "CFL", group: "football", sport: "football", league: "cfl" },
];

const GROUPS: Record<GroupKey, readonly string[]> = {
  football: ["NFL", "CFB", "CFL"],
  basketball: ["NBA", "NCAAM", "WNBA"],
  soccer: ["MLS", "EPL", "LALIGA", "LIGUE1", "SERIEA", "BUNDESLIGA"],
};

const PAGE_SIZE = 50;

function parseTxnDate(value: string) {
  if (!value) return null;

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function fmtDateHeading(value: string) {
  const date = parseTxnDate(value);
  if (!date) return "Unknown Date";

  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function dateGroupKey(value: string) {
  const date = parseTxnDate(value);
  if (!date) return "unknown";

  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

function transactionAgeDays(value: string) {
  const date = parseTxnDate(value);
  if (!date) return Number.POSITIVE_INFINITY;

  const now = new Date();
  const txnDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  return Math.floor((today.getTime() - txnDay.getTime()) / 86400000);
}

function classifyTransaction(description: string) {
  const text = String(description || "").toLowerCase();
  const matches: TransactionType[] = [];

  const add = (key: TransactionTypeKey, label: string, pattern: RegExp) => {
    if (pattern.test(text)) {
      matches.push({ key, label });
    }
  };

  add("trade", "Trade", /\btraded\b|\btrade\b/);
  add("signed", "Signed", /\bsigned\b|\bsigns\b|\bsigning\b/);
  add(
    "il",
    "Injured List",
    /\binjured list\b|\bdisabled list\b|\bplaced\b[^.]*\bil\b|\b15-day il\b|\b10-day il\b|\b60-day il\b/,
  );
  add(
    "released",
    "Released / DFA",
    /\bdesignated\b[^.]*\bassignment\b|\bdfa\b|\breleased\b/,
  );
  add("reinstated", "Reinstated", /\breinstated\b|\bactivated\b/);
  add("recalled", "Recalled", /\brecalled\b/);
  add("optioned", "Optioned", /\boptioned\b|\bassigned\b|\bassignment\b/);
  add("claimed", "Claimed", /\bclaimed\b/);
  add("waived", "Waived", /\bwaived\b|\bwaivers\b/);

  if (matches.length === 0) {
    matches.push({ key: "other", label: "Other" });
  }

  return matches;
}

function sourceLabel(key: string) {
  return SOURCES.find((source) => source.key === key)?.label ?? key;
}

async function fetchLeagueTransactions(
  source: SourceConfig,
  signal: AbortSignal,
): Promise<TransactionRow[]> {
  const url =
    "https://site.api.espn.com/apis/site/v2/sports/" +
    source.sport +
    "/" +
    source.league +
    "/transactions";

  try {
    const response = await fetch(url, {
      cache: "no-store",
      signal,
    });

    if (!response.ok) return [];

    const data = (await response.json()) as EspnTransactionsResponse;
    const transactions = data.transactions ?? [];

    return transactions.map((transaction) => ({
      league: source.key,
      label: source.label,
      group: source.group,
      date: transaction.date ?? "",
      team: transaction.team
        ? transaction.team.abbreviation || transaction.team.displayName || ""
        : "",
      teamName: transaction.team
        ? transaction.team.displayName ||
          transaction.team.name ||
          transaction.team.abbreviation ||
          ""
        : "",
      desc: transaction.description ?? "",
      types: classifyTransaction(transaction.description ?? ""),
    }));
  } catch (error) {
    if (signal.aborted) return [];

    console.warn(`${source.key} transactions failed:`, error);
    return [];
  }
}

export default function Transactions() {
  const [allTxns, setAllTxns] = useState<TransactionRow[]>([]);
  const [activeFilterType, setActiveFilterType] = useState<FilterType>("all");
  const [activeFilterValue, setActiveFilterValue] = useState("all");
  const [searchInput, setSearchInput] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [periodFilter, setPeriodFilter] = useState("7");
  const [visibleLimit, setVisibleLimit] = useState(PAGE_SIZE);
  const [openGroup, setOpenGroup] = useState<GroupKey | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [status, setStatus] = useState<StatusState>({
    text: "Loading...",
    className: "",
    dotClassName: "yellow",
  });

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;

    const loadAll = async () => {
      setStatus({
        text: "Fetching transactions...",
        className: "loading",
        dotClassName: "yellow",
      });
      setAllTxns([]);
      setLoaded(false);

      try {
        const results = await Promise.all(
          SOURCES.map((source) => fetchLeagueTransactions(source, controller.signal)),
        );

        if (!mounted || controller.signal.aborted) return;

        const rows = results.flat();
        setAllTxns(rows);
        setLoaded(true);

        if (rows.length === 0) {
          setStatus({
            text: "No transactions loaded",
            className: "",
            dotClassName: "",
          });
          return;
        }

        const updatedTime = new Date().toLocaleTimeString("en-US", {
          hour: "numeric",
          minute: "2-digit",
        });

        setStatus({
          text: `${rows.length} TRANSACTIONS LOADED Â· UPDATED ${updatedTime}`,
          className: "",
          dotClassName: "green",
        });
      } catch (error) {
        if (!mounted || controller.signal.aborted) return;

        console.error(error);
        setAllTxns([]);
        setLoaded(true);
        setStatus({
          text: "Error loading transactions",
          className: "error",
          dotClassName: "red",
        });
      }
    };

    void loadAll();

    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    const closeOnDocumentClick = (event: globalThis.MouseEvent) => {
      const target = event.target;

      if (!(target instanceof Element) || !target.closest(".control-group")) {
        setOpenGroup(null);
      }
    };

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpenGroup(null);
      }
    };

    document.addEventListener("click", closeOnDocumentClick);
    document.addEventListener("keydown", closeOnEscape);

    return () => {
      document.removeEventListener("click", closeOnDocumentClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  const applyFilter = (type: FilterType, value: string) => {
    setActiveFilterType(type);
    setActiveFilterValue(value);
    setVisibleLimit(PAGE_SIZE);
    setOpenGroup(null);
  };

  const filteredTransactions = useMemo(() => {
    let rows = allTxns.slice();

    if (activeFilterType === "league") {
      rows = rows.filter((row) => row.league === activeFilterValue);
    }

    if (activeFilterType === "group") {
      const allowed = GROUPS[activeFilterValue as GroupKey] ?? [];
      rows = rows.filter((row) => allowed.includes(row.league));
    }

    if (typeFilter !== "all") {
      rows = rows.filter((row) =>
        row.types.some((transactionType) => transactionType.key === typeFilter),
      );
    }

    rows = rows.filter((row) => {
      if (periodFilter === "all") return true;

      const ageDays = transactionAgeDays(row.date);

      if (!Number.isFinite(ageDays) || ageDays < 0) {
        return false;
      }

      if (periodFilter === "today") {
        return ageDays === 0;
      }

      const days = Number.parseInt(periodFilter, 10);
      if (!Number.isFinite(days)) return true;

      return ageDays <= days - 1;
    });

    const query = searchInput.trim().toLowerCase();

    if (query) {
      rows = rows.filter(
        (row) =>
          row.team.toLowerCase().includes(query) ||
          row.teamName.toLowerCase().includes(query) ||
          row.desc.toLowerCase().includes(query) ||
          row.label.toLowerCase().includes(query) ||
          row.types.some((transactionType) =>
            transactionType.label.toLowerCase().includes(query),
          ),
      );
    }

    rows.sort((a, b) => {
      const aTime = a.date ? new Date(a.date).getTime() : 0;
      const bTime = b.date ? new Date(b.date).getTime() : 0;
      return bTime - aTime;
    });

    return rows;
  }, [
    activeFilterType,
    activeFilterValue,
    allTxns,
    periodFilter,
    searchInput,
    typeFilter,
  ]);

  const shownTransactions = useMemo(
    () => filteredTransactions.slice(0, visibleLimit),
    [filteredTransactions, visibleLimit],
  );

  const displayedGroups = useMemo(() => {
    const groups: Array<{
      key: string;
      heading: string;
      rows: TransactionRow[];
    }> = [];

    for (const row of shownTransactions) {
      const key = dateGroupKey(row.date);
      const previous = groups[groups.length - 1];

      if (!previous || previous.key !== key) {
        groups.push({
          key,
          heading: fmtDateHeading(row.date),
          rows: [row],
        });
        continue;
      }

      previous.rows.push(row);
    }

    return groups;
  }, [shownTransactions]);

  const isGroupActive = (group: GroupKey) => {
    if (activeFilterType === "group") {
      return activeFilterValue === group;
    }

    if (activeFilterType === "league") {
      return GROUPS[group].includes(activeFilterValue);
    }

    return false;
  };

  const isLeagueActive = (league: string) =>
    activeFilterType === "league" && activeFilterValue === league;

  const toggleGroup = (event: ReactMouseEvent, group: GroupKey) => {
    event.stopPropagation();
    setOpenGroup((current) => (current === group ? null : group));
  };

  const selectFilter = (
    event: ReactMouseEvent,
    type: FilterType,
    value: string,
  ) => {
    event.stopPropagation();
    applyFilter(type, value);
  };

  const statusClassName = `status-bar ${status.className}`.trim();
  const statusDotClassName = `status-dot ${status.dotClassName}`.trim();

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Transactions</div>
          <div className="page-subtitle">
            All Â· Football Â· NHL Â· MLB Â· Basketball Â· Soccer Â· UFC
          </div>
        </div>
      </div>

      <div className="controls" id="league-controls">
        <button
          type="button"
          className={`league-pill ${activeFilterType === "all" ? "active" : ""}`.trim()}
          onClick={(event) => selectFilter(event, "all", "all")}
        >
          All
        </button>

        <div
          className={`control-group ${openGroup === "football" ? "open" : ""}`.trim()}
          data-group="football"
        >
          <button
            type="button"
            className={`group-pill ${isGroupActive("football") ? "active" : ""}`.trim()}
            onClick={(event) => toggleGroup(event, "football")}
          >
            Football
          </button>
          <div className="submenu">
            <button
              type="button"
              className={`submenu-pill ${
                activeFilterType === "group" && activeFilterValue === "football"
                  ? "active"
                  : ""
              }`.trim()}
              onClick={(event) => selectFilter(event, "group", "football")}
            >
              All Football
            </button>
            {[
              ["NFL", "NFL"],
              ["CFB", "College Football"],
              ["CFL", "CFL"],
            ].map(([league, label]) => (
              <button
                key={league}
                type="button"
                className={`submenu-pill ${isLeagueActive(league) ? "active" : ""}`.trim()}
                onClick={(event) => selectFilter(event, "league", league)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          className={`league-pill ${isLeagueActive("NHL") ? "active" : ""}`.trim()}
          onClick={(event) => selectFilter(event, "league", "NHL")}
        >
          NHL
        </button>

        <button
          type="button"
          className={`league-pill ${isLeagueActive("MLB") ? "active" : ""}`.trim()}
          onClick={(event) => selectFilter(event, "league", "MLB")}
        >
          MLB
        </button>

        <div
          className={`control-group ${openGroup === "basketball" ? "open" : ""}`.trim()}
          data-group="basketball"
        >
          <button
            type="button"
            className={`group-pill ${isGroupActive("basketball") ? "active" : ""}`.trim()}
            onClick={(event) => toggleGroup(event, "basketball")}
          >
            Basketball
          </button>
          <div className="submenu">
            <button
              type="button"
              className={`submenu-pill ${
                activeFilterType === "group" && activeFilterValue === "basketball"
                  ? "active"
                  : ""
              }`.trim()}
              onClick={(event) => selectFilter(event, "group", "basketball")}
            >
              All Basketball
            </button>
            {[
              ["NBA", "NBA"],
              ["NCAAM", "College Basketball"],
              ["WNBA", "WNBA"],
            ].map(([league, label]) => (
              <button
                key={league}
                type="button"
                className={`submenu-pill ${isLeagueActive(league) ? "active" : ""}`.trim()}
                onClick={(event) => selectFilter(event, "league", league)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div
          className={`control-group ${openGroup === "soccer" ? "open" : ""}`.trim()}
          data-group="soccer"
        >
          <button
            type="button"
            className={`group-pill ${isGroupActive("soccer") ? "active" : ""}`.trim()}
            onClick={(event) => toggleGroup(event, "soccer")}
          >
            Soccer
          </button>
          <div className="submenu">
            <button
              type="button"
              className={`submenu-pill ${
                activeFilterType === "group" && activeFilterValue === "soccer"
                  ? "active"
                  : ""
              }`.trim()}
              onClick={(event) => selectFilter(event, "group", "soccer")}
            >
              All Soccer
            </button>
            {[
              ["MLS", "MLS"],
              ["EPL", "EPL"],
              ["LALIGA", "La Liga"],
              ["LIGUE1", "Ligue 1"],
              ["SERIEA", "Serie A"],
              ["BUNDESLIGA", "Bundesliga"],
            ].map(([league, label]) => (
              <button
                key={league}
                type="button"
                className={`submenu-pill ${isLeagueActive(league) ? "active" : ""}`.trim()}
                onClick={(event) => selectFilter(event, "league", league)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          className={`league-pill ${isLeagueActive("UFC") ? "active" : ""}`.trim()}
          onClick={(event) => selectFilter(event, "league", "UFC")}
        >
          UFC
        </button>

        <input
          type="text"
          className="search-box"
          id="txn-search"
          placeholder="Search team or move..."
          value={searchInput}
          onChange={(event) => {
            setSearchInput(event.target.value);
            setVisibleLimit(PAGE_SIZE);
          }}
        />
      </div>

      <div className={statusClassName} id="txn-status">
        <span className={statusDotClassName} id="status-dot" />
        <span id="status-text">{status.text}</span>
      </div>

      <div className="filter-toolbar">
        <span className="toolbar-label">Type</span>
        <select
          className="toolbar-select"
          id="type-filter"
          value={typeFilter}
          onChange={(event) => {
            setTypeFilter(event.target.value);
            setVisibleLimit(PAGE_SIZE);
          }}
        >
          <option value="all">All</option>
          <option value="signed">Signed</option>
          <option value="trade">Trade</option>
          <option value="il">Injured List</option>
          <option value="reinstated">Activated / Reinstated</option>
          <option value="recalled">Recalled</option>
          <option value="optioned">Optioned / Assigned</option>
          <option value="claimed">Claimed</option>
          <option value="waived">Waived</option>
          <option value="released">Released / DFA</option>
          <option value="other">Other</option>
        </select>

        <span className="toolbar-label">Period</span>
        <select
          className="toolbar-select"
          id="period-filter"
          value={periodFilter}
          onChange={(event) => {
            setPeriodFilter(event.target.value);
            setVisibleLimit(PAGE_SIZE);
          }}
        >
          <option value="today">Today</option>
          <option value="3">Last 3 Days</option>
          <option value="7">Last 7 Days</option>
          <option value="30">Last 30 Days</option>
          <option value="all">All Loaded</option>
        </select>

        <span className="result-count" id="result-count">
          {loaded
            ? `Showing ${Math.min(
                shownTransactions.length,
                filteredTransactions.length,
              )} of ${filteredTransactions.length} matching transactions`
            : "â€”"}
        </span>
      </div>

      <div className="main">
        <div className="txn-feed" id="txn-feed">
          {displayedGroups.map((group) => (
            <section className="txn-date-group" key={group.key}>
              <div className="txn-date-heading">
                <span>{group.heading}</span>
                <span className="txn-date-count">{group.rows.length} shown</span>
              </div>

              <div>
                {group.rows.map((transaction, index) => {
                  const teamTitle = transaction.teamName || transaction.team || "";

                  return (
                    <div
                      className="txn-row"
                      key={`${transaction.league}-${transaction.date}-${transaction.team}-${transaction.desc}-${index}`}
                    >
                      <div className={`txn-league league-${transaction.league}`}>
                        {transaction.label || sourceLabel(transaction.league)}
                      </div>

                      <div className="txn-team" title={teamTitle}>
                        {transaction.team || "â€”"}
                      </div>

                      <div className="txn-types">
                        {transaction.types.map((transactionType) => (
                          <span
                            className={`txn-type type-${transactionType.key}`}
                            key={`${transactionType.key}-${transactionType.label}`}
                          >
                            {transactionType.label}
                          </span>
                        ))}
                      </div>

                      <div className="txn-desc">{transaction.desc || "â€”"}</div>
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </div>

        {loaded && filteredTransactions.length === 0 ? (
          <div className="empty-state" id="txn-empty">
            No transactions found
          </div>
        ) : null}

        {loaded && filteredTransactions.length > visibleLimit ? (
          <button
            type="button"
            className="load-more"
            id="load-more"
            style={{ display: "block" }}
            onClick={() => {
              setVisibleLimit((current) => current + PAGE_SIZE);
            }}
          >
            Load 50 More
          </button>
        ) : null}
      </div>
    </>
  );
}