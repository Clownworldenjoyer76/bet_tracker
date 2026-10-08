import { useEffect, useMemo, useState } from "react";
import dashboardData from "../data/baseball-dashboard.json";

type Cell = string | number | null | undefined;
type Row = Record<string, Cell>;

type MarketData = {
  by?: Record<string, Row[]>;
  by_side?: Record<string, Row[]>;
};

type FeedData = {
  feed?: string;
  label?: string;
  headline?: Row;
  by_market_summary?: Row[];
  markets?: Record<string, MarketData>;
  overview?: Record<string, Row[]>;
};

const ALL_DATA =
  dashboardData as unknown as Record<string, FeedData>;

type Column = {
  key: string;
  label: string;
  fmt?: "int" | "pct" | "num" | "text";
  decimals?: number;
  color?: boolean;
};

const METRIC_COLUMNS: Column[] = [
  { key: "variable", label: "Bucket" },
  { key: "Win", label: "W", fmt: "int" },
  { key: "Loss", label: "L", fmt: "int" },
  { key: "Push", label: "P", fmt: "int" },
  { key: "Total", label: "Total", fmt: "int" },
  { key: "Win_Pct", label: "Win %", fmt: "pct" },
  { key: "units", label: "Units", fmt: "num", decimals: 2, color: true },
  {
    key: "ROI_Excluding_Pushes",
    label: "ROI excl. pushes",
    fmt: "pct",
    color: true,
  },
  {
    key: "ROI_Including_Pushes",
    label: "ROI incl. pushes",
    fmt: "pct",
    color: true,
  },
  { key: "avg_ev", label: "Avg EV", fmt: "pct" },
  { key: "avg_odds", label: "Avg odds", fmt: "num", decimals: 0 },
];

const METRIC_SIDE_COLUMNS: Column[] = [
  { key: "side_group", label: "Side" },
  ...METRIC_COLUMNS,
];

const OVERVIEW_COLUMNS: Column[] = [
  { key: "Win", label: "W", fmt: "int" },
  { key: "Loss", label: "L", fmt: "int" },
  { key: "Push", label: "P", fmt: "int" },
  { key: "Total", label: "Total", fmt: "int" },
  { key: "Win_Pct", label: "Win %", fmt: "pct" },
  { key: "units", label: "Units", fmt: "num", decimals: 2, color: true },
  {
    key: "ROI_Excluding_Pushes",
    label: "ROI excl. pushes",
    fmt: "pct",
    color: true,
  },
  {
    key: "ROI_Including_Pushes",
    label: "ROI incl. pushes",
    fmt: "pct",
    color: true,
  },
  { key: "avg_ev", label: "Avg EV", fmt: "pct" },
  { key: "avg_odds", label: "Avg odds", fmt: "num", decimals: 0 },
];

function numberValue(value: Cell): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function fmtPct(value: Cell): string {
  const number = numberValue(value);
  return number === null ? "" : `${(number * 100).toFixed(2)}%`;
}

function fmtNum(value: Cell, decimals = 2): string {
  const number = numberValue(value);
  return number === null ? "" : number.toFixed(decimals);
}

function fmtInt(value: Cell): string {
  const number = numberValue(value);
  return number === null ? "" : number.toLocaleString();
}

function signedClass(value: Cell): string {
  const number = numberValue(value);

  if (number === null) return "";
  if (number > 0) return "pos";
  if (number < 0) return "neg";

  return "";
}

function winPctClass(value: Cell): string {
  const number = numberValue(value);

  if (number === null) return "";
  if (number >= 0.8) return "win-pct-strong";
  if (number >= 0.7) return "win-pct-green";
  if (number >= 0.6) return "win-pct-light";
  if (number >= 0.5) return "win-pct-neutral";

  return "win-pct-red";
}

function displayValue(
  value: Cell,
  column: Column,
): string {
  if (column.fmt === "int") {
    return fmtInt(value);
  }

  if (column.fmt === "pct") {
    return fmtPct(value);
  }

  if (column.fmt === "num") {
    return fmtNum(value, column.decimals ?? 2);
  }

  return value === null || value === undefined
    ? ""
    : String(value);
}

