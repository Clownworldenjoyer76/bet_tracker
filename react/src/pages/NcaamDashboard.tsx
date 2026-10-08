import { useMemo, useState } from "react";

import "../../../app/frontend/src/assets/css/generated/basketball-dashboard.css";

import allData from "../data/ncaam-dashboard.json";


type Row = Record<string, unknown>;

type Feed = Record<string, unknown>;

type AllData = Record<string, Record<string, Feed>>;

const data = allData as unknown as AllData;

const MARKET_ORDER = [
  "moneyline",
  "spread",
  "total",
];

const MARKET_LABELS: Record<string, string> = {
  moneyline: "Moneyline",
  spread: "Spread",
  total: "Total",
};

function labelize(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, char => char.toUpperCase());
}

function isRecord(value: unknown): value is Row {
  return Boolean(
    value &&
      typeof value === "object" &&
      !Array.isArray(value),
  );
}

function asRows(value: unknown): Row[] {
  if (!Array.isArray(value)) return [];

  return value.filter(isRecord);
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "";
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "";

    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, {
          maximumFractionDigits: 4,
        });
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function numericValue(value: unknown) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string") {
    const cleaned = value.replace(/[%,$]/g, "").trim();
    const parsed = Number(cleaned);

    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function valueClass(value: unknown) {
  const numeric = numericValue(value);

  if (numeric === null) return "";

  if (numeric > 0) return "pos";
  if (numeric < 0) return "neg";

  return "";
}

function Table({ rows }: { rows: Row[] }) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [ascending, setAscending] = useState(true);

  const columns = useMemo(() => {
    const keys: string[] = [];

    rows.forEach(row => {
      Object.keys(row).forEach(key => {
        if (!keys.includes(key)) {
          keys.push(key);
        }
      });
    });

    return keys;
  }, [rows]);

  const sortedRows = useMemo(() => {
    if (!sortKey) return rows;

    return [...rows].sort((a, b) => {
      const aNumeric = numericValue(a[sortKey]);
      const bNumeric = numericValue(b[sortKey]);

      let result = 0;

      if (
        aNumeric !== null &&
        bNumeric !== null
      ) {
        result = aNumeric - bNumeric;
      } else {
        result = String(a[sortKey] ?? "").localeCompare(
          String(b[sortKey] ?? ""),
        );
      }

      return ascending ? result : -result;
    });
  }, [rows, sortKey, ascending]);

  if (!rows.length) {
    return <div className="empty">No rows.</div>;
  }

  function changeSort(key: string) {
    if (sortKey === key) {
      setAscending(value => !value);
      return;
    }

    setSortKey(key);
    setAscending(true);
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map(column => (
              <th
                key={column}
                onClick={() => changeSort(column)}
              >
                {labelize(column)}
                {sortKey === column && (
                  <span className="sort-arrow">
                    {ascending ? " ▲" : " ▼"}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {sortedRows.map((row, index) => (
            <tr key={index}>
              {columns.map(column => (
                <td
                  key={column}
                  className={valueClass(row[column])}
                >
                  {formatValue(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Kpis({ data }: { data: unknown }) {
  if (!isRecord(data)) return null;

  const entries = Object.entries(data).filter(
    ([, value]) =>
      value !== null &&
      typeof value !== "object",
  );

  if (!entries.length) return null;

  return (
    <section className="kpis" id="headline">
      {entries.map(([key, value]) => (
        <div className="kpi" key={key}>
          <div className="kpi-label">
            {labelize(key)}
          </div>
          <div
            className={`kpi-value ${valueClass(value)}`}
          >
            {formatValue(value)}
          </div>
        </div>
      ))}
    </section>
  );
}

function ObjectTables({
  data,
}: {
  data: unknown;
}) {
  if (!isRecord(data)) {
    return null;
  }

  const tables = Object.entries(data).filter(
    ([, value]) => Array.isArray(value),
  );

  if (!tables.length) {
    return null;
  }

  return (
    <>
      {tables.map(([key, value]) => (
        <section key={key}>
          <h2>{labelize(key)}</h2>
          <Table rows={asRows(value)} />
        </section>
      ))}
    </>
  );
}

function FeedContent({ feed }: { feed: Feed }) {
  const [activeTab, setActiveTab] =
    useState("overview");

  const marketTabs = MARKET_ORDER.filter(
    key => isRecord(feed[key]),
  );

  const tabs = [
    "overview",
    ...marketTabs,
  ];

  const activeMarket =
    activeTab !== "overview"
      ? feed[activeTab]
      : null;

  return (
    <>
      <Kpis data={feed.grand_total} />

      <div id="report-tabs">
        <div className="tabs">
          {tabs.map(tab => (
            <button
              key={tab}
              type="button"
              className={`tab ${
                activeTab === tab ? "active" : ""
              }`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === "overview"
                ? "Overview"
                : MARKET_LABELS[tab] ?? labelize(tab)}
            </button>
          ))}
        </div>

        <div className="tab-body">
          {activeTab === "overview" ? (
            <>
              <ObjectTables data={feed} />

              {!Array.isArray(feed.by_market_summary) &&
                !Array.isArray(feed.quality) && (
                  <div className="empty">
                    No rows.
                  </div>
                )}
            </>
          ) : (
            <ObjectTables data={activeMarket} />
          )}
        </div>
      </div>
    </>
  );
}

export default function NbaDashboard() {
  const seasons = Object.keys(data);

  const [season, setSeason] = useState(() => {
    try {
      const stored = localStorage.getItem(
        "basketball_dash_season",
      );

      if (stored && data[stored]) {
        return stored;
      }
    } catch {}

    return data.current
      ? "current"
      : seasons[0] ?? "";
  });

  const leagues = Object.keys(
    data[season]?.leagues ?? {},
  );

  const [league, setLeague] = useState(() => {
    try {
      const stored = localStorage.getItem(
        "basketball_dash_league",
      );

      if (
        stored &&
        data[season]?.leagues &&
        data[season]?.leagues[stored]
      ) {
        return stored;
      }
    } catch {}

    return leagues.includes("nba")
      ? "nba"
      : leagues[0] ?? "";
  });

  const activeLeague: Feed = (data[season]?.leagues?.[league] ?? data[season]?.leagues?.nba ?? {}) as Feed;

  function changeSeason(value: string) {
    setSeason(value);

    const nextLeagues = Object.keys(
      data[value]?.leagues ?? {},
    );

    const nextLeague = nextLeagues.includes("nba")
      ? "nba"
      : nextLeagues[0] ?? "";

    setLeague(nextLeague);

    try {
      localStorage.setItem(
        "basketball_dash_season",
        value,
      );
      localStorage.setItem(
        "basketball_dash_league",
        nextLeague,
      );
    } catch {}
  }

  function changeLeague(value: string) {
    setLeague(value);

    try {
      localStorage.setItem(
        "basketball_dash_league",
        value,
      );
    } catch {}
  }

  return (
    <>
      <header>
        <h1>NCAAM Dashboard</h1>
        <span className="ts">
          React migration
        </span>
      </header>

      <div className="feed-bar">
        <span className="lbl">Season:</span>

        <select
          value={season}
          onChange={event =>
            changeSeason(event.target.value)
          }
        >
          {seasons.map(value => (
            <option key={value} value={value}>
              {labelize(value)}
            </option>
          ))}
        </select>

        <span className="lbl">League:</span>

        <select
          value={league}
          onChange={event =>
            changeLeague(event.target.value)
          }
        >
          {leagues.map(value => (
            <option key={value} value={value}>
              {value.toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      <FeedContent feed={activeLeague} />
    </>
  );
}







