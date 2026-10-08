import { useEffect, useMemo, useRef, useState } from "react";

import "../../../app/frontend/src/assets/css/matstheme.css";
import "../../../app/frontend/src/assets/css/dashboard.css";
import "./nfl-dashboard.css";
import "../../../app/frontend/src/assets/css/site-polish.css";

import data from "../data/nfl-dashboard.json";

type RawRow = Record<string, string | number | null | undefined>;

type StatRow = {
  variable: string;
  side_group: string;
  bets: number;
  wins: number;
  losses: number;
  pushes: number;
  win_rate: number;
  units: number;
  roi: number;
  avg_ev: number;
  avg_odds: number;
  avg_model: number;
  cumulative_units: number;
};

type Column = {
  key: keyof StatRow;
  label: string;
  format?: "pct" | "units" | "odds" | "int";
  color?: "win" | "loss";
};

const nflData = data as unknown as Record<string, RawRow[]>;

const PAGE_SIZE = 50;

function num(value: unknown): number {
  if (value === null || value === undefined || value === "") return NaN;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : NaN;
}

function pct(value: number): string {
  return Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—";
}

function pct2(value: number): string {
  return Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : "—";
}

function american(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(0)}`;
}

function signed(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}

function intText(value: number): string {
  return Number.isFinite(value) ? String(value) : "—";
}

function text(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function labelize(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, char => char.toUpperCase());
}

function winRateClass(rate: number): string {
  if (rate >= 0.6) return "wr-high";
  if (rate >= 0.5) return "wr-mid";
  return "wr-low";
}

function toStat(row: RawRow): StatRow {
  return {
    variable: text(row.variable),
    side_group: text(row.side_group),
    bets: num(row.Total),
    wins: num(row.Win),
    losses: num(row.Loss),
    pushes: num(row.Push),
    win_rate: num(row.Win_Pct),
    units: num(row.units),
    roi: num(row.ROI_Excluding_Pushes),
    avg_ev: num(row.avg_ev),
    avg_odds: num(row.avg_odds),
    avg_model: num(row.avg_model_prob),
    cumulative_units: num(row.cumulative_units),
  };
}

function reportRows(key: string): StatRow[] {
  return (nflData[key] ?? []).map(toStat);
}

const METRIC_COLUMNS: Column[] = [
  { key: "bets", label: "Bets", format: "int" },
  { key: "wins", label: "W", format: "int", color: "win" },
  { key: "losses", label: "L", format: "int", color: "loss" },
  { key: "pushes", label: "P", format: "int" },
  { key: "win_rate", label: "Win Rate", format: "pct" },
  { key: "units", label: "Units", format: "units" },
  { key: "roi", label: "ROI", format: "pct" },
  { key: "avg_ev", label: "Avg EV", format: "pct" },
  { key: "avg_odds", label: "Avg Odds", format: "odds" },
  { key: "avg_model", label: "Avg Model", format: "pct" },
];

function columns(
  label: string,
  options?: { side?: boolean; cumulative?: boolean },
): Column[] {
  const result: Column[] = [{ key: "variable", label }];

  if (options?.side) {
    result.push({ key: "side_group", label: "Side" });
  }

  result.push(...METRIC_COLUMNS);

  if (options?.cumulative) {
    result.push({
      key: "cumulative_units",
      label: "Cum Units",
      format: "units",
    });
  }

  return result;
}

function cellValue(row: StatRow, column: Column): string {
  const value = row[column.key];

  if (column.key === "variable" || column.key === "side_group") {
    return String(value ?? "—");
  }

  if (column.format === "pct") return pct(Number(value));
  if (column.format === "units") return signed(Number(value));
  if (column.format === "odds") return american(Number(value));
  if (column.format === "int") return intText(Number(value));

  return String(value ?? "—");
}

function DataTable({
  rows,
  columns: tableColumns,
}: {
  rows: StatRow[];
  columns: Column[];
}) {
  const [sortKey, setSortKey] = useState<keyof StatRow | null>(null);
  const [ascending, setAscending] = useState(true);

  const sorted = useMemo(() => {
    if (!sortKey) return rows;

    return [...rows].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];

      if (typeof av === "number" && typeof bv === "number") {
        if (Number.isNaN(av) && Number.isNaN(bv)) return 0;
        if (Number.isNaN(av)) return 1;
        if (Number.isNaN(bv)) return -1;
        return ascending ? av - bv : bv - av;
      }

      return ascending
        ? String(av).localeCompare(String(bv), undefined, { numeric: true })
        : String(bv).localeCompare(String(av), undefined, { numeric: true });
    });
  }, [rows, sortKey, ascending]);

  function handleSort(key: keyof StatRow) {
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
          {tableColumns.map(column => (
            <th key={column.key} onClick={() => handleSort(column.key)}>
              {column.label}
            </th>
          ))}
        </tr>
      </thead>

      <tbody>
        {sorted.map((row, index) => (
          <tr key={`${row.side_group}-${row.variable}-${index}`}>
            {tableColumns.map(column => {
              const value = cellValue(row, column);

              if (column.key === "win_rate") {
                if (!Number.isFinite(row.win_rate)) {
                  return <td key={column.key}>{value}</td>;
                }

                return (
                  <td key={column.key}>
                    <span className={`wr-badge ${winRateClass(row.win_rate)}`}>
                      {value}
                    </span>
                  </td>
                );
              }

              let className = "";

              if (column.key === "roi") {
                className = Number(row.roi) >= 0 ? "win" : "loss";
              }

              if (column.key === "units" || column.key === "cumulative_units") {
                className = Number(row[column.key]) >= 0 ? "win" : "loss";
              }

              if (column.color === "win") className = "win";
              if (column.color === "loss") className = "loss";

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

function DateChart({ rows, canvasId }: { rows: StatRow[]; canvasId: string }) {
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

      const pad = { top: 20, right: 20, bottom: 50, left: 50 };
      const chartWidth = width - pad.left - pad.right;
      const chartHeight = height - pad.top - pad.bottom;

      const values = rows.map(row =>
        Number.isFinite(row.win_rate) ? row.win_rate * 100 : 0,
      );

      const x = (index: number) =>
        pad.left + (index / Math.max(rows.length - 1, 1)) * chartWidth;

      const y = (value: number) =>
        pad.top + chartHeight - (value / 100) * chartHeight;

      ctx.strokeStyle = "rgba(255,255,255,0.05)";
      ctx.lineWidth = 1;

      for (let i = 0; i <= 4; i++) {
        const lineY = pad.top + (chartHeight / 4) * i;

        ctx.beginPath();
        ctx.moveTo(pad.left, lineY);
        ctx.lineTo(width - pad.right, lineY);
        ctx.stroke();
      }

      ctx.strokeStyle = "rgba(255,255,255,0.15)";

      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top);
      ctx.lineTo(pad.left, height - pad.bottom);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(pad.left, height - pad.bottom);
      ctx.lineTo(width - pad.right, height - pad.bottom);
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

        gradient.addColorStop(0, "rgba(0,191,255,0.25)");
        gradient.addColorStop(1, "rgba(0,191,255,0.01)");

        ctx.fillStyle = gradient;

        ctx.beginPath();
        ctx.moveTo(x(0), y(values[0]));

        for (let i = 1; i < values.length; i++) {
          ctx.lineTo(x(i), y(values[i]));
        }

        ctx.lineTo(x(values.length - 1), height - pad.bottom);
        ctx.lineTo(x(0), height - pad.bottom);
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
          ctx.arc(x(index), y(value), 3, 0, Math.PI * 2);
          ctx.fill();
        });
      } else {
        ctx.fillStyle = "#00bfff";
        ctx.beginPath();
        ctx.arc(x(0), y(values[0]), 3, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.fillStyle = "rgba(124,135,150,0.7)";
      ctx.font = "9px monospace";
      ctx.textAlign = "center";

      const step = Math.max(1, Math.ceil(rows.length / 10));

      rows.forEach((row, index) => {
        if (index % step !== 0) return;

        ctx.fillText(row.variable, x(index), height - pad.bottom + 18);
      });

      ctx.textAlign = "right";

      for (let i = 0; i <= 4; i++) {
        const value = 100 - (100 / 4) * i;

        ctx.fillText(
          `${value.toFixed(0)}%`,
          pad.left - 8,
          pad.top + (chartHeight / 4) * i + 4,
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
      <canvas ref={canvasRef} id={canvasId} height={280} />
    </div>
  );
}

function Block({
  title,
  rows,
  tableColumns,
}: {
  title: string;
  rows: StatRow[];
  tableColumns: Column[];
}) {
  return (
    <div>
      <div className="section-title" style={{ fontSize: "1rem" }}>
        {title}
      </div>

      <div className="table-wrap">
        <DataTable rows={rows} columns={tableColumns} />
      </div>
    </div>
  );
}

function BucketSection({
  title,
  dimension,
  label,
}: {
  title: string;
  dimension: string;
  label: string;
}) {
  const tableColumns = columns(label);

  return (
    <section className="section active">
      <div className="section-title">
        <span />
        {title}
      </div>

      <div className="grid-2">
        <Block
          title="MONEYLINE"
          rows={reportRows(`moneyline_by_${dimension}`)}
          tableColumns={tableColumns}
        />

        <Block
          title="SPREAD"
          rows={reportRows(`spread_by_${dimension}`)}
          tableColumns={tableColumns}
        />
      </div>

      <Block
        title="TOTAL"
        rows={reportRows(`total_by_${dimension}`)}
        tableColumns={tableColumns}
      />
    </section>
  );
}

function LinesSection() {
  const tableColumns = columns("Bucket");

  return (
    <section className="section active">
      <div className="section-title">
        <span />
        BY LINE / RANGE
      </div>

      <div className="grid-2">
        <Block
          title="SPREAD BY LINE"
          rows={reportRows("spread_by_line")}
          tableColumns={tableColumns}
        />

        <Block
          title="SPREAD BY SPREAD RANGE"
          rows={reportRows("spread_by_spread_range")}
          tableColumns={tableColumns}
        />
      </div>

      <div className="grid-2">
        <Block
          title="TOTAL BY LINE"
          rows={reportRows("total_by_line")}
          tableColumns={tableColumns}
        />

        <Block
          title="TOTAL BY TOTAL RANGE"
          rows={reportRows("total_by_total_range")}
          tableColumns={tableColumns}
        />
      </div>
    </section>
  );
}

const DRILL_MARKETS: [string, string][] = [
  ["moneyline", "Moneyline"],
  ["spread", "Spread"],
  ["total", "Total"],
];

function dimensionsFor(market: string): string[] {
  const dimensions: string[] = [];
  const pattern = new RegExp(`^${market}_by_(.+?)(_side_summary)?$`);

  Object.keys(nflData).forEach(key => {
    const match = key.match(pattern);
    const dimension = match?.[1];

    if (dimension && !dimensions.includes(dimension)) {
      dimensions.push(dimension);
    }
  });

  return dimensions;
}

function Drilldown() {
  const [market, setMarket] = useState("moneyline");
  const [dimension, setDimension] = useState("");
  const [split, setSplit] = useState(false);

  const dimensions = useMemo(() => dimensionsFor(market), [market]);

  const activeDimension = dimensions.includes(dimension)
    ? dimension
    : (dimensions[0] ?? "");

  const sideKey = `${market}_by_${activeDimension}_side_summary`;
  const canSplit = Boolean(nflData[sideKey]?.length);
  const useSplit = split && canSplit;

  const rows = reportRows(
    useSplit ? sideKey : `${market}_by_${activeDimension}`,
  );

  return (
    <>
      <div className="pagination">
        {DRILL_MARKETS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={`page-btn ${market === key ? "active" : ""}`}
            onClick={() => setMarket(key)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="pagination">
        {dimensions.map(key => (
          <button
            key={key}
            type="button"
            className={`page-btn ${activeDimension === key ? "active" : ""}`}
            onClick={() => setDimension(key)}
          >
            {labelize(key)}
          </button>
        ))}

        {canSplit && (
          <button
            type="button"
            className={`page-btn ${useSplit ? "active" : ""}`}
            onClick={() => setSplit(value => !value)}
          >
            Split By Side
          </button>
        )}
      </div>

      <div className="table-wrap">
        <DataTable
          rows={rows}
          columns={columns(labelize(activeDimension), { side: useSplit })}
        />
      </div>
    </>
  );
}

function BetLog() {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);

  const allRows = nflData.bet_log ?? [];

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

  const pages = Math.ceil(filtered.length / PAGE_SIZE);

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
        onChange={event => setQuery(event.target.value)}
      />

      <div className="table-wrap">
        {!visible.length ? (
          <div className="loading">No bet log data</div>
        ) : (
          <table>
            <thead>
              <tr>
                {[
                  "Week",
                  "Game Date",
                  "Away Team",
                  "Home Team",
                  "Market",
                  "Bet Side",
                  "Line",
                  "Odds",
                  "Model Prob",
                  "Edge",
                  "EV",
                  "Kelly",
                  "Result",
                  "Units",
                  "Score",
                ].map(label => (
                  <th key={label}>{label}</th>
                ))}
              </tr>
            </thead>

            <tbody>
              {visible.map((row, index) => {
                const units = num(row.bet_units);
                const result = String(row.bet_result ?? "").toLowerCase();

                return (
                  <tr
                    key={`${row.game_id ?? ""}-${row.market_type ?? ""}-${row.bet_side ?? ""}-${index}`}
                  >
                    <td>{text(row.week)}</td>
                    <td>{text(row.game_date)}</td>
                    <td>{text(row.away_team)}</td>
                    <td>{text(row.home_team)}</td>
                    <td>{text(row.market_type)}</td>
                    <td>{text(row.bet_side)}</td>
                    <td>{text(row.line)}</td>
                    <td>{american(num(row.odds_american))}</td>
                    <td>{pct(num(row.model_prob))}</td>
                    <td>{pct2(num(row.edge))}</td>
                    <td>{pct2(num(row.ev))}</td>
                    <td>{pct2(num(row.kelly))}</td>
                    <td
                      className={
                        result === "win"
                          ? "win"
                          : result === "loss"
                            ? "loss"
                            : "push"
                      }
                    >
                      {text(row.bet_result)}
                    </td>
                    <td className={units >= 0 ? "win" : "loss"}>
                      {signed(units)}
                    </td>
                    <td>
                      {text(row.away_score)}-{text(row.home_score)}
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
          {Array.from({ length: pages }, (_, index) => (
            <button
              key={index}
              type="button"
              className={`page-btn ${index === page ? "active" : ""}`}
              onClick={() => setPage(index)}
            >
              {index + 1}
            </button>
          ))}
        </div>
      )}
    </>
  );
}

function MarketBars({ rows }: { rows: StatRow[] }) {
  const maxBets = Math.max(...rows.map(row => row.bets).filter(Number.isFinite), 1);

  return (
    <div className="bar-chart">
      <div
        className="section-title"
        style={{ fontSize: "1rem", marginBottom: "20px" }}
      >
        WIN RATE BY MARKET
      </div>

      {rows.map(row => {
        const width = Math.max(
          ((Number.isFinite(row.bets) ? row.bets : 0) / maxBets) * 100,
          2,
        );

        const barClass =
          row.win_rate >= 0.6
            ? "win-bar"
            : row.win_rate >= 0.5
              ? "neutral-bar"
              : "loss-bar";

        return (
          <div className="bar-row" key={row.variable}>
            <div className="bar-label">{row.variable.toUpperCase()}</div>

            <div className="bar-track">
              <div className={`bar-fill ${barClass}`} style={{ width: `${width}%` }}>
                {intText(row.wins)}W / {intText(row.losses)}L
                {row.pushes > 0 ? ` / ${intText(row.pushes)}P` : ""}
              </div>
            </div>

            <div className="bar-meta">
              <span className={`wr-badge ${winRateClass(row.win_rate)}`}>
                {pct(row.win_rate)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

const TABS: [string, string][] = [
  ["market", "Market"],
  ["side", "Side"],
  ["ev", "EV"],
  ["odds", "Odds"],
  ["kelly", "Kelly"],
  ["winprob", "Win Prob"],
  ["lines", "Lines"],
  ["week", "By Week"],
  ["date", "By Date"],
  ["time", "Day/Night"],
  ["drill", "Drilldown"],
  ["betlog", "Bet Log"],
];

export default function NflDashboard() {
  const overallRow: RawRow = nflData.summary_overall?.[0] ?? {};
  const hasData = (nflData.bet_log ?? []).length > 0;

  const totalBets = num(overallRow.Total);
  const winRate = num(overallRow.Win_Pct);
  const roi = num(overallRow.ROI_Excluding_Pushes);
  const units = num(overallRow.units);
  const wins = num(overallRow.Win);
  const losses = num(overallRow.Loss);
  const pushes = num(overallRow.Push);
  const avgEv = num(overallRow.avg_ev);
  const avgOdds = num(overallRow.avg_odds);
  const avgModel = num(overallRow.avg_model_prob);

  const marketRows = useMemo(() => reportRows("summary_by_market"), []);
  const sideRows = useMemo(() => reportRows("summary_by_side_group"), []);
  const weekRows = useMemo(() => reportRows("summary_by_week"), []);
  const dateRows = useMemo(() => reportRows("summary_by_date"), []);
  const dayNightRows = useMemo(() => reportRows("summary_by_day_night"), []);
  const seasonTypeRows = useMemo(() => reportRows("summary_by_season_type"), []);

  const [activeTab, setActiveTab] = useState("market");

  useEffect(() => {
    document.body.classList.add("generated-dashboard");

    return () => {
      document.body.classList.remove("generated-dashboard");
    };
  }, []);

  return (
    <>
      <header>
        <div>
          <h1>NFL Analytics</h1>
          <div className="header-sub">Betting Performance Dashboard</div>
        </div>

        <div className="status-pill">{hasData ? "LIVE" : "NO DATA"}</div>
      </header>

      <div className="dash-tabs">
        {TABS.map(([key, label]) => (
          <a
            key={key}
            className={activeTab === key ? "active" : ""}
            onClick={() => setActiveTab(key)}
          >
            {label}
          </a>
        ))}
      </div>

      <main>
        <div className="stat-grid">
          <div className="stat-card accent">
            <div className="stat-label">Total Bets</div>
            <div className="stat-value accent">{intText(totalBets)}</div>
          </div>

          <div className="stat-card green">
            <div className="stat-label">Win Rate</div>
            <div className="stat-value green">{pct(winRate)}</div>
          </div>

          <div className="stat-card gold">
            <div className="stat-label">ROI</div>
            <div className="stat-value gold">{pct(roi)}</div>
          </div>

          <div className="stat-card green">
            <div className="stat-label">Units</div>
            <div className={`stat-value ${units >= 0 ? "green" : "red"}`}>
              {signed(units)}
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Wins</div>
            <div className="stat-value green">{intText(wins)}</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Losses</div>
            <div className="stat-value red">{intText(losses)}</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Pushes</div>
            <div className="stat-value">{intText(pushes)}</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Avg EV</div>
            <div className="stat-value accent">{pct2(avgEv)}</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Avg Odds</div>
            <div className="stat-value">{american(avgOdds)}</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Avg Model</div>
            <div className="stat-value">{pct(avgModel)}</div>
          </div>
        </div>

        {activeTab === "market" && (
          <section className="section active">
            <div className="section-title">
              <span />
              BY MARKET
            </div>

            <MarketBars rows={marketRows} />

            <div className="table-wrap">
              <DataTable rows={marketRows} columns={columns("Market")} />
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
              <DataTable rows={sideRows} columns={columns("Side")} />
            </div>
          </section>
        )}

        {activeTab === "ev" && (
          <BucketSection title="BY EV BUCKET" dimension="ev" label="EV Bucket" />
        )}

        {activeTab === "odds" && (
          <BucketSection title="BY ODDS BUCKET" dimension="odds" label="Odds Bucket" />
        )}

        {activeTab === "kelly" && (
          <BucketSection title="BY KELLY BUCKET" dimension="kelly" label="Kelly Bucket" />
        )}

        {activeTab === "winprob" && (
          <BucketSection
            title="BY WIN PROBABILITY BUCKET"
            dimension="win_prob"
            label="Win Prob Bucket"
          />
        )}

        {activeTab === "lines" && <LinesSection />}

        {activeTab === "week" && (
          <section className="section active">
            <div className="section-title">
              <span />
              PERFORMANCE BY WEEK
            </div>

            <DateChart rows={weekRows} canvasId="nfl-week-canvas" />

            <div className="table-wrap">
              <DataTable rows={weekRows} columns={columns("Week", { cumulative: true })} />
            </div>
          </section>
        )}

        {activeTab === "date" && (
          <section className="section active">
            <div className="section-title">
              <span />
              PERFORMANCE BY DATE
            </div>

            <DateChart rows={dateRows} canvasId="nfl-date-canvas" />

            <div className="table-wrap">
              <DataTable rows={dateRows} columns={columns("Date", { cumulative: true })} />
            </div>
          </section>
        )}

        {activeTab === "time" && (
          <section className="section active">
            <div className="section-title">
              <span />
              DAY / NIGHT AND SEASON TYPE
            </div>

            <div className="grid-2">
              <Block
                title="DAY / NIGHT"
                rows={dayNightRows}
                tableColumns={columns("Slot")}
              />

              <Block
                title="SEASON TYPE"
                rows={seasonTypeRows}
                tableColumns={columns("Season Type")}
              />
            </div>
          </section>
        )}

        {activeTab === "drill" && (
          <section className="section active">
            <div className="section-title">
              <span />
              MARKET DRILLDOWN
            </div>

            <Drilldown />
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
      </main>
    </>
  );
}
