
#!/usr/bin/env python3
"""MORLEY 07M: auditoria espacial de residuos ePSF.

Reutiliza los mapas NPZ generados por 07K y
las coordenadas de 07B.

No modifica FITS, no reajusta modelos y no hace ZOGY.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
VAL = ROOT / "outputs" / "validations"

SOURCE_B = VAL / "morley_07b_instrumental.json"
SOURCE_K = VAL / "morley_07k_residuals.json"
OUTPUT = VAL / "morley_07m_field_audit.json"


def read_json(path):
    if not path.is_file():
        raise FileNotFoundError(f"No existe: {path}")

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def safe_npz(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Ruta NPZ ausente")

    relative = Path(raw)

    if (
        relative.is_absolute()
        or relative.suffix.lower() != ".npz"
    ):
        raise ValueError("Ruta NPZ invalida")

    full = (ROOT / relative).resolve()

    if (
        not full.is_relative_to(ROOT.resolve())
        or not full.is_file()
    ):
        raise FileNotFoundError(
            f"NPZ no localizado: {raw}"
        )

    return full


def values_summary(values):
    if len(values) == 0:
        return {
            "n": 0,
            "mean_z2": None,
            "median_abs_z": None,
        }

    return {
        "n": int(len(values)),
        "mean_z2": float(
            np.mean(values**2)
        ),
        "median_abs_z": float(
            np.median(np.abs(values))
        ),
    }


def connected_hotspots(z, good, threshold):
    """Agrupar residuos extremos con conectividad 8."""

    hot = good & (np.abs(z) >= threshold)
    seen = np.zeros(hot.shape, dtype=bool)

    groups = []
    ny, nx = hot.shape

    for y0, x0 in np.argwhere(hot):
        y0 = int(y0)
        x0 = int(x0)

        if seen[y0, x0]:
            continue

        todo = [(y0, x0)]
        seen[y0, x0] = True
        coords = []

        while todo:
            y, x = todo.pop()
            coords.append((y, x))

            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy = y + dy
                    xx = x + dx

                    if (
                        0 <= yy < ny
                        and 0 <= xx < nx
                        and hot[yy, xx]
                        and not seen[yy, xx]
                    ):
                        seen[yy, xx] = True
                        todo.append((yy, xx))

        ys = np.array(
            [p[0] for p in coords],
            dtype=int,
        )

        xs = np.array(
            [p[1] for p in coords],
            dtype=int,
        )

        squared = z[ys, xs] ** 2

        groups.append({
            "n_pixels": len(coords),
            "peak_abs_z": float(
                np.max(np.abs(z[ys, xs]))
            ),
            "chi2_contribution": float(
                squared.sum()
            ),
            "centroid_window_xy": [
                float(np.mean(xs)),
                float(np.mean(ys)),
            ],
        })

    return sorted(
        groups,
        key=lambda g: g["chi2_contribution"],
        reverse=True,
    )


def audit(obs, meta, threshold, trim_fraction):
    obs_id = obs.get("obs_id")

    result = {
        "obs_id": obs_id,
        "status": "ERROR",
        "issues": [],
    }

    try:
        if meta.get("obs_id") != obs_id:
            raise ValueError(
                "IDs de 07B y 07K no coinciden"
            )

        if (
            meta.get("status")
            != "RESIDUAL_DIAGNOSTIC_ONLY"
            or not meta.get("chi2_reproduced")
        ):
            raise ValueError(
                "07K incompleto o no reproducible"
            )

        with np.load(
            safe_npz(meta.get("array_file")),
            allow_pickle=False,
        ) as data:
            z = np.asarray(
                data["residual_sigma"],
                dtype=float,
            )

            good = np.asarray(
                data["valid"],
                dtype=bool,
            )

        if (
            z.ndim != 2
            or z.shape != good.shape
            or min(z.shape) < 7
        ):
            raise ValueError(
                "Dimensiones NPZ incompatibles"
            )

        good = good & np.isfinite(z)

        if np.count_nonzero(good) < 30:
            raise ValueError(
                "Menos de 30 residuos validos"
            )

        xc, yc = map(
            float,
            obs["target_cutout_xy_0based"],
        )

        center_x = (
            (z.shape[1] - 1) / 2
            + (xc - round(xc))
        )

        center_y = (
            (z.shape[0] - 1) / 2
            + (yc - round(yc))
        )

        yy, xx = np.indices(
            z.shape,
            dtype=float,
        )

        dx = xx - center_x
        dy = yy - center_y

        radius = np.hypot(dx, dy)

        core = good & (radius <= 3.0)
        outer = good & (radius > 3.0)

        outer_values = z[outer]

        if len(outer_values) < 20:
            raise ValueError(
                "Menos de 20 residuos exteriores"
            )

        # Descartar solo para el diagnostico
        # la fraccion de valores |z| mas grandes.
        # No modifica los residuos originales.
        take = max(
            1,
            int(
                np.floor(
                    len(outer_values)
                    * (1 - trim_fraction)
                )
            ),
        )

        small = np.sort(
            np.abs(outer_values)
        )[:take]

        total_chi2 = float(
            np.sum(z[good] ** 2)
        )

        outer_chi2 = float(
            np.sum(outer_values**2)
        )

        high = np.sort(
            z[good] ** 2
        )[::-1]

        top_n = min(5, len(high))

        result.update({
            "status": "FIELD_AUDIT_DIAGNOSTIC_ONLY",
            "window_shape": list(z.shape),
            "valid_pixels": int(good.sum()),
            "core": values_summary(z[core]),
            "outer": values_summary(outer_values),
            "outer_trimmed_mean_z2": float(
                np.mean(small**2)
            ),
            "outer_trimmed_fraction": trim_fraction,
            "outer_above_2sigma_fraction": float(
                np.mean(
                    np.abs(outer_values) > 2
                )
            ),
            "outer_above_3sigma_fraction": float(
                np.mean(
                    np.abs(outer_values) > 3
                )
            ),
            "outer_fraction_of_total_chi2": (
                outer_chi2 / total_chi2
                if total_chi2 > 0
                else None
            ),
            "top5_pixel_fraction_of_total_chi2": (
                float(
                    np.sum(high[:top_n])
                    / total_chi2
                )
                if total_chi2 > 0
                else None
            ),
            "radial_bins": [],
            "quadrants_outer": {},
            "largest_abs_residuals": [],
            "connected_hotspots": connected_hotspots(
                z, good, threshold
            )[:10],
            "hotspot_threshold_abs_z": threshold,
            "no_statistical_significance_claim": True,
            "noise_covariance_validated": False,
            "real_zogy_authorized": False,
        })

        # Diagnostico radial.
        for lo, hi in (
            (0, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 7),
            (7, 10),
        ):
            segment = (
                good
                & (radius >= lo)
                & (radius < hi)
            )

            result["radial_bins"].append({
                "r_min": lo,
                "r_max": hi,
                **values_summary(z[segment]),
            })

        # Diagnostico espacial por cuadrantes.
        quadrants = {
            "left_lower": (
                (dx < 0) & (dy < 0)
            ),
            "right_lower": (
                (dx >= 0) & (dy < 0)
            ),
            "left_upper": (
                (dx < 0) & (dy >= 0)
            ),
            "right_upper": (
                (dx >= 0) & (dy >= 0)
            ),
        }

        for key, mask in quadrants.items():
            result["quadrants_outer"][key] = (
                values_summary(z[outer & mask])
            )

        # Cinco residuos de mayor magnitud.
        ordered = sorted(
            np.argwhere(good),
            key=lambda p: abs(
                z[int(p[0]), int(p[1])]
            ),
            reverse=True,
        )

        for yi, xi in ordered[:5]:
            yi = int(yi)
            xi = int(xi)

            result[
                "largest_abs_residuals"
            ].append({
                "window_xy": [xi, yi],
                "offset_from_target_xy_pixels": [
                    float(xi - center_x),
                    float(yi - center_y),
                ],
                "residual_sigma": float(
                    z[yi, xi]
                ),
                "region": (
                    "core"
                    if radius[yi, xi] <= 3
                    else "outer"
                ),
            })

    except Exception as exc:
        result["issues"].append(
            f"{type(exc).__name__}: {exc}"
        )

    return result


def main():
    parser = argparse.ArgumentParser(
        description=(
            "MORLEY 07M - diagnostico espacial"
        )
    )

    parser.add_argument(
        "--pair-id",
        choices=("C001", "C002", "C003"),
    )

    parser.add_argument(
        "--hotspot-threshold",
        type=float,
        default=2.5,
    )

    parser.add_argument(
        "--trim-fraction",
        type=float,
        default=0.10,
    )

    args = parser.parse_args()

    if (
        not 1.0 <= args.hotspot_threshold <= 10.0
        or not 0.01 <= args.trim_fraction <= 0.3
    ):
        parser.error(
            "Parametros fuera de rango"
        )

    source = read_json(SOURCE_B)
    previous = read_json(SOURCE_K)

    by_pair = {
        pair["pair_id"]: pair
        for pair in previous["pairs"]
    }

    records = []

    for pair in source["pairs"]:
        pid = pair["pair_id"]

        if args.pair_id and pid != args.pair_id:
            continue

        k_pair = by_pair.get(pid, {})

        k_obs = {
            item["obs_id"]: item
            for item in k_pair.get(
                "observations", []
            )
        }

        measurements = [
            audit(
                obs,
                k_obs.get(obs["obs_id"], {}),
                args.hotspot_threshold,
                args.trim_fraction,
            )
            for obs in pair["exposures"]
        ]

        complete = (
            len(measurements) == 2
            and all(
                m["status"]
                == "FIELD_AUDIT_DIAGNOSTIC_ONLY"
                for m in measurements
            )
        )

        status = (
            "FIELD_AUDIT_COMPLETED"
            if complete
            else "FIELD_AUDIT_INCOMPLETE"
        )

        records.append({
            "pair_id": pid,
            "status": status,
            "observations": measurements,
            "real_zogy_authorized": False,
        })

        print(f"{pid} -> {status}")

        for item in measurements:
            if item["status"] == "ERROR":
                print(
                    f"  {item['obs_id']}: "
                    f"ERROR: {'; '.join(item['issues'])}"
                )
                continue

            print(
                f"  {item['obs_id']}: "
                f"exterior z²="
                f"{item['outer']['mean_z2']:.3f} "
                f"| recorte "
                f"{args.trim_fraction:.0%}="
                f"{item['outer_trimmed_mean_z2']:.3f} "
                f"| >3sigma="
                f"{item['outer_above_3sigma_fraction']:.1%} "
                f"| top5 chi²="
                f"{item['top5_pixel_fraction_of_total_chi2']:.1%}"
            )

    if not records:
        parser.error(
            "No se encontraron parejas"
        )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "schema_version": "morley.07m.field_audit.v1",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_07k": SOURCE_K.name,
        "thresholds_are_exploratory": True,
        "real_zogy_authorized": False,
        "pairs": records,
    }

    OUTPUT.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    print("\nJSON:", OUTPUT)
    print(
        "Anomalias: DIAGNOSTICO, "
        "sin deteccion fisica ni ZOGY"
    )


if __name__ == "__main__":
    main()
