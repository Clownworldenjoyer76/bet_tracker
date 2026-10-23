#!/usr/bin/env python3
"""Seed neutral-bias cleaned NBA ensemble files for the 2026 opening backfill only.

Generated historical predictions are retrospective; they are NOT asserted to have
existed before tipoff. No timestamp or point-in-time provenance is fabricated.
Existing cleaned files are preserved after game-ID validation.
"""
import csv
import os
from pathlib import Path

ROOT = Path('docs/win/basketball/00_intake')
EXPECTED = {
 '2026_10_20': {'401909088', '401909089', '401909090'},
 '2026_10_21': {'401909834', '401909835', '401909836', '401909091', '401909837', '401909838', '401909839', '401909840', '401909092', '401909841', '401909842'},
 '2026_10_22': {'401909093', '401909094'},
}

def read(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)

def main():
    if os.getenv('BASKETBALL_FULL_REBUILD', '').strip().lower() not in ('1','true','yes','on'):
        print('NBA BACKFILL: skipped (not full rebuild)')
        return
    ready = []
    for day, expected in EXPECTED.items():
        filename = f'{day}_NBA_predictions.csv'
        src = ROOT / 'predictions_ensemble/nba' / filename
        dst = ROOT / 'predictions/predictions_cleaned/nba' / filename
        if not src.is_file():
            raise RuntimeError(f'NBA BACKFILL missing reconstructed ensemble: {src}')
        headers, rows = read(src)
        ids = [r.get('game_id', '').strip() for r in rows]
        if len(ids) != len(set(ids)) or set(ids) != expected:
            raise RuntimeError(f'NBA BACKFILL incomplete ensemble {day}: expected={sorted(expected)} found={sorted(ids)}')
        if dst.exists():
            _headers, current = read(dst)
            current_ids = [r.get('game_id', '').strip() for r in current]
            if len(current_ids) != len(set(current_ids)) or set(current_ids) != expected:
                raise RuntimeError(f'NBA BACKFILL existing cleaned file is incomplete: {dst}')
            print(f'NBA BACKFILL existing cleaned preserved: {dst}')
            continue
        for col in ('bias_applied','margin_bias','total_bias'):
            if col not in headers: headers.append(col)
        for r in rows:
            r['bias_applied'] = '1'
            r['margin_bias'] = '0.000'
            r['total_bias'] = '0.000'
        ready.append((dst, headers, rows))
    # Validate all three dates before making any writes.
    for dst, headers, rows in ready:
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix('.csv.tmp')
        try:
            with tmp.open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
                writer.writeheader(); writer.writerows(rows)
            tmp.replace(dst)
        finally:
            if tmp.exists(): tmp.unlink()
        print(f'NBA BACKFILL cleaned ensemble seeded with zero historical bias: {dst} ({len(rows)})')
    print('NBA BACKFILL HISTORICAL CLEANED INPUTS: PASS')

if __name__ == '__main__': main()
