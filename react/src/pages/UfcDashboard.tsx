import { useEffect, useMemo, useState } from "react";

import "../../../app/frontend/src/assets/css/generated/ufc-dashboard.css";

import data from "../data/ufc-dashboard.json";
import reportColumns from "../data/ufc-report-columns.json";

type Row = Record<string, unknown>;

type Column = {
  key: string;
  label: string;
  fmt?: string;
};

const TABS = [
  { key: "ev", label: "EV" },
  { key: "odds", label: "Odds" },
  { key: "implied_prob", label: "Implied Prob" },
  { key: "model_prob", label: "Model Prob" },
  { key: "dratings_prob", label: "DRatings Prob" },
  { key: "date", label: "By Date" },
] as const;

const columns = reportColumns as Column[];
const ufcData = data as {
  headline: Row;
  reports: Record<string, { rows?: Row[] }>;
};

function fmtPct(value: unknown) {
  if (
    value == null ||
    Number.isNaN(Number(value))
  ) {
    return "";
  }

  return `${(Number(value) * 100).toFixed(2)}%`;
}

function fmtNum(
  value: unknown,
  decimals = 3,
) {
  if (
    value == null ||
    Number.isNaN(Number(value))
  ) {
    return "";
  }

  return Number(value).toFixed(decimals);
}

function fmtInt(value: unknown) {
  if (
    value == null ||
    Number.isNaN(Number(value))
  ) {
    return "";
  }

  return Number(value).toLocaleString();
}

function signedClass(value: unknown) {
  if (
    value == null ||
    Number.isNaN(Number(value))
  ) {
    return "";
  }

  return Number(value) > 0
    ? "good"
    : Number(value) < 0
      ? "bad"
      : "";
}

function winPctClass(value: unknown) {
  if (
    value == null ||
    Number.isNaN(Number(value))
  ) {
    return "";
  }

  const pct = Number(value);

  if (pct >= 0.80) return "win-pct-strong";
  if (pct >= 0.70) return "win-pct-green";
  if (pct >= 0.60) return "win-pct-light";
  if (pct >= 0.50) return "win-pct-neutral";

  return "win-pct-red";
}

function formatValue(
  value: unknown,
  column: Column,
) {
  switch (column.fmt) {
    case "pct":
      return fmtPct(value);

    case "int":
      return fmtInt(value);

    case "num":
      return fmtNum(value);

    default:
      return value == null ? "" : String(value);
  }
}

function sortValue(value: unknown) {
  if (
    value == null ||
    value === ""
  ) {
    return null;
  }

  const numeric = Number(value);

  if (!Number.isNaN(numeric)) {
    return numeric;
  }

  return String(value).toLowerCase();
}

function ReportTable({
  rows,
}: {
  rows: Row[];
}) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] =
    useState<"asc" | "desc">("desc");

  const sortedRows = useMemo(() => {
    if (!sortKey) {
      return rows;
    }

    return [...rows].sort((a, b) => {
      const av = sortValue(a[sortKey]);
      const bv = sortValue(b[sortKey]);

      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;

      let comparison = 0;

      if (
        typeof av === "number" &&
        typeof bv === "number"
      ) {
        comparison = av - bv;
      } else {
        comparison = String(av).localeCompare(
          String(bv),
        );
      }

      return sortDir === "asc"
        ? comparison
        : -comparison;
    });
  }, [rows, sortKey, sortDir]);

  if (!rows.length) {
    return (
      <div className="muted">
        No rows available.
      </div>
    );
  }

  function handleSort(key: string) {
    if (sortKey === key) {
      setSortDir((current) =>
        current === "asc"
          ? "desc"
          : "asc",
      );
      return;
    }

    setSortKey(key);
    setSortDir("desc");
  }

  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                onClick={() =>
                  handleSort(column.key)
                }
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {sortedRows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => {
                const value =
                  row[column.key];

                let className = "";

                if (
                  column.key === "win_pct"
                ) {
                  className =
                    winPctClass(value);
                } else if (
                  column.key === "units" ||
                  column.key === "roi"
                ) {
                  className =
                    signedClass(value);
                }

                return (
                  <td
                    key={column.key}
                    className={className}
                  >
                    {formatValue(
                      value,
                      column,
                    )}
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
  value: unknown;
  format: "int" | "pct" | "num";
}) {
  let display = "";

  if (format === "int") {
    display = fmtInt(value);
  } else if (format === "pct") {
    display = fmtPct(value);
  } else {
    display = fmtNum(value);
  }

  return (
    <div className="kpi">
      <div className="kpi-label">
        {label}
      </div>
      <div className="kpi-value">
        {display}
      </div>
    </div>
  );
}

export default function UfcDashboard() {
  const [activeTab, setActiveTab] =
    useState("ev");

  useEffect(() => {
    document.body.classList.add("generated-dashboard");

    return () => {
      document.body.classList.remove("generated-dashboard");
    };
  }, []);
  const headline =
    ufcData.headline;

  return (
    <>
      <header>
        <h1>UFC Dashboard</h1>

        <span className="ts">
          Built 2026-09-27T06:35:24+00:00 UTC
        </span>
      </header>

      <section
        className="kpis"
        id="headline"
      >
        <Kpi
          label="Bets"
          value={headline.bets}
          format="int"
        />
        <Kpi
          label="Wins"
          value={headline.wins}
          format="int"
        />
        <Kpi
          label="Losses"
          value={headline.losses}
          format="int"
        />
        <Kpi
          label="Pushes"
          value={headline.pushes}
          format="int"
        />
        <Kpi
          label="Win %"
          value={headline.win_pct}
          format="pct"
        />
        <Kpi
          label="Units"
          value={headline.units}
          format="num"
        />
        <Kpi
          label="ROI"
          value={headline.roi}
          format="pct"
        />
      </section>

      <div id="report-tabs">
        <div className="tabs">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              className={`tab ${
                activeTab === tab.key
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                setActiveTab(tab.key)
              }
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="tab-body">
          {TABS.map((tab) => {
            if (
              activeTab !== tab.key
            ) {
              return null;
            }

            const rows =
              ufcData.reports[
                tab.key
              ]?.rows ?? [];

            return (
              <div
                key={tab.key}
                className="tab-panel"
                data-key={tab.key}
              >
                <ReportTable
                  rows={rows}
                />
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

