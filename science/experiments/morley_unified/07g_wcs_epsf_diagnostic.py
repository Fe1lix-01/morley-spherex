
#!/usr/bin/env python3
"""MORLEY 07G: diagnostico geometrico WCS y ePSF.

Sin descargas, sin registro empirico,
sin resta de imagenes y sin ZOGY real.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


ROOT = Path(__file__).resolve().parent
VAL = ROOT / "outputs" / "validations"

SOURCE = VAL / "morley_07b_instrumental.json"
FOOTPRINT = VAL / "morley_07f_spectral_footprint.json"
OUTPUT = VAL / "morley_07g_wcs_epsf.json"


def read_json(path):
    if not path.is_file():
        raise FileNotFoundError(path)

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def safe_fits(raw):
    if not isinstance(raw, str) or not raw:
        raise ValueError("Ruta FITS vacia")

    value = Path(raw)

    if value.is_absolute():
        raise ValueError(
            "Solo se admiten rutas relativas"
        )

    result = (ROOT / value).resolve()

    if (
        not result.is_relative_to(ROOT.resolve())
        or result.suffix.lower() != ".fits"
    ):
        raise ValueError(
            "Ruta FITS fuera del proyecto"
        )

    if not result.is_file():
        raise FileNotFoundError(result)

    return result


def epsf_statistics(stamp, ovs_x, ovs_y):
    """Momentos descriptivos, NO ajuste de ePSF."""

    a = np.asarray(stamp, dtype=float)

    if (
        a.ndim != 2
        or not np.isfinite(a).all()
        or min(a.shape) < 3
    ):
        raise ValueError("ePSF invalida")

    if ovs_x <= 0 or ovs_y <= 0:
        raise ValueError(
            "Sobremuestreo invalido"
        )

    # Parte positiva para diagnosticar anchura.
    # No constituye normalizacion cientifica.
    weights = np.maximum(a, 0.0)
    total = float(weights.sum())

    if not np.isfinite(total) or total <= 0:
        raise ValueError(
            "ePSF sin masa positiva"
        )

    yy, xx = np.indices(
        a.shape, dtype=float
    )

    xx = (
        xx - (a.shape[1] - 1) / 2
    ) / ovs_x

    yy = (
        yy - (a.shape[0] - 1) / 2
    ) / ovs_y

    cx = float(
        np.sum(weights * xx) / total
    )

    cy = float(
        np.sum(weights * yy) / total
    )

    sx = math.sqrt(
        float(
            np.sum(
                weights * (xx - cx) ** 2
            ) / total
        )
    )

    sy = math.sqrt(
        float(
            np.sum(
                weights * (yy - cy) ** 2
            ) / total
        )
    )

    sigma_rms = math.sqrt(
        (sx * sx + sy * sy) / 2
    )

    return {
        "stamp_shape": list(a.shape),
        "oversampling_xy": [
            ovs_x, ovs_y
        ],
        "fraction_negative_samples": round(
            float(np.mean(a < 0)), 6
        ),
        "positive_part_centroid_native_pix": [
            round(cx, 6),
            round(cy, 6),
        ],
        "positive_part_sigma_xy_native_pix": [
            round(sx, 6),
            round(sy, 6),
        ],
        "positive_part_sigma_rms_native_pix": round(
            sigma_rms, 6
        ),
        "not_a_fitted_psf": True,
    }


def load_observation(obs):
    path = safe_fits(obs["file"])

    with fits.open(path, memmap=False) as hdul:
        if (
            "IMAGE" not in hdul
            or "EPSF" not in hdul
        ):
            raise ValueError(
                "Faltan IMAGE o EPSF"
            )

        header = hdul["IMAGE"].header
        shape = hdul["IMAGE"].data.shape

        if len(shape) != 2:
            raise ValueError(
                "IMAGE no es 2D"
            )

        wcs = WCS(
            header, fobj=hdul
        ).celestial

        epsf = hdul["EPSF"]

        if (
            epsf.data is None
            or "EPSF" not in epsf.columns.names
        ):
            raise ValueError(
                "Tabla EPSF invalida"
            )

        row = int(
            obs["epsf_zone"]["row_0based"]
        )

        if not 0 <= row < len(epsf.data):
            raise ValueError(
                "Indice EPSF fuera de rango"
            )

        stamp = np.asarray(
            epsf.data["EPSF"][row],
            dtype=float,
        )

        ovs_x = float(
            epsf.header.get("OVSMPX", 0)
        )

        ovs_y = float(
            epsf.header.get("OVSMPY", 0)
        )

        stats = epsf_statistics(
            stamp, ovs_x, ovs_y
        )

    x, y = map(
        float,
        obs["target_cutout_xy_0based"],
    )

    if not (
        0 <= x < shape[1]
        and 0 <= y < shape[0]
    ):
        raise ValueError(
            "Objetivo fuera del recorte"
        )

    return {
        "obs_id": obs["obs_id"],
        "shape": shape,
        "wcs": wcs,
        "xy": (x, y),
        "epsf": stats,
    }


def wcs_to_other(a, b, x, y):
    ra, dec = a["wcs"].pixel_to_world_values(
        x, y
    )

    return b["wcs"].world_to_pixel_values(
        ra, dec
    )


def inspect_pair(pair, radius):
    oa, ob = pair["exposures"]

    a = load_observation(oa)
    b = load_observation(ob)

    xa, ya = a["xy"]
    xb, yb = b["xy"]

    # Transformacion obtenida de los WCS.
    # NO es una medicion empirica de registro.
    mapped_center = np.array(
        wcs_to_other(a, b, xa, ya),
        dtype=float,
    )

    mapped_dx = np.array(
        wcs_to_other(
            a, b, xa + 1, ya
        ),
        dtype=float,
    )

    mapped_dy = np.array(
        wcs_to_other(
            a, b, xa, ya + 1
        ),
        dtype=float,
    )

    jacobian = np.column_stack((
        mapped_dx - mapped_center,
        mapped_dy - mapped_center,
    ))

    determinant = float(
        np.linalg.det(jacobian)
    )

    if (
        not np.isfinite(jacobian).all()
        or abs(determinant) < 1e-8
    ):
        raise ValueError(
            "Transformacion WCS degenerada"
        )

    offsets = np.arange(
        -radius,
        radius + 1,
        dtype=float,
    )

    gx, gy = np.meshgrid(
        xa + offsets,
        ya + offsets,
    )

    tx, ty = wcs_to_other(
        a, b, gx, gy
    )

    tx = np.asarray(
        tx, dtype=float
    )

    ty = np.asarray(
        ty, dtype=float
    )

    inside = (
        np.isfinite(tx)
        & np.isfinite(ty)
        & (tx >= 0)
        & (ty >= 0)
        & (tx < b["shape"][1] - 1)
        & (ty < b["shape"][0] - 1)
    )

    singular_values = np.linalg.svd(
        jacobian, compute_uv=False
    )

    sigma_a = a["epsf"][
        "positive_part_sigma_rms_native_pix"
    ]

    sigma_b = b["epsf"][
        "positive_part_sigma_rms_native_pix"
    ]

    ratio = (
        float(
            max(sigma_a, sigma_b)
            / min(sigma_a, sigma_b)
        )
        if min(sigma_a, sigma_b) > 0
        else None
    )

    return {
        "pair_id": pair["pair_id"],
        "status": (
            "GEOMETRY_AND_EPSF_DIAGNOSTIC_ONLY"
        ),
        "observation_ids": [
            a["obs_id"],
            b["obs_id"],
        ],
        "mapped_center_in_second_cutout_xy_0based": (
            mapped_center.tolist()
        ),
        "catalog_center_in_second_cutout_xy_0based": [
            xb, yb
        ],
        "center_consistency_pixels_not_astrometric_residual": float(
            np.linalg.norm(
                mapped_center
                - np.array([xb, yb])
            )
        ),
        "local_jacobian_second_pixels_per_first_pixel": (
            jacobian.tolist()
        ),
        "local_jacobian_determinant": determinant,
        "local_singular_values": (
            singular_values.tolist()
        ),
        "wcs_footprint_points_inside_second_cutout": int(
            inside.sum()
        ),
        "wcs_footprint_total_points": int(
            inside.size
        ),
        "first_epsf": a["epsf"],
        "second_epsf": b["epsf"],
        "epsf_sigma_rms_ratio_descriptive": ratio,
        "empirical_star_registration_done": False,
        "epsf_subpixel_model_fitted": False,
        "photometric_scale_estimated": False,
        "real_zogy_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(
        description="MORLEY 07G WCS y ePSF"
    )

    parser.add_argument(
        "--pair-id",
        choices=["C001", "C002", "C003"],
    )

    parser.add_argument(
        "--radius",
        type=int,
        default=5,
    )

    args = parser.parse_args()

    if not 2 <= args.radius <= 10:
        parser.error(
            "El radio debe estar entre 2 y 10"
        )

    b = read_json(SOURCE)
    f = read_json(FOOTPRINT)

    approved = {
        p["pair_id"]
        for p in f["pairs"]
        if p.get("status")
        == "SPECTRAL_FOOTPRINT_DIAGNOSTIC"
    }

    records = []

    for pair in b["pairs"]:
        pair_id = pair["pair_id"]

        if (
            args.pair_id
            and pair_id != args.pair_id
        ):
            continue

        try:
            if pair_id not in approved:
                raise ValueError(
                    "07F no completo el diagnostico"
                )

            result = inspect_pair(
                pair, args.radius
            )

        except Exception as exc:
            result = {
                "pair_id": pair_id,
                "status": "ERROR",
                "error": (
                    f"{type(exc).__name__}: {exc}"
                ),
                "real_zogy_authorized": False,
            }

        records.append(result)

        print(
            f"{pair_id} -> {result['status']}"
        )

        if result["status"] == "ERROR":
            print(
                "  Error:",
                result["error"],
            )
        else:
            print(
                "  Cobertura WCS:",
                f"{result['wcs_footprint_points_inside_second_cutout']}/"
                f"{result['wcs_footprint_total_points']}",
            )

            print(
                "  Relacion sigma ePSF:",
                f"{result['epsf_sigma_rms_ratio_descriptive']:.4f}",
            )

            print(
                "  Determinante Jacobiano WCS:",
                f"{result['local_jacobian_determinant']:.6f}",
            )

    if not records:
        parser.error(
            "No se selecciono ningun par"
        )

    payload = {
        "schema_version": (
            "morley.wcs_epsf_diagnostic.v1"
        ),
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "evidence_type": (
            "real_spherex_instrumental_diagnostic"
        ),
        "wcs_geometry_is_not_empirical_registration": True,
        "epsf_moments_are_not_psf_model_fits": True,
        "real_zogy_authorized": False,
        "pairs": records,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    print("\nJSON:", OUTPUT)
    print("ZOGY real: NO AUTORIZADO")


if __name__ == "__main__":
    main()
