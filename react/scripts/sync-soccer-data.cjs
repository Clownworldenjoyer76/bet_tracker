const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const source = path.resolve(root, "../app/frontend/src/assets/js/pages/soccer_dashboard.js");
const output = path.join(root, "src/data/soccer-dashboard.json");

const text = fs.readFileSync(source, "utf8");
const match = text.match(/const ALL_DATA\s*=\s*(\{[\s\S]*\});\s*document\.addEventListener/);

if (!match) throw new Error("Could not extract Soccer ALL_DATA");

const data = JSON.parse(match[1]);
for (const key of ["all","mls","epl","laliga","ligue1","seriea","bundesliga"]) {
  if (!data[key]) throw new Error(`Missing Soccer league: ${key}`);
}

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, JSON.stringify(data));

console.log("SOCCER DATA EXTRACTION: PASS");
