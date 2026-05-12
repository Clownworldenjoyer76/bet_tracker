import { fetchCSV } from "./csv.js";

let cachedMaps = null;

export async function loadMLBMaps() {
  if (cachedMaps) return cachedMaps;

  const [pitchers, teams, venues] = await Promise.all([
    fetchCSV("win/baseball/maps/mlb_pitcher_ids.csv"),
    fetchCSV("win/baseball/maps/mlb_team_ids.csv"),
    fetchCSV("win/baseball/maps/mlb_venue_ids.csv"),
  ]);

  const pitcherById = {};
  const teamById = {};
  const venueById = {};

  pitchers.rows.forEach(row => {
    if (row.pitcher_id) pitcherById[String(row.pitcher_id)] = row;
  });

  teams.rows.forEach(row => {
    if (row.team_id) teamById[String(row.team_id)] = row;
  });

  venues.rows.forEach(row => {
    if (row.venue_id) venueById[String(row.venue_id)] = row;
  });

  cachedMaps = {
    pitcherById,
    teamById,
    venueById,
  };

  return cachedMaps;
}

export function pitcherName(id, maps) {
  if (!id) return "";

  return maps?.pitcherById?.[String(id)]?.full_name || "";
}

export function venueName(id, maps) {
  if (!id) return "";

  return maps?.venueById?.[String(id)]?.venue_name || "";
}

export function teamName(id, maps) {
  if (!id) return "";

  return maps?.teamById?.[String(id)]?.name || "";
}
