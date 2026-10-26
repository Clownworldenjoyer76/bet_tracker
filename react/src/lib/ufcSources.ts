// UFC consolidated frontend feeds. The selections file contains every fight;
// only rows with selected_fighter equal to a fighter in the matchup are picks.
const REPO_BASE = "https://raw.githubusercontent.com/Clownworldenjoyer76/bet_tracker/main/";
const INDEX_URL = "https://api.github.com/repos/Clownworldenjoyer76/bet_tracker/contents/frontend/data/ufc/pred_sb_sel?ref=main";
const SELECTION_DIR = "frontend/data/ufc/pred_sb_sel/";

type UfcRow = Record<string, string>;
type GithubItem = { type?: string; name?: string };

export async function findUfcEventDate(signal?: AbortSignal): Promise<string | null> {
  try {
    const res = await fetch(INDEX_URL, { cache: "no-store", signal });
    if (!res.ok) return null;
    const items: GithubItem[] = await res.json();
    if (!Array.isArray(items)) return null;
    const dates = items
      .filter((item) => item.type === "file")
      .map((item) => /^([0-9]{4}_[0-9]{2}_[0-9]{2})_pred_sb_sel_ufc\.csv$/i.exec(item.name || ""))
      .filter((m): m is RegExpExecArray => m !== null)
      .map((m) => m[1])
      .sort();
    if (!dates.length) return null;
    const today = new Date();
    const todayKey = [today.getFullYear(), String(today.getMonth() + 1).padStart(2, "0"), String(today.getDate()).padStart(2, "0")].join("_");
    return dates.find((d) => d >= todayKey) || dates[dates.length - 1];
  } catch (error) {
    if (!signal?.aborted) console.warn("Unable to discover UFC event dates:", error);
    return null;
  }
}

export async function fetchUfcSelection(date: string, signal?: AbortSignal): Promise<UfcRow[]> {
  const url = REPO_BASE + SELECTION_DIR + date + "_pred_sb_sel_ufc.csv";
  const res = await fetch(url, { cache: "no-store", signal });
  if (!res.ok) return [];
  const text = await res.text();
  const lines = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  // The defined feed has plain CSV cells; support standard quoted commas too.
  const parseLine = (line: string): string[] => {
    const values: string[] = [];
    let value = "";
    let quoted = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"') {
        if (quoted && line[i + 1] === '"') { value += '"'; i++; }
        else quoted = !quoted;
      } else if (c === "," && !quoted) {
        values.push(value.trim()); value = "";
      } else { value += c; }
    }
    values.push(value.trim());
    return values;
  };
  const headers = parseLine(lines[0]);
  return lines.slice(1).filter((line) => line.trim()).map((line) => {
    const values = parseLine(line);
    const row: UfcRow = {};
    headers.forEach((header, i) => { row[header] = values[i] ?? ""; });
    return row;
  });
}

export function toSelectedUfcRows(rows: UfcRow[]): UfcRow[] {
  return rows.flatMap((row) => {
    const selected = String(row.selected_fighter || "").trim();
    if (!selected) return [];
    const isF1 = selected.toLowerCase() === String(row.fighter_1 || "").trim().toLowerCase();
    const isF2 = selected.toLowerCase() === String(row.fighter_2 || "").trim().toLowerCase();
    if (!isF1 && !isF2) return [];
    const suffix = isF1 ? "f1" : "f2";
    return [{
      ...row,
      fighter: isF1 ? row.fighter_1 : row.fighter_2,
      opponent: isF1 ? row.fighter_2 : row.fighter_1,
      moneyline: row["moneyline_" + suffix] || "",
      implied_prob: row["implied_prob_" + suffix] || "",
      model_prob: row["model_prob_" + suffix] || "",
      edge: row["edge_" + suffix] || "",
      ev: row["ev_" + suffix] || "",
      kelly: row.selected_kelly || "",
    }];
  });
}