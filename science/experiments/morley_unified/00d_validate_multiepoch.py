#!/usr/bin/env python3
"""MORLEY 00D: all-pairs DR1/QR3 temporal FITS precheck, including same-release observations.

Input: outputs/catalogs/spherex_sia_inventory.csv from Practice 00C.
Uses official IRSA Level-2 cutout URLs; reuses verified existing local FITS.
Checks real DATE-OBS, RA/Dec, approximate WCS-WAVE and local variance.
No real ZOGY, ePSF fitting, CWAVE/CBAND, or discovery of genuine motion.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HERE = Path(__file__).resolve().parent
CATALOG = HERE / "outputs" / "catalogs"
DATA = HERE / "outputs" / "data" / "candidates_05"
SIA_CSV = CATALOG / "spherex_sia_inventory.csv"


def load_inspector():
    path = HERE / "00_select_fits_candidates.py"
    if not path.exists():
        raise FileNotFoundError("Falta 00_select_fits_candidates.py junto al script 00D")
    spec = importlib.util.spec_from_file_location("morley00_inspector", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def official_fits_url(raw):
    parsed = urlparse(str(raw).strip())
    if (parsed.scheme != "https" or parsed.hostname != "irsa.ipac.caltech.edu"
        or not re.fullmatch(r"/ibe/data/spherex/(dr1|qr3)/level2/[A-Za-z0-9_./-]+\.fits", parsed.path)):
        raise ValueError("URL FITS no pertenece al archivo oficial DR1/QR3 Level 2")
    return f"https://irsa.ipac.caltech.edu{parsed.path}"


def load_catalog(path, detector):
    if not path.exists():
        raise FileNotFoundError(f"No existe catalogo 00C: {path}")
    result = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            collection = row.get("collection", "")
            det = row.get("detector", "")
            if collection not in ("spherex_dr1", "spherex_qr3"):
                continue
            if detector != "all" and det != detector:
                continue
            if det not in {f"D{x}" for x in range(1, 7)}:
                continue
            try:
                url = official_fits_url(row["access_url"])
                when = float(row["t_min_mjd"])
                if not math.isfinite(when) or when <= 0:
                    continue
                obs_id = row["obs_id"].strip()
                if not re.fullmatch(r"20\d{2}W\d{2}_[12][A-Za-z]_\d{4}_[1-4]", obs_id):
                    continue
                result[url] = {"obs_id": obs_id, "detector": det,
                               "collection": collection, "access_url": url, "t_min_mjd": when}
            except (KeyError, ValueError, TypeError):
                continue
    return sorted(result.values(), key=lambda r: (r["detector"], r["collection"], r["t_min_mjd"]))


def spread_select(rows, count):
    """Spread selection over MJD rather than choosing only the first N images."""
    rows = sorted(rows, key=lambda r: r["t_min_mjd"])
    if len(rows) <= count:
        return rows
    indices = list(dict.fromkeys(int(round(v)) for v in np.linspace(0, len(rows)-1, count)))
    return [rows[i] for i in indices]


def file_path(url, ra, dec, size_deg):
    stem = Path(urlparse(url).path).stem
    tag = f"ra{ra:.5f}_dec{dec:+.5f}_size{size_deg:.3f}"
    tag = tag.replace(".", "p").replace("+", "pos").replace("-", "neg")
    return DATA / (stem + "__" + tag + ".fits")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_or_download(session, inspector, row, ra, dec, size, limit_mb, offline):
    path = file_path(row["access_url"], ra, dec, size)
    out = {**row, "status": "error", "ready_for_zogy": False}
    if path.exists():
        try:
            data = inspector.inspect_fits(path, ra, dec)
            return {**out, **data, "status": "existing_verified",
                    "cutout_file": path.relative_to(HERE).as_posix(), "sha256": sha256(path)}
        except Exception as exc:
            return {**out, "error": f"FITS existente no valido (se conservo): {exc}"}
    if offline:
        return {**out, "error": "No existe FITS local (modo --offline)"}
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".fits.part")
    tmp.unlink(missing_ok=True)
    try:
        with session.get(row["access_url"], params={"center": f"{ra:.8f},{dec:.8f}",
                     "size": f"{size:.5f}"}, timeout=(12, 65), stream=True) as response:
            response.raise_for_status()
            out["cutout_request_url"] = response.url
            size_bytes = 0
            with tmp.open("wb") as f:
                for block in response.iter_content(256 * 1024):
                    if not block:
                        continue
                    size_bytes += len(block)
                    if size_bytes > limit_mb * 1024 * 1024:
                        raise ValueError(f"Recorte excede el limite de {limit_mb} MB")
                    f.write(block)
        data = inspector.inspect_fits(tmp, ra, dec)
        tmp.replace(path)
        return {**out, **data, "status": "downloaded_verified",
                "cutout_file": path.relative_to(HERE).as_posix(), "sha256": sha256(path)}
    except Exception as exc:
        return {**out, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        tmp.unlink(missing_ok=True)


def obs_date(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def pair_candidates(records, days_min=30., mismatch_max=0.25, good_min=0.90):
    """Compare all unique verified observation pairs, including same-release epochs."""
    valid = [
        r for r in records
        if r["status"] in ("existing_verified", "downloaded_verified")
    ]
    pairs = []

    for i, a in enumerate(valid):
        for b in valid[i + 1:]:
            if a["detector"] != b["detector"]:
                continue
            try:
                a_date, b_date = obs_date(a["date_obs"]), obs_date(b["date_obs"])
                earlier, later = (a, b) if a_date <= b_date else (b, a)
                separation_days = abs((b_date - a_date).total_seconds()) / 86400.
                wave_a, wave_b = float(a["wavelength_um"]), float(b["wavelength_um"])
                width_a, width_b = float(a["bandwidth_um"]), float(b["bandwidth_um"])
                width_mean = (width_a + width_b) / 2.
                if width_mean <= 0:
                    continue
                mismatch = abs(wave_a - wave_b) / width_mean
                overlap = max(
                    0.,
                    min(wave_a + width_a / 2., wave_b + width_b / 2.)
                    - max(wave_a - width_a / 2., wave_b - width_b / 2.)
                )
                quality = (
                    a["central_good"] and b["central_good"]
                    and a["finite_variance_fraction_7x7"] >= good_min
                    and b["finite_variance_fraction_7x7"] >= good_min
                )
                if separation_days < days_min:
                    status = "BLOCKED_TIME_POLICY"
                elif not quality:
                    status = "REVIEW_PIXEL_QUALITY"
                elif mismatch > mismatch_max:
                    status = "REVIEW_SPECTRAL_MISMATCH"
                else:
                    status = "PRECHECK_PASS_NEEDS_CALIBRATION"

                pairs.append({
                    "earlier": {
                        "obs_id": earlier["obs_id"],
                        "access_url": earlier["access_url"],
                        "local_file": earlier["cutout_file"],
                    },
                    "later": {
                        "obs_id": later["obs_id"],
                        "access_url": later["access_url"],
                        "local_file": later["cutout_file"],
                    },
                    "detector": a["detector"],
                    "separation_days": round(separation_days, 4),
                    "relative_mismatch": round(mismatch, 6),
                    "approximate_overlap_fraction": round(overlap / min(width_a, width_b), 5),
                    "status": status,
                    "wavelength_basis": "target_pixel_WCS-WAVE_approximate",
                    "cwave_cband_verified": False,
                    "wcs_registered": False,
                    "epsf_fitted": False,
                    "real_zogy_executed": False,
                    "ready_for_zogy": False,
                })
            except (ValueError, KeyError, TypeError, ZeroDivisionError):
                continue

    pairs.sort(key=lambda p: (
        p["status"] != "PRECHECK_PASS_NEEDS_CALIBRATION",
        p["relative_mismatch"],
        -p["separation_days"],
    ))
    for i, pair in enumerate(pairs, 1):
        pair["pair_id"] = f"C{i:03d}"
    return pairs

def main():
    ap = argparse.ArgumentParser(description="MORLEY: 2026 DR1/QR3 all-pairs FITS multi-epoch validation")
    ap.add_argument("--detector", choices=["all"] + [f"D{i}" for i in range(1, 7)], default="D6")
    ap.add_argument("--per-epoch", type=int, default=3,
                    help="Number of candidate cutouts per collection per detector")
    ap.add_argument("--ra", type=float, default=295.4097841)
    ap.add_argument("--dec", type=float, default=-15.2231692)
    ap.add_argument("--size-deg", type=float, default=0.10)
    ap.add_argument("--max-mb", type=int, default=40)
    ap.add_argument("--min-days", type=float, default=30)
    ap.add_argument("--threshold", type=float, default=0.25)
    ap.add_argument("--offline", action="store_true", help="Only reuse already downloaded cutouts")
    args = ap.parse_args()
    if not (0 <= args.ra < 360 and -90 <= args.dec <= 90 and
            1 <= args.per_epoch <= 20 and 0 < args.size_deg <= 0.20 and
            1 <= args.max_mb <= 200 and 0 <= args.min_days <= 3650 and
            0 < args.threshold <= 1):
        ap.error("Parametros invalidos")
    try:
        all_rows = load_catalog(SIA_CSV, args.detector)
        inspector = load_inspector()
    except Exception as exc:
        print("ERROR:", exc)
        return 2
    print("MORLEY 00D - Todas las combinaciones temporales verificadas")
    print(f"Catalogo: {len(all_rows)} observaciones; detector={args.detector}; limite={args.per_epoch}/epoca")
    selected = []
    detectors = [f"D{i}" for i in range(1, 7)] if args.detector == "all" else [args.detector]
    for detector in detectors:
        for collection in ("spherex_dr1", "spherex_qr3"):
            group = [x for x in all_rows if x["detector"] == detector and x["collection"] == collection]
            chosen = spread_select(group, args.per_epoch)
            print(f"  {detector} {collection}: {len(group)} disponibles, {len(chosen)} seleccionados")
            selected.extend(chosen)
    if not selected:
        print("Sin URL para las colecciones seleccionadas. No se alteran catalogos previos.")
        return 2
    retries = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=frozenset(["GET"]))
    records = []
    with requests.Session() as s:
        s.mount("https://", HTTPAdapter(max_retries=retries))
        s.headers["User-Agent"] = "MORLEY-00D-MultiEpoch/1.0"
        for i, row in enumerate(selected, 1):
            result = inspect_or_download(s, inspector, row, args.ra, args.dec,
                                         args.size_deg, args.max_mb, args.offline)
            records.append(result)
            wave = (f"lambda~{result['wavelength_um']:.6f}um"
                    if "wavelength_um" in result else result.get("error", ""))
            print(f"[{i:02d}/{len(selected):02d}] {row['obs_id']} [{row['detector']}] "
                  f"{result['status']} {wave}")
    pairs = pair_candidates(records, args.min_days, args.threshold)
    passed = [x for x in pairs if x["status"] == "PRECHECK_PASS_NEEDS_CALIBRATION"]
    report = {
        "schema_version": "morley.epoch_pairs.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "IRSA_SIA2_CATALOG_AND_VERIFIED_L2_CUTOUTS",
        "target": {"ra_deg": args.ra, "dec_deg": args.dec, "frame": "ICRS"},
        "selection": {"detector": args.detector, "per_epoch": args.per_epoch,
                      "min_days": args.min_days, "spectral_mismatch_threshold": args.threshold},
        "scientific_integrity": {"wcs_wave_approximate_only": True,
                                 "cwave_cband_verified": False, "real_zogy_executed": False,
                                 "ready_for_zogy": False, "motion_detected": False},
        "observations": records, "pairs": pairs,
        "summary": {"selected_cutouts": len(selected),
                    "verified_cutouts": sum(x["status"] in ("downloaded_verified", "existing_verified") for x in records),
                    "total_pairs": len(pairs), "precheck_passes": len(passed)},
    }
    CATALOG.mkdir(parents=True, exist_ok=True)
    path = CATALOG / "candidate_pairs_multiepoch_05.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nCANDIDATE PAIRS - ALL VERIFIED EPOCHS:")
    for pair in pairs[:12]:
        print(f" {pair['pair_id']} {pair['earlier']['obs_id']} / {pair['later']['obs_id']} "
              f"({pair['detector']}) days={pair['separation_days']:.1f} "
              f"mismatch={pair['relative_mismatch']:.4f} | {pair['status']}")
    print(f"Resumen: {len(pairs)} parejas, {len(passed)} prechecks aprobados")
    print("JSON:", path)
    print("ZOGY REAL: NO EJECUTADO; requiere CWAVE/CBAND, ePSF y registro WCS.")
    if passed:
        print(f"Primera pareja preseleccionada: {passed[0]['pair_id']}")
        print("Siguiente: python .\\06_science_routes.py "
              f"--input .\\outputs\\catalogs\\candidate_pairs_multiepoch_05.json "
              f"--min-days {args.min_days:g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
