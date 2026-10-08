const fs = require("fs");
const path = require("path");

const BASE =
  "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/docs/win/football/cfb/04_final_results/reports/";

const FILES = {};

// Overview reports
const OVERVIEW = {
  bet_log: "cfb_bet_log.csv",
  calibration: "cfb_calibration_by_probability.csv",
  probability_metrics: "cfb_probability_metrics.csv",
  cumulative_units_by_week: "cfb_cumulative_units_by_week.csv",
  summary_overall: "cfb_summary_overall.csv",
  summary_by_market: "cfb_summary_by_market.csv",
  summary_by_side_group: "cfb_summary_by_side_group.csv",
  summary_by_week: "cfb_summary_by_week.csv",
  summary_by_day_night: "cfb_summary_by_day_night.csv",
};

for (const [key, file] of Object.entries(OVERVIEW)) {
  FILES[key] = BASE + "overview/" + file;
}

// Per-market reports.
// dimensions: files named <prefix><dimension>.csv
// splits: files named <prefix><dimension>_<suffix>.csv
const MARKETS = [
  {
    key: "moneyline",
    dir: "moneyline",
    prefix: "cfb_moneyline_by_",
    dimensions: ["ev", "home_away", "kelly", "odds", "win_prob"],
    splits: {
      ev: "home_away_summary",
      kelly: "home_away_summary",
      odds: "home_away_summary",
      win_prob: "home_away_summary",
    },
  },
  {
    key: "spread",
    dir: "spread",
    prefix: "cfb_spread_by_",
    dimensions: [
      "ev",
      "favorite_underdog",
      "home_away",
      "kelly",
      "line",
      "odds",
      "win_prob",
    ],
    splits: {
      ev: "home_away_summary",
      kelly: "home_away_summary",
      line: "home_away_summary",
      odds: "home_away_summary",
      win_prob: "home_away_summary",
    },
  },
  {
    key: "total",
    dir: "totals",
    prefix: "cfb_total_by_",
    dimensions: ["ev", "kelly", "odds", "over_under", "total_range", "win_prob"],
    splits: {
      ev: "over_under_summary",
      kelly: "over_under_summary",
      odds: "over_under_summary",
      total_range: "over_under_summary",
      win_prob: "over_under_summary",
    },
  },
];

for (const market of MARKETS) {
  for (const dimension of market.dimensions) {
    FILES[`${market.key}_by_${dimension}`] =
      BASE + market.dir + "/" + market.prefix + dimension + ".csv";

    const suffix = market.splits[dimension];

    if (suffix) {
      FILES[`${market.key}_by_${dimension}_split`] =
        BASE +
        market.dir +
        "/" +
        market.prefix +
        dimension +
        "_" +
        suffix +
        ".csv";
    }
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

  const outputPath = path.resolve("src", "data", "cfb-dashboard.json");

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  fs.writeFileSync(outputPath, JSON.stringify(data, null, 2), "utf8");

  console.log("");
  console.log("CFB DATA EXTRACTION: PASS");
  console.log(`Datasets: ${Object.keys(data).length}`);
  console.log(`Bet log rows: ${data.bet_log.length}`);
  console.log(`Output: ${outputPath}`);
}

main().catch(error => {
  console.error("");
  console.error("CFB DATA EXTRACTION: FAILED");
  console.error(error.message);
  process.exit(1);
});
