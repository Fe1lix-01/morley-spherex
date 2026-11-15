
#!/usr/bin/env python3
"""MORLEY 07H: diagnostico empirico astrometrico.

Busca fuentes fuera del objetivo, calcula centroides y
compara posiciones medidas contra predicciones WCS.

NO registra ni resta imagenes.
NO declara movimiento astronomico.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


ROOT = Path(__file__).resolve().parent
VAL = ROOT / "outputs" / "validations"

SOURCE = VAL / "morley_07b_instrumental.json"
GEOM = VAL / "morley_07g_wcs_epsf.json"
OUTPUT = VAL / "morley_07h_astrometry.json"

# Mascara conservadora para buscar fuentes.
# SOURCE (21) y FULLSAMPLE (12) se conservan.
EXCLUDED_BITS = (
    0, 1, 2, 6, 7, 9, 10, 11, 14, 15,
    17, 19, 20, 22, 25, 26, 27, 28, 29,
)

BAD_FLAG_MASK = sum(
    1 << bit for bit in EXCLUDED_BITS
)


def read_json(path):
    if not path.is_file():
        raise FileNotFoundError(path)

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def safe_fits(raw):
    if not isinstance(raw, str) or not raw:
        raise ValueError("Falta ruta FITS")

    p = Path(raw)

    if p.is_absolute():
        raise ValueError(
            "Ruta absoluta no permitida"
        )

    p = (ROOT / p).resolve()

    if (
        not p.is_relative_to(ROOT.resolve())
        or p.suffix.lower() != ".fits"
    ):
        raise ValueError(
            "FITS fuera del proyecto"
        )

    if not p.is_file():
        raise FileNotFoundError(p)

    return p


def load_obs(record):
    path = safe_fits(record["file"])

    with fits.open(path, memmap=False) as hdul:
        required = (
            "IMAGE", "VARIANCE", "FLAGS"
        )

        if any(name not in hdul for name in required):
            raise ValueError(
                "Faltan IMAGE/VARIANCE/FLAGS"
            )

        image = np.asarray(
            hdul["IMAGE"].data,
            dtype=float,
        ).copy()

        variance = np.asarray(
            hdul["VARIANCE"].data,
            dtype=float,
        ).copy()

        flags = np.asarray(
            hdul["FLAGS"].data
        ).copy()

        if (
            image.ndim != 2
            or image.shape != variance.shape
            or image.shape != flags.shape
        ):
            raise ValueError(
                "Dimensiones incompatibles"
            )

        if not np.issubdtype(
            flags.dtype, np.integer
        ):
            raise ValueError(
                "FLAGS no es entero"
            )

        wcs = WCS(
            hdul["IMAGE"].header,
            fobj=hdul,
        ).celestial

        zodi_used = False

        if "ZODI" in hdul:
            z = hdul["ZODI"].data

            if (
                z is not None
                and z.shape == image.shape
            ):
                z = np.asarray(z, dtype=float)

                if np.isfinite(z).all():
                    # Solo para detectar fuentes.
                    # NO se guarda una imagen modificada.
                    image -= z
                    zodi_used = True

    return {
        "id": record["obs_id"],
        "image": image,
        "variance": variance,
        "flags": flags.astype(np.int64),
        "wcs": wcs,
        "target_xy": tuple(
            map(
                float,
                record[
                    "target_cutout_xy_0based"
                ],
            )
        ),
        "zodi_removed_for_detection_only": (
            zodi_used
        ),
    }


def detect_sources(
    obs,
    threshold,
    exclusion,
    limit,
):
    im = obs["image"]
    va = obs["variance"]
    fl = obs["flags"]

    good = (
        np.isfinite(im)
        & np.isfinite(va)
        & (va > 0)
        & ((fl & BAD_FLAG_MASK) == 0)
    )

    if int(good.sum()) < 80:
        return [], {
            "error": "Muy pocos pixeles limpios"
        }

    bg = float(
        np.median(im[good])
    )

    scatter = 1.4826 * float(
        np.median(
            np.abs(im[good] - bg)
        )
    )

    var_sigma = float(
        np.median(
            np.sqrt(va[good])
        )
    )

    noise = max(
        scatter,
        var_sigma,
        1e-12,
    )

    residual = im - bg

    snr = np.where(
        good,
        residual / noise,
        -np.inf,
    )

    peaks = np.argwhere(
        snr >= threshold
    )

    peaks = sorted(
        peaks,
        key=lambda ij: snr[
            ij[0], ij[1]
        ],
        reverse=True,
    )

    selected = []

    tx, ty = obs["target_xy"]
    ny, nx = im.shape

    for iy, ix in peaks:
        iy = int(iy)
        ix = int(ix)

        if (
            ix < 4
            or iy < 4
            or ix >= nx - 4
            or iy >= ny - 4
        ):
            continue

        # Nunca utilizar el objetivo principal
        # como referencia de alineacion.
        if (
            (ix - tx) ** 2
            + (iy - ty) ** 2
            < exclusion ** 2
        ):
            continue

        box3 = snr[
            iy - 1:iy + 2,
            ix - 1:ix + 2,
        ]

        if snr[iy, ix] < float(
            np.max(box3)
        ):
            continue

        box = residual[
            iy - 2:iy + 3,
            ix - 2:ix + 3,
        ]

        valid = good[
            iy - 2:iy + 3,
            ix - 2:ix + 3,
        ]

        if int(valid.sum()) < 20:
            continue

        weights = np.where(
            valid,
            np.maximum(box, 0.0),
            0.0,
        )

        total = float(
            weights.sum()
        )

        if total <= 0:
            continue

        gy, gx = np.indices(
            (5, 5),
            dtype=float,
        )

        mx = float(
            np.sum(
                weights * (gx + ix - 2)
            ) / total
        )

        my = float(
            np.sum(
                weights * (gy + iy - 2)
            ) / total
        )

        if (
            abs(mx - ix) > 1.2
            or abs(my - iy) > 1.2
        ):
            continue

        size = np.sqrt(
            float(
                np.sum(
                    weights * (
                        (gx + ix - 2 - mx) ** 2
                        + (gy + iy - 2 - my) ** 2
                    )
                ) / total
            )
        )

        if not 0.45 <= size <= 3.0:
            continue

        # Evitar detecciones duplicadas.
        too_close = any(
            (
                (mx - p["x"]) ** 2
                + (my - p["y"]) ** 2
            ) < 4.5 ** 2
            for p in selected
        )

        if too_close:
            continue

        selected.append({
            "x": mx,
            "y": my,
            "snr_peak": float(
                snr[iy, ix]
            ),
            "size_rms_pix": float(size),
        })

        if len(selected) >= limit:
            break

    return selected, {
        "background": bg,
        "noise_scale": noise,
        "numeric_good_fraction": float(
            good.mean()
        ),
        "zodi_removed_for_detection_only": (
            obs["zodi_removed_for_detection_only"]
        ),
    }


def match_sources(
    a,
    b,
    detections_a,
    detections_b,
    max_dist,
):
    if not detections_a or not detections_b:
        return []

    ax = np.array([
        p["x"] for p in detections_a
    ])

    ay = np.array([
        p["y"] for p in detections_a
    ])

    sky_ra, sky_dec = (
        a["wcs"].pixel_to_world_values(
            ax, ay
        )
    )

    pred_x, pred_y = (
        b["wcs"].world_to_pixel_values(
            sky_ra,
            sky_dec,
        )
    )

    candidates = []

    for i, (x, y) in enumerate(
        zip(pred_x, pred_y)
    ):
        if not np.isfinite(
            [x, y]
        ).all():
            continue

        for j, p in enumerate(
            detections_b
        ):
            distance = float(
                np.hypot(
                    p["x"] - x,
                    p["y"] - y,
                )
            )

            if distance <= max_dist:
                candidates.append((
                    distance,
                    i,
                    j,
                    float(x),
                    float(y),
                ))

    selected = []
    used_a = set()
    used_b = set()

    for distance, i, j, x, y in sorted(
        candidates
    ):
        if i in used_a or j in used_b:
            continue

        used_a.add(i)
        used_b.add(j)

        p = detections_b[j]

        selected.append({
            "a_xy": [
                float(ax[i]),
                float(ay[i]),
            ],
            "b_measured_xy": [
                p["x"],
                p["y"],
            ],
            "b_wcs_predicted_xy": [
                x, y
            ],
            "residual_b_xy_pix": [
                p["x"] - x,
                p["y"] - y,
            ],
            "nearest_distance_pix": (
                distance
            ),
        })

    return selected


def fit_offsets(
    matches,
    min_matches,
):
    if len(matches) < min_matches:
        return {
            "status": (
                "INSUFFICIENT_OFFTARGET_MATCHES"
            ),
            "matches_before_clipping": (
                len(matches)
            ),
            "inliers": 0,
        }

    residuals = np.array([
        m["residual_b_xy_pix"]
        for m in matches
    ])

    keep = np.ones(
        len(residuals),
        dtype=bool,
    )

    for _ in range(5):
        median = np.median(
            residuals[keep],
            axis=0,
        )

        distance = np.linalg.norm(
            residuals - median,
            axis=1,
        )

        mad = 1.4826 * np.median(
            distance[keep]
        )

        cutoff = max(
            0.65,
            3 * float(mad),
        )

        new_keep = (
            distance <= cutoff
        )

        if int(
            new_keep.sum()
        ) < min_matches:
            break

        if np.array_equal(
            keep,
            new_keep,
        ):
            break

        keep = new_keep

    n = int(
        keep.sum()
    )

    if n < min_matches:
        return {
            "status": (
                "INSUFFICIENT_ROBUST_INLIERS"
            ),
            "matches_before_clipping": (
                len(matches)
            ),
            "inliers": n,
        }

    median = np.median(
        residuals[keep],
        axis=0,
    )

    err = (
        residuals[keep] - median
    )

    rms = float(
        np.sqrt(
            np.mean(
                np.sum(
                    err * err,
                    axis=1,
                )
            )
        )
    )

    refs = np.asarray([
        m["b_measured_xy"]
        for k, m in enumerate(matches)
        if keep[k]
    ])

    extent = np.ptp(
        refs,
        axis=0,
    )

    spread_ok = bool(
        np.min(extent) >= 10.0
    )

    status = (
        "OFFTARGET_OFFSET_ESTIMATED_REVIEW_REQUIRED"
    )

    if rms > 1.0:
        status = (
            "FIELD_MATCH_SCATTER_TOO_LARGE"
        )

    if not spread_ok:
        status = (
            "FIELD_REFERENCES_TOO_CLUSTERED"
        )

    return {
        "status": status,
        "matches_before_clipping": (
            len(matches)
        ),
        "inliers": n,
        "wcs_offset_median_xy_pix": [
            float(median[0]),
            float(median[1]),
        ],
        "inlier_rms_2d_pix": rms,
        "inlier_position_extent_xy_pix": [
            float(v)
            for v in extent
        ],
        "inlier_matches": [
            m
            for k, m in enumerate(matches)
            if keep[k]
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "MORLEY 07H - "
            "Astrometria local de campo"
        )
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
    )

    parser.add_argument(
        "--exclude-radius",
        type=float,
        default=10.0,
    )

    parser.add_argument(
        "--match-radius",
        type=float,
        default=3.0,
    )

    parser.add_argument(
        "--min-matches",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--max-sources",
        type=int,
        default=60,
    )

    args = parser.parse_args()

    if (
        not np.isfinite(args.threshold)
        or args.threshold <= 0
        or not np.isfinite(args.exclude_radius)
        or args.exclude_radius < 5
        or not np.isfinite(args.match_radius)
        or args.match_radius <= 0
        or not 3 <= args.min_matches <= 50
        or not 5 <= args.max_sources <= 200
    ):
        parser.error(
            "Parametros de deteccion invalidos"
        )

    input_data = read_json(SOURCE)
    geom = read_json(GEOM)

    allowed = {
        p["pair_id"]
        for p in geom.get("pairs", [])
        if p.get("status")
        == "GEOMETRY_AND_EPSF_DIAGNOSTIC_ONLY"
    }

    reports = []

    for pair in input_data.get(
        "pairs", []
    ):
        pid = pair["pair_id"]

        out = {
            "pair_id": pid,
            "status": "ERROR",
            "real_zogy_authorized": False,
            "registration_applied": False,
            "motion_detected": False,
        }

        try:
            if pid not in allowed:
                raise ValueError(
                    "Falta diagnostico en 07G"
                )

            a, b = [
                load_obs(obs)
                for obs in pair["exposures"]
            ]

            da, qa = detect_sources(
                a,
                args.threshold,
                args.exclude_radius,
                args.max_sources,
            )

            db, qb = detect_sources(
                b,
                args.threshold,
                args.exclude_radius,
                args.max_sources,
            )

            matches = match_sources(
                a, b, da, db,
                args.match_radius,
            )

            fit = fit_offsets(
                matches,
                args.min_matches,
            )

            out.update({
                "status": fit.pop("status"),
                "source_candidates_per_epoch": [
                    len(da), len(db)
                ],
                "detection_info": [
                    qa, qb
                ],
                "fit": fit,
                "independently_confirmed_static_stars": (
                    False
                ),
                "astrometric_registration_completed": (
                    False
                ),
            })

        except Exception as exc:
            out["error"] = (
                f"{type(exc).__name__}: {exc}"
            )

        reports.append(out)

        fit = out.get("fit", {})

        print(
            f"{pid} -> {out['status']} "
            f"| fuentes: "
            f"{out.get('source_candidates_per_epoch', ['?', '?'])} "
            f"| matches: "
            f"{fit.get('matches_before_clipping', 0)} "
            f"| inliers: "
            f"{fit.get('inliers', 0)}"
        )

        if (
            "wcs_offset_median_xy_pix"
            in fit
        ):
            print(
                "  Residual WCS (px):",
                [
                    round(v, 4)
                    for v in fit[
                        "wcs_offset_median_xy_pix"
                    ]
                ],
                "| RMS:",
                round(
                    fit["inlier_rms_2d_pix"],
                    4,
                ),
            )

        if "error" in out:
            print(
                "  Error:",
                out["error"],
            )

    payload = {
        "schema_version": "morley.07h.v1",
        "generated_at_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "evidence_type": (
            "offtarget_source_centroid_diagnostic"
        ),
        "no_verified_static_reference_catalog": (
            True
        ),
        "no_robust_registration_claim": True,
        "no_flux_resampling_or_subtraction": True,
        "real_zogy_authorized": False,
        "parameters": vars(args),
        "pairs": reports,
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
    print(
        "Registro astrometrico cientifico: "
        "NO CONFIRMADO"
    )
    print(
        "ZOGY real: NO AUTORIZADO"
    )


if __name__ == "__main__":
    main()
