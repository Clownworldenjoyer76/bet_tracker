#!/usr/bin/env python3
"""
# docs/win/mma/ufc/scripts/03_select/03_select.py

Filters edge output using rules defined in docs/win/mma/ufc/config/markets.yaml.

Input:
    docs/win/mma/ufc/02_edges/{date}_ufc_edges.csv
    docs/win/mma/ufc/config/markets.yaml

Output:
    docs/win/mma/ufc/03_select/{date}_ufc_select.csv
"""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

# --- Paths ---
EDGES_DIR = Path("docs/win/mma/ufc/02_edges")
CONFIG_PATH = Path("docs/win/mma/ufc/config/markets.yaml")
OUT_DIR = Path("docs/win/mma/ufc/03_select")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Load config ---
with CONFIG_PATH.open(encoding="utf-8") as f:
    config = yaml.safe_load(f)

ml_config = config["ufc"]["moneyline"]

enabled = ml_config.get("enabled", True)
pick_pref = ml_config.get("pick_preference", "best_ev")

odds_bands = ml_config.get("odds_bands", [])
edge_bands = ml_config.get("edge_bands", [])
ev_bands = ml_config.get("ev_bands", [])
kelly_bands = ml_config.get("kelly_bands", [])

model_prob_min = ml_config.get("model_probability_minimum", 0.0)
dratings_prob_min = ml_config.get("dratings_probability_minimum", 0.0)


def safe_float(val):
    try:
        if val is None:
            return None

        s = str(val).strip()
        if s == "":
            return None

        return float(s.replace("+", ""))
    except Exception:
        return None


def ml_to_float(ml_str):
    return safe_float(ml_str)


def in_any_band(value, bands):
    """Returns True if value falls within at least one [min, max] band."""
    v = safe_float(value)
    if v is None:
        return False

    try:
        return any(float(lo) <= v <= float(hi) for lo, hi in bands)
    except Exception:
        return False


def pick_metric_from_values(candidate: dict, pref: str) -> float:
    """
    Return the metric value used for final sorting and within-fight selection.

    Uses candidate output keys, not raw row keys.
    """
    mapping = {
        "best_ev": "ev",
        "best_edge": "edge",
        "best_kelly": "kelly",
        "best_model_prob": "model_prob",
        "best_dratings_prob": "dratings_prob",
    }

    col = mapping.get(pref, "ev")
    return safe_float(candidate.get(col)) or 0.0


def passes_filters(ml, edge, ev, kelly, model_prob, dratings_prob):
    if not enabled:
        return False

    if odds_bands and not in_any_band(ml, odds_bands):
        return False

    if edge_bands and not in_any_band(edge, edge_bands):
        return False

    if ev_bands and not in_any_band(ev, ev_bands):
        return False

    if kelly_bands and not in_any_band(kelly, kelly_bands):
        return False

    # Required when configured.
    # Blank / missing / non-numeric model probability now fails.
    if model_prob_min is not None:
        model_prob_val = safe_float(model_prob)
        if model_prob_val is None or model_prob_val < float(model_prob_min):
            return False

    # Required when configured.
    # Blank / missing / non-numeric DRatings probability now fails.
    if dratings_prob_min is not None:
        dratings_prob_val = safe_float(dratings_prob)
        if dratings_prob_val is None or dratings_prob_val < float(dratings_prob_min):
            return False

    return True


def make_candidate(row: dict, fighter_key: str) -> dict:
    """
    Build one fighter candidate from a fight row.

    fighter_key:
        f1 = fighter_1 side
        f2 = fighter_2 side
    """
    if fighter_key == "f1":
        return {
            "match_date": row["match_date"],
            "fighter": row["fighter_1"],
            "opponent": row["fighter_2"],
            "moneyline": row["moneyline_f1"],
            "implied_prob": row["implied_prob_f1"],
            "model_prob": row["model_prob_f1"],
            "dratings_prob": row["dratings_prob_f1"],
            "edge": row["edge_f1"],
            "ev": row["ev_f1"],
            "kelly": row["kelly_f1"],
        }

    return {
        "match_date": row["match_date"],
        "fighter": row["fighter_2"],
        "opponent": row["fighter_1"],
        "moneyline": row["moneyline_f2"],
        "implied_prob": row["implied_prob_f2"],
        "model_prob": row["model_prob_f2"],
        "dratings_prob": row["dratings_prob_f2"],
        "edge": row["edge_f2"],
        "ev": row["ev_f2"],
        "kelly": row["kelly_f2"],
    }


def candidate_passes(row: dict, fighter_key: str) -> bool:
    """
    Apply filters to one fighter side from the raw edge row.
    """
    suffix = "_f1" if fighter_key == "f1" else "_f2"

    ml = ml_to_float(row.get(f"moneyline{suffix}"))
    edge = safe_float(row.get(f"edge{suffix}"))
    ev = safe_float(row.get(f"ev{suffix}"))
    kelly = safe_float(row.get(f"kelly{suffix}"))
    model_prob = safe_float(row.get(f"model_prob{suffix}"))
    dratings_prob = safe_float(row.get(f"dratings_prob{suffix}"))

    return passes_filters(
        ml=ml,
        edge=edge,
        ev=ev,
        kelly=kelly,
        model_prob=model_prob,
        dratings_prob=dratings_prob,
    )


# --- Process each edges file ---
edges_files = sorted(EDGES_DIR.glob("*_ufc_edges.csv"))

if not edges_files:
    print("No edges files found.")
    raise SystemExit(1)


for edges_file in edges_files:
    date_str = edges_file.stem.replace("_ufc_edges", "")

    with edges_file.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"No rows in {edges_file.name}, skipping")
        continue

    selected = []

    for row in rows:
        candidates = []

        # Check fighter 1
        if candidate_passes(row, "f1"):
            c1 = make_candidate(row, "f1")
            c1["_sort_val"] = pick_metric_from_values(c1, pick_pref)
            candidates.append(c1)

        # Check fighter 2
        if candidate_passes(row, "f2"):
            c2 = make_candidate(row, "f2")
            c2["_sort_val"] = pick_metric_from_values(c2, pick_pref)
            candidates.append(c2)

        # Pick best candidate from this fight per pick_preference
        if candidates:
            best = max(candidates, key=lambda x: x["_sort_val"])
            selected.append(best)

    # Sort all selected picks by the same pick_preference used above.
    selected.sort(key=lambda x: x["_sort_val"], reverse=True)

    for row in selected:
        row.pop("_sort_val", None)

    out_file = OUT_DIR / f"{date_str}_ufc_select.csv"

    if selected:
        with out_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(selected[0].keys()))
            writer.writeheader()
            writer.writerows(selected)

        print(f"WROTE {out_file} ({len(selected)} picks)")

    else:
        print(f"No picks passed filters for {date_str}")
