export function isPresent(value) {
  return value !== undefined && value !== null && String(value).trim() !== "";
}

export function esc(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[char]));
}

export function fmt(value) {
  return isPresent(value) ? esc(String(value).trim()) : "";
}

export function dateToUnderscore(dateStr) {
  return String(dateStr || "").trim().replaceAll("-", "_");
}

export function formatDate(value) {
  if (!isPresent(value)) return "";

  const raw = String(value).trim().replaceAll("-", "_");
  const parts = raw.split("_");

  if (parts.length < 3) return fmt(value);

  const yyyy = parts[0];
  const mm = parts[1].padStart(2, "0");
  const dd = parts[2].padStart(2, "0");

  return `${mm}/${dd}/${String(yyyy).slice(-2)}`;
}

export function formatTime(value) {
  if (!isPresent(value)) return "";

  const raw = String(value).trim();

  const alreadyAmPm = raw.match(/^(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)$/i);
  if (alreadyAmPm) {
    return `${parseInt(alreadyAmPm[1], 10)}:${alreadyAmPm[2]} ${alreadyAmPm[3].toUpperCase()}`;
  }

  const military = raw.match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
  if (military) {
    let hour = parseInt(military[1], 10);
    const minute = military[2];
    const suffix = hour >= 12 ? "PM" : "AM";

    if (hour === 0) hour = 12;
    else if (hour > 12) hour -= 12;

    return `${hour}:${minute} ${suffix}`;
  }

  return fmt(raw);
}

export function parseSortTime(value) {
  if (!isPresent(value)) return 99999;

  const formatted = formatTime(value);
  const match = formatted.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);

  if (!match) return 99999;

  let hour = parseInt(match[1], 10);
  const minute = parseInt(match[2], 10);
  const suffix = match[3].toUpperCase();

  if (suffix === "PM" && hour !== 12) hour += 12;
  if (suffix === "AM" && hour === 12) hour = 0;

  return hour * 60 + minute;
}

export function formatProb(value) {
  if (!isPresent(value)) return "";

  const number = parseFloat(value);
  if (Number.isNaN(number)) return fmt(value);

  return `${(number <= 1 ? number * 100 : number).toFixed(1)}%`;
}

export function formatOneDecimal(value) {
  if (!isPresent(value)) return "";

  const number = parseFloat(value);
  if (Number.isNaN(number)) return fmt(value);

  return number.toFixed(1);
}

export function formatOdds(value) {
  if (!isPresent(value)) return "";

  const raw = String(value).trim();
  if (/^[+-]/.test(raw)) return raw;

  const number = parseFloat(raw);
  if (Number.isNaN(number)) return fmt(raw);

  return number > 0 ? `+${number}` : String(number);
}

export function decimalToAmerican(value) {
  if (!isPresent(value)) return "";

  const decimal = parseFloat(value);
  if (Number.isNaN(decimal) || decimal <= 1) return "";

  if (decimal >= 2) return `+${Math.round((decimal - 1) * 100)}`;

  return String(Math.round(-100 / (decimal - 1)));
}

export function handLabel(value) {
  const hand = String(value || "").trim().toUpperCase();

  if (hand === "R") return "Right Handed";
  if (hand === "L") return "Left Handed";

  return "";
}

export function plusLine(value) {
  if (!isPresent(value)) return "";

  const raw = String(value).trim();
  const number = parseFloat(raw);

  if (Number.isNaN(number)) return fmt(raw);

  return number > 0 ? `+${number}` : String(number);
}
