const fs = require("fs");

const sourcePath =
  "../app/frontend/src/assets/js/generated/ufc-dashboard.js";

const dataPath =
  "src/data/ufc-dashboard.json";

const columnsPath =
  "src/data/ufc-report-columns.json";

const source = fs.readFileSync(sourcePath, "utf8");

function extractLiteral(name) {
  const assignment = new RegExp(
    String.raw`(?:const|let|var)\s+${name}\s*=\s*`,
  );

  const match = assignment.exec(source);

  if (!match) {
    throw new Error(`Could not locate ${name}.`);
  }

  let start = match.index + match[0].length;

  while (
    start < source.length &&
    /\s/.test(source[start])
  ) {
    start++;
  }

  const opening = source[start];

  if (opening !== "{" && opening !== "[") {
    throw new Error(
      `${name} does not begin with an object or array.`,
    );
  }

  const closing = opening === "{" ? "}" : "]";

  let depth = 0;
  let quote = null;
  let escaped = false;

  for (let i = start; i < source.length; i++) {
    const ch = source[i];

    if (quote) {
      if (escaped) {
        escaped = false;
      } else if (ch === "\\") {
        escaped = true;
      } else if (ch === quote) {
        quote = null;
      }
      continue;
    }

    if (
      ch === '"' ||
      ch === "'" ||
      ch === "`"
    ) {
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

  throw new Error(`Could not locate end of ${name}.`);
}

function evaluateLiteral(name) {
  const literal = extractLiteral(name);

  try {
    return Function(
      `"use strict"; return (${literal});`,
    )();
  } catch (error) {
    throw new Error(
      `Could not evaluate ${name}: ${error.message}`,
    );
  }
}

const data = evaluateLiteral("DATA");
const columns = evaluateLiteral("REPORT_COLUMNS");

if (!data || typeof data !== "object") {
  throw new Error("UFC DATA is not an object.");
}

if (!data.headline || typeof data.headline !== "object") {
  throw new Error("UFC DATA.headline is missing.");
}

if (!data.reports || typeof data.reports !== "object") {
  throw new Error("UFC DATA.reports is missing.");
}

if (!Array.isArray(columns) || columns.length !== 12) {
  throw new Error(
    `Expected exactly 12 UFC report columns; found ${
      Array.isArray(columns) ? columns.length : "invalid"
    }.`,
  );
}

fs.writeFileSync(
  dataPath,
  JSON.stringify(data, null, 2),
  "utf8",
);

fs.writeFileSync(
  columnsPath,
  JSON.stringify(columns, null, 2),
  "utf8",
);

console.log("UFC DATA EXTRACTION: PASS");
console.log(`Reports: ${Object.keys(data.reports).join(", ")}`);
console.log(`Columns: ${columns.length}`);
