/*
  Saves the pipeline data published under frontend/data into the React build, as the
  fallback the pages use when the live GitHub copy cannot be fetched (see src/lib/liveData.tsx).

    ../frontend/data/dashboards/<name>.json       -> src/data/live/dashboard-<name>.json
    ../frontend/data/pipeline_health/<sport>.json -> src/data/live/pipeline-health-<sport>.json
*/
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const published = path.resolve(root, "..", "frontend", "data");

const DASHBOARDS = ["basketball", "nba", "ncaam", "wnba", "soccer", "baseball", "ufc", "nhl", "nfl", "cfb"];
const PIPELINE_HEALTH = ["basketball", "mlb", "nhl", "cfb", "soccer", "ufc"];

function copyJson(source, target, check) {
  const text = fs.readFileSync(source, "utf8");
  const value = JSON.parse(text);
  check(value, source);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, JSON.stringify(value), "utf8");
  return value;
}

for (const name of DASHBOARDS) {
  const value = copyJson(
    path.join(published, "dashboards", `${name}.json`),
    path.join(root, "src", "data", "live", `dashboard-${name}.json`),
    (doc, source) => {
      if (!doc || typeof doc !== "object" || !("data" in doc) || !doc.generated_at) {
        throw new Error(`${source}: expected {"generated_at", "data"}`);
      }
    }
  );
  console.log(`dashboard ${name}: generated ${value.generated_at}`);
}

for (const sport of PIPELINE_HEALTH) {
  const value = copyJson(
    path.join(published, "pipeline_health", `${sport}.json`),
    path.join(root, "src", "data", "live", `pipeline-health-${sport}.json`),
    (doc, source) => {
      if (!doc || typeof doc !== "object" || Array.isArray(doc)) {
        throw new Error(`${source}: expected a JSON object`);
      }
    }
  );
  console.log(`pipeline health ${sport}: generated ${value.generated_at_utc || "unknown"}`);
}

console.log("LIVE DATA SNAPSHOTS: PASS");
