#!/usr/bin/env python3
"""MORLEY 06: scientific routing and single-exposure aperture diagnostics.

Offline. Reads the pair JSON produced by MORLEY 00B or 00D and cached Level-2
SPHEREx FITS cutouts. DOES NOT compute ZOGY, science-grade photometry, motion,
variability, or source classification.

Outputs outputs/validations/morley_science_routes.json.
Requirements: numpy, astropy (already in the MORLEY .venv).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_area

HOME = Path(__file__).resolve().parent
CATALOG = HOME / "outputs" / "catalogs"
OUT = HOME / "outputs" / "validations" / "morley_science_routes.json"
VALID_STATES = {"existing_verified", "downloaded_verified"}


def now():
    return datetime.now(timezone.utc).isoformat()


def safe_number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def path_in_project(value):
    """Prevent JSON-provided paths from accidentally reading outside workspace."""
    if not isinstance(value, str) or not value.strip():
        return None
    p = Path(value)
    if p.is_absolute():
        return None
    full = (HOME / p).resolve()
    try:
        full.relative_to(HOME.resolve())
    except ValueError:
        return None
    return full


def load_input(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Catalog JSON must be an object")
    if not isinstance(data.get("observations"), list):
        raise ValueError("Missing observations list; supply 00B/00D report")
    if not isinstance(data.get("pairs"), list):
        raise ValueError("Missing pairs list; supply 00B/00D report")
    return data


def measure_single_cutout(record, ra, dec, aperture_radius, inner, outer):
    """Diagnostic aperture sum, with simple local-sky median and formal error.

    NOT total flux: no ePSF/aperture correction, local background model,
    astrometric refinement or correlated-noise treatment.
    """
    result = {
        "obs_id": record.get("obs_id"),
        "detector": record.get("detector"),
        "collection": record.get("collection"),
        "date_obs": record.get("date_obs"),
        "wavelength_um_approx": record.get("wavelength_um"),
        "bandwidth_um_approx": record.get("bandwidth_um"),
        "file": record.get("cutout_file"),
        "status": "UNAVAILABLE",
        "evidence_type": "observed_image_diagnostic",
        "science_grade_photometry": False,
    }
    if record.get("status") not in VALID_STATES:
        result["reason"] = "Observation not verified in input catalog"
        return result
    path = path_in_project(record.get("cutout_file") or record.get("file"))
    if path is None or not path.is_file() or path.suffix.lower() != ".fits":
        result["reason"] = "Cached FITS not found inside workspace"
        return result
    try:
        with fits.open(path, memmap=False) as h:
            if not all(n in h for n in ("IMAGE", "VARIANCE", "FLAGS")):
                raise ValueError("IMAGE/VARIANCE/FLAGS extension missing")
            image = h["IMAGE"].data
            variance = h["VARIANCE"].data
            flags = h["FLAGS"].data
            if (image is None or variance is None or flags is None or
                image.ndim != 2 or image.shape != variance.shape or
                image.shape != flags.shape):
                raise ValueError("Inconsistent FITS array dimensions")
            # Preserve FITS/WCS warnings, including inconsistent SIP metadata.
            wcs = WCS(h["IMAGE"].header, fobj=h).celestial
            x, y = map(float, wcs.world_to_pixel_values(ra, dec))
            ny, nx = image.shape
            if not (math.isfinite(x) and math.isfinite(y) and
                    outer + 1 <= x < nx - outer - 1 and
                    outer + 1 <= y < ny - outer - 1):
                raise ValueError(f"Target too close to cutout edge: x={x:.2f}, y={y:.2f}, size={nx}x{ny}")
            # Process a small patch: avoids loading large masks unnecessarily.
            x0, x1 = max(0, math.floor(x - outer - 1)), min(nx, math.ceil(x + outer + 2))
            y0, y1 = max(0, math.floor(y - outer - 1)), min(ny, math.ceil(y + outer + 2))
            yy, xx = np.mgrid[y0:y1, x0:x1]
            r2 = (xx - x)**2 + (yy - y)**2
            is_ap = r2 <= aperture_radius ** 2
            is_bg = (r2 >= inner ** 2) & (r2 <= outer ** 2)
            dat = np.asarray(image[y0:y1, x0:x1], dtype=float)
            var = np.asarray(variance[y0:y1, x0:x1], dtype=float)
            mask = np.asarray(flags[y0:y1, x0:x1])
            good = np.isfinite(dat) & np.isfinite(var) & (var > 0) & (mask == 0)
            ap = is_ap & good
            bg = is_bg & good
            nap, nbg = int(ap.sum()), int(bg.sum())
            n_geo = int(is_ap.sum())
            if nap < 5 or nap / n_geo < 0.80 or nbg < 15:
                raise ValueError(f"Insufficient unflagged pixels for aperture/background: {nap}/{n_geo} aperture, {nbg} bg")
            bg_level = float(np.median(dat[bg]))
            # Explicitly a diagnostic of the single image, NOT time variability.
            net = float(np.sum(dat[ap] - bg_level))
            # This formal variance is approximate; median background estimate
            # and resampling correlations are not treated rigorously.
            formal_var = float(np.sum(var[ap]) + (nap ** 2) * np.median(var[bg]) / nbg)
            err = math.sqrt(formal_var) if formal_var > 0 else None
            bunit = str(h["IMAGE"].header.get("BUNIT", "unknown"))
            result.update({
                "status": "SINGLE_IMAGE_APERTURE_DIAGNOSTIC",
                "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "pixel_xy": [round(x, 3), round(y, 3)],
                "date_obs": result["date_obs"] or h["IMAGE"].header.get("DATE-OBS"),
                "bunit": bunit,
                "aperture_radius_pix": aperture_radius,
                "background_annulus_pix": [inner, outer],
                "good_aperture_pixels": nap,
                "background_pixels": nbg,
                "local_background_image_units": bg_level,
                "net_aperture_sum_image_units_times_pixels": net,
                "formal_sum_error_same_units": err,
                "formal_snr_diagnostic": net / err if err else None,
                "limitations": [
                    "No ePSF/aperture correction; NOT total source flux",
                    "Uncertainty does not fully capture correlated noise or background systematics",
                    "No time variability or physical source identity inferred",
                ],
            })
            if bunit.replace(" ", "").lower() == "mjy/sr":
                try:
                    pixel_sr = float(proj_plane_pixel_area(wcs)) * (math.pi / 180.0) ** 2
                    if pixel_sr > 0 and math.isfinite(pixel_sr):
                        factor = pixel_sr * 1e9
                        result["uncorrected_aperture_mJy_estimate"] = net * factor
                        result["uncorrected_aperture_mJy_formal_error"] = err * factor if err else None
                        result["pixel_solid_angle_sr_approx"] = pixel_sr
                except (ValueError, TypeError, ArithmeticError):
                    result["mJy_conversion_status"] = "pixel_area_unavailable"
    except Exception as exc:
        result["status"] = "DIAGNOSTIC_BLOCKED"
        result["reason"] = f"{type(exc).__name__}: {exc}"
    return result


def decide_pair(pair, measurements, thresh, min_days):
    a = pair.get("earlier") or {}
    b = pair.get("later") or {}
    a_id, b_id = a.get("obs_id"), b.get("obs_id")
    obs_a, obs_b = measurements.get(a_id, {}), measurements.get(b_id, {})
    valid_a = obs_a.get("status") == "SINGLE_IMAGE_APERTURE_DIAGNOSTIC"
    valid_b = obs_b.get("status") == "SINGLE_IMAGE_APERTURE_DIAGNOSTIC"
    mismatch = safe_number(pair.get("relative_mismatch"))
    dt = safe_number(pair.get("separation_days"))
    reasons = []
    if not (valid_a and valid_b):
        route = "INSUFFICIENT_INDIVIDUAL_DATA"
        reasons.append("An image lacks a usable, unflagged aperture/background diagnostic")
    elif dt is None or dt <= 0 or dt < min_days:
        route = "TEMPORAL_REVIEW"
        reasons.append("Time separation absent, zero, or below policy minimum")
    elif mismatch is None:
        route = "SPECTRAL_REVIEW"
        reasons.append("No valid spectral mismatch value")
    elif pair.get("status") == "REVIEW_PIXEL_QUALITY":
        route = "QUALITY_REVIEW"
        reasons.append("Input catalog reports a pixel quality issue")
    elif mismatch > thresh:
        route = "SPECTRAL_ANALYSIS_ONLY"
        reasons.append("Different effective wavelengths: independent measurements only, NOT temporal variability")
    else:
        route = "TEMPORAL_CALIBRATION_CANDIDATE"
        reasons.append("Approximate band agreement; precise CWAVE/CBAND required before any subtraction")
    return {
        "pair_id": pair.get("pair_id"),
        "earlier_obs_id": a_id,
        "later_obs_id": b_id,
        "detector": pair.get("detector"),
        "separation_days": dt,
        "relative_mismatch_approx": mismatch,
        "input_precheck": pair.get("status"),
        "route": route,
        "reasons": reasons,
        "observed_single_image_diagnostics_available": [valid_a, valid_b],
        "cwave_cband_verified": False,
        "wcs_registration_verified": False,
        "epsf_fitted": False,
        "real_zogy_executed": False,
        "temporal_variability_claimed": False,
    }


def main():
    ap = argparse.ArgumentParser(description="MORLEY: offline science route selector + single-image aperture diagnostics")
    ap.add_argument("--input", type=Path, help="JSON from 00B or 00D; autodetect if omitted")
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--ra", type=float, help="Override RA of input target in degrees")
    ap.add_argument("--dec", type=float, help="Override Dec of input target in degrees")
    ap.add_argument("--threshold", type=float, default=0.25)
    ap.add_argument("--min-days", type=float, default=0.0, help="Minimum elapsed days; 0 does not require a long baseline")
    ap.add_argument("--aperture", type=float, default=2.0)
    ap.add_argument("--bg-inner", type=float, default=5.0)
    ap.add_argument("--bg-outer", type=float, default=8.0)
    args = ap.parse_args()
    if not (0 < args.threshold <= 1 and args.min_days >= 0 and
            0.5 <= args.aperture < args.bg_inner < args.bg_outer <= 20):
        ap.error("Invalid thresholds/aperture")
    candidates = [CATALOG / "candidate_pairs_multiepoch_05.json", CATALOG / "candidate_pairs_sia_05.json", CATALOG / "candidate_pairs_for_05.json"]
    source = args.input or next((p for p in candidates if p.is_file()), None)
    if source is None or not source.is_file():
        ap.error("No candidate JSON found; run 00B/00D first or specify --input")
    try:
        data = load_input(source)
        target = data.get("target") or {}
        ra = args.ra if args.ra is not None else safe_number(target.get("ra_deg"))
        dec = args.dec if args.dec is not None else safe_number(target.get("dec_deg"))
        if ra is None or dec is None or not (0 <= ra < 360 and -90 <= dec <= 90):
            raise ValueError("Missing/invalid ICRS RA/Dec; supply --ra and --dec")
        observations = data["observations"]
        measurements = {}
        for r in observations:
            if not isinstance(r, dict) or not r.get("obs_id"):
                continue
            m = measure_single_cutout(r, ra, dec, args.aperture, args.bg_inner, args.bg_outer)
            # Keep usable observation in case duplicates exist.
            key = r["obs_id"]
            if key not in measurements or (m["status"] == "SINGLE_IMAGE_APERTURE_DIAGNOSTIC"):
                measurements[key] = m
        pairs = [decide_pair(p, measurements, args.threshold, args.min_days)
                 for p in data["pairs"] if isinstance(p, dict)]
        counts = Counter(x["route"] for x in pairs)
        measurements_status = Counter(x["status"] for x in measurements.values())
        result = {
            "schema_version": "morley.science_routes.v1",
            "generated_at_utc": now(),
            "input_report": str(source),
            "target": {"ra_deg": ra, "dec_deg": dec, "frame": "ICRS"},
            "method": "offline routing and diagnostic aperture photometry of individual Level-2 cutouts",
            "scientific_integrity": {
                "evidence_type": "observed_image_diagnostic",
                "aperture_photometry_science_grade": False,
                "cwave_cband_verified": False,
                "real_zogy_executed": False,
                "motion_detected": False,
                "temporal_variability_claimed": False,
                "crossmatch_executed": False,
            },
            "summary": {"observations": len(measurements), "observation_statuses": dict(measurements_status),
                        "pairs": len(pairs), "routes": dict(counts)},
            "single_observation_diagnostics": list(measurements.values()),
            "pair_routes": pairs,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        print("MORLEY 06 - Independent scientific routes (OFFLINE)")
        print(f"Source: {source}")
        print(f"Observations: {len(measurements)} | usable aperture diagnostics: {measurements_status['SINGLE_IMAGE_APERTURE_DIAGNOSTIC']}")
        print(f"Pairs: {len(pairs)}")
        for k, v in sorted(counts.items()):
            print(f"  {k}: {v}")
        for p in pairs[:8]:
            print(f"  {p['pair_id']}: {p['earlier_obs_id']} / {p['later_obs_id']} -> {p['route']}")
        print("Real ZOGY: NOT EXECUTED | Variability: NOT CLAIMED")
        print(f"JSON: {args.output}")
        return 0
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