function DashboardTable({
  data,
  columns,
}: {
  data: Row[];
  columns: Column[];
}) {
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const rows = useMemo(() => {
    const result = [...data];

    if (!sortCol) return result;

    result.sort((a, b) => {
      const av = a[sortCol];
      const bv = b[sortCol];

      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;

      const an = numberValue(av);
      const bn = numberValue(bv);

      if (an !== null && bn !== null) {
        return sortDir === "asc" ? an - bn : bn - an;
      }

      const comparison = String(av).localeCompare(String(bv));

      return sortDir === "asc"
        ? comparison
        : -comparison;
    });

    return result;
  }, [data, sortCol, sortDir]);

  if (!data.length) {
    return <div className="muted">No rows.</div>;
  }

  const handleSort = (key: string) => {
    if (sortCol === key) {
      setSortDir((value) =>
        value === "asc" ? "desc" : "asc",
      );
      return;
    }

    setSortCol(key);
    setSortDir("desc");
  };

  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={
                  sortCol === column.key ? "sorted" : ""
                }
                onClick={() => handleSort(column.key)}
              >
                {column.label}
                {" "}
                <span className="arrow">▼</span>
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column) => {
                const value = row[column.key];

                let className = "";

                if (column.fmt === "pct" &&
                    column.key === "Win_Pct") {
                  className = winPctClass(value);
                } else if (column.color) {
                  className = signedClass(value);
                }

                return (
                  <td
                    key={column.key}
                    className={[
                      column.fmt === "int" ||
                      column.fmt === "pct" ||
                      column.fmt === "num"
                        ? "num"
                        : "",
                      className,
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  >
                    {displayValue(value, column)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Kpi({
  label,
  value,
  format,
}: {
  label: string;
  value: Cell;
  format: "pct" | "int" | "signed" | "num";
}) {
  let display = "N/A";

  if (
    value !== null &&
    value !== undefined &&
    value !== ""
  ) {
    if (format === "pct") display = fmtPct(value);
    if (format === "int") display = fmtInt(value);
    if (format === "num") display = fmtNum(value);
    if (format === "signed") {
      const number = numberValue(value);
      display =
        number === null
          ? "N/A"
          : `${number >= 0 ? "+" : ""}${number.toFixed(2)}`;
    }
  }

  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div
        className={`value ${
          format === "signed" ? signedClass(value) : ""
        }`}
      >
        {display}
      </div>
    </div>
  );
}

function FeedSection({
  data,
}: {
  data: FeedData;
}) {
  const [marketTab, setMarketTab] = useState("moneyline");
  const [overviewTab, setOverviewTab] =
    useState("market");

  const [dimensions, setDimensions] =
    useState<Record<string, string>>({});

  const [views, setViews] =
    useState<Record<string, "overall" | "side">>({});

  const markets = data.markets ?? {};

  const marketData = markets[marketTab] ?? {
    by: {},
    by_side: {},
  };

  const dims = Object.keys(marketData.by ?? {});

  const selectedDimension =
    dimensions[marketTab] ?? dims[0] ?? "";

  const selectedView =
    views[marketTab] ?? "overall";

  const rows =
    selectedView === "side"
      ? marketData.by_side?.[selectedDimension] ?? []
      : marketData.by?.[selectedDimension] ?? [];

  const overview = data.overview ?? {};

  return (
    <section
      className="feed-section active"
      data-feed={data.feed}
    >
      <h2>{data.label ?? data.feed}</h2>

      <div className="kpis">
        <Kpi
          label="Bets"
          value={data.headline?.Total}
          format="int"
        />
        <Kpi
          label="Wins"
          value={data.headline?.Win}
          format="int"
        />
        <Kpi
          label="Losses"
          value={data.headline?.Loss}
          format="int"
        />
        <Kpi
          label="Pushes"
          value={data.headline?.Push}
          format="int"
        />
        <Kpi
          label="Win %"
          value={data.headline?.Win_Pct}
          format="pct"
        />
        <Kpi
          label="Units"
          value={data.headline?.units}
          format="signed"
        />
        <Kpi
          label="ROI excl. pushes"
          value={data.headline?.ROI_Excluding_Pushes}
          format="pct"
        />
        <Kpi
          label="ROI incl. pushes"
          value={data.headline?.ROI_Including_Pushes}
          format="pct"
        />
        <Kpi
          label="Avg EV"
          value={data.headline?.avg_ev}
          format="pct"
        />
        <Kpi
          label="Avg odds"
          value={data.headline?.avg_odds}
          format="num"
        />
      </div>

      <DashboardTable
        data={data.by_market_summary ?? []}
        columns={[
          { key: "market_type", label: "Market" },
          ...OVERVIEW_COLUMNS,
        ]}
      />

      <h2>Market Analysis</h2>

      <div className="market-area">
        <div className="tabs">
          {["moneyline", "run_line", "total"].map((key) => (
            <div
              key={key}
              className={`tab ${
                marketTab === key ? "active" : ""
              }`}
              onClick={() => setMarketTab(key)}
            >
              {key === "run_line"
                ? "Run Line"
                : key === "moneyline"
                  ? "Moneyline"
                  : "Total"}
            </div>
          ))}
        </div>

        <div className="tab-body">
          <div className="tab-panel">
            <div className="controls">
              <label>
                Dimension:{" "}
                <select
                  className="dim-select"
                  value={selectedDimension}
                  onChange={(event) =>
                    setDimensions((current) => ({
                      ...current,
                      [marketTab]: event.target.value,
                    }))
                  }
                >
                  {dims.map((dimension) => (
                    <option
                      key={dimension}
                      value={dimension}
                    >
                      {dimension.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                View:{" "}
                <select
                  className="view-select"
                  value={selectedView}
                  onChange={(event) =>
                    setViews((current) => ({
                      ...current,
                      [marketTab]:
                        event.target.value as
                          | "overall"
                          | "side",
                    }))
                  }
                >
                  <option value="overall">
                    Overall
                  </option>
                  <option value="side">
                    Split by side
                  </option>
                </select>
              </label>
            </div>

            <div className="market-table">
              <DashboardTable
                data={rows}
                columns={
                  selectedView === "side"
                    ? METRIC_SIDE_COLUMNS
                    : METRIC_COLUMNS
                }
              />
            </div>
          </div>
        </div>
      </div>

      <h2>Overview</h2>

      <div className="overview-area">
        <div className="tabs">
          {[
            ["market", "By market"],
            ["side", "By side"],
            ["date", "By date"],
            ["day_night", "Day / night"],
            ["confidence", "Low confidence"],
          ].map(([key, label]) => (
            <div
              key={key}
              className={`tab ${
                overviewTab === key ? "active" : ""
              }`}
              onClick={() => setOverviewTab(key)}
            >
              {label}
            </div>
          ))}
        </div>

        <div className="tab-body">
          {overviewTab === "market" && (
            <DashboardTable
              data={overview.by_market ?? []}
              columns={[
                { key: "variable", label: "Market" },
                ...OVERVIEW_COLUMNS,
              ]}
            />
          )}

          {overviewTab === "side" && (
            <DashboardTable
              data={overview.by_side_group ?? []}
              columns={[
                { key: "variable", label: "Side" },
                ...OVERVIEW_COLUMNS,
              ]}
            />
          )}

          {overviewTab === "date" && (
            <DashboardTable
              data={overview.by_date ?? []}
              columns={[
                { key: "variable", label: "Date" },
                ...OVERVIEW_COLUMNS,
                {
                  key: "cumulative_units",
                  label: "Cumulative units",
                  fmt: "num",
                  decimals: 2,
                  color: true,
                },
              ]}
            />
          )}

          {overviewTab === "day_night" && (
            <DashboardTable
              data={overview.by_day_night ?? []}
              columns={[
                { key: "variable", label: "Day / Night" },
                ...OVERVIEW_COLUMNS,
              ]}
            />
          )}

          {overviewTab === "confidence" && (
            <DashboardTable
              data={overview.by_low_confidence ?? []}
              columns={[
                { key: "variable", label: "Low confidence" },
                ...OVERVIEW_COLUMNS,
              ]}
            />
          )}
        </div>
      </div>
    </section>
  );
}

export default function BaseballDashboard() {
  const feeds = Object.keys(ALL_DATA);

  const [feed, setFeed] = useState(() => {
    try {
      const stored = localStorage.getItem(
        "baseball_dash_feed",
      );

      if (stored && ALL_DATA[stored]) {
        return stored;
      }
    } catch {}

    return "mlb";
  });

  useEffect(() => {
    document.body.classList.add("generated-dashboard");

    const link = document.createElement("link");
    link.id = "smh-baseball-dashboard-css";
    link.rel = "stylesheet";
    link.href =
      "/assets/css/generated/baseball-dashboard.css";

    document.head.appendChild(link);

    return () => {
      document.body.classList.remove(
        "generated-dashboard",
      );
      link.remove();
    };
  }, []);

  const activeFeed = ALL_DATA[feed] ?? ALL_DATA.mlb;

  return (
    <>
      <header>
        <h1>MLB Dashboard</h1>
        <span className="ts">
          Built 2026-09-27T11:52:58+00:00 UTC
        </span>
      </header>

      <div className="feed-bar">
        <span className="lbl">Feed:</span>

        {feeds.map((key) => (
          <button
            key={key}
            type="button"
            className={`feed-btn ${
              feed === key ? "active" : ""
            }`}
            onClick={() => {
              setFeed(key);

              try {
                localStorage.setItem(
                  "baseball_dash_feed",
                  key,
                );
              } catch {}
            }}
          >
            {ALL_DATA[key].label ?? key}
          </button>
        ))}
      </div>

      <FeedSection data={activeFeed} />
    </>
  );
}
