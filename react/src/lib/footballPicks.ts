/*
  Football picks resolve their current week from pipeline health.

  CFB pipeline source:
    docs/win/football/cfb/config/current_week.yaml

  NFL pipeline source:
    docs/win/football/nfl/config/settings.yaml

  Earlier weeks are found using actual selected-picks files,
  not hard-coded calendar-to-week date ranges.
*/

export type FootballLeague = "CFB" | "NFL";

type Row = Record<string, string>;

export type FootballCsvResult = {
  ok: boolean;
  rows: Row[];
  source?: string;
};

type CsvLoader = (
  path: string,
  signal: AbortSignal
) => Promise<FootballCsvResult>;

type Target = {
  season: number;
  week: number;
};

type HealthDocument = {
  report_week?: unknown;
  season?: unknown;
  leagues?: {
    cfb?: {
      week?: unknown;
      season?: unknown;
    };
    nfl?: {
      configured_target?: {
        week?: unknown;
        season?: unknown;
      };
    };
  };
};

const HEALTH_BASE =
  "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/frontend/data/pipeline_health/";

function validInteger(
  value: unknown,
  min: number,
  max: number
): number {
  if (
    value === undefined ||
    value === null ||
    value === "" ||
    typeof value === "boolean"
  ) {
    throw new Error(
      "Football pipeline metadata is missing a required integer."
    );
  }

  const number = Number(value);

  if (
    !Number.isInteger(number) ||
    number < min ||
    number > max
  ) {
    throw new Error(
      "Football pipeline metadata contains an invalid integer."
    );
  }

  return number;
}

function extractTarget(
  league: FootballLeague,
  document: HealthDocument
): Target {
  if (league === "CFB") {
    const cfb = document.leagues?.cfb;

    if (!cfb) {
      throw new Error("CFB pipeline-health target is missing.");
    }

    const week = validInteger(cfb.week, 1, 25);

    const season = validInteger(
      cfb.season ?? document.season,
      2000,
      2100
    );

    if (
      document.report_week !== undefined &&
      Number(document.report_week) !== week
    ) {
      throw new Error(
        "CFB pipeline-health week values disagree."
      );
    }

    return { season, week };
  }

  const nfl = document.leagues?.nfl?.configured_target;

  if (!nfl) {
    throw new Error("NFL pipeline-health target is missing.");
  }

  return {
    season: validInteger(nfl.season, 2000, 2100),
    week: validInteger(nfl.week, 1, 25),
  };
}

async function fetchTarget(
  league: FootballLeague,
  signal: AbortSignal
): Promise<Target> {
  const response = await fetch(
    HEALTH_BASE + league.toLowerCase() + ".json",
    {
      cache: "no-store",
      signal,
    }
  );

  if (!response.ok) {
    throw new Error(
      "Football pipeline health request failed: HTTP " +
        response.status
    );
  }

  const document =
    (await response.json()) as HealthDocument;

  if (!document || typeof document !== "object") {
    throw new Error(
      "Football pipeline health is not an object."
    );
  }

  return extractTarget(league, document);
}

function normalizedDate(value: string): string {
  return String(value || "")
    .trim()
    .replaceAll("_", "-");
}

function validDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }

  const parsed = new Date(value + "T00:00:00Z");

  return (
    !Number.isNaN(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === value
  );
}

export async function resolveFootballSelections(
  league: FootballLeague,
  selectedDate: string,
  signal: AbortSignal,
  loadCsv: CsvLoader
): Promise<FootballCsvResult> {
  const date = normalizedDate(selectedDate);

  if (!validDate(date)) {
    return { ok: true, rows: [] };
  }

  const target = await fetchTarget(league, signal);
  const requestedYear = Number(date.slice(0, 4));

  // January postseason games may belong to
  // the preceding football season.
  if (
    requestedYear < target.season ||
    requestedYear > target.season + 1
  ) {
    return { ok: true, rows: [] };
  }

  let foundReadableFile = false;

  for (let week = target.week; week >= 1; week--) {
    if (signal.aborted) {
      throw new Error(
        "Football selections request was cancelled."
      );
    }

    const path =
      "win/football/" +
      league.toLowerCase() +
      "/03_picks/selected/week_" +
      week +
      "_" +
      league +
      "_select_picks.csv";

    const result = await loadCsv(path, signal);

    if (!result.ok) {
      continue;
    }

    foundReadableFile = true;

    const rows = result.rows.filter(
      (row) =>
        Number(row.season) === target.season &&
        Number(row.week) === week &&
        validDate(normalizedDate(row.game_date))
    );

    const exact = rows.filter(
      (row) =>
        normalizedDate(row.game_date) === date
    );

    if (exact.length > 0) {
      return {
        ok: true,
        rows: exact,
        source: path,
      };
    }

    // Do not display picks from a different date.
    if (
      rows.some(
        (row) => normalizedDate(row.game_date) <= date
      )
    ) {
      return {
        ok: true,
        rows: [],
        source: path,
      };
    }
  }

  return {
    ok: foundReadableFile,
    rows: [],
  };
}