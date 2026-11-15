
#!/usr/bin/env python3
"""MORLEY 07 - Auditoria de pares reales, sin ejecutar ZOGY."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales


ROOT = Path(__file__).resolve().parent

CAT = (
    ROOT / "outputs" / "catalogs"
    / "candidate_pairs_multiepoch_05.json"
)

ROUTES = (
    ROOT / "outputs" / "validations"
    / "morley_science_routes.json"
)

OUT = (
    ROOT / "outputs" / "validations"
    / "morley_07_audit.json"
)

VERIFIED = {
    "existing_verified",
    "downloaded_verified",
}


def local_path(relative):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("Falta ruta cutout_file")

    p = Path(relative)

    if p.is_absolute():
        raise ValueError("Solo se permiten rutas relativas")

    full = (ROOT / p).resolve()

    if not full.is_relative_to(ROOT.resolve()):
        raise ValueError("Ruta fuera del proyecto")

    if full.suffix.lower() != ".fits" or not full.is_file():
        raise FileNotFoundError(f"FITS no encontrado: {relative}")

    return full


def inspect(record, ra, dec):
    result = {
        "obs_id": record.get("obs_id"),
        "status": "BLOCKED",
        "cutout_file": record.get("cutout_file"),
        "issues": [],
    }

    if record.get("status") not in VERIFIED:
        result["issues"].append("FITS no verificado en 00D")
        return result

    try:
        path = local_path(record.get("cutout_file"))

        with fits.open(path, memmap=False) as hdul:
            required = (
                "IMAGE",
                "VARIANCE",
                "FLAGS",
                "EPSF",
                "WCS-WAVE",
            )

            missing = [
                name for name in required
                if name not in hdul
            ]

            if missing:
                raise ValueError(
                    "Faltan extensiones: " + ", ".join(missing)
                )

            image = np.asarray(hdul["IMAGE"].data)
            variance = np.asarray(hdul["VARIANCE"].data)
            flags = np.asarray(hdul["FLAGS"].data)

            if (
                image.ndim != 2
                or image.shape != variance.shape
                or image.shape != flags.shape
            ):
                raise ValueError(
                    "Dimensiones IMAGE/VARIANCE/FLAGS incompatibles"
                )

            header = hdul["IMAGE"].header
            wcs = WCS(header, fobj=hdul).celestial

            x, y = map(
                float,
                wcs.world_to_pixel_values(ra, dec),
            )

            ny, nx = image.shape

            if not (
                np.isfinite(x)
                and np.isfinite(y)
                and 4 <= x < nx - 4
                and 4 <= y < ny - 4
            ):
                raise ValueError(
                    "Objetivo fuera de la region 7x7"
                )

            ix = int(round(x))
            iy = int(round(y))

            region = (
                slice(iy - 3, iy + 4),
                slice(ix - 3, ix + 4),
            )

            im = image[region]
            va = variance[region]
            fl = flags[region]

            if im.shape != (7, 7):
                raise ValueError("Region truncada")

            good = (
                np.isfinite(im)
                & np.isfinite(va)
                & (va > 0)
                & (fl == 0)
            )

            sip_detected = any(
                key in header
                for key in ("A_ORDER", "B_ORDER")
            )

            sip_suffix = (
                "-SIP" in str(header.get("CTYPE1", ""))
                and "-SIP" in str(header.get("CTYPE2", ""))
            )

            sip_inconsistent = bool(
                sip_detected and not sip_suffix
            )

            scales = (
                np.asarray(
                    proj_plane_pixel_scales(wcs),
                    dtype=float,
                ) * 3600
            )

            bunit = str(
                header.get("BUNIT", "UNKNOWN")
            ).strip()

            result.update({
                "status": "AUDITABLE_NOT_CALIBRATED",
                "image_shape_yx": [ny, nx],
                "target_pixel_xy": [
                    round(x, 3),
                    round(y, 3),
                ],
                "pixel_scales_arcsec": [
                    round(float(v), 6)
                    for v in scales
                ],
                "bunit": bunit,
                "usable_fraction_7x7": round(
                    float(good.mean()), 4
                ),
                "nonzero_flags_fraction_7x7": round(
                    float(np.mean(fl != 0)), 4
                ),
                "sip_warning_header_inconsistent": (
                    sip_inconsistent
                ),
                "epsf_extension_present": True,
                "wcs_wave_extension_present": True,
                "fits_size_bytes": path.stat().st_size,
            })

            if sip_inconsistent:
                result["issues"].append(
                    "SIP sin sufijo -SIP; revisar astrometria"
                )

            if float(good.mean()) < 0.80:
                result["issues"].append(
                    "Menos del 80% de pixeles utilizables"
                )

            if bunit.lower().replace(" ", "") != "mjy/sr":
                result["issues"].append(
                    f"BUNIT inesperada: {bunit}"
                )

    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: {exc}"
        )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="MORLEY 07 - Auditoria instrumental"
    )

    parser.add_argument(
        "--pairs", type=Path, default=CAT
    )
    parser.add_argument(
        "--routes", type=Path, default=ROUTES
    )
    parser.add_argument(
        "--pair-id", default=None
    )

    args = parser.parse_args()

    if not args.pairs.is_file() or not args.routes.is_file():
        parser.error(
            "Ejecuta primero 00D y 06"
        )

    catalog = json.loads(
        args.pairs.read_text(encoding="utf-8-sig")
    )

    routing = json.loads(
        args.routes.read_text(encoding="utf-8-sig")
    )

    target = catalog["target"]
    ra = float(target["ra_deg"])
    dec = float(target["dec_deg"])

    if not (0 <= ra < 360 and -90 <= dec <= 90):
        parser.error("Coordenadas invalidas")

    route_target = routing["target"]

    if (
        abs(float(route_target["ra_deg"]) - ra) > 1e-7
        or abs(float(route_target["dec_deg"]) - dec) > 1e-7
    ):
        parser.error(
            "00D y 06 tienen coordenadas distintas"
        )

    observations = {
        o["obs_id"]: o
        for o in catalog["observations"]
        if o.get("obs_id")
    }

    route_by_id = {
        p["pair_id"]: p
        for p in routing["pair_routes"]
    }

    selected = []

    for pair in catalog["pairs"]:
        pair_id = pair["pair_id"]
        routed = route_by_id.get(pair_id, {})
        route = routed.get("route")

        first = pair["earlier"]["obs_id"]
        second = pair["later"]["obs_id"]

        expected_ids = (
            routed.get("earlier_obs_id"),
            routed.get("later_obs_id"),
        )

        if expected_ids != (first, second):
            route = "STALE_06_REPORT"

        if pair.get("status") != (
            "PRECHECK_PASS_NEEDS_CALIBRATION"
        ):
            route = "NOT_APPROVED_IN_00D"

        if args.pair_id and pair_id != args.pair_id:
            continue

        if (
            args.pair_id is None
            and route != "TEMPORAL_CALIBRATION_CANDIDATE"
        ):
            continue

        audit_a = inspect(
            observations.get(first, {}),
            ra,
            dec,
        )

        audit_b = inspect(
            observations.get(second, {}),
            ra,
            dec,
        )

        audits = [audit_a, audit_b]

        valid = all(
            a["status"] == "AUDITABLE_NOT_CALIBRATED"
            for a in audits
        )

        problems = []

        if route != "TEMPORAL_CALIBRATION_CANDIDATE":
            problems.append(
                "Par no aprobado o reporte 06 desactualizado"
            )

        if not valid:
            problems.append(
                "Al menos un FITS no pudo auditarse"
            )

        if audit_a.get("bunit") != audit_b.get("bunit"):
            problems.append("Unidades BUNIT diferentes")

        problems.extend([
            "Falta validar CWAVE/CBAND cientificos",
            "Falta verificar registro astrometrico",
            "Falta ajustar ePSF y escala fotometrica",
            "Falta modelo de ruido y mascaras para ZOGY",
        ])

        selected.append({
            "pair_id": pair_id,
            "obs_ids": [first, second],
            "route_from_06": route,
            "separation_days": pair.get(
                "separation_days"
            ),
            "relative_mismatch_approx": pair.get(
                "relative_mismatch"
            ),
            "individual_audits": audits,
            "status": (
                "CALIBRATION_REQUIRED"
                if valid
                else "AUDIT_BLOCKED"
            ),
            "blocking_reasons": problems,
            "cwave_cband_verified": False,
            "wcs_registration_verified": False,
            "epsf_fitted": False,
            "real_zogy_authorized": False,
        })

    if args.pair_id and not selected:
        parser.error(
            f"No existe el par {args.pair_id}"
        )

    report = {
        "schema_version": "morley.calibration_audit.v1",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "target": target,
        "pairs_audited": len(selected),
        "pairs": selected,
        "scientific_integrity": {
            "observed_data_audited": True,
            "scientific_calibration_completed": False,
            "real_zogy_executed": False,
            "motion_detected": False,
        },
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    print("MORLEY 07 - AUDITORIA REAL")

    for pair in selected:
        print(
            pair["pair_id"],
            "->",
            pair["status"],
            "| ZOGY real: NO AUTORIZADO",
        )

        for obs in pair["individual_audits"]:
            print(
                " ",
                obs.get("obs_id"),
                "->",
                obs["status"],
                "| SIP inconsistente:",
                obs.get(
                    "sip_warning_header_inconsistent",
                    "?",
                ),
            )

    print("JSON:", OUT)
    print(
        "Pendiente: CWAVE/CBAND, WCS, ePSF y ruido."
    )


if __name__ == "__main__":
    main()
