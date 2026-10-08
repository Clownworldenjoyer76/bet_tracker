const fs = require("fs");
const path = require("path");

const BASE =
  "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/docs/win/hockey/nhl/05_final_scores/";

const FILES = {
  bets:
    BASE + "graded/NHL_final.csv",

  market_tally:
    BASE + "nhl_market_tally.csv",

  moneyline_ev:
    BASE + "reports/moneyline/nhl_moneyline_by_ev.csv",

  moneyline_kelly:
    BASE + "reports/moneyline/nhl_moneyline_by_kelly.csv",

  moneyline_odds:
    BASE + "reports/moneyline/nhl_moneyline_by_odds.csv",

  moneyline_win_prob:
    BASE + "reports/moneyline/nhl_moneyline_by_win_prob.csv",

  puckline_ev:
    BASE + "reports/puckline/nhl_puck_line_by_ev.csv",

  puckline_kelly:
    BASE + "reports/puckline/nhl_puck_line_by_kelly.csv",

  puckline_odds:
    BASE + "reports/puckline/nhl_puck_line_by_odds.csv",

  puckline_side:
    BASE + "reports/puckline/nhl_puck_line_by_side.csv",

  puckline_win_prob:
    BASE + "reports/puckline/nhl_puck_line_by_win_prob.csv",

  total_ev:
    BASE + "reports/total/nhl_total_by_ev.csv",

  total_kelly:
    BASE + "reports/total/nhl_total_by_kelly.csv",

  total_odds:
    BASE + "reports/total/nhl_total_by_odds.csv",

  total_side:
    BASE + "reports/total/nhl_total_by_side.csv",

  total_range:
    BASE + "reports/total/nhl_total_by_total_range.csv",

  total_win_prob:
    BASE + "reports/total/nhl_total_by_win_prob.csv"
};

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

  const headers = rows[0].map(h => h.trim());

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
      `${name}: HTTP ${response.status} ${response.statusText}`
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

  const outputPath = path.resolve(
    "src",
    "data",
    "nhl-dashboard.json"
  );

  fs.mkdirSync(path.dirname(outputPath), {
    recursive: true
  });

  fs.writeFileSync(
    outputPath,
    JSON.stringify(data, null, 2),
    "utf8"
  );

  console.log("");
  console.log("NHL DATA EXTRACTION: PASS");
  console.log(`Datasets: ${Object.keys(data).length}`);
  console.log(`Bet rows: ${data.bets.length}`);
  console.log(`Market tally rows: ${data.market_tally.length}`);
  console.log(`Output: ${outputPath}`);
}

main().catch(error => {
  console.error("");
  console.error("NHL DATA EXTRACTION: FAILED");
  console.error(error.message);
  process.exit(1);
});
