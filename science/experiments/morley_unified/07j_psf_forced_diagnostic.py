
#!/usr/bin/env python3
"""MORLEY 07J - fotometria forzada ePSF, SOLO DIAGNOSTICA.

No genera flujos fisicos integrados, no compara variabilidad,
no registra imagenes ni autoriza ZOGY real.
Requiere resultados 07B, 07G, 07H y 07I.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits


ROOT = Path(__file__).resolve().parent
VAL = ROOT / "outputs" / "validations"

INPUTS = {
    "07b": VAL / "morley_07b_instrumental.json",
    "07g": VAL / "morley_07g_wcs_epsf.json",
    "07h": VAL / "morley_07h_astrometry.json",
    "07i": VAL / "morley_07i_photometry.json",
}

OUTPUT = VAL / "morley_07j_psf_forced.json"

BAD_BITS = (
    0, 1, 2, 6, 7, 9, 10, 11, 14, 15,
    17, 19, 20, 22, 25, 26, 27, 28, 29,
)

BAD_MASK = sum(1 << bit for bit in BAD_BITS)


def json_data(path):
    if not path.is_file():
        raise FileNotFoundError(f"Falta reporte: {path}")

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def safe_fits(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Ruta FITS ausente")

    p = Path(raw)

    if p.is_absolute():
        raise ValueError(
            "El FITS debe tener ruta relativa"
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


def sample_epsf(stamp, u, v):
    """Interpolar ePSF en centros de pixeles nativos."""

    ny, nx = stamp.shape

    inside = (
        np.isfinite(u)
        & np.isfinite(v)
        & (u >= 0)
        & (v >= 0)
        & (u <= nx - 1)
        & (v <= ny - 1)
    )

    u0 = np.floor(
        np.where(inside, u, 0)
    ).astype(int)

    v0 = np.floor(
        np.where(inside, v, 0)
    ).astype(int)

    u1 = np.minimum(u0 + 1, nx - 1)
    v1 = np.minimum(v0 + 1, ny - 1)

    du = np.where(inside, u - u0, 0.0)
    dv = np.where(inside, v - v0, 0.0)

    sampled = (
        (1 - du) * (1 - dv) * stamp[v0, u0]
        + du * (1 - dv) * stamp[v0, u1]
        + (1 - du) * dv * stamp[v1, u0]
        + du * dv * stamp[v1, u1]
    )

    return np.where(inside, sampled, 0.0)


def forced_fit(obs, radius=6, min_psf_coverage=0.75):
    result = {
        "obs_id": obs.get("obs_id"),
        "status": "BLOCKED",
        "issues": [],
        "evidence_type": "diagnostic_psf_amplitude_only",
    }

    try:
        if not obs.get("epsf_selected"):
            raise ValueError(
                "07B no selecciono ePSF"
            )

        path = safe_fits(obs.get("file"))

        x, y = map(
            float,
            obs["target_cutout_xy_0based"],
        )

        ix, iy = int(round(x)), int(round(y))

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
                hdul["FLAGS"].data
            )

            unit = str(
                hdul["IMAGE"].header.get(
                    "BUNIT", ""
                )
            ).strip()

            tab = hdul["EPSF"].data
            header = hdul["EPSF"].header

            index = int(
                obs["epsf_zone"]["row_0based"]
            )

            stamp = np.asarray(
                tab["EPSF"][index],
                dtype=float,
            )

            ovs_x = int(header.get("OVSMPX", 0))
            ovs_y = int(header.get("OVSMPY", 0))

            detcoord = str(
                header.get("DETCOORD", "")
            ).strip()

        if (
            image.ndim != 2
            or variance.shape != image.shape
            or flags.shape != image.shape
        ):
            raise ValueError(
                "Dimensiones FITS incompatibles"
            )

        if not np.issubdtype(
            flags.dtype,
            np.integer,
        ):
            raise ValueError(
                "FLAGS debe ser entero"
            )

        if unit.lower().replace(" ", "") != "mjy/sr":
            raise ValueError(
                f"Unidad inesperada: {unit}"
            )

        if (
            stamp.ndim != 2
            or min(stamp.shape) < 5
            or not np.isfinite(stamp).all()
        ):
            raise ValueError("ePSF invalida")

        if ovs_x <= 0 or ovs_y <= 0:
            raise ValueError(
                "Sobremuestreo ePSF invalido"
            )

        if detcoord.lower() not in ("sky", ""):
            raise ValueError(
                f"Orientacion ePSF no verificada: {detcoord}"
            )

        if not (np.isfinite(x) and np.isfinite(y)):
            raise ValueError("Centro no finito")

        if (
            ix - radius < 0
            or iy - radius < 0
            or ix + radius >= image.shape[1]
            or iy + radius >= image.shape[0]
        ):
            raise ValueError(
                "Ventana de ajuste truncada"
            )

        ys, xs = np.mgrid[
            iy - radius:iy + radius + 1,
            ix - radius:ix + radius + 1,
        ]

        stamp_x = (
            (xs - x) * ovs_x
            + (stamp.shape[1] - 1) / 2
        )

        stamp_y = (
            (ys - y) * ovs_y
            + (stamp.shape[0] - 1) / 2
        )

        model = sample_epsf(
            stamp, stamp_x, stamp_y
        )

        total = float(np.sum(model))

        if not np.isfinite(total) or total <= 0:
            raise ValueError(
                "Modelo ePSF no normalizable"
            )

        # Normalizacion diagnostica en ventana finita.
        # La amplitud no es un flujo fisico calibrado.
        model /= total

        sl_y = slice(
            iy - radius,
            iy + radius + 1,
        )

        sl_x = slice(
            ix - radius,
            ix + radius + 1,
        )

        im = image[sl_y, sl_x]
        va = variance[sl_y, sl_x]
        fl = flags[sl_y, sl_x].astype(np.int64)

        good = (
            np.isfinite(im)
            & np.isfinite(va)
            & (va > 0)
            & ((fl & BAD_MASK) == 0)
        )

        coverage = float(
            model[good].sum()
        )

        result.update({
            "valid_pixel_count": int(good.sum()),
            "total_pixel_count": int(good.size),
            "psf_weight_coverage": coverage,
            "epsf_zone_index": index,
            "epsf_stamp_shape": list(stamp.shape),
            "oversampling_xy": [ovs_x, ovs_y],
            "detcoord": detcoord,
        })

        if int(good.sum()) < 35:
            raise ValueError(
                "Pocos pixeles utilizables"
            )

        if coverage < min_psf_coverage:
            raise ValueError(
                "Cobertura de ePSF insuficiente"
            )

        # Modelo lineal:
        # amplitud ePSF + fondo + gradientes X/Y.
        coords_x = (xs - x) / radius
        coords_y = (ys - y) / radius

        design = np.column_stack((
            model[good],
            np.ones(int(good.sum())),
            coords_x[good],
            coords_y[good],
        ))

        yy = im[good]
        sigma = np.sqrt(va[good])

        A = design / sigma[:, None]
        b = yy / sigma

        beta, _, rank, _ = np.linalg.lstsq(
            A, b, rcond=None
        )

        if rank != 4:
            raise ValueError(
                "Ajuste degenerado"
            )

        normal = A.T @ A

        condition = float(
            np.linalg.cond(normal)
        )

        if (
            not np.isfinite(condition)
            or condition > 1e12
        ):
            raise ValueError(
                "Matriz mal condicionada"
            )

        covariance = np.linalg.inv(normal)

        amplitude = float(beta[0])

        amp_err = float(
            np.sqrt(covariance[0, 0])
        )

        if (
            not np.isfinite(amp_err)
            or amp_err <= 0
        ):
            raise ValueError(
                "Incertidumbre formal invalida"
            )

        residuals = b - A @ beta
        dof = max(len(b) - 4, 1)

        chi2_reduced = float(
            np.sum(residuals**2) / dof
        )

        result.update({
            "status": "FORCED_EPSF_DIAGNOSTIC_ONLY",
            "psf_model_amplitude_uncalibrated": amplitude,
            "psf_model_amplitude_error_formal_diagonal": amp_err,
            "psf_model_snr_formal_not_detection": (
                amplitude / amp_err
            ),
            "background_intercept_mjy_sr": float(
                beta[1]
            ),
            "background_gradient_x_scaled": float(
                beta[2]
            ),
            "background_gradient_y_scaled": float(
                beta[3]
            ),
            "reduced_chi2_diagonal_only": chi2_reduced,
            "normal_matrix_condition_number": condition,
            "psf_model_normalized_on_finite_window": True,
            "source_blending_modelled": False,
            "noise_covariance_modelled": False,
            "astrometric_offset_applied": False,
            "pixel_solid_angle_applied": False,
            "aperture_or_absolute_flux_calibrated": False,
            "variability_claimed": False,
            "real_zogy_authorized": False,
        })

    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: {exc}"
        )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="MORLEY 07J - ePSF forzada diagnostica"
    )

    parser.add_argument(
        "--pair-id",
        choices=("C001", "C002", "C003"),
    )

    parser.add_argument(
        "--radius",
        type=int,
        default=6,
    )

    parser.add_argument(
        "--min-psf-coverage",
        type=float,
        default=0.75,
    )

    args = parser.parse_args()

    if (
        not 4 <= args.radius <= 10
        or not 0.5 <= args.min_psf_coverage <= 1.0
    ):
        parser.error(
            "Parametros fuera de rango"
        )

    reports = {
        key: json_data(path)
        for key, path in INPUTS.items()
    }

    source = reports["07b"]

    geom = {
        p["pair_id"]: p
        for p in reports["07g"].get("pairs", [])
    }

    astro = {
        p["pair_id"]: p
        for p in reports["07h"].get("pairs", [])
    }

    aperture = {
        p["pair_id"]: p
        for p in reports["07i"].get("pairs", [])
    }

    records = []

    for pair in source.get("pairs", []):
        pid = pair["pair_id"]

        if args.pair_id and args.pair_id != pid:
            continue

        ids = [
            obs["obs_id"]
            for obs in pair["exposures"]
        ]

        gp = geom.get(pid, {})
        hp = astro.get(pid, {})
        ip = aperture.get(pid, {})

        iids = [
            m.get("obs_id")
            for m in ip.get("observations", [])
        ]

        prior_ok = (
            gp.get("observation_ids") == ids
            and gp.get("status")
            == "GEOMETRY_AND_EPSF_DIAGNOSTIC_ONLY"
            and hp.get("status")
            == "OFFTARGET_OFFSET_ESTIMATED_REVIEW_REQUIRED"
            and ip.get("status")
            == "DIAGNOSTIC_MEASUREMENTS_AVAILABLE"
            and iids == ids
        )

        if prior_ok:
            measurements = [
                forced_fit(
                    obs,
                    args.radius,
                    args.min_psf_coverage,
                )
                for obs in pair["exposures"]
            ]

            complete = all(
                m["status"] == "FORCED_EPSF_DIAGNOSTIC_ONLY"
                for m in measurements
            )

            status = (
                "PSF_DIAGNOSTICS_AVAILABLE"
                if complete
                else "PSF_DIAGNOSTICS_INCOMPLETE"
            )
        else:
            measurements = []
            status = "STALE_OR_INCOMPLETE_PRIOR_REPORTS"

        records.append({
            "pair_id": pid,
            "status": status,
            "observations": measurements,
            "real_zogy_authorized": False,
            "relative_photometric_scale_calibrated": False,
            "variability_detected": False,
        })

        print(f"{pid} -> {status}")

        for m in measurements:
            snr = m.get(
                "psf_model_snr_formal_not_detection"
            )

            chi2 = m.get(
                "reduced_chi2_diagonal_only"
            )

            if snr is None:
                print(
                    f"  {m['obs_id']}: {m['status']} "
                    f"| {m['issues']}"
                )
            else:
                print(
                    f"  {m['obs_id']}: {m['status']} "
                    f"| cobertura ePSF="
                    f"{m['psf_weight_coverage']:.1%} "
                    f"| SNR formal={snr:.2f}"
                )

            if chi2 is not None:
                print(
                    "    chi2 reducido (diagonal):",
                    f"{chi2:.3f}",
                )

    if not records:
        parser.error(
            "No se encontraron pares"
        )

    payload = {
        "schema_version": "morley.07j.epsf_forced_diagnostic.v1",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "evidence_type": "real_spherex_uncalibrated_psf_diagnostic",
        "parameters": vars(args),
        "spectral_response_and_zeropoints_harmonized": False,
        "empirical_registration_applied": False,
        "noise_covariance_calibrated": False,
        "real_zogy_authorized": False,
        "variability_claimed": False,
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
    print(
        "Fotometria calibrada: NO "
        "| Variabilidad: NO "
        "| ZOGY real: NO"
    )


if __name__ == "__main__":
    main()
