#!/usr/bin/env python3
"""MORLEY 00B (reconstruido): consultar SIA2 DR1 y QR3 y guardar caché VOTable.

Produce outputs/catalogs/sia_cache/spherex_dr1.xml y spherex_qr3.xml.
No descarga FITS ni afirma movimiento/variabilidad.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from morley_sia import COLLECTIONS, ENDPOINT, parse_inventory

HOME = Path(__file__).resolve().parent
CACHE = HOME / 'outputs' / 'catalogs' / 'sia_cache'
REPORT = HOME / 'outputs' / 'catalogs' / 'sia_discovery_00b.json'


def main():
    p = argparse.ArgumentParser(description='MORLEY 00B - consulta SIA2 a IRSA, DR1/QR3')
    p.add_argument('--ra', type=float, default=295.4097841)
    p.add_argument('--dec', type=float, default=-15.2231692)
    p.add_argument('--radius-deg', type=float, default=0.08)
    p.add_argument('--maxrec', type=int, default=10000)
    a = p.parse_args()
    if not (0 <= a.ra < 360 and -90 <= a.dec <= 90 and 0 < a.radius_deg <= 1 and 1 <= a.maxrec <= 100000):
        p.error('RA, Dec, radio o MAXREC fuera de rango')
    CACHE.mkdir(parents=True, exist_ok=True)
    retry = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=frozenset(['GET']))
    outcomes = {}
    with requests.Session() as session:
        session.mount('https://', HTTPAdapter(max_retries=retry))
        session.headers['User-Agent'] = 'MORLEY-SIA2-00B/1.0 (education/research)'
        for collection in COLLECTIONS:
            path = CACHE / f'{collection}.xml'
            params = {
                'COLLECTION': collection,
                'POS': f'CIRCLE {a.ra:.8f} {a.dec:.8f} {a.radius_deg:.6f}',
                'MAXREC': str(a.maxrec),
            }
            print(f'[00B] Consultando {collection} ...')
            try:
                response = session.get(ENDPOINT, params=params, timeout=(15, 80))
                response.raise_for_status()
                candidate_rows = parse_inventory(response.content, collection)
                # Atomic replace; never overwrite working cache with invalid response.
                tmp = path.with_suffix('.xml.part')
                tmp.write_bytes(response.content)
                tmp.replace(path)
                outcomes[collection] = {'status': 'ok', 'rows_valid': len(candidate_rows), 'cache': path.relative_to(HOME).as_posix(), 'query_url': response.url}
                print(f'  VOTable guardado | observaciones Level-2 oficiales validas: {len(candidate_rows)}')
            except Exception as exc:
                outcomes[collection] = {'status': 'error', 'reason': f'{type(exc).__name__}: {exc}', 'previous_cache_retained': path.exists()}
                print(f'  ERROR {collection}: {exc}')
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        'schema_version': 'morley.sia_discovery.v1',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'target': {'ra_deg': a.ra, 'dec_deg': a.dec, 'radius_deg': a.radius_deg},
        'source': 'live_IRSA_SIA2', 'collections': outcomes, 'science_validated': False,
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Reporte:', REPORT)
    if not all(o['status'] == 'ok' for o in outcomes.values()):
        print('Fallo una consulta. Se conservaron los caches validos anteriores, si existian.')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
