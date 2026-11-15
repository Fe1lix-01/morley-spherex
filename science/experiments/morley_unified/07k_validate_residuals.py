
#!/usr/bin/env python3
"""MORLEY 07K - diagnostico de residuos del ajuste ePSF de 07J.

Reproduce el modelo de 07J con sus parametros guardados; comprueba
chi2, distribucion de residuos y correlacion entre pixeles vecinos.

No realiza calibracion fisica, registro WCS ni ZOGY real.
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

FILE_B = VAL / "morley_07b_instrumental.json"
FILE_J = VAL / "morley_07j_psf_forced.json"

OUTPUT = VAL / "morley_07k_residuals.json"
ARRAY_DIR = VAL / "residuals_07k"

BAD_BITS = (
    0, 1, 2, 6, 7, 9, 10, 11, 14, 15,
    17, 19, 20, 22, 25, 26, 27, 28, 29,
)

BAD_MASK = sum(1 << bit for bit in BAD_BITS)


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Falta: {path}")

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def safe_fits(raw: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError("Ruta FITS ausente")

    path = Path(raw)

    if path.is_absolute():
        raise ValueError("Solo rutas relativas")

    path = (ROOT / path).resolve()

    if (
        not path.is_relative_to(ROOT.resolve())
        or path.suffix.lower() != ".fits"
    ):
        raise ValueError(
            "FITS fuera de MORLEY_PIPELINE_UNIFICADO"
        )

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def sample_epsf(
    stamp: np.ndarray,
    u: np.ndarray,
    v: np.ndarray,
) -> np.ndarray:
    """Misma interpolacion bilineal utilizada en MORLEY 07J."""

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


def neighbor_corr(
    z: np.ndarray,
    valid: np.ndarray,
    axis: int,
) -> dict:
    """Correlacion descriptiva entre residuos vecinos."""

    if axis == 1:
        ok = valid[:, :-1] & valid[:, 1:]
        left = z[:, :-1][ok]
        right = z[:, 1:][ok]
    else:
        ok = valid[:-1, :] & valid[1:, :]
        left = z[:-1, :][ok]
        right = z[1:, :][ok]

    n = len(left)
    value = None

    if (
        n >= 12
        and np.std(left) > 1e-10
        and np.std(right) > 1e-10
    ):
        value = float(
            np.corrcoef(left, right)[0, 1]
        )

    return {
        "pairs": n,
        "correlation": value,
    }


def measure(obs: dict, fit: dict, radius: int) -> dict:

    result = {
        "obs_id": obs.get("obs_id"),
        "status": "ERROR",
        "issues": [],
    }

    try:
        if fit.get("status") != "FORCED_EPSF_DIAGNOSTIC_ONLY":
            raise ValueError(
                "07J no completo este ajuste"
            )

        if fit.get("obs_id") != obs.get("obs_id"):
            raise ValueError(
                "Los IDs de 07B y 07J no coinciden"
            )

        if not obs.get("epsf_selected"):
            raise ValueError(
                "07B no selecciono ePSF"
            )

        x, y = map(
            float,
            obs["target_cutout_xy_0based"],
        )

        ix = round(x)
        iy = round(y)

        with fits.open(
            safe_fits(obs["file"]),
            memmap=False,
        ) as hdul:

            im_full = np.asarray(
                hdul["IMAGE"].data,
                dtype=float,
            )

            va_full = np.asarray(
                hdul["VARIANCE"].data,
                dtype=float,
            )

            fl_full = np.asarray(
                hdul["FLAGS"].data
            )

            table = hdul["EPSF"].data
            hdr = hdul["EPSF"].header

            row = int(
                obs["epsf_zone"]["row_0based"]
            )

            stamp = np.asarray(
                table["EPSF"][row],
                dtype=float,
            )

            ovs_x = int(
                hdr.get("OVSMPX", 0)
            )

            ovs_y = int(
                hdr.get("OVSMPY", 0)
            )

        if (
            im_full.ndim != 2
            or im_full.shape != va_full.shape
            or im_full.shape != fl_full.shape
            or not np.issubdtype(
                fl_full.dtype, np.integer
            )
        ):
            raise ValueError(
                "IMAGE/VARIANCE/FLAGS invalidos"
            )

        if (
            min(ovs_x, ovs_y) <= 0
            or stamp.ndim != 2
            or not np.isfinite(stamp).all()
        ):
            raise ValueError("ePSF invalida")

        ny, nx = im_full.shape

        if (
            ix - radius < 0
            or iy - radius < 0
            or ix + radius >= nx
            or iy + radius >= ny
        ):
            raise ValueError(
                "Ventana truncada"
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
            stamp,
            stamp_x,
            stamp_y,
        )

        mass = float(model.sum())

        if mass <= 0 or not np.isfinite(mass):
            raise ValueError(
                "Modelo ePSF no normalizable"
            )

        # Mismo convenio local de 07J.
        model /= mass

        sl = np.s_[
            iy - radius:iy + radius + 1,
            ix - radius:ix + radius + 1,
        ]

        im = im_full[sl]
        va = va_full[sl]
        fl = fl_full[sl].astype(np.int64)

        good = (
            np.isfinite(im)
            & np.isfinite(va)
            & (va > 0)
            & ((fl & BAD_MASK) == 0)
        )

        n = int(good.sum())

        if n <= 4:
            raise ValueError(
                "Insuficientes pixeles para cuatro parametros"
            )

        # Reconstruir el modelo ajustado por 07J.
        amp = float(
            fit["psf_model_amplitude_uncalibrated"]
        )

        bg = float(
            fit["background_intercept_mjy_sr"]
        )

        gx = float(
            fit["background_gradient_x_scaled"]
        )

        gy = float(
            fit["background_gradient_y_scaled"]
        )

        predicted = (
            amp * model
            + bg
            + gx * (xs - x) / radius
            + gy * (ys - y) / radius
        )

        # Residuos estandarizados por varianza.
        z = np.full(
            im.shape,
            np.nan,
            dtype=float,
        )

        z[good] = (
            (im[good] - predicted[good])
            / np.sqrt(va[good])
        )

        zv = z[good]

        chi2 = float(
            np.dot(zv, zv) / (n - 4)
        )

        expected = float(
            fit["reduced_chi2_diagonal_only"]
        )

        reproducible = (
            abs(chi2 - expected)
            <= max(
                0.01,
                0.005 * abs(expected),
            )
        )

        # Separar residuos del nucleo y del exterior.
        r = np.hypot(
            xs - x,
            ys - y,
        )

        core = good & (r <= 3.0)
        outer = good & (r > 3.0)

        def mean_z2(mask):
            if mask.sum() == 0:
                return None

            return float(
                np.mean(z[mask] ** 2)
            )

        cx = neighbor_corr(
            z,
            good,
            axis=1,
        )

        cy = neighbor_corr(
            z,
            good,
            axis=0,
        )

        issues = []

        if not reproducible:
            issues.append(
                "Chi2 no reproduce 07J; "
                "revisar archivos o parametros"
            )

        if chi2 > 1.8:
            issues.append(
                "Chi2 diagonal elevado: revisar modelo, "
                "ruido y contaminantes"
            )

        if any(
            item["correlation"] is not None
            and abs(item["correlation"]) > 0.3
            for item in (cx, cy)
        ):
            issues.append(
                "Correlacion espacial de residuos: "
                "revisar covarianza/modelo"
            )

        if int(outer.sum()) < 20:
            issues.append(
                "Pocas muestras exteriores "
                "para diagnostico local"
            )

        # Guardar mapas pequenos para inspeccion futura.
        ARRAY_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        array_path = (
            ARRAY_DIR / f"{obs['obs_id']}.npz"
        )

        np.savez_compressed(
            array_path,
            residual_sigma=z,
            valid=good,
            predicted_mjy_sr=predicted,
            image_mjy_sr=im,
            psf_template=model,
        )

        result.update({
            "status": (
                "RESIDUAL_DIAGNOSTIC_ONLY"
                if reproducible
                else "REPRODUCIBILITY_FAILURE"
            ),
            "chi2_reduced_recomputed": chi2,
            "chi2_reduced_reported_07j": expected,
            "chi2_reproduced": reproducible,
            "valid_pixels": n,
            "degrees_of_freedom": n - 4,
            "residual_mean_sigma": float(
                np.mean(zv)
            ),
            "residual_std_sigma": float(
                np.std(zv, ddof=1)
            ),
            "residual_median_sigma": float(
                np.median(zv)
            ),
            "residual_p95_absolute_sigma": float(
                np.percentile(abs(zv), 95)
            ),
            "fraction_absolute_residual_above_3sigma": float(
                np.mean(abs(zv) > 3)
            ),
            "mean_squared_residual_core_r_le_3px": (
                mean_z2(core)
            ),
            "mean_squared_residual_outer_r_gt_3px": (
                mean_z2(outer)
            ),
            "core_pixels": int(core.sum()),
            "outer_pixels": int(outer.sum()),
            "neighbor_x": cx,
            "neighbor_y": cy,
            "array_file": str(
                array_path.relative_to(ROOT)
            ),
            "issues": issues,
            "noise_model": "diagonal_variance_only",
            "noise_covariance_validated": False,
            "real_zogy_authorized": False,
        })

    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: {exc}"
        )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="MORLEY 07K - residuos ePSF"
    )

    parser.add_argument(
        "--pair-id",
        choices=("C001", "C002", "C003"),
    )

    args = parser.parse_args()

    b = read_json(FILE_B)
    j = read_json(FILE_J)

    radius = int(
        j.get("parameters", {}).get("radius", 6)
    )

    if radius < 4 or radius > 10:
        parser.error(
            "Radio de 07J fuera de rango"
        )

    by_id = {
        p["pair_id"]: p
        for p in j["pairs"]
    }

    reports = []

    for pair in b["pairs"]:
        pid = pair["pair_id"]

        if args.pair_id and pid != args.pair_id:
            continue

        from_j = by_id.get(pid, {})

        fits = {
            o["obs_id"]: o
            for o in from_j.get("observations", [])
        }

        results = [
            measure(
                o,
                fits.get(o["obs_id"], {}),
                radius,
            )
            for o in pair["exposures"]
        ]

        complete = all(
            v["status"] == "RESIDUAL_DIAGNOSTIC_ONLY"
            for v in results
        )

        status = (
            "RESIDUALS_COMPUTED"
            if complete
            else "INCOMPLETE_OR_STALE"
        )

        reports.append({
            "pair_id": pid,
            "status": status,
            "observations": results,
            "real_zogy_authorized": False,
        })

        print(f"{pid} -> {status}")

        for v in results:
            chi = v.get(
                "chi2_reduced_recomputed"
            )

            chi_text = (
                f"{chi:.3f}"
                if chi is not None
                else "N/D"
            )

            print(
                f"  {v['obs_id']} "
                f"| chi2={chi_text} "
                f"| reproduce 07J: "
                f"{v.get('chi2_reproduced', False)}"
            )

            for issue in v["issues"]:
                print("   -", issue)

    if not reports:
        parser.error(
            "No se encontraron parejas"
        )

    payload = {
        "schema_version": "morley.07k.residuals.v1",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "based_on": [
            FILE_B.name,
            FILE_J.name,
        ],
        "radius_from_07j": radius,
        "evidence_type": (
            "real_spherex_uncalibrated_psf_residual_diagnostics"
        ),
        "statistical_significance_calibrated": False,
        "astrometric_registration_completed": False,
        "real_zogy_authorized": False,
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
    print("ZOGY real: NO AUTORIZADO")


if __name__ == "__main__":
    main()
