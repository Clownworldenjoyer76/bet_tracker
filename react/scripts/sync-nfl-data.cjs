const fs = require("fs");
const path = require("path");

const BASE =
  "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/docs/win/football/nfl/04_final_results/reports/";

const FILES = {};

// Overview reports
const OVERVIEW = {
  bet_log: "nfl_bet_log.csv",
  summary_overall: "nfl_summary_overall.csv",
  summary_by_market: "nfl_summary_by_market.csv",
  summary_by_side_group: "nfl_summary_by_side_group.csv",
  summary_by_week: "nfl_summary_by_week.csv",
  summary_by_date: "nfl_summary_by_date.csv",
  summary_by_day_night: "nfl_summary_by_day_night.csv",
  summary_by_season_type: "nfl_summary_by_season_type.csv",
};

for (const [key, file] of Object.entries(OVERVIEW)) {
  FILES[key] = BASE + "overview/" + file;
}

// Per-market reports. Folder name, file prefix and key prefix per market.
const MARKETS = [
  {
    key: "moneyline",
    dir: "moneyline",
    prefix: "nfl_moneyline_by_",
    dimensions: ["ev", "kelly", "odds", "week", "win_prob"],
  },
  {
    key: "spread",
    dir: "spread",
    prefix: "nfl_spread_by_",
    dimensions: [
      "ev",
      "kelly",
      "line",
      "odds",
      "side",
      "spread_range",
      "week",
      "win_prob",
    ],
  },
  {
    key: "total",
    dir: "totals",
    prefix: "nfl_total_by_",
    dimensions: [
      "ev",
      "kelly",
      "line",
      "odds",
      "side",
      "total_range",
      "week",
      "win_prob",
    ],
  },
];

for (const market of MARKETS) {
  for (const dimension of market.dimensions) {
    const file = market.prefix + dimension;

    FILES[`${market.key}_by_${dimension}`] =
      BASE + market.dir + "/" + file + ".csv";

    FILES[`${market.key}_by_${dimension}_side_summary`] =
      BASE + market.dir + "/" + file + "_side_summary.csv";
  }
}

function parseCSV(text) {
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1];

    if (ch === '"' && quoted && next === '"') {
      value += '"';
      i++;
      continue;
    }

    if (ch === '"') {
      quoted = !quoted;
      continue;
    }

    if (ch === "," && !quoted) {
      row.push(value);
      value = "";
      continue;
    }

    if ((ch === "\n" || ch === "\r") && !quoted) {
      if (ch === "\r" && next === "\n") i++;

      row.push(value);
      value = "";

      if (row.some(v => v !== "")) {
        rows.push(row);
      }

      row = [];
      continue;
    }

    value += ch;
  }

  if (value !== "" || row.length) {
    row.push(value);

    if (row.some(v => v !== "")) {
      rows.push(row);
    }
  }

  if (!rows.length) return [];

  const headers = rows[0].map(h => h.replace(/^﻿/, "").trim());

  return rows.slice(1).map(values => {
    const obj = {};

    headers.forEach((header, index) => {
      obj[header] = values[index] ?? "";
    });

    return obj;
  });
}

async function fetchCSV(name, url) {
  process.stdout.write(`Fetching ${name}... `);

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(
      `${name}: HTTP ${response.status} ${response.statusText} (${url})`
    );
  }

  const text = await response.text();
  const rows = parseCSV(text);

  console.log(`PASS (${rows.length} rows)`);

  return rows;
}

async function main() {
  const data = {};

  for (const [name, url] of Object.entries(FILES)) {
    data[name] = await fetchCSV(name, url);
  }

  const outputPath = path.resolve("src", "data", "nfl-dashboard.json");

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  fs.writeFileSync(outputPath, JSON.stringify(data, null, 2), "utf8");

  console.log("");
  console.log("NFL DATA EXTRACTION: PASS");
  console.log(`Datasets: ${Object.keys(data).length}`);
  console.log(`Bet log rows: ${data.bet_log.length}`);
  console.log(`Output: ${outputPath}`);
}

main().catch(error => {
  console.error("");
  console.error("NFL DATA EXTRACTION: FAILED");
  console.error(error.message);
  process.exit(1);
});
