/*
  PipelineHealth - native React port of legacy pipeline_health.html + assets/js/pages/pipeline_health.js.

  Legacy behaviors found and preserved:
   1. Six sport sources (Basketball, MLB, NHL, CFB, Soccer, UFC), each fetched once on load from the relative path
      data/pipeline_health/{key}.json with cache: "no-store", all in parallel. A non-OK response or fetch error
      marks that sport as not loaded.
   2. Status bar: yellow dot + "Loading pipeline health data..." until loading finishes; then green dot with
      "N sport pipeline file(s) loaded - selectors become active as each sport is added", or red dot with
      "No pipeline health files could be loaded" when none loaded.
   3. Sport selector pills: All, Basketball, MLB, NHL, CFB, Soccer, UFC. The clicked pill becomes active (even if that sport
      has no data); pills of sports that did not load get the "unavailable" class (never the All pill); applied once loading finishes (or on the first pill click).
   4. Content (shown after loading): All = every loaded sport panel; one sport = that panel; if nothing to show,
      "<Label> pipeline health is not available yet" (specific sport) or "No pipeline health data available" (All).
   5. Sport panel: name, "Game date: ... - Generated: ..." (generated_at_utc formatted en-US with time zone, raw value if not a
      date, "unknown" if empty), status badge (Failed when fatal_errors exist or status text matches fail/error/critical/fatal/
      unhealthy; Warning when status matches warn; else Healthy).
   6. Summary cards: Fatal Errors, Active Leagues (in_season === true), Stages Successful (SUCCESS count / total), Warnings
      (red / yellow text when non-zero).
   7. League cards (when leagues exist): name, badge (Offseason when in_season === false, Warning on coverage/identity/issues/
      critical failures or a warning naming the league, else Healthy), six metric counts (default 0), note with season range,
      issues, or "In season; no games scheduled today." / "No coverage or identity issues reported."
   8. Warnings section: optional "Fatal Errors" box (fatal_errors), then "Warnings Requiring Attention" with de-duplicated warnings
      from warnings, wnba_bias_drift, sdv_health, league issues and sdv_health.current rows, or "No warnings reported."
   9. Pipeline Stages table (Stage, Status, Log) with status colouring (bad / warn / ok) when stage_status exists.
  10. Model & Data Health (when sdv_health exists): Production Configuration card and League Models card
      (artifact Valid/Invalid rows, ensemble weights valid count).
  11. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials (nav.js is loaded by SiteShell).
  Difference: values are rendered as React text (legacy escaped them into innerHTML) - same visible result.
*/
import { useEffect, useState } from "react";
import "../../../app/frontend/src/assets/css/pages/pipeline_health.css";

const MID = String.fromCharCode(0xb7);
const EMDASH = String.fromCharCode(0x2014);
const ENDASH = String.fromCharCode(0x2013);

type Source = { key: string; label: string; path: string };
type Loose = Record<string, any>;

const SPORT_SOURCES: Source[] = [
  { key: "basketball", label: "Basketball", path: "data/pipeline_health/basketball.json" },
  { key: "mlb", label: "MLB", path: "data/pipeline_health/mlb.json" },
  { key: "nhl", label: "NHL", path: "data/pipeline_health/nhl.json" },
  { key: "cfb", label: "CFB", path: "data/pipeline_health/cfb.json" },
  { key: "soccer", label: "Soccer", path: "data/pipeline_health/soccer.json" },
  { key: "ufc", label: "UFC", path: "data/pipeline_health/ufc.json" },
];

function arr(v: any): any[] {
  return Array.isArray(v) ? v : [];
}

function obj(v: any): Loose {
  return v && typeof v === "object" && !Array.isArray(v) ? v : {};
}

function text(v: any): string {
  return String(v == null ? "" : v);
}

