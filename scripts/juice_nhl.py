#!/usr/bin/env python3
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


INPUT_DIR = Path("docs/win/edge")
OUTPUT_DIR = Path("docs/win/final")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JUICE_TABLE_PATH = Path("config/nhl/nhl_juice_table.csv")


@dataclass(frozen=True)
class JuiceRule:
    market_type: str          # moneyline / totals / spread
    band_low: float           # inclusive
    band_high: float          # exclusive (except last band)
    side: str                 # any / over / under / favorite / underdog
    extra_juice_pct: float    # 0.15 for +15%
    notes: str = ""


def decimal_to_american(decimal: float) -> int:
    if decimal >= 2.0:
        return int(round(100 * (decimal - 1)))
    return int(round(-100 / (decimal - 1)))


def american_to_decimal(american: int) -> float:
    if american > 0:
        return 1 + (american / 100)
    return 1 + (100 / abs(american))


def load_juice_rules(path: Path) -> List[JuiceRule]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config: {path}")

    rules: List[JuiceRule] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"market_type", "band_low", "band_high", "side", "extra_juice_pct"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"Invalid schema in {path}. Required columns: {sorted(required)}"
            )

        for row in reader:
            mt = (row.get("market_type") or "").strip().lower()
            if not mt:
                continue

            rules.append(
                JuiceRule(
                    market_type=mt,
                    band_low=float(row["band_low"]),
                    band_high=float(row["band_high"]),
                    side=(row.get("side") or "any").strip().lower(),
                    extra_juice_pct=float(row["extra_juice_pct"]),
                    notes=(row.get("notes") or "").strip(),
                )
            )

    # Deterministic band matching
    rules.sort(key=lambda r: (r.market_type, r.side, r.band_low, r.band_high))
    return rules


def match_rule(
    rules: List[JuiceRule],
    market_type: str,
    value: float,
    side: str = "any",
) -> Optional[JuiceRule]:
    mt = market_type.strip().lower()
    sd = side.strip().lower()

    # Prefer exact side rules over "any"
    exact = [r for r in rules if r.market_type == mt and r.side == sd]
    any_side = [r for r in rules if r.market_type == mt and r.side == "any"]

    def find_match(cands: List[JuiceRule]) -> Optional[JuiceRule]:
        for r in cands:
            # [low, high) by default
            if r.band_low <= value < r.band_high:
                return r
        # if value is exactly at the top end, allow last band to catch it
        if cands:
            top = max(cands, key=lambda x: x.band_high)
            if value == top.band_high:
                return top
        return None

    return find_match(exact) or find_match(any_side)


def process_file(path: Path, rules: List[JuiceRule]):
    suffix = path.name.replace("edge_nhl_", "")
    output_path = OUTPUT_DIR / f"final_nhl_{suffix}"

    with path.open(newline="", encoding="utf-8") as infile, \
         output_path.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        if not reader.fieldnames:
            raise ValueError(f"{path} has no headers")

        fieldnames = list(reader.fieldnames)
        if "personally_acceptable_american_odds" not in fieldnames:
            fieldnames.append("personally_acceptable_american_odds")
        if "personally_acceptable_decimal_odds" not in fieldnames:
            fieldnames.append("personally_acceptable_decimal_odds")

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            raw_p = (row.get("win_probability") or "").strip()
            raw_acc_dec = (row.get("acceptable_decimal_odds") or "").strip()
            raw_acc_am = (row.get("acceptable_american_odds") or "").strip()

            if not raw_p or not raw_acc_dec or not raw_acc_am:
                row["personally_acceptable_american_odds"] = ""
                row["personally_acceptable_decimal_odds"] = ""
                writer.writerow(row)
                continue

            try:
                p = float(raw_p)
                base_decimal = float(raw_acc_dec)
                base_american = int(float(raw_acc_am))
            except ValueError:
                row["personally_acceptable_american_odds"] = ""
                row["personally_acceptable_decimal_odds"] = ""
                writer.writerow(row)
                continue

            rule = match_rule(rules, market_type="moneyline", value=p, side="any")
            edge_pct = rule.extra_juice_pct if rule else 0.0

            personal_decimal = base_decimal * (1.0 + edge_pct)
            personal_american = decimal_to_american(personal_decimal)

            # Cap: favorites may not flip past +120
            if base_american < 0 and personal_american > 120:
                personal_american = 120
                personal_decimal = american_to_decimal(personal_american)

            # Cap: extreme tails
            if p < 0.10 and personal_american > 2500:
                personal_american = 2500
                personal_decimal = american_to_decimal(personal_american)

            row["personally_acceptable_american_odds"] = personal_american
            row["personally_acceptable_decimal_odds"] = round(personal_decimal, 6)
            writer.writerow(row)

    print(f"Created {output_path}")


def main():
    rules = load_juice_rules(JUICE_TABLE_PATH)

    files = sorted(INPUT_DIR.glob("edge_nhl_*.csv"))
    if not files:
        raise FileNotFoundError(f"No NHL edge files found in {INPUT_DIR}")

    for path in files:
        process_file(path, rules)


if __name__ == "__main__":
    main()
