
#!/usr/bin/env python3
"""MORLEY 08 - ZOGY sobre imagenes sinteticas.

No procesa observaciones reales.
Genera cuatro escenarios para validar H0-H3.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent

OUT = (
    ROOT / "outputs" / "validations" / "synthetic_08"
)


def psf_fft(shape, width, sharp=0.08):
    ny, nx = shape

    y = np.minimum(
        np.arange(ny),
        ny - np.arange(ny),
    )[:, None]

    x = np.minimum(
        np.arange(nx),
        nx - np.arange(nx),
    )[None, :]

    psf = np.exp(
        -0.5 * (x*x + y*y) / (width*width)
    )

    psf /= psf.sum()

    # Componente estrecha para evitar frecuencias
    # completamente degeneradas en esta simulacion.
    psf *= (1.0 - sharp)
    psf[0, 0] += sharp

    return np.fft.fft2(psf)


def shift_fft(shape, x, y):
    ny, nx = shape

    ky = np.fft.fftfreq(ny)[:, None]
    kx = np.fft.fftfreq(nx)[None, :]

    return np.exp(
        -2j * np.pi * (kx*x + ky*y)
    )


def simulate(scenario, seed, size=96):
    shape = (size, size)

    rng = np.random.default_rng(seed)

    cx = cy = size // 2

    base_flux = 260.0

    delta_flux = (
        0.0
        if scenario in ("null", "motion")
        else 75.0
    )

    if scenario in ("null", "flux"):
        dx, dy = 0.0, 0.0
    else:
        dx, dy = 0.55, -0.40

    sigma_r = 1.0
    sigma_n = 1.0

    pr = psf_fft(shape, width=1.35)
    pn = psf_fft(shape, width=1.65)

    ref = (
        base_flux
        * np.fft.ifft2(
            pr * shift_fft(shape, cx, cy)
        ).real
    )

    new = (
        (base_flux + delta_flux)
        * np.fft.ifft2(
            pn * shift_fft(
                shape,
                cx + dx,
                cy + dy,
            )
        ).real
    )

    ref += rng.normal(
        0,
        sigma_r,
        shape,
    )

    new += rng.normal(
        0,
        sigma_n,
        shape,
    )

    # Formula ZOGY sintetica.
    # El denominador combina las varianzas
    # de las dos imagenes mediante una SUMA.
    den = np.sqrt(
        sigma_n**2 * np.abs(pr)**2
        + sigma_r**2 * np.abs(pn)**2
    )

    if (
        not np.all(np.isfinite(den))
        or np.any(den < 1e-8)
    ):
        raise RuntimeError(
            "PSF mal condicionada en Fourier"
        )

    diff_hat = (
        pr * np.fft.fft2(new)
        - pn * np.fft.fft2(ref)
    ) / den

    diff = np.fft.ifft2(diff_hat).real

    # PSF efectiva de la diferencia.
    pd_hat = (pr * pn) / den

    pd_centered = np.fft.fftshift(
        np.fft.ifft2(pd_hat).real
    )

    return {
        "diff": diff,
        "pd_centered": pd_centered,
        "ref": ref,
        "new": new,
        "cx": cx,
        "cy": cy,
        "sigma_r": sigma_r,
        "sigma_n": sigma_n,
        "true_flux_delta": delta_flux,
        "true_dx": dx,
        "true_dy": dy,
        "base_flux": base_flux,
        "scenario": scenario,
    }


def main():
    parser = argparse.ArgumentParser(
        description="MORLEY 08 - ZOGY sintetico"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
    )

    parser.add_argument(
        "--scenario",
        choices=[
            "all",
            "null",
            "flux",
            "motion",
            "both",
        ],
        default="all",
    )

    args = parser.parse_args()

    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    scenarios = (
        ["null", "flux", "motion", "both"]
        if args.scenario == "all"
        else [args.scenario]
    )

    results = []

    for i, name in enumerate(scenarios):
        data = simulate(
            name,
            args.seed + i,
        )

        output = OUT / f"{name}.npz"

        np.savez_compressed(
            output,
            **data,
            evidence_type="synthetic_test_only",
            real_zogy_executed=False,
            synthetic_zogy_executed=True,
        )

        noise_std = float(data["diff"].std())

        results.append({
            "scenario": name,
            "file": str(
                output.relative_to(ROOT)
            ),
            "difference_noise_std_full": noise_std,
            "true_delta_flux": data[
                "true_flux_delta"
            ],
            "true_dx_pix": data["true_dx"],
            "true_dy_pix": data["true_dy"],
        })

        print(
            f"{name:7s}: {output} "
            f"| std(D)={noise_std:.3f}"
        )

    report = {
        "schema_version": "morley.zogy_synthetic.v1",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "scientific_integrity": {
            "evidence_type": "synthetic_test_only",
            "real_spherex_images_processed": False,
            "real_zogy_executed": False,
            "motion_detected": False,
        },
        "cases": results,
    }

    path = OUT / "manifest.json"

    path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("Manifest:", path)

    print(
        "Solo prueba sintetica. "
        "No utiliza observaciones SPHEREx."
    )


if __name__ == "__main__":
    main()