function prettyName(value: any): string {
  return String(value || "")
    .replace(/\.txt$/i, "")
    .replace(/\.json$/i, "")
    .replace(/^\d+_/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function stageName(path: any): string {
  const parts = String(path || "").split("/");
  return prettyName(parts[parts.length - 1] || path || "Stage");
}

function parseStageClass(value: any): string {
  const s = String(value || "").toUpperCase();
  if (/FAILED|FAILURE|ERROR|CRITICAL|FATAL|UNHEALTHY/.test(s)) return "stage-bad";
  if (/WARNING|WARN/.test(s)) return "stage-warn";
  if (/SUCCESS|HEALTHY|CLEAN/.test(s)) return "stage-ok";
  return "";
}

function formatGenerated(value: any): string {
  if (!value) return "unknown";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

function seasonText(cfgValue: any): string {
  const cfg = obj(cfgValue);
  if (!cfg.start_month || !cfg.start_day || !cfg.end_month || !cfg.end_day) return "";
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return (
    months[cfg.start_month - 1] + " " + cfg.start_day + " " + ENDASH + " " +
    months[cfg.end_month - 1] + " " + cfg.end_day
  );
}

function collectLeagueIssues(league: Loose): string[] {
  const issues: string[] = [];
  const coverage = obj(league.coverage);
  const identity = obj(league.identity);

  Object.entries(coverage).forEach(([k, v]) => {
    if (Array.isArray(v) && v.length) issues.push(prettyName(k) + ": " + v.length);
    else if (typeof v === "number" && v > 0) issues.push(prettyName(k) + ": " + v);
  });

  Object.entries(identity).forEach(([k, v]) => {
    if (Array.isArray(v) && v.length) issues.push(prettyName(k) + ": " + v.length);
    else if (typeof v === "number" && v > 0) issues.push(prettyName(k) + ": " + v);
  });

  arr(league.issues).forEach((v) => issues.push(String(v)));
  arr(league.critical_failures).forEach((v) => issues.push(String(v)));

  return issues;
}

function collectWarnings(data: Loose): string[] {
  const out: string[] = [];
  const seen = new Set<string>();

  const add = (v: any) => {
    const s = String(v || "").trim();
    if (!s || seen.has(s)) return;
    seen.add(s);
    out.push(s);
  };

  arr(data.warnings).forEach(add);
  arr(obj(data.wnba_bias_drift).warnings).forEach(add);
  arr(obj(data.sdv_health).warnings).forEach(add);

  Object.entries(obj(data.leagues)).forEach(([lg, row]) => {
    collectLeagueIssues(obj(row)).forEach((v) => add(lg.toUpperCase() + ": " + v));
  });

  Object.entries(obj(obj(data.sdv_health).current)).forEach(([lg, row]) => {
    arr(obj(row).issues).forEach((v) => add(lg.toUpperCase() + ": " + v));
    arr(obj(row).critical_failures).forEach((v) => add(lg.toUpperCase() + ": " + v));
  });

  return out;
}

function sportStatus(data: Loose): "failed" | "warning" | "healthy" {
  if (arr(data.fatal_errors).length) return "failed";
  const raw = String(data.status || "").toLowerCase();
  if (/fail|error|critical|fatal|unhealthy/.test(raw)) return "failed";
  if (/warn/.test(raw)) return "warning";
  return "healthy";
}

function leagueStatus(key: string, league: Loose, data: Loose): "offseason" | "warning" | "healthy" {
  if (league.in_season === false) return "offseason";
  const warnings = collectWarnings(data);
  const hasNamedWarning = warnings.some((w) => w.toLowerCase().includes(key.toLowerCase()));
  if (collectLeagueIssues(league).length || hasNamedWarning) return "warning";
  return "healthy";
}

function summaryFor(data: Loose) {
  const leagues = Object.values(obj(data.leagues));
  const stages = arr(data.stage_status);
  const stageSuccess = stages.filter((s) => /SUCCESS/i.test(String(obj(s).status || ""))).length;

  return {
    fatal: arr(data.fatal_errors).length,
    active: leagues.filter((l) => obj(l).in_season === true).length,
    stages: stageSuccess + "/" + stages.length,
    warnings: collectWarnings(data).length,
  };
}

function LeagueCard({ leagueKey, leagueValue, data }: { leagueKey: string; leagueValue: any; data: Loose }) {
  const league = obj(leagueValue);
  const c = obj(league.counts);
  const status = leagueStatus(leagueKey, league, data);
  const label =
    status === "offseason" ? "Offseason" : status === "warning" ? "Warning" : "Healthy";
  const issues = collectLeagueIssues(league);
  const season = seasonText(league.season_config);

  let note = season ? "Season: " + season + ". " : "";
  if (issues.length) note += issues.join(" " + MID + " ");
  else if (league.in_season === true && Number(c.scheduled_games || 0) === 0)
    note += "In season; no games scheduled today.";
  else note += "No coverage or identity issues reported.";

  const metrics: [string, any][] = [
    ["Scheduled", c.scheduled_games],
    ["Predictions", c.prediction_games],
    ["Sportsbook", c.sportsbook_games],
    ["Merged", c.merged_games],
    ["Selected Bets", c.selected_bets],
    ["Locked Bets", c.locked_bets],
  ];

  return (
    <section className="league-card">
      <div className="league-head">
        <div className="league-name">{leagueKey.toUpperCase()}</div>
        <span className={"badge " + status}>{label}</span>
      </div>
      <div className="league-body">
        <div className="metrics">
          {metrics.map(([metricLabel, value]) => (
            <div className="metric" key={metricLabel}>
              <div className="metric-value">{text(value ?? 0)}</div>
              <div className="metric-label">{metricLabel}</div>
            </div>
          ))}
        </div>
        <div className="league-note">{note}</div>
      </div>
    </section>
  );
}

function Warnings({ data }: { data: Loose }) {
  const fatals = arr(data.fatal_errors);
  const warnings = collectWarnings(data);

  return (
    <>
      {fatals.length ? (
        <>
          <div className="section-title">Fatal Errors</div>
          <div className="warning-box fatal-box">
            <ul className="warning-list">
              {fatals.map((v, i) => (
                <li key={i}>{text(v)}</li>
              ))}
            </ul>
          </div>
        </>
      ) : null}

      <div className="section-title">Warnings Requiring Attention</div>
      <div className="warning-box">
        <ul className="warning-list">
          {warnings.length ? (
            warnings.map((v, i) => <li key={i}>{v}</li>)
          ) : (
            <li style={{ color: "var(--text-muted)" }}>No warnings reported.</li>
          )}
        </ul>
      </div>
    </>
  );
}

function Stages({ data }: { data: Loose }) {
  const stages = arr(data.stage_status);
  if (!stages.length) return null;

  return (
    <>
      <div className="section-title">Pipeline Stages</div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Stage</th>
              <th>Status</th>
              <th>Log</th>
            </tr>
          </thead>
          <tbody>
            {stages.map((raw, i) => {
              const s = obj(raw);
              const cls = parseStageClass(s.status);

              return (
                <tr key={i}>
                  <td>{stageName(s.path)}</td>
                  <td className={cls}>{text(s.status || "Unknown")}</td>
                  <td>{text(s.path || "")}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

function ModelHealth({ data }: { data: Loose }) {
  const sdv = obj(data.sdv_health);
  if (!Object.keys(sdv).length) return null;

  const cfg = obj(sdv.configs);
  const modelCfg = obj(cfg.model_config);
  const sdvModel = obj(cfg.sdv_model);
  const manifests = obj(sdv.historical_manifests);
  const artifacts = obj(sdv.model_artifacts);
  const weights = obj(sdv.ensemble_weights);
  const artifactEntries = Object.entries(artifacts);
  const validWeights = Object.values(weights).filter((v) => obj(v).valid === true).length;
  const weightCount = Object.keys(weights).length;

  return (
    <>
      <div className="section-title">Model &amp; Data Health</div>
      <div className="data-grid">
        <div className="data-card">
          <div className="data-card-title">Production Configuration</div>
          <div className="data-row">
            <span className="data-key">Prediction source</span>
            <span className="data-value">
              {text(sdv.configured_production_source || modelCfg.configured_source || EMDASH)}
            </span>
          </div>
          <div className="data-row">
            <span className="data-key">SDV model version</span>
            <span className="data-value">{text(sdvModel.model_version || EMDASH)}</span>
          </div>
          <div className="data-row">
            <span className="data-key">Feature version</span>
            <span className="data-value">{text(sdvModel.feature_version || EMDASH)}</span>
          </div>
          <div className="data-row">
            <span className="data-key">Historical manifests</span>
            <span
              className={
                "data-value " +
                (manifests.valid_count === manifests.required_count ? "ok" : "warn-text")
              }
            >
              {text(manifests.valid_count ?? EMDASH)} / {text(manifests.required_count ?? EMDASH)} valid
            </span>
          </div>
        </div>

        <div className="data-card">
          <div className="data-card-title">League Models</div>
          {artifactEntries.length ? (
            artifactEntries.map(([k, v]) => {
              const artifact = obj(v);
              const invalid = artifact.valid === false;

              return (
                <div className="data-row" key={k}>
                  <span className="data-key">{k.toUpperCase()}</span>
                  <span className={"data-value " + (invalid ? "bad-text" : "ok")}>
                    {invalid ? "Invalid" : "Valid"}
                  </span>
                </div>
              );
            })
          ) : (
            <div className="data-row">
              <span className="data-key">Artifacts</span>
              <span className="data-value">No artifact summary</span>
            </div>
          )}
          <div className="data-row">
            <span className="data-key">Ensemble weights</span>
            <span className={"data-value " + (validWeights === weightCount ? "ok" : "warn-text")}>
              {validWeights} / {weightCount} valid
            </span>
          </div>
        </div>
      </div>
    </>
  );
}

function SportPanel({ source, data }: { source: Source; data: Loose }) {
  const summary = summaryFor(data);
  const status = sportStatus(data);
  const statusLabel = status === "failed" ? "Failed" : status === "warning" ? "Warning" : "Healthy";
  const leagues = obj(data.leagues);
  const leagueEntries = Object.entries(leagues);

  return (
    <section className="sport-panel" data-rendered-sport={source.key}>
      <div className="sport-head">
        <div>
          <div className="sport-name">{source.label}</div>
          <div className="sport-meta">
            Game date: {text(data.game_date_new_york || EMDASH)} {MID} Generated:{" "}
            {formatGenerated(data.generated_at_utc)}
          </div>
        </div>
        <span className={"badge " + status}>{statusLabel}</span>
      </div>

      <div className="summary-grid">
        <div className="summary-card">
          <div className="summary-label">Fatal Errors</div>
          <div className={"summary-value" + (summary.fatal ? " bad-text" : "")}>{summary.fatal}</div>
        </div>
        <div className="summary-card">
          <div className="summary-label">Active Leagues</div>
          <div className="summary-value">{summary.active}</div>
        </div>
        <div className="summary-card">
          <div className="summary-label">Stages Successful</div>
          <div className="summary-value">{summary.stages}</div>
        </div>
        <div className="summary-card">
          <div className="summary-label">Warnings</div>
          <div className={"summary-value" + (summary.warnings ? " warn-text" : "")}>
            {summary.warnings}
          </div>
        </div>
      </div>

      {leagueEntries.length ? (
        <>
          <div className="section-title">League Status</div>
          <div className="league-grid">
            {leagueEntries.map(([k, v]) => (
              <LeagueCard key={k} leagueKey={k} leagueValue={v} data={data} />
            ))}
          </div>
        </>
      ) : null}

      <Warnings data={data} />
      <Stages data={data} />
      <ModelHealth data={data} />
    </section>
  );
}

export default function PipelineHealth() {
  const [health, setHealth] = useState<Record<string, Loose>>({});
  const [loaded, setLoaded] = useState(false);
  const [loadedCount, setLoadedCount] = useState(0);
  const [activeSport, setActiveSport] = useState("all");
  // Legacy: a pill click re-runs updateControls() and render() even before loading finishes.
  const [interacted, setInteracted] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    const loadAll = async () => {
      const next: Record<string, Loose> = {};

      const results = await Promise.all(
        SPORT_SOURCES.map(async (source) => {
          try {
            const response = await fetch(source.path, {
              cache: "no-store",
              signal: controller.signal,
            });

            if (!response.ok) return { source, ok: false };

            next[source.key] = await response.json();

            return { source, ok: true };
          } catch {
            return { source, ok: false };
          }
        })
      );

      if (controller.signal.aborted) return;

      setHealth(next);
      setLoadedCount(results.filter((r) => r.ok).length);
      setLoaded(true);
    };

    loadAll();

    return () => controller.abort();
  }, []);

  const ready = loaded || interacted;

  const selected = SPORT_SOURCES.filter(
    (s) => health[s.key] && (activeSport === "all" || s.key === activeSport)
  );

  const dotClass = !loaded ? "yellow" : loadedCount ? "green" : "red";

  const statusText = !loaded
    ? "Loading pipeline health data..."
    : loadedCount
      ? loadedCount +
        " sport pipeline " +
        (loadedCount === 1 ? "file" : "files") +
        " loaded " +
        MID +
        " selectors become active as each sport is added"
      : "No pipeline health files could be loaded";

  const activeSource = SPORT_SOURCES.find((s) => s.key === activeSport);

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Pipeline Health</div>
          <div className="page-subtitle">
            {["All", "Basketball", "MLB", "NHL", "CFB", "Soccer", "UFC"].join(" " + MID + " ")}
          </div>
        </div>
      </div>

      <div className="controls" id="sport-controls">
        <button
          type="button"
          className={"sport-pill" + (activeSport === "all" ? " active" : "")}
          data-sport="all"
          onClick={() => {
            setActiveSport("all");
            setInteracted(true);
          }}
        >
          All
        </button>

        {SPORT_SOURCES.map((source) => (
          <button
            type="button"
            key={source.key}
            className={
              "sport-pill" +
              (activeSport === source.key ? " active" : "") +
              (ready && !health[source.key] ? " unavailable" : "")
            }
            data-sport={source.key}
            onClick={() => {
              setActiveSport(source.key);
              setInteracted(true);
            }}
          >
            {source.label}
          </button>
        ))}
      </div>

      <div className="status-bar" id="status-bar">
        <span className={"status-dot " + dotClass} id="load-dot" />
        <span id="load-text">{statusText}</span>
      </div>

      <div className="main">
        <div id="health-content">
          {ready ? (
            selected.length ? (
              selected.map((source) => (
                <SportPanel key={source.key} source={source} data={health[source.key]} />
              ))
            ) : (
              <div className="empty-state">
                {activeSource
                  ? activeSource.label + " pipeline health is not available yet"
                  : "No pipeline health data available"}
              </div>
            )
          ) : null}
        </div>
      </div>
    </>
  );
}
