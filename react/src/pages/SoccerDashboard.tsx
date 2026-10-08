import { useMemo, useState } from "react";
import "../styles/soccer-dashboard.css";
import allData from "../data/soccer-dashboard.json";

type Row = Record<string, any>;

type Column = {
  key: string;
  label: string;
  fmt?: "int" | "pct" | "num";
  decimals?: number;
  signed?: boolean;
};

type MarketData = {
  display?: string;
  by?: Record<string, Row[]>;
  by_side?: Record<string, Row[]>;
};

type LeagueData = {
  league?: string;
  display?: string;
  is_all?: boolean;
  headline?: {
    wins?: number;
    losses?: number;
    pushes?: number;
    total?: number;
    win_pct?: number;
  };
  tally?: Row[];
  by_market?: Row[];
  model_metrics?: Row[];
  calibration?: Row[];
  xg_metrics?: Row[];
  markets?: Record<string, MarketData>;
};

const DATA = allData as unknown as Record<string, LeagueData>;

const LEAGUES = [
  "all",
  "mls",
  "epl",
  "laliga",
  "ligue1",
  "seriea",
  "bundesliga",
].filter(key => DATA[key]);

const RESULT_COLUMNS: Column[] = [
  { key: "bucket", label: "Bucket" },
  { key: "Win", label: "W", fmt: "int" },
  { key: "Loss", label: "L", fmt: "int" },
  { key: "Push", label: "P", fmt: "int" },
  { key: "Total", label: "Total", fmt: "int" },
  { key: "Sample_Count", label: "Sample", fmt: "int" },
  { key: "Win_Pct", label: "Win %", fmt: "pct" },
];

const RESULT_SIDE_COLUMNS: Column[] = [
  { key: "side", label: "Side" },
  ...RESULT_COLUMNS,
];

const MODEL_COLUMNS: Column[] = [
  { key: "model", label: "Model" },
  { key: "sample_count", label: "Sample", fmt: "int" },
  { key: "brier_score", label: "Brier", fmt: "num", decimals: 4 },
  { key: "log_loss", label: "Log Loss", fmt: "num", decimals: 4 },
  { key: "rps", label: "RPS", fmt: "num", decimals: 4 },
];

const XG_COLUMNS: Column[] = [
  { key: "sample_count", label: "Sample", fmt: "int" },
  { key: "home_xg_mae", label: "Home xG MAE", fmt: "num", decimals: 3 },
  { key: "home_xg_rmse", label: "Home xG RMSE", fmt: "num", decimals: 3 },
  { key: "home_xg_bias", label: "Home xG Bias", fmt: "num", decimals: 3, signed: true },
  { key: "away_xg_mae", label: "Away xG MAE", fmt: "num", decimals: 3 },
  { key: "away_xg_rmse", label: "Away xG RMSE", fmt: "num", decimals: 3 },
  { key: "away_xg_bias", label: "Away xG Bias", fmt: "num", decimals: 3, signed: true },
  { key: "total_xg_mae", label: "Total xG MAE", fmt: "num", decimals: 3 },
  { key: "total_xg_rmse", label: "Total xG RMSE", fmt: "num", decimals: 3 },
  { key: "total_xg_bias", label: "Total xG Bias", fmt: "num", decimals: 3, signed: true },
];

const CAL_COLUMNS: Column[] = [
  { key: "model", label: "Model" },
  { key: "outcome", label: "Outcome" },
  { key: "bucket", label: "Bucket" },
  { key: "sample_count", label: "Sample", fmt: "int" },
  { key: "mean_predicted_probability", label: "Mean Pred", fmt: "pct" },
  { key: "observed_rate", label: "Observed", fmt: "pct" },
  { key: "calibration_gap", label: "Gap", fmt: "num", decimals: 4, signed: true },
];

