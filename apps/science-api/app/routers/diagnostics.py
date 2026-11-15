"""Public, read-only view of an *existing* Morley offline science report.

No remote downloads, calculations, arbitrary file paths, or scientific claims are
made by this router. Results always identify the source region and provenance.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/science/diagnostics", tags=["Science Diagnostics"])

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_REPORT = (
    REPO_ROOT
    / "science/experiments/morley_unified/outputs/validations/"
    / "morley_science_routes_recheck.json"
)
MAX_REPORT_BYTES = 10 * 1024 * 1024

RouteType = Literal[
    "TEMPORAL_CALIBRATION_CANDIDATE",
    "SPECTRAL_ANALYSIS_ONLY",
    "TEMPORAL_REVIEW",
    "INSUFFICIENT_INDIVIDUAL_DATA",
]

# Return only explicitly selected, non-sensitive fields. Never expose FITS paths,
# local workspace locations, hashes or internal URLs through these endpoints.
OBSERVATION_FIELDS = (
    "obs_id", "detector", "collection", "date_obs", "status",
    "evidence_type", "science_grade_photometry", "wavelength_um_approx",
    "bandwidth_um_approx", "bunit", "pixel_xy", "good_aperture_pixels",
    "background_pixels", "local_background_image_units",
    "net_aperture_sum_image_units_times_pixels", "formal_sum_error_same_units",
    "formal_snr_diagnostic", "uncorrected_aperture_mJy_estimate",
    "uncorrected_aperture_mJy_formal_error", "limitations",
)
PAIR_FIELDS = (
    "pair_id", "earlier_obs_id", "later_obs_id", "detector",
    "separation_days", "relative_mismatch_approx", "input_precheck",
    "route", "reasons", "observed_single_image_diagnostics_available",
    "cwave_cband_verified", "wcs_registration_verified", "epsf_fitted",
    "real_zogy_executed", "temporal_variability_claimed",
)


def _safe_json(value: Any) -> Any:
    """Convert any non-finite numeric diagnostic to JSON null."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _safe_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe_json(v) for v in value]
    return value


def _report() -> dict[str, Any]:
    path = Path(os.environ.get("MORLEY_SCIENCE_REPORT_PATH") or DEFAULT_REPORT)
    try:
        if not path.is_file():
            raise HTTPException(
                status_code=503,
                detail="El reporte científico todavía no está disponible en este servidor.",
            )
        if path.stat().st_size > MAX_REPORT_BYTES:
            raise HTTPException(status_code=503, detail="El reporte científico supera el límite permitido.")
        with path.open("r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except HTTPException:
        raise
    except (OSError, ValueError, UnicodeError):
        raise HTTPException(status_code=503, detail="No se pudo leer el reporte científico.") from None

    required = ("target", "summary", "scientific_integrity", "single_observation_diagnostics", "pair_routes")
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != "morley.science_routes.v1"
        or any(field not in data for field in required)
        or not isinstance(data["target"], dict)
        or not isinstance(data["summary"], dict)
        or not isinstance(data["scientific_integrity"], dict)
        or not isinstance(data["single_observation_diagnostics"], list)
        or not isinstance(data["pair_routes"], list)
    ):
        raise HTTPException(status_code=503, detail="El reporte científico tiene un formato no compatible.")
    return data


def _metadata(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": report["schema_version"],
        "generated_at_utc": report.get("generated_at_utc"),
        "target": report["target"],
        "scientific_integrity": report["scientific_integrity"],
        "source_kind": "offline_scientific_diagnostic",
    }


def _pick(item: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {k: item[k] for k in fields if k in item}


@router.get("/summary")
def diagnostics_summary() -> dict[str, Any]:
    data = _report()
    return _safe_json({**_metadata(data), "summary": data["summary"]})


@router.get("/observations")
def diagnostics_observations(
    status: str | None = Query(default=None, max_length=80),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    data = _report()
    items = [o for o in data["single_observation_diagnostics"] if isinstance(o, dict)]
    if status is not None:
        items = [o for o in items if o.get("status") == status]
    return _safe_json({
        **_metadata(data),
        "total": len(items),
        "offset": offset,
        "limit": limit,
        "items": [_pick(o, OBSERVATION_FIELDS) for o in items[offset:offset + limit]],
    })


@router.get("/pairs")
def diagnostics_pairs(
    route: RouteType | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    data = _report()
    items = [p for p in data["pair_routes"] if isinstance(p, dict)]
    if route is not None:
        items = [p for p in items if p.get("route") == route]
    return _safe_json({
        **_metadata(data),
        "total": len(items),
        "offset": offset,
        "limit": limit,
        "items": [_pick(p, PAIR_FIELDS) for p in items[offset:offset + limit]],
    })
