#!/usr/bin/env python3
"""MORLEY 00C (reconstruido): convierte caché 00B a inventario CSV compatible con 00D.

Lee outputs/catalogs/sia_cache/{spherex_dr1,spherex_qr3}.xml.
Escribe outputs/catalogs/spherex_sia_inventory.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from morley_sia import COLLECTIONS, parse_inventory

HOME = Path(__file__).resolve().parent
CATALOG = HOME / 'outputs' / 'catalogs'
CACHE = CATALOG / 'sia_cache'
FIELDS = ('collection', 'detector', 'obs_id', 't_min_mjd', 'access_url')


def write_csv(path, rows):
    tmp = path.with_suffix('.csv.part')
    with tmp.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def main():
    p = argparse.ArgumentParser(description='MORLEY 00C - inventario SIA2 desde cache 00B')
    p.add_argument('--detector', choices=['all'] + [f'D{i}' for i in range(1, 7)], default='D6')
    a = p.parse_args()
    outputs = {}
    rows = []
    for collection in COLLECTIONS:
        file = CACHE / f'{collection}.xml'
        if not file.exists():
            p.error(f'Falta cache de 00B: {file}. Ejecuta primero 00b_discover_sia_candidates.py')
        try:
            result = parse_inventory(file.read_bytes(), collection)
        except Exception as exc:
            p.error(f'Cache {file} invalido: {exc}')
        outputs[collection] = len(result)
        rows.extend(result)
    if not rows:
        p.error('SIA2 devolvio 0 observaciones Level-2 validas; no se crea catalogo vacio')
    rows.sort(key=lambda x: (x['detector'], x['collection'], float(x['t_min_mjd'])))
    CATALOG.mkdir(parents=True, exist_ok=True)
    inv = CATALOG / 'spherex_sia_inventory.csv'
    write_csv(inv, rows)
    subset = [x for x in rows if a.detector == 'all' or x['detector'] == a.detector]
    write_csv(CATALOG / 'candidatos_d6_sia.csv', [x for x in rows if x['detector'] == 'D6'])
    summary = {
        'schema_version': 'morley.sia_inventory.v1',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'source': 'cache_IRSA_SIA2_from_00B',
        'counts_by_collection': outputs,
        'counts_by_detector': dict(Counter(x['detector'] for x in rows)),
        'observations_total': len(rows),
        'selected_detector': a.detector,
        'selected_detector_count': len(subset),
        'inventory': inv.relative_to(HOME).as_posix(),
        'science_validated': False,
    }
    (CATALOG / 'spherex_sia_report.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'MORLEY 00C - Catalogo SIA2: {len(rows)} observaciones totales | {a.detector}: {len(subset)}')
    for key, count in outputs.items():
        print(f'  {key}: {count}')
    print('CSV:', inv)
    print('Aviso: este inventario contiene metadatos, NO FITS validados.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
