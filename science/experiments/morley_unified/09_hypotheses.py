
#!/usr/bin/env python3
"""MORLEY 09 - Hipotesis H0-H3 sinteticas.

H0: Sin cambio
H1: Cambio de flujo
H2: Movimiento
H3: Movimiento y cambio de flujo

Entrada: productos sinteticos de MORLEY 08.
No ejecuta inferencia cientifica sobre datos reales.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent

SRC = (
    ROOT / "outputs" / "validations" / "synthetic_08"
)

OUT = (
    ROOT / "outputs" / "validations"
    / "morley_09_hypotheses.json"
)


def evaluate(path, radius, max_shift=1.0):
    with np.load(path, allow_pickle=False) as f:
        evidence = str(
            f["evidence_type"].item()
        )

        if evidence != "synthetic_test_only":
            raise ValueError(
                "Solo se permiten datos sinteticos de 08"
            )

        d = np.asarray(
            f["diff"],
            dtype=float,
        )

        pd = np.asarray(
            f["pd_centered"],
            dtype=float,
        )

        cx = int(f["cx"])
        cy = int(f["cy"])

        base_flux = float(f["base_flux"])

        scenario = str(
            f["scenario"].item()
        )

        truth = {
            "delta_flux": float(
                f["true_flux_delta"]
            ),
            "dx": float(f["true_dx"]),
            "dy": float(f["true_dy"]),
        }

    if (
        d.ndim != 2
        or d.shape != pd.shape
        or not np.isfinite(d).all()
        or not np.isfinite(pd).all()
    ):
        raise ValueError(
            f"Imagen o PSF invalida: {path}"
        )

    if min(
        cx,
        cy,
        d.shape[0] - 1 - cy,
        d.shape[1] - 1 - cx,
    ) < radius:
        raise ValueError(
            "Region de ajuste fuera de imagen"
        )

    roi = (
        slice(cy - radius, cy + radius + 1),
        slice(cx - radius, cx + radius + 1),
    )

    y = d[roi].ravel()
    n = y.size

    pd_hat = np.fft.fft2(
        np.fft.ifftshift(pd)
    )

    fy = np.fft.fftfreq(
        d.shape[0]
    )[:, None]

    fx = np.fft.fftfreq(
        d.shape[1]
    )[None, :]

    def template(dx, dy):
        phase = np.exp(
            -2j * np.pi * (
                fx * (cx + dx)
                + fy * (cy + dy)
            )
        )

        shifted = np.fft.ifft2(
            pd_hat * phase
        ).real

        return shifted[roi].ravel()

    base = template(0.0, 0.0)

    # H0: no existe cambio.
    models = {
        "H0": {
            "chi2": float(np.dot(y, y)),
            "k": 0,
            "params": {},
        }
    }

    # H1: cambio de flujo con posicion fija.
    delta_flux = float(
        np.dot(base, y)
        / np.dot(base, base)
    )

    residual = y - delta_flux * base

    models["H1"] = {
        "chi2": float(np.dot(residual, residual)),
        "k": 1,
        "params": {
            "delta_flux": delta_flux,
        },
    }

    best_h2 = (
        float("inf"),
        0.0,
        0.0,
    )

    best_h3 = (
        float("inf"),
        0.0,
        0.0,
        0.0,
    )

    # Busqueda inicial de desplazamientos.
    grid = np.linspace(
        -max_shift,
        max_shift,
        21,
    )

    for stage in range(2):
        if stage == 0:
            coords = [
                (dx, dy)
                for dx in grid
                for dy in grid
            ]

        else:
            step = max_shift / 10.0

            offsets = np.linspace(
                -step,
                step,
                11,
            )

            centers = [
                (best_h2[1], best_h2[2]),
                (best_h3[1], best_h3[2]),
            ]

            coords = list({
                (
                    round(x + dx, 6),
                    round(y0 + dy, 6),
                )
                for x, y0 in centers
                for dx in offsets
                for dy in offsets
                if (
                    abs(x + dx) <= max_shift
                    and abs(y0 + dy) <= max_shift
                )
            })

        for dx, dy in coords:
            shifted = template(dx, dy)

            # H2: mismo flujo, distinta posicion.
            pred_h2 = base_flux * (
                shifted - base
            )

            chi2_h2 = float(
                np.sum(
                    (y - pred_h2) ** 2
                )
            )

            if chi2_h2 < best_h2[0]:
                best_h2 = (
                    chi2_h2,
                    dx,
                    dy,
                )

            # H3: flujo y posicion variables.
            target = y + base_flux * base

            new_flux = float(
                np.dot(shifted, target)
                / np.dot(shifted, shifted)
            )

            new_delta = new_flux - base_flux

            pred_h3 = (
                new_flux * shifted
                - base_flux * base
            )

            chi2_h3 = float(
                np.sum(
                    (y - pred_h3) ** 2
                )
            )

            if chi2_h3 < best_h3[0]:
                best_h3 = (
                    chi2_h3,
                    dx,
                    dy,
                    new_delta,
                )

    models["H2"] = {
        "chi2": best_h2[0],
        "k": 2,
        "params": {
            "dx": float(best_h2[1]),
            "dy": float(best_h2[2]),
        },
    }

    models["H3"] = {
        "chi2": best_h3[0],
        "k": 3,
        "params": {
            "dx": float(best_h3[1]),
            "dy": float(best_h3[2]),
            "delta_flux": float(best_h3[3]),
        },
    }

    # BIC con varianza blanca conocida = 1.
    for model in models.values():
        model["bic"] = round(
            model["chi2"]
            + model["k"] * np.log(n),
            4,
        )

        model["chi2"] = round(
            model["chi2"],
            4,
        )

    # Regla conservadora exploratoria:
    # elegir el modelo mas sencillo dentro
    # de Delta BIC <= 6 respecto al minimo.
    bic_min = min(
        m["bic"]
        for m in models.values()
    )

    plausible = [
        h for h in models
        if models[h]["bic"] <= bic_min + 6.0
    ]

    best = min(
        plausible,
        key=lambda h: models[h]["k"],
    )

    sorted_bic = sorted(
        m["bic"]
        for m in models.values()
    )

    return {
        "scenario": scenario,
        "source": str(
            path.relative_to(ROOT)
        ),
        "best_hypothesis": best,
        "bic_gap_to_second": round(
            sorted_bic[1] - sorted_bic[0],
            3,
        ),
        "models": models,
        "truth": truth,
        "fit_pixels": n,
        "evidence_type": "synthetic_test_only",
        "real_motion_detected": False,
    }


def main():
    parser = argparse.ArgumentParser(
        description="MORLEY 09 - H0 H1 H2 H3"
    )

    parser.add_argument(
        "--radius",
        type=int,
        default=12,
    )

    args = parser.parse_args()

    if not 5 <= args.radius <= 20:
        parser.error(
            "radius debe estar entre 5 y 20"
        )

    scenarios = [
        "null",
        "flux",
        "motion",
        "both",
    ]

    paths = [
        SRC / f"{s}.npz"
        for s in scenarios
    ]

    if any(not p.is_file() for p in paths):
        parser.error(
            "Faltan archivos: ejecuta primero MORLEY 08"
        )

    cases = [
        evaluate(p, args.radius)
        for p in paths
    ]

    expected = {
        "null": "H0",
        "flux": "H1",
        "motion": "H2",
        "both": "H3",
    }

    matches = sum(
        c["best_hypothesis"]
        == expected[c["scenario"]]
        for c in cases
    )

    for c in cases:
        print(
            f"{c['scenario']:7s} -> "
            f"{c['best_hypothesis']} "
            f"(esperado {expected[c['scenario']]}) "
            f"| margen BIC={c['bic_gap_to_second']:.2f}"
        )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        "schema_version": "morley.synthetic_hypotheses.v1",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "matched_synthetic_cases": (
            f"{matches}/{len(cases)}"
        ),
        "evidence_type": "synthetic_test_only",
        "real_zogy_executed": False,
        "note": (
            "No representa sensibilidad ni "
            "tasa de falsos positivos reales"
        ),
        "cases": cases,
    }

    OUT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("JSON:", OUT)

    if matches != len(cases):
        print(
            "AVISO: revisar alguna hipotesis sintetica"
        )


if __name__ == "__main__":
    main()
