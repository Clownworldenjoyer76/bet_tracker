const fs = require("fs");
const path = require("path");
const vm = require("vm");

const sourcePath = path.resolve(
  "..",
  "app",
  "frontend",
  "src",
  "assets",
  "js",
  "pages",
  "nba_dashboard.js"
);

const outputPath = path.resolve(
  "src",
  "data",
  "nba-dashboard.json"
);

function extractExpression(source, marker) {
  const markerIndex = source.indexOf(marker);

  if (markerIndex < 0) {
    throw new Error(`Could not locate ${marker}`);
  }

  let start = markerIndex + marker.length;

  while (/\s/.test(source[start] || "")) {
    start++;
  }

  if (source[start] !== "{" && source[start] !== "[") {
    throw new Error(
      `Expected object/array after ${marker}, found ${JSON.stringify(source[start])}`
    );
  }

  const opening = source[start];
  const closing = opening === "{" ? "}" : "]";

  let depth = 0;
  let quote = null;
  let escaped = false;
  let lineComment = false;
  let blockComment = false;

  for (let i = start; i < source.length; i++) {
    const ch = source[i];
    const next = source[i + 1];

    if (lineComment) {
      if (ch === "\n") {
        lineComment = false;
      }
      continue;
    }

    if (blockComment) {
      if (ch === "*" && next === "/") {
        blockComment = false;
        i++;
      }
      continue;
    }

    if (quote) {
      if (escaped) {
        escaped = false;
        continue;
      }

      if (ch === "\\") {
        escaped = true;
        continue;
      }

      if (ch === quote) {
        quote = null;
      }

      continue;
    }

    if (ch === "/" && next === "/") {
      lineComment = true;
      i++;
      continue;
    }

    if (ch === "/" && next === "*") {
      blockComment = true;
      i++;
      continue;
    }

    if (ch === '"' || ch === "'" || ch === "`") {
      quote = ch;
      continue;
    }

    if (ch === opening) {
      depth++;
      continue;
    }

    if (ch === closing) {
      depth--;

      if (depth === 0) {
        return source.slice(start, i + 1);
      }
    }
  }

  throw new Error(`Could not locate end of ${marker}`);
}

function main() {
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`NBA source not found: ${sourcePath}`);
  }

  const source = fs.readFileSync(sourcePath, "utf8");

  const expression = extractExpression(
    source,
    "const ALL_DATA ="
  );

  let data;

  try {
    data = vm.runInNewContext(`(${expression})`);
  } catch (error) {
    throw new Error(
      `Could not evaluate NBA ALL_DATA: ${error.message}`
    );
  }

  if (!data || typeof data !== "object") {
    throw new Error("NBA ALL_DATA did not evaluate to an object.");
  }

  fs.writeFileSync(
    outputPath,
    JSON.stringify(data, null, 2),
    "utf8"
  );

  const seasons = Object.keys(data);

  let leagueCount = 0;

  for (const season of seasons) {
    if (
      data[season] &&
      typeof data[season] === "object"
    ) {
      leagueCount += Object.keys(data[season]).length;
    }
  }

  console.log("");
  console.log("NBA DATA EXTRACTION: PASS");
  console.log(`Seasons: ${seasons.join(", ")}`);
  console.log(`Season/league datasets: ${leagueCount}`);
  console.log(`Output: ${outputPath}`);
}

main();
