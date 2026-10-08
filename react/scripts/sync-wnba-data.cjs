const fs = require("fs");
const path = require("path");

const sourcePath = path.resolve(
  "../app/frontend/src/assets/js/pages/wnba_dashboard.js"
);

const outputPath = path.resolve(
  "src/data/wnba-dashboard.json"
);

const source = fs.readFileSync(sourcePath, "utf8");
const marker = "const ALL_DATA =";
const markerIndex = source.indexOf(marker);

if (markerIndex < 0) {
  throw new Error("WNBA ALL_DATA declaration not found.");
}

let start = markerIndex + marker.length;

while (/\s/.test(source[start])) start++;

if (source[start] !== "{") {
  throw new Error("WNBA ALL_DATA does not begin with JSON object.");
}

let depth = 0;
let quoted = false;
let escaped = false;
let end = -1;

for (let i = start; i < source.length; i++) {
  const ch = source[i];

  if (quoted) {
    if (escaped) {
      escaped = false;
    } else if (ch === "\\") {
      escaped = true;
    } else if (ch === '"') {
      quoted = false;
    }
    continue;
  }

  if (ch === '"') {
    quoted = true;
    continue;
  }

  if (ch === "{") depth++;

  if (ch === "}") {
    depth--;

    if (depth === 0) {
      end = i + 1;
      break;
    }
  }
}

if (end < 0) {
  throw new Error("Could not locate end of WNBA ALL_DATA.");
}

const data = JSON.parse(source.slice(start, end));

if (!data.current?.leagues?.wnba) {
  throw new Error("Extracted WNBA data does not contain current.leagues.wnba.");
}

fs.mkdirSync(path.dirname(outputPath), { recursive: true });

fs.writeFileSync(
  outputPath,
  JSON.stringify(data, null, 2),
  "utf8"
);

console.log("WNBA DATA EXTRACTION: PASS");
console.log("WNBA output:", outputPath);
console.log("WNBA leagues:", Object.keys(data.current.leagues).join(", "));
