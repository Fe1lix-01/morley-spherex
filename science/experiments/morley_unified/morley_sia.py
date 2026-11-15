"""Utilities for the reconstructed MORLEY 00B/00C SIA2 discovery stages.

This is new compatibility code, not a recovered copy of the original scripts.
Only official on-premises SPHEREx DR1/QR3 Level-2 MEF URLs are accepted.
"""
from __future__ import annotations

import re
from io import BytesIO
from urllib.parse import urlparse

import numpy as np
from astropy.io.votable import parse

ENDPOINT = "https://irsa.ipac.caltech.edu/SIA"
COLLECTIONS = ("spherex_dr1", "spherex_qr3")
OBSID_RE = re.compile(r"level2_(20\d{2}W\d{2}_[12][A-Za-z]_\d{4}_[1-4])D([1-6])_spx_", re.I)
FITS_PATH = re.compile(r"/ibe/data/spherex/(dr1|qr3)/level2/[A-Za-z0-9_./-]+\.fits", re.I)


def allowed_url(raw):
    parsed = urlparse(str(raw).strip())
    if (parsed.scheme != 'https' or parsed.hostname != 'irsa.ipac.caltech.edu'
            or parsed.username or parsed.password or not FITS_PATH.fullmatch(parsed.path)):
        return None
    return f'https://irsa.ipac.caltech.edu{parsed.path}'


def _clean(value):
    if value is None or np.ma.is_masked(value):
        return None
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='replace')
    value = str(value).strip()
    return value if value and value.lower() not in ('none', 'nan', '--') else None


def parse_inventory(votable_bytes, expected_collection):
    """Return standardized rows from genuine SIA2 VOTable response bytes.

    Raises on parse failures, absent columns, or a QUERY_STATUS=ERROR response.
    """
    if b'VOTABLE' not in votable_bytes[:3000].upper():
        raise ValueError('Respuesta SIA2 no parece VOTable XML')
    votable = parse(BytesIO(votable_bytes), verify='ignore')
    for resource in votable.resources:
        for info in resource.infos:
            if str(info.name).upper() == 'QUERY_STATUS' and str(info.value).upper() == 'ERROR':
                raise ValueError(f'SIA2 QUERY_STATUS ERROR: {info.content or info.value}')
    first = votable.get_first_table()
    if first is None:
        raise ValueError('SIA2 sin tabla de resultados')
    table = first.to_table(use_names_over_ids=True)
    lower = {str(name).lower(): str(name) for name in table.colnames}
    if 'access_url' not in lower or not any(k in lower for k in ('t_min', 't_min_mjd', 'time_bounds_lower')):
        raise ValueError(f'SIA2 requiere access_url y t_min; columnas recibidas: {list(table.colnames)}')

    result = {}
    for row in table:
        raw_url = _clean(row[lower['access_url']])
        url = allowed_url(raw_url) if raw_url else None
        if url is None:
            continue
        collection_from_url = 'spherex_dr1' if '/spherex/dr1/' in url else 'spherex_qr3'
        if collection_from_url != expected_collection:
            continue
        match = OBSID_RE.search(url)
        if not match:
            continue
        time_raw = next((_clean(row[lower[k]]) for k in ('t_min', 't_min_mjd', 'time_bounds_lower') if k in lower), None)
        try:
            mjd = float(time_raw)
        except (TypeError, ValueError):
            continue
        if not np.isfinite(mjd) or mjd <= 0:
            continue
        result[url] = {
            'collection': expected_collection,
            'detector': f'D{match.group(2)}',
            'obs_id': match.group(1),
            't_min_mjd': f'{mjd:.9f}',
            'access_url': url,
        }
    return sorted(result.values(), key=lambda x: (x['detector'], float(x['t_min_mjd']), x['obs_id']))
