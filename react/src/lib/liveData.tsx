/*
  Live pipeline data for the dashboards and Pipeline Health.

  The pipelines publish frontend/data/dashboards/<name>.json ({ generated_at, data }) and
  frontend/data/pipeline_health/<sport>.json to GitHub. Pages fetch those files live from
  raw.githubusercontent.com. If the live request fails, the copy saved into the build
  (refreshed at build time by scripts/sync-live-data-snapshots.cjs)
  is loaded instead - only then, as a separate chunk - and the page says how old it is.
  Saved copies: src/data/live/dashboard-<name>.json and src/data/live/pipeline-health-<sport>.json.
*/
import { useEffect, useState } from "react";
import "./liveData.css";

export const LIVE_DATA_BASE =
  "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/frontend/data/";

const LIVE_TIMEOUT_MS = 10000;

const savedCopies = import.meta.glob<{ default: unknown }>("../data/live/*.json");

export async function fetchLiveJson(path: string, signal?: AbortSignal): Promise<unknown> {
  const timeout = new AbortController();
  const timer = window.setTimeout(() => timeout.abort(), LIVE_TIMEOUT_MS);
  const forward = () => timeout.abort();
  signal?.addEventListener("abort", forward);

  try {
    const response = await fetch(LIVE_DATA_BASE + path, {
      cache: "no-cache",
      signal: timeout.signal,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status} for ${path}`);
    return await response.json();
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener("abort", forward);
  }
}

export async function loadSnapshot(kind: "dashboard" | "pipeline-health", name: string): Promise<unknown> {
  const loader = savedCopies[`../data/live/${kind}-${name}.json`];
  if (!loader) throw new Error(`No saved ${kind} data for ${name}`);
  return (await loader()).default;
}

export function formatAsOf(value: unknown): string {
  const raw = String(value ?? "").trim();
  if (!raw) return "an unknown time";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

type Envelope = { generated_at?: unknown; data?: unknown };

function readEnvelope(value: unknown): { data: unknown; generatedAt: string } {
  const envelope = (value ?? {}) as Envelope;
  if (!envelope || typeof envelope !== "object" || envelope.data === undefined) {
    throw new Error("Dashboard data file has no data field");
  }
  return { data: envelope.data, generatedAt: String(envelope.generated_at ?? "") };
}

export type DashboardDataState =
  | { status: "loading" }
  | { status: "failed" }
  | { status: "ready"; source: "live" | "snapshot"; generatedAt: string };

/*
  Loads dashboards/<name>.json live, falling back to the saved copy. `apply` receives the
  `data` payload before the page renders with it.
*/
export function useDashboardData(name: string, apply: (data: unknown) => void): DashboardDataState {
  const [state, setState] = useState<DashboardDataState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    const load = async () => {
      let loaded: { data: unknown; generatedAt: string } | null = null;
      let source: "live" | "snapshot" = "live";

      try {
        loaded = readEnvelope(await fetchLiveJson(`dashboards/${name}.json`, controller.signal));
      } catch {
        if (controller.signal.aborted) return;
        try {
          loaded = readEnvelope(await loadSnapshot("dashboard", name));
          source = "snapshot";
        } catch {
          loaded = null;
        }
      }

      if (controller.signal.aborted) return;
      if (!loaded) {
        setState({ status: "failed" });
        return;
      }
      apply(loaded.data);
      setState({ status: "ready", source, generatedAt: loaded.generatedAt });
    };

    load();
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  return state;
}

export function DashboardDataStatus({ state }: { state: DashboardDataState }) {
  if (state.status === "loading") {
    return <div className="live-data-status">Loading dashboard data...</div>;
  }
  if (state.status === "failed") {
    return <div className="live-data-status live-data-failed">Dashboard data could not be loaded.</div>;
  }
  return null;
}

export function SavedDataNotice({ generatedAt }: { generatedAt: string }) {
  return (
    <div className="live-data-notice" role="status">
      Live data is unavailable. Showing saved data as of {formatAsOf(generatedAt)}.
    </div>
  );
}