function fmtPct(value: any) {
  if (value == null || Number.isNaN(Number(value))) return "";
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function fmtInt(value: any) {
  if (value == null || Number.isNaN(Number(value))) return "";
  return Number(value).toLocaleString();
}

function fmtNum(value: any, decimals = 3) {
  if (value == null || Number.isNaN(Number(value))) return "";
  return Number(value).toFixed(decimals);
}

function winPctClass(value: any) {
  const pct = Number(value);
  if (Number.isNaN(pct)) return "";
  if (pct >= 0.8) return "win-pct-strong";
  if (pct >= 0.7) return "win-pct-green";
  if (pct >= 0.6) return "win-pct-light";
  if (pct >= 0.5) return "win-pct-neutral";
  return "win-pct-red";
}

function SortableTable({
  rows,
  columns,
}: {
  rows: Row[];
  columns: Column[];
}) {
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sorted = useMemo(() => {
    const result = [...rows];
    if (!sortCol) return result;

    result.sort((a, b) => {
      const av = a[sortCol];
      const bv = b[sortCol];

      if (av == null) return 1;
      if (bv == null) return -1;

      const an = Number(av);
      const bn = Number(bv);

      if (!Number.isNaN(an) && !Number.isNaN(bn)) {
        return sortDir === "asc" ? an - bn : bn - an;
      }

      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });

    return result;
  }, [rows, sortCol, sortDir]);

  if (!rows.length) return <div className="muted">No rows available.</div>;

  function sort(key: string) {
    if (sortCol === key) {
      setSortDir(value => (value === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(key);
      setSortDir("desc");
    }
  }

  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            {columns.map(column => (
              <th key={column.key} onClick={() => sort(column.key)}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map(column => {
                const value = row[column.key];
                const classes: string[] = [];

                if (column.fmt) classes.push("num");
                if (column.key === "Win_Pct") classes.push(winPctClass(value));
                if (column.signed) {
                  const number = Number(value);
                  if (number > 0) classes.push("good");
                  if (number < 0) classes.push("bad");
                }

                let display = value == null ? "" : String(value);

                if (column.fmt === "int") display = fmtInt(value);
                if (column.fmt === "pct") display = fmtPct(value);
                if (column.fmt === "num") display = fmtNum(value, column.decimals ?? 3);

                return (
                  <td key={column.key} className={classes.filter(Boolean).join(" ")}>
                    {display}
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

function Kpis({ data }: { data: LeagueData }) {
  const h = data.headline ?? {};

  const items = [
    ["Bets", fmtInt(h.total)],
    ["Wins", fmtInt(h.wins)],
    ["Losses", fmtInt(h.losses)],
    ["Pushes", fmtInt(h.pushes)],
    ["Win %", fmtPct(h.win_pct)],
  ];

  return (
    <div className="kpis">
      {items.map(([label, value]) => (
        <div className="kpi" key={label}>
          <div className="label">{label}</div>
          <div className="value">{value || "N/A"}</div>
        </div>
      ))}
    </div>
  );
}

function ModelQuality({ data }: { data: LeagueData }) {
  const [tab, setTab] = useState("core");
  const [model, setModel] = useState("ALL");
  const [outcome, setOutcome] = useState("ALL");

  const leagueColumn: Column[] = [{ key: "league", label: "League" }];

  const modelColumns = data.is_all
    ? [...leagueColumn, ...MODEL_COLUMNS]
    : MODEL_COLUMNS;

  const xgColumns = data.is_all
    ? [...leagueColumn, ...XG_COLUMNS]
    : XG_COLUMNS;

  const calColumns = data.is_all
    ? [...leagueColumn, ...CAL_COLUMNS]
    : CAL_COLUMNS;

  const calibration = data.calibration ?? [];

  const models = [...new Set(calibration.map(row => row.model).filter(Boolean))].sort();
  const outcomes = [...new Set(calibration.map(row => row.outcome).filter(Boolean))].sort();

  const filteredCalibration = calibration.filter(
    row =>
      (model === "ALL" || String(row.model) === model) &&
      (outcome === "ALL" || String(row.outcome) === outcome)
  );

  return (
    <div className="model-area">
      <div className="tabs">
        <button className={`tab ${tab === "core" ? "active" : ""}`} onClick={() => setTab("core")}>
          Core Metrics
        </button>
        <button className={`tab ${tab === "xg" ? "active" : ""}`} onClick={() => setTab("xg")}>
          xG Metrics
        </button>
        <button
          className={`tab ${tab === "calibration" ? "active" : ""}`}
          onClick={() => setTab("calibration")}
        >
          Calibration
        </button>
      </div>

      <div className="tab-body">
        {tab === "core" && (
          <SortableTable rows={data.model_metrics ?? []} columns={modelColumns} />
        )}

        {tab === "xg" && (
          <SortableTable rows={data.xg_metrics ?? []} columns={xgColumns} />
        )}

        {tab === "calibration" && (
          <>
            {calibration.length ? (
              <>
                <div className="controls">
                  <label>
                    Model:{" "}
                    <select value={model} onChange={event => setModel(event.target.value)}>
                      <option value="ALL">All</option>
                      {models.map(value => (
                        <option key={value} value={value}>{value}</option>
                      ))}
                    </select>
                  </label>

                  <label>
                    Outcome:{" "}
                    <select value={outcome} onChange={event => setOutcome(event.target.value)}>
                      <option value="ALL">All</option>
                      {outcomes.map(value => (
                        <option key={value} value={value}>{value}</option>
                      ))}
                    </select>
                  </label>
                </div>

                <SortableTable rows={filteredCalibration} columns={calColumns} />
              </>
            ) : (
              <div className="muted">No calibration rows available.</div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function MarketPanel({ market }: { market: MarketData }) {
  const dimensions = Object.keys(market.by ?? {});
  const [dimension, setDimension] = useState(dimensions[0] ?? "");
  const [view, setView] = useState<"overall" | "side">("overall");

  if (!dimensions.length) {
    return <div className="muted">No market drilldown reports available.</div>;
  }

  const rows =
    view === "side"
      ? market.by_side?.[dimension] ?? []
      : market.by?.[dimension] ?? [];

  return (
    <>
      <div className="controls">
        <label>
          Dimension:{" "}
          <select value={dimension} onChange={event => setDimension(event.target.value)}>
            {dimensions.map(value => (
              <option key={value} value={value}>
                {value.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </label>

        <label>
          View:{" "}
          <select
            value={view}
            onChange={event => setView(event.target.value as "overall" | "side")}
          >
            <option value="overall">Overall</option>
            <option value="side">Split by side</option>
          </select>
        </label>
      </div>

      <SortableTable
        rows={rows}
        columns={view === "side" ? RESULT_SIDE_COLUMNS : RESULT_COLUMNS}
      />
    </>
  );
}

function MarketDrilldown({ data }: { data: LeagueData }) {
  const markets = Object.entries(data.markets ?? {}).filter(
    ([, market]) => Object.keys(market.by ?? {}).length > 0
  );

  const [active, setActive] = useState(markets[0]?.[0] ?? "");

  if (!markets.length) {
    return <div className="muted">No market drilldown reports available.</div>;
  }

  const selected =
    markets.find(([key]) => key === active) ??
    markets[0];

  return (
    <div className="market-area">
      <div className="tabs">
        {markets.map(([key, market]) => (
          <button
            key={key}
            className={`tab ${selected[0] === key ? "active" : ""}`}
            onClick={() => setActive(key)}
          >
            {market.display ?? key}
          </button>
        ))}
      </div>

      <div className="tab-body">
        <MarketPanel key={selected[0]} market={selected[1]} />
      </div>
    </div>
  );
}

function LeagueView({ data }: { data: LeagueData }) {
  return (
    <main>
      <section className="league-section active">
        <h2>{data.display ?? data.league ?? "Soccer"} Analytics</h2>

        <Kpis data={data} />

        <h2>By Market</h2>
        <SortableTable
          rows={data.by_market ?? []}
          columns={[
            { key: "market_display", label: "Market" },
            { key: "Win", label: "W", fmt: "int" },
            { key: "Loss", label: "L", fmt: "int" },
            { key: "Push", label: "P", fmt: "int" },
            { key: "Total", label: "Total", fmt: "int" },
            { key: "Win_Pct", label: "Win %", fmt: "pct" },
          ]}
        />

        <h2>By Market + Side</h2>
        <SortableTable
          rows={data.tally ?? []}
          columns={[
            { key: "market", label: "Market" },
            { key: "market_type", label: "Side" },
            { key: "Win", label: "W", fmt: "int" },
            { key: "Loss", label: "L", fmt: "int" },
            { key: "Push", label: "P", fmt: "int" },
            { key: "Total", label: "Total", fmt: "int" },
            { key: "Win_Pct", label: "Win %", fmt: "pct" },
          ]}
        />

        <h2>Model Quality</h2>
        <ModelQuality data={data} />

        <h2>Per Market Drilldown</h2>
        <MarketDrilldown data={data} />
      </section>
    </main>
  );
}

export default function SoccerDashboard() {
  const [league, setLeague] = useState(() => {
    try {
      const requested = new URLSearchParams(window.location.search).get("league");
      if (requested && DATA[requested]) return requested;
    } catch {}
    try {
      const stored = localStorage.getItem("soccer_dash_league");
      if (stored && DATA[stored]) return stored;
    } catch {}
    return "all";
  });

  function changeLeague(value: string) {
    setLeague(value);
    try {
      localStorage.setItem("soccer_dash_league", value);
    } catch {}
  }

  const data = DATA[league] ?? DATA.all;

  return (
    <div className="soccer-dashboard">
      <header>
        <h1>Soccer Dashboard</h1>
      </header>

      <div className="league-bar">
        <span className="lbl">League:</span>
        {LEAGUES.map(key => (
          <button
            key={key}
            className={`league-btn ${league === key ? "active" : ""}`}
            onClick={() => changeLeague(key)}
          >
            {DATA[key]?.display ?? key}
          </button>
        ))}
      </div>

      <LeagueView key={league} data={data} />
    </div>
  );
}

