export function parseCSV(text) {
  const clean = String(text || "").replace(/^\uFEFF/, "").trim();
  if (!clean) return [];

  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let i = 0; i < clean.length; i++) {
    const ch = clean[i];
    const next = clean[i + 1];

    if (ch === '"') {
      if (quoted && next === '"') {
        cell += '"';
        i++;
      } else {
        quoted = !quoted;
      }
      continue;
    }

    if (ch === "," && !quoted) {
      row.push(cell.trim());
      cell = "";
      continue;
    }

    if ((ch === "\n" || ch === "\r") && !quoted) {
      if (ch === "\r" && next === "\n") i++;
      row.push(cell.trim());
      rows.push(row);
      row = [];
      cell = "";
      continue;
    }

    cell += ch;
  }

  row.push(cell.trim());
  rows.push(row);

  if (rows.length < 2) return [];

  const headers = rows[0].map(h =>
    String(h || "")
      .replace(/^\uFEFF/, "")
      .replace(/^"+|"+$/g, "")
      .trim()
  );

  return rows
    .slice(1)
    .filter(r => r.some(v => String(v || "").trim() !== ""))
    .map(vals => {
      const obj = {};
      headers.forEach((h, i) => {
        obj[h] = String(vals[i] ?? "").trim();
      });
      return obj;
    });
}

export async function fetchCSV(path) {
  if (!path) return { ok: false, path, rows: [] };

  try {
    const cacheBust = path.includes("?") ? `&v=${Date.now()}` : `?v=${Date.now()}`;
    const res = await fetch(`${path}${cacheBust}`, { cache: "no-store" });

    if (!res.ok) return { ok: false, path, rows: [] };

    const text = await res.text();
    return { ok: true, path, rows: parseCSV(text) };
  } catch {
    return { ok: false, path, rows: [] };
  }
}

export async function fetchFirstCSV(paths) {
  for (const path of paths || []) {
    const res = await fetchCSV(path);
    if (res.ok) return res;
  }

  return { ok: false, path: "", rows: [] };
}
