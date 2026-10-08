import { useEffect, useMemo, useRef, useState } from "react";

import "../../../app/frontend/src/assets/css/matstheme.css";
import "../../../app/frontend/src/assets/css/dashboard.css";
import "../../../app/frontend/src/assets/css/pages/nhl_dashboard.css";
import "../../../app/frontend/src/assets/css/site-polish.css";

import data from "../data/nhl-dashboard.json";

type RawRow = Record<string, string | number | null | undefined>;

type SummaryRow = {
  variable: string;
  bets: number;
  wins: number;
  losses: number;
  win_rate: number;
  units: number;
  roi: number;
  avg_edge: number;
  avg_odds: number;
};

type Column = {
  key: keyof SummaryRow;
  label: string;
  format?: "pct" | "units" | "odds" | "int";
  color?: "win" | "loss";
};

const nhlData = data as Record<string, RawRow[]>;

const PAGE_SIZE = 50;

function num(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : NaN;
}

function pct(value: number): string {
  return Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—";
}

function edgePct(value: number): string {
  return Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : "—";
}

function american(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(0)}`;
}

function unitValue(odds: number, result: string): number {
  const normalized = result.toLowerCase();

  if (normalized === "win") {
    if (!Number.isFinite(odds)) return 0;
    return odds > 0 ? odds / 100 : 100 / Math.abs(odds);
  }

  if (normalized === "loss") return -1;
  return 0;
}

function summarize(variable: string, rows: RawRow[]): SummaryRow {
  const wins = rows.filter(
    row => String(row.bet_result ?? "").toLowerCase() === "win",
  ).length;

  const losses = rows.filter(
    row => String(row.bet_result ?? "").toLowerCase() === "loss",
  ).length;

  const bets = rows.length;
  const settled = wins + losses;

  const units = rows.reduce((total, row) => {
    return (
      total +
      unitValue(
        num(row.dk_odds_american),
        String(row.bet_result ?? ""),
      )
    );
  }, 0);

  const edges = rows
    .map(row => num(row.edge))
    .filter(Number.isFinite);

  const odds = rows
    .map(row => num(row.dk_odds_american))
    .filter(Number.isFinite);

  return {
    variable,
    bets,
    wins,
    losses,
    win_rate: settled ? wins / settled : NaN,
    units,
    roi: settled ? units / settled : NaN,
    avg_edge: edges.length
      ? edges.reduce((a, b) => a + b, 0) / edges.length
      : NaN,
    avg_odds: odds.length
      ? odds.reduce((a, b) => a + b, 0) / odds.length
      : NaN,
  };
}

function groupSummary(
  rows: RawRow[],
  key: (row: RawRow) => string,
): SummaryRow[] {
  const groups = new Map<string, RawRow[]>();

  rows.forEach(row => {
    const variable = key(row) || "—";

    if (!groups.has(variable)) {
      groups.set(variable, []);
    }

    groups.get(variable)!.push(row);
  });

  return Array.from(groups.entries()).map(([variable, grouped]) =>
    summarize(variable, grouped),
  );
}

function reportRows(key: string): SummaryRow[] {
  return (nhlData[key] ?? []).map(row => ({
    variable: String(row.variable ?? "—"),
    bets: num(row.Total),
    wins: num(row.Win),
    losses: num(row.Loss),
    win_rate: num(row.Win_Pct),
    units: num(row.units),
    roi: num(row.roi),
    avg_edge: num(row.avg_ev),
    avg_odds: num(row.avg_odds),
  }));
}

function marketTallyRows(): SummaryRow[] {
  return (nhlData.market_tally ?? []).map(row => ({
    variable: String(row.market_type ?? "—"),
    bets: num(row.bets_including_pushes ?? row.Total),
    wins: num(row.Win),
    losses: num(row.Loss),
    win_rate: num(row.Win_Pct),
    units: num(row.units),
    roi: num(row.roi),
    avg_edge: num(row.avg_ev),
    avg_odds: num(row.avg_odds),
  }));
}

const SUMMARY_COLUMNS: Column[] = [
  { key: "variable", label: "Variable" },
  { key: "bets", label: "Bets", format: "int" },
  { key: "wins", label: "Wins", format: "int", color: "win" },
  { key: "losses", label: "Losses", format: "int", color: "loss" },
  { key: "win_rate", label: "Win Rate", format: "pct" },
  { key: "units", label: "Units", format: "units" },
  { key: "roi", label: "ROI", format: "pct" },
  { key: "avg_edge", label: "Avg Edge", format: "pct" },
  { key: "avg_odds", label: "Avg Odds", format: "odds" },
];

const BUCKET_COLUMNS: Column[] = [
  { key: "variable", label: "Bucket" },
  { key: "bets", label: "Bets", format: "int" },
  { key: "wins", label: "Wins", format: "int", color: "win" },
  { key: "losses", label: "Losses", format: "int", color: "loss" },
  { key: "win_rate", label: "Win Rate", format: "pct" },
  { key: "units", label: "Units", format: "units" },
  { key: "roi", label: "ROI", format: "pct" },
];

const TALLY_COLUMNS: Column[] = [
  { key: "variable", label: "Market" },
  { key: "wins", label: "Wins", format: "int", color: "win" },
  { key: "losses", label: "Losses", format: "int", color: "loss" },
  { key: "bets", label: "Bets", format: "int" },
  { key: "win_rate", label: "Win Rate", format: "pct" },
  { key: "units", label: "Units", format: "units" },
  { key: "roi", label: "ROI", format: "pct" },
];

function cellValue(row: SummaryRow, column: Column): string {
  const value = row[column.key];

  if (column.key === "variable") {
    return String(value ?? "—");
  }

  if (column.format === "pct") {
    return pct(Number(value));
  }

  if (column.format === "units") {
    const nValue = Number(value);
    return Number.isFinite(nValue)
      ? `${nValue >= 0 ? "+" : ""}${nValue.toFixed(2)}`
      : "—";
  }

  if (column.format === "odds") {
    return american(Number(value));
  }

  if (column.format === "int") {
    return Number.isFinite(Number(value))
      ? String(Number(value))
      : "—";
  }

  return String(value ?? "—");
}

function DataTable({
  rows,
  columns,
}: {
  rows: SummaryRow[];
  columns: Column[];
}) {
  const [sortKey, setSortKey] =
    useState<keyof SummaryRow>("variable");
  const [ascending, setAscending] = useState(true);

  const sorted = useMemo(() => {
    return [...rows].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];

      if (typeof av === "number" && typeof bv === "number") {
        if (Number.isNaN(av)) return 1;
        if (Number.isNaN(bv)) return -1;
        return ascending ? av - bv : bv - av;
      }

      return ascending
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
  }, [rows, sortKey, ascending]);

  function handleSort(key: keyof SummaryRow) {
    if (sortKey === key) {
      setAscending(value => !value);
    } else {
      setSortKey(key);
      setAscending(true);
    }
  }

  if (!rows.length) {
    return <div className="loading">No data</div>;
  }

  return (
    <table>
      <thead>
        <tr>
          {columns.map(column => (
            <th
              key={column.key}
              onClick={() => handleSort(column.key)}
            >
              {column.label}
            </th>
          ))}
        </tr>
      </thead>

      <tbody>
        {sorted.map((row, index) => (
          <tr key={`${row.variable}-${index}`}>
            {columns.map(column => {
              const value = cellValue(row, column);

              if (column.key === "win_rate") {
                const rate = row.win_rate;
                const cls =
                  rate >= 0.6
                    ? "wr-high"
                    : rate >= 0.5
                      ? "wr-mid"
                      : "wr-low";

                return (
                  <td key={column.key}>
                    <span className={`wr-badge ${cls}`}>
                      {value}
                    </span>
                  </td>
                );
              }

              let className = "";

              if (column.key === "roi") {
                className =
                  Number(row.roi) >= 0 ? "win" : "loss";
              }

              if (column.key === "units") {
                className =
                  Number(row.units) >= 0 ? "win" : "loss";
              }

              if (column.color === "win") {
                className = "win";
              }

              if (column.color === "loss") {
                className = "loss";
              }

              return (
                <td key={column.key} className={className}>
                  {value}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DateChart({
  rows,
}: {
  rows: SummaryRow[];
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;

    if (!canvas || !rows.length) return;

    function draw() {
      const rect = canvas!.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const width = Math.max(rect.width, 320);
      const height = 280;

      canvas!.width = Math.round(width * dpr);
      canvas!.height = Math.round(height * dpr);

      const ctx = canvas!.getContext("2d");

      if (!ctx) return;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);

      const pad = {
        top: 20,
        right: 20,
        bottom: 50,
        left: 50,
      };

      const chartWidth =
        width - pad.left - pad.right;

      const chartHeight =
        height - pad.top - pad.bottom;

      const values = rows.map(row =>
        Number.isFinite(row.win_rate)
          ? row.win_rate * 100
          : 0,
      );

      const x = (index: number) =>
        pad.left +
        (index / Math.max(rows.length - 1, 1)) *
          chartWidth;

      const y = (value: number) =>
        pad.top +
        chartHeight -
        (value / 100) * chartHeight;

      ctx.strokeStyle = "rgba(255,255,255,0.05)";
      ctx.lineWidth = 1;

      for (let i = 0; i <= 4; i++) {
        const lineY =
          pad.top + (chartHeight / 4) * i;

        ctx.beginPath();
        ctx.moveTo(pad.left, lineY);
        ctx.lineTo(width - pad.right, lineY);
        ctx.stroke();
      }

      ctx.strokeStyle = "rgba(255,255,255,0.15)";

      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top);
      ctx.lineTo(
        pad.left,
        height - pad.bottom,
      );
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(
        pad.left,
        height - pad.bottom,
      );
      ctx.lineTo(
        width - pad.right,
        height - pad.bottom,
      );
      ctx.stroke();

      const y50 = y(50);

      ctx.strokeStyle = "rgba(255,214,0,0.2)";
      ctx.setLineDash([4, 4]);

      ctx.beginPath();
      ctx.moveTo(pad.left, y50);
      ctx.lineTo(width - pad.right, y50);
      ctx.stroke();

      ctx.setLineDash([]);

      if (rows.length > 1) {
        const gradient = ctx.createLinearGradient(
          0,
          pad.top,
          0,
          height - pad.bottom,
        );

        gradient.addColorStop(
          0,
          "rgba(0,191,255,0.25)",
        );

        gradient.addColorStop(
          1,
          "rgba(0,191,255,0.01)",
        );

        ctx.fillStyle = gradient;

        ctx.beginPath();
        ctx.moveTo(x(0), y(values[0]));

        for (let i = 1; i < values.length; i++) {
          ctx.lineTo(x(i), y(values[i]));
        }

        ctx.lineTo(
          x(values.length - 1),
          height - pad.bottom,
        );

        ctx.lineTo(
          x(0),
          height - pad.bottom,
        );

        ctx.closePath();
        ctx.fill();

        ctx.strokeStyle = "#00bfff";
        ctx.lineWidth = 2;

        ctx.beginPath();
        ctx.moveTo(x(0), y(values[0]));

        for (let i = 1; i < values.length; i++) {
          ctx.lineTo(x(i), y(values[i]));
        }

        ctx.stroke();

        ctx.fillStyle = "#00bfff";

        values.forEach((value, index) => {
          ctx.beginPath();
          ctx.arc(
            x(index),
            y(value),
            3,
            0,
            Math.PI * 2,
          );
          ctx.fill();
        });
      }

      ctx.fillStyle = "rgba(124,135,150,0.7)";
      ctx.font = "9px monospace";
      ctx.textAlign = "center";

      const step = Math.max(
        1,
        Math.ceil(rows.length / 10),
      );

      rows.forEach((row, index) => {
        if (index % step !== 0) return;

        const label = row.variable
          .replace(/^2026_/, "")
          .replace(/_/g, "/");

        ctx.fillText(
          label,
          x(index),
          height - pad.bottom + 18,
        );
      });

      ctx.textAlign = "right";

      for (let i = 0; i <= 4; i++) {
        const value = 100 - (100 / 4) * i;

        ctx.fillText(
          `${value.toFixed(0)}%`,
          pad.left - 8,
          pad.top +
            (chartHeight / 4) * i +
            4,
        );
      }
    }

    draw();

    window.addEventListener("resize", draw);

    return () => {
      window.removeEventListener("resize", draw);
    };
  }, [rows]);

  return (
    <div className="date-chart">
      <canvas
        ref={canvasRef}
        id="nhl-date-canvas"
        height={280}
      />
    </div>
  );
}

function BucketSection({
  title,
  moneyline,
  puckLine,
  total,
}: {
  title: string;
  moneyline: SummaryRow[];
  puckLine: SummaryRow[];
  total: SummaryRow[];
}) {
  return (
    <section className="section active">
      <div className="section-title">
        <span />
        {title}
      </div>

      <div className="grid-2">
        <div>
          <div
            className="section-title"
            style={{ fontSize: "1rem" }}
          >
            MONEYLINE
          </div>

          <div className="table-wrap">
            <DataTable
              rows={moneyline}
              columns={BUCKET_COLUMNS}
            />
          </div>
        </div>

        <div>
          <div
            className="section-title"
            style={{ fontSize: "1rem" }}
          >
            PUCK LINE
          </div>

          <div className="table-wrap">
            <DataTable
              rows={puckLine}
              columns={BUCKET_COLUMNS}
            />
          </div>
        </div>
      </div>

      <div
        className="section-title"
        style={{ fontSize: "1rem" }}
      >
        TOTAL
      </div>

      <div className="table-wrap">
        <DataTable
          rows={total}
          columns={BUCKET_COLUMNS}
        />
      </div>
    </section>
  );
}

function BetLog() {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);

  const allRows = nhlData.bets ?? [];

  const filtered = useMemo(() => {
    const lower = query.toLowerCase();

    if (!lower) return allRows;

    return allRows.filter(row =>
      Object.values(row).some(value =>
        String(value ?? "")
          .toLowerCase()
          .includes(lower),
      ),
    );
  }, [allRows, query]);

  const pages = Math.ceil(
    filtered.length / PAGE_SIZE,
  );

  const visible = filtered.slice(
    page * PAGE_SIZE,
    page * PAGE_SIZE + PAGE_SIZE,
  );

  useEffect(() => {
    setPage(0);
  }, [query]);

  return (
    <>
      <input
        type="text"
        className="search-bar"
        placeholder="Search teams, market, result..."
        value={query}
        onChange={event =>
          setQuery(event.target.value)
        }
      />

      <div className="table-wrap">
        {!visible.length ? (
          <div className="loading">
            No bet log data
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                {[
                  "Game Date",
                  "Away Team",
                  "Home Team",
                  "Market",
                  "Bet Side",
                  "Line",
                  "Take Odds",
                  "Selected Edge",
                  "Bet Result",
                  "Units",
                ].map(label => (
                  <th key={label}>{label}</th>
                ))}
              </tr>
            </thead>

            <tbody>
              {visible.map((row, index) => {
                const odds = num(
                  row.dk_odds_american,
                );

                const units = unitValue(
                  odds,
                  String(row.bet_result ?? ""),
                );

                const result =
                  String(
                    row.bet_result ?? "",
                  ).toLowerCase();

                return (
                  <tr
                    key={`${row.game_id ?? index}-${index}`}
                  >
                    <td>
                      {String(
                        row.game_date ?? "—",
                      )}
                    </td>
                    <td>
                      {String(
                        row.away_team ?? "—",
                      )}
                    </td>
                    <td>
                      {String(
                        row.home_team ?? "—",
                      )}
                    </td>
                    <td>
                      {String(
                        row.market_type ?? "—",
                      )}
                    </td>
                    <td>
                      {String(
                        row.bet_side ?? "—",
                      )}
                    </td>
                    <td>
                      {String(row.line ?? "—")}
                    </td>
                    <td>
                      {american(odds)}
                    </td>
                    <td>
                      {edgePct(num(row.edge))}
                    </td>
                    <td
                      className={
                        result === "win"
                          ? "win"
                          : result === "loss"
                            ? "loss"
                            : "push"
                      }
                    >
                      {String(
                        row.bet_result ?? "—",
                      )}
                    </td>
                    <td
                      className={
                        units >= 0
                          ? "win"
                          : "loss"
                      }
                    >
                      {units >= 0 ? "+" : ""}
                      {units.toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {pages > 1 && (
        <div className="pagination">
          {Array.from(
            { length: pages },
            (_, index) => (
              <button
                key={index}
                type="button"
                className={`page-btn ${
                  index === page ? "active" : ""
                }`}
                onClick={() => setPage(index)}
              >
                {index + 1}
              </button>
            ),
          )}
        </div>
      )}
    </>
  );
}

function MarketTally() {
  const rows = marketTallyRows();

  const maxBets = Math.max(
    ...rows.map(row => row.bets),
    1,
  );

  return (
    <>
      <div className="bar-chart">
        <div
          className="section-title"
          style={{
            fontSize: "1rem",
            marginBottom: "20px",
          }}
        >
          WIN RATE BY MARKET
        </div>

        {rows.map(row => {
          const width = Math.max(
            (row.bets / maxBets) * 100,
            2,
          );

          const barClass =
            row.win_rate >= 0.6
              ? "win-bar"
              : row.win_rate >= 0.5
                ? "neutral-bar"
                : "loss-bar";

          return (
            <div
              className="bar-row"
              key={row.variable}
            >
              <div className="bar-label">
                {row.variable.toUpperCase()}
              </div>

              <div className="bar-track">
                <div
                  className={`bar-fill ${barClass}`}
                  style={{
                    width: `${width}%`,
                  }}
                >
                  {row.wins}W / {row.losses}L
                </div>
              </div>

              <div className="bar-meta">
                <span
                  className={`wr-badge ${
                    row.win_rate >= 0.6
                      ? "wr-high"
                      : row.win_rate >= 0.5
                        ? "wr-mid"
                        : "wr-low"
                  }`}
                >
                  {pct(row.win_rate)}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="table-wrap">
        <DataTable
          rows={rows}
          columns={TALLY_COLUMNS}
        />
      </div>
    </>
  );
}

export default function NhlDashboard() {
  const bets = nhlData.bets ?? [];

  const overall = useMemo(
    () => summarize("ALL", bets),
    [bets],
  );

  const marketRows = useMemo(
    () =>
      groupSummary(
        bets,
        row => String(row.market_type ?? ""),
      ),
    [bets],
  );

  const sideRows = useMemo(
    () =>
      groupSummary(
        bets,
        row => String(row.bet_side ?? ""),
      ),
    [bets],
  );

  const dateRows = useMemo(
    () =>
      groupSummary(
        [...bets].sort((a, b) =>
          String(a.game_date ?? "").localeCompare(
            String(b.game_date ?? ""),
          ),
        ),
        row => String(row.game_date ?? ""),
      ),
    [bets],
  );

  const [activeTab, setActiveTab] =
    useState("market");

  useEffect(() => {
    document.body.classList.add(
      "generated-dashboard",
    );

    return () => {
      document.body.classList.remove(
        "generated-dashboard",
      );
    };
  }, []);

  const edge = {
    moneyline: reportRows("moneyline_ev"),
    puckLine: reportRows("puckline_ev"),
    total: reportRows("total_ev"),
  };

  const odds = {
    moneyline: reportRows("moneyline_odds"),
    puckLine: reportRows("puckline_odds"),
    total: reportRows("total_odds"),
  };

  const kelly = {
    moneyline: reportRows("moneyline_kelly"),
    puckLine: reportRows("puckline_kelly"),
    total: reportRows("total_kelly"),
  };

  return (
    <>
      <header>
        <div>
          <h1>NHL Analytics</h1>
          <div className="header-sub">
            Betting Performance Dashboard
          </div>
        </div>

        <div className="status-pill">
          {bets.length ? "LIVE" : "NO DATA"}
        </div>
      </header>

      <div className="dash-tabs">
        {[
          ["market", "Market"],
          ["side", "Side"],
          ["edge", "Edge"],
          ["odds", "Odds"],
          ["kelly", "Kelly"],
          ["date", "By Date"],
          ["betlog", "Bet Log"],
          ["tally", "Tally"],
        ].map(([key, label]) => (
          <a
            key={key}
            className={
              activeTab === key ? "active" : ""
            }
            onClick={() => setActiveTab(key)}
          >
            {label}
          </a>
        ))}
      </div>

      <main>
        <div className="stat-grid">
          <div className="stat-card accent">
            <div className="stat-label">
              Total Bets
            </div>
            <div className="stat-value accent">
              {overall.bets}
            </div>
          </div>

          <div className="stat-card green">
            <div className="stat-label">
              Win Rate
            </div>
            <div className="stat-value green">
              {pct(overall.win_rate)}
            </div>
          </div>

          <div className="stat-card gold">
            <div className="stat-label">
              ROI
            </div>
            <div className="stat-value gold">
              {pct(overall.roi)}
            </div>
          </div>

          <div className="stat-card green">
            <div className="stat-label">
              Units
            </div>
            <div
              className={`stat-value ${
                overall.units >= 0
                  ? "green"
                  : "red"
              }`}
            >
              {overall.units >= 0 ? "+" : ""}
              {overall.units.toFixed(2)}
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">
              Wins
            </div>
            <div className="stat-value green">
              {overall.wins}
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">
              Losses
            </div>
            <div className="stat-value red">
              {overall.losses}
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">
              Avg Edge
            </div>
            <div className="stat-value accent">
              {edgePct(overall.avg_edge)}
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">
              Avg Odds
            </div>
            <div className="stat-value">
              {american(overall.avg_odds)}
            </div>
          </div>
        </div>

        {activeTab === "market" && (
          <section className="section active">
            <div className="section-title">
              <span />
              BY MARKET
            </div>

            <div className="table-wrap">
              <DataTable
                rows={marketRows}
                columns={SUMMARY_COLUMNS}
              />
            </div>
          </section>
        )}

        {activeTab === "side" && (
          <section className="section active">
            <div className="section-title">
              <span />
              BY SIDE
            </div>

            <div className="table-wrap">
              <DataTable
                rows={sideRows}
                columns={SUMMARY_COLUMNS}
              />
            </div>
          </section>
        )}

        {activeTab === "edge" && (
          <BucketSection
            title="BY EDGE BUCKET"
            moneyline={edge.moneyline}
            puckLine={edge.puckLine}
            total={edge.total}
          />
        )}

        {activeTab === "odds" && (
          <BucketSection
            title="BY ODDS BUCKET"
            moneyline={odds.moneyline}
            puckLine={odds.puckLine}
            total={odds.total}
          />
        )}

        {activeTab === "kelly" && (
          <BucketSection
            title="BY KELLY BUCKET"
            moneyline={kelly.moneyline}
            puckLine={kelly.puckLine}
            total={kelly.total}
          />
        )}

        {activeTab === "date" && (
          <section className="section active">
            <div className="section-title">
              <span />
              PERFORMANCE BY DATE
            </div>

            <DateChart rows={dateRows} />

            <div className="table-wrap">
              <DataTable
                rows={dateRows}
                columns={SUMMARY_COLUMNS}
              />
            </div>
          </section>
        )}

        {activeTab === "betlog" && (
          <section className="section active">
            <div className="section-title">
              <span />
              BET LOG
            </div>

            <BetLog />
          </section>
        )}

        {activeTab === "tally" && (
          <section className="section active">
            <div className="section-title">
              <span />
              MARKET TALLY
            </div>

            <MarketTally />
          </section>
        )}
      </main>
    </>
  );
}
