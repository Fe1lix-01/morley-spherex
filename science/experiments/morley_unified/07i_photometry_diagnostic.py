
#!/usr/bin/env python3
"""MORLEY 07I: diagnostico fotometrico de apertura y fondo local.

Lee recortes reales de SPHEREx Level-2.
No ajusta ePSF, no registra imagenes, no obtiene
flujos calibrados ni afirma deteccion de variabilidad.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits


ROOT = Path(__file__).resolve().parent
VAL = ROOT / "outputs" / "validations"

IN_B = VAL / "morley_07b_instrumental.json"
IN_G = VAL / "morley_07g_wcs_epsf.json"
IN_H = VAL / "morley_07h_astrometry.json"
OUT = VAL / "morley_07i_photometry.json"

# Misma mascara conservadora usada en 07H.
# SOURCE se conserva en la apertura, pero se excluye del fondo.
EXCLUDED_BITS = (
    0, 1, 2, 6, 7, 9, 10, 11, 14, 15,
    17, 19, 20, 22, 25, 26, 27, 28, 29,
)

BAD_MASK = sum(1 << bit for bit in EXCLUDED_BITS)
SOURCE_BIT = 1 << 21


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Falta reporte: {path.name}")

    return json.loads(path.read_text(encoding="utf-8-sig"))


def fits_file(raw: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Ruta FITS vacia")

    path = Path(raw)

    if path.is_absolute():
        raise ValueError("Se requieren rutas FITS relativas")

    resolved = (ROOT / path).resolve()

    if (
        not resolved.is_relative_to(ROOT.resolve())
        or resolved.suffix.lower() != ".fits"
    ):
        raise ValueError("Ruta FITS fuera del proyecto")

    if not resolved.is_file():
        raise FileNotFoundError(resolved)

    return resolved


def fractional_weights(
    xgrid: np.ndarray,
    ygrid: np.ndarray,
    xc: float,
    yc: float,
    radius: float,
    subsamples: int = 8,
) -> np.ndarray:
    """Fraccion de cada pixel cubierta por una apertura circular."""

    offsets = (np.arange(subsamples, dtype=float) + 0.5) / subsamples - 0.5

    xx = xgrid[..., None, None] + offsets[None, None, :, None] - xc
    yy = ygrid[..., None, None] + offsets[None, None, None, :] - yc

    return np.mean(
        xx * xx + yy * yy <= radius * radius,
        axis=(-2, -1),
    )


def robust_background(values: np.ndarray) -> tuple[float, float, int]:
    """Mediana y MAD del anillo, con recorte iterativo 3 sigma."""

    values = np.asarray(values, dtype=float)
    mask = np.isfinite(values)

    for _ in range(4):
        valid = values[mask]

        if len(valid) < 10:
            break

        median = float(np.median(valid))
        sigma = 1.4826 * float(
            np.median(np.abs(valid - median))
        )

        if sigma < 1e-12:
            break

        new_mask = mask & (
            np.abs(values - median) <= 3 * sigma
        )

        if new_mask.sum() == mask.sum():
            break

        mask = new_mask

    valid = values[mask]

    if len(valid) < 10:
        raise ValueError(
            "Fondo insuficiente tras sigma-clipping"
        )

    median = float(np.median(valid))
    scatter = 1.4826 * float(
        np.median(np.abs(valid - median))
    )

    return median, scatter, int(len(valid))


def inspect_exposure(
    obs: dict,
    aperture: float,
    bg_inner: float,
    bg_outer: float,
    min_ap_coverage: float,
    min_bg_pixels: int,
) -> dict:

    result = {
        "obs_id": obs.get("obs_id"),
        "status": "BLOCKED",
        "file": obs.get("file"),
        "issues": [],
    }

    try:
        path = fits_file(obs.get("file"))
        xc, yc = map(
            float,
            obs["target_cutout_xy_0based"],
        )

        with fits.open(path, memmap=False) as hdul:
            image = np.asarray(
                hdul["IMAGE"].data,
                dtype=float,
            )

            variance = np.asarray(
                hdul["VARIANCE"].data,
                dtype=float,
            )

            flags = np.asarray(
                hdul["FLAGS"].data,
            )

            unit = str(
                hdul["IMAGE"].header.get("BUNIT", "")
            ).strip()

            zodi_available = "ZODI" in hdul

        if (
            image.ndim != 2
            or variance.shape != image.shape
            or flags.shape != image.shape
            or not np.issubdtype(flags.dtype, np.integer)
        ):
            raise ValueError(
                "IMAGE/VARIANCE/FLAGS invalidos"
            )

        if unit.lower().replace(" ", "") != "mjy/sr":
            raise ValueError(
                f"BUNIT inesperada: {unit!r}"
            )

        if not (np.isfinite(xc) and np.isfinite(yc)):
            raise ValueError(
                "Posicion objetivo invalida"
            )

        ny, nx = image.shape

        xlo = max(
            0,
            int(math.floor(xc - bg_outer - 1)),
        )
        xhi = min(
            nx,
            int(math.ceil(xc + bg_outer + 2)),
        )
        ylo = max(
            0,
            int(math.floor(yc - bg_outer - 1)),
        )
        yhi = min(
            ny,
            int(math.ceil(yc + bg_outer + 2)),
        )

        if xhi <= xlo or yhi <= ylo:
            raise ValueError(
                "Objetivo fuera del recorte"
            )

        yg, xg = np.mgrid[
            ylo:yhi,
            xlo:xhi,
        ]

        ap = fractional_weights(
            xg,
            yg,
            xc,
            yc,
            aperture,
        )

        ann = (
            fractional_weights(
                xg, yg, xc, yc, bg_outer
            )
            - fractional_weights(
                xg, yg, xc, yc, bg_inner
            )
        )

        im = image[ylo:yhi, xlo:xhi]
        va = variance[ylo:yhi, xlo:xhi]
        fl = flags[ylo:yhi, xlo:xhi].astype(np.int64)

        numeric = (
            np.isfinite(im)
            & np.isfinite(va)
            & (va > 0)
        )

        good_ap = (
            numeric
            & ((fl & BAD_MASK) == 0)
        )

        good_bg = (
            good_ap
            & ((fl & SOURCE_BIT) == 0)
        )

        ap_geom = float(
            ap.sum() / (math.pi * aperture**2)
        )

        ap_good = float(
            (ap * good_ap).sum()
            / max(ap.sum(), 1e-15)
        )

        bg_geom = float(
            ann.sum()
            / (
                math.pi
                * (bg_outer**2 - bg_inner**2)
            )
        )

        bg_mask = (
            (ann > 0.5)
            & good_bg
        )

        bg_pixels = int(bg_mask.sum())

        result.update({
            "target_cutout_xy_0based": [xc, yc],
            "bunit": unit,
            "aperture_radius_pix": aperture,
            "background_annulus_pix": [
                bg_inner,
                bg_outer,
            ],
            "aperture_geometric_fraction": round(
                ap_geom, 5
            ),
            "aperture_good_fraction": round(
                ap_good, 5
            ),
            "background_geometric_fraction": round(
                bg_geom, 5
            ),
            "background_candidate_pixels": bg_pixels,
            "zodi_present_not_subtracted": zodi_available,
        })

        if ap_geom < 0.95:
            result["issues"].append(
                "Apertura geometrica truncada"
            )

        if ap_good < min_ap_coverage:
            result["issues"].append(
                "Demasiados pixeles excluidos"
            )

        if bg_geom < 0.85:
            result["issues"].append(
                "Anillo de fondo truncado"
            )

        if bg_pixels < min_bg_pixels:
            result["issues"].append(
                "Pocos pixeles de fondo sin SOURCE"
            )

        if result["issues"]:
            return result

        bg, scatter, nbg = robust_background(
            im[bg_mask]
        )

        # Evitar propagacion de NaN.
        # 0 * NaN sigue siendo NaN en NumPy.

        weights = np.where(
            good_ap,
            ap,
            0.0,
        )

        safe_signal = np.where(
            good_ap,
            im - bg,
            0.0,
        )

        safe_variance = np.where(
            good_ap,
            va,
            0.0,
        )

        signal = float(
            np.sum(weights * safe_signal)
        )

        formal_var = float(
            np.sum(weights**2 * safe_variance)
        )

        if not np.isfinite(signal):
            raise ValueError(
                "Senal no finita despues del enmascaramiento"
            )

        if not np.isfinite(formal_var) or formal_var <= 0:
            raise ValueError(
                "Varianza de apertura invalida despues del enmascaramiento"
            )

        # Aproximacion exploratoria:
        # ruido gaussiano independiente.

        bg_sem = (
            1.2533 * scatter
            / math.sqrt(nbg)
        )

        approx_error = math.sqrt(
            formal_var
            + (float(weights.sum()) * bg_sem) ** 2
        )

        if not np.isfinite(approx_error) or approx_error <= 0:
            raise ValueError(
                "Incertidumbre no positiva"
            )

        result.update({
            "status": "APERTURE_DIAGNOSTIC_ONLY",
            "background_mjy_sr": bg,
            "background_scatter_mjy_sr": scatter,
            "background_pixels_after_clipping": nbg,
            "background_median_error_approx_mjy_sr": bg_sem,
            "uncalibrated_aperture_excess_mjy_sr_times_pixel": signal,
            "formal_diagonal_error_same_units": approx_error,
            "formal_snr_not_a_detection_claim": (
                signal / approx_error
            ),
            "aperture_area_usable_pixels": float(
                weights.sum()
            ),
        })

    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: {exc}"
        )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MORLEY 07I - Fotometria diagnostica"
    )

    parser.add_argument(
        "--pair-id",
        choices=("C001", "C002", "C003"),
    )
    parser.add_argument(
        "--aperture",
        type=float,
        default=2.5,
    )
    parser.add_argument(
        "--bg-inner",
        type=float,
        default=5.0,
    )
    parser.add_argument(
        "--bg-outer",
        type=float,
        default=9.0,
    )
    parser.add_argument(
        "--min-ap-coverage",
        type=float,
        default=0.80,
    )
    parser.add_argument(
        "--min-bg-pixels",
        type=int,
        default=20,
    )

    args = parser.parse_args()

    if not (
        1 <= args.aperture
        < args.bg_inner
        < args.bg_outer <= 20
    ):
        parser.error(
            "Radios de apertura y fondo invalidos"
        )

    if (
        not 0.5 <= args.min_ap_coverage <= 1
        or args.min_bg_pixels < 10
    ):
        parser.error(
            "Limites de cobertura invalidos"
        )

    source = read_json(IN_B)
    geom = read_json(IN_G)
    astro = read_json(IN_H)

    geom_by = {
        p["pair_id"]: p
        for p in geom["pairs"]
    }

    astro_by = {
        p["pair_id"]: p
        for p in astro["pairs"]
    }

    pairs = []

    for pair in source["pairs"]:
        pid = pair["pair_id"]

        if args.pair_id and pid != args.pair_id:
            continue

        gp = geom_by.get(pid, {})
        hp = astro_by.get(pid, {})

        ids = [
            obs["obs_id"]
            for obs in pair["exposures"]
        ]

        reports_ok = (
            gp.get("observation_ids") == ids
            and gp.get("status")
            == "GEOMETRY_AND_EPSF_DIAGNOSTIC_ONLY"
            and hp.get("status")
            == "OFFTARGET_OFFSET_ESTIMATED_REVIEW_REQUIRED"
        )

        if not reports_ok:
            entry = {
                "pair_id": pid,
                "status": "STALE_OR_INCOMPLETE_PRIOR_REPORTS",
                "observations": [],
                "real_zogy_authorized": False,
            }

        else:
            measurements = [
                inspect_exposure(
                    obs,
                    args.aperture,
                    args.bg_inner,
                    args.bg_outer,
                    args.min_ap_coverage,
                    args.min_bg_pixels,
                )
                for obs in pair["exposures"]
            ]

            complete = all(
                m["status"] == "APERTURE_DIAGNOSTIC_ONLY"
                for m in measurements
            )

            entry = {
                "pair_id": pid,
                "status": (
                    "DIAGNOSTIC_MEASUREMENTS_AVAILABLE"
                    if complete
                    else "APERTURE_DIAGNOSTIC_INCOMPLETE"
                ),
                "observations": measurements,
                "offtarget_wcs_residual_median_xy_pix_not_applied": (
                    hp.get("fit", {}).get(
                        "wcs_offset_median_xy_pix"
                    )
                ),
                "epsf_sigma_rms_ratio_descriptive": gp.get(
                    "epsf_sigma_rms_ratio_descriptive"
                ),
                "psf_aperture_correction_performed": False,
                "relative_photometric_scale_calibrated": False,
                "registered_image_subtraction_performed": False,
                "real_zogy_authorized": False,
                "variability_detected": False,
            }

        pairs.append(entry)

        print(
            f"{pid} -> {entry['status']}"
        )

        for obs in entry.get("observations", []):
            coverage = obs.get(
                "aperture_good_fraction",
                float("nan"),
            )

            nbg = obs.get(
                "background_pixels_after_clipping",
                0,
            )

            snr = obs.get(
                "formal_snr_not_a_detection_claim"
            )

            snr_text = (
                f"{snr:.2f}"
                if snr is not None
                else "N/D"
            )

            print(
                f"  {obs['obs_id']}: {obs['status']} "
                f"| cobertura={coverage:.1%} "
                f"| fondo n={nbg} "
                f"| SNR formal={snr_text}"
            )

            for issue in obs.get("issues", []):
                print("   -", issue)

    if not pairs:
        parser.error(
            "Ninguna pareja seleccionada"
        )

    payload = {
        "schema_version": "morley.07i.aperture_diagnostic.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_type": (
            "real_spherex_uncalibrated_aperture_diagnostic"
        ),
        "parameters": vars(args),
        "mask_policy_excluded_bits": list(EXCLUDED_BITS),
        "source_bit_excluded_only_for_background": True,
        "background_error_assumes_independent_gaussian_pixels": True,
        "per_pixel_area_and_psf_aperture_corrections_done": False,
        "empirical_registration_applied": False,
        "real_zogy_authorized": False,
        "variability_claimed": False,
        "pairs": pairs,
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    print("\nJSON:", OUT)
    print(
        "Flujos calibrados: NO "
        "| Variabilidad: NO "
        "| ZOGY real: NO"
    )


if __name__ == "__main__":
    main()
