
#!/usr/bin/env python3
"""MORLEY 07F - Compatibilidad espectral espacial.

Compara CWAVE/CBAND en una region comun del cielo
usando WCS para transformar entre las dos epocas.

Solo diagnostico. No registra imagenes empiricamente,
no iguala PSF, no resta imagenes ni autoriza ZOGY.
"""

import argparse
import hashlib
import json
from contextlib import ExitStack
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


ROOT = Path(__file__).resolve().parent
VAL = ROOT / "outputs" / "validations"

IN_B = VAL / "morley_07b_instrumental.json"
IN_E = VAL / "morley_07e_spectral_exact.json"
OUT = VAL / "morley_07f_spectral_footprint.json"


def read_json(path):
    if not path.is_file():
        raise FileNotFoundError(path)

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def safe_file(value):
    path = Path(value)

    if path.is_absolute():
        raise ValueError("Ruta absoluta no permitida")

    path = (ROOT / path).resolve()

    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Ruta fuera del proyecto")

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def load_image(obs):
    path = safe_file(obs["file"])

    with fits.open(path, memmap=False) as hdul:
        header = hdul["IMAGE"].header

        wcs = WCS(
            header,
            fobj=hdul,
        ).celestial

        image = np.asarray(
            hdul["IMAGE"].data,
            dtype=float,
        ).copy()

        variance = np.asarray(
            hdul["VARIANCE"].data,
            dtype=float,
        ).copy()

        offset_x = 1.0 - float(
            header["CRPIX1A"]
        )

        offset_y = 1.0 - float(
            header["CRPIX2A"]
        )

    if image.shape != variance.shape:
        raise ValueError(
            "IMAGE/VARIANCE no coinciden"
        )

    return {
        "wcs": wcs,
        "image": image,
        "variance": variance,
        "offset_x": offset_x,
        "offset_y": offset_y,
    }


def bilinear(array, x, y):
    ny, nx = array.shape

    valid = (
        np.isfinite(x)
        & np.isfinite(y)
        & (x >= 0)
        & (y >= 0)
        & (x < nx - 1)
        & (y < ny - 1)
    )

    sx = np.where(valid, x, 0)
    sy = np.where(valid, y, 0)

    x0 = np.floor(sx).astype(int)
    y0 = np.floor(sy).astype(int)

    dx = sx - x0
    dy = sy - y0

    a = array[y0, x0]
    b = array[y0, x0 + 1]
    c = array[y0 + 1, x0]
    d = array[y0 + 1, x0 + 1]

    value = (
        (1 - dx) * (1 - dy) * a
        + dx * (1 - dy) * b
        + (1 - dx) * dy * c
        + dx * dy * d
    )

    return np.where(valid, value, np.nan)


def numeric_valid(exposure, x, y):
    im = exposure["image"]
    va = exposure["variance"]

    ny, nx = im.shape

    valid = (
        np.isfinite(x)
        & np.isfinite(y)
        & (x >= 0)
        & (y >= 0)
        & (x < nx)
        & (y < ny)
    )

    xx = np.rint(
        np.where(valid, x, 0)
    ).astype(int)

    yy = np.rint(
        np.where(valid, y, 0)
    ).astype(int)

    xx = np.clip(xx, 0, nx - 1)
    yy = np.clip(yy, 0, ny - 1)

    return (
        valid
        & np.isfinite(im[yy, xx])
        & np.isfinite(va[yy, xx])
        & (va[yy, xx] > 0)
    )


def inspect_pair(pair, cal, samples, radius, threshold):
    oa, ob = pair["exposures"]

    a = load_image(oa)
    b = load_image(ob)

    ra = samples[oa["obs_id"]]["release"]
    rb = samples[ob["obs_id"]]["release"]

    if ra not in cal or rb not in cal:
        raise ValueError("Coleccion sin calibracion")

    x0, y0 = map(
        float,
        oa["target_cutout_xy_0based"],
    )

    offsets = np.arange(
        -radius,
        radius + 1,
    )

    dx, dy = np.meshgrid(
        offsets,
        offsets,
    )

    xa = x0 + dx
    ya = y0 + dy

    # Posiciones del cielo de la primera epoca.
    sky_ra, sky_dec = (
        a["wcs"].pixel_to_world_values(
            xa, ya
        )
    )

    # Posiciones correspondientes en la segunda.
    xb, yb = (
        b["wcs"].world_to_pixel_values(
            sky_ra, sky_dec
        )
    )

    # Transformar pixels de recorte a detector padre.
    ax = xa + a["offset_x"]
    ay = ya + a["offset_y"]

    bx = xb + b["offset_x"]
    by = yb + b["offset_y"]

    ca = cal[ra]
    cb = cal[rb]

    wa = bilinear(
        ca["CWAVE"].data,
        ax, ay,
    )

    wb = bilinear(
        cb["CWAVE"].data,
        bx, by,
    )

    ba = bilinear(
        ca["CBAND"].data,
        ax, ay,
    )

    bb = bilinear(
        cb["CBAND"].data,
        bx, by,
    )

    with np.errstate(
        invalid="ignore",
        divide="ignore",
    ):
        mismatch = (
            np.abs(wa - wb)
            / ((ba + bb) / 2)
        )

    spectral_valid = (
        np.isfinite(mismatch)
        & np.isfinite(ba)
        & np.isfinite(bb)
        & (ba > 0)
        & (bb > 0)
    )

    # Diagnostico numerico, NO mascara cientifica.
    numeric = (
        numeric_valid(a, xa, ya)
        & numeric_valid(b, xb, yb)
    )

    usable = spectral_valid & numeric

    values = mismatch[usable]

    total = mismatch.size
    count = int(values.size)

    if count < 15:
        return {
            "pair_id": pair["pair_id"],
            "status": "INSUFFICIENT_OVERLAP",
            "total_points": int(total),
            "usable_points": count,
            "real_zogy_authorized": False,
        }

    center = mismatch[radius, radius]

    summary = {
        "pair_id": pair["pair_id"],
        "status": "SPECTRAL_FOOTPRINT_DIAGNOSTIC",
        "grid_size": 2 * radius + 1,
        "total_points": int(total),
        "usable_points": count,
        "usable_fraction": float(count / total),
        "center_mismatch": (
            float(center)
            if np.isfinite(center)
            else None
        ),
        "median_mismatch": float(
            np.median(values)
        ),
        "p95_mismatch": float(
            np.percentile(values, 95)
        ),
        "maximum_mismatch": float(
            np.max(values)
        ),
        "fraction_below_threshold": float(
            np.mean(values <= threshold)
        ),
        "threshold_exploratory": threshold,
        "method": (
            "Same-sky WCS projection, bilinear "
            "CWAVE/CBAND, numeric-valid samples"
        ),
        "empirical_astrometric_registration": False,
        "full_spectral_response_verified": False,
        "psf_matched": False,
        "noise_covariance_calibrated": False,
        "real_zogy_authorized": False,
    }

    return summary


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--radius",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.25,
    )

    args = parser.parse_args()

    if not 2 <= args.radius <= 10:
        parser.error(
            "radius debe estar entre 2 y 10"
        )

    if not np.isfinite(args.threshold) or args.threshold <= 0:
        parser.error("threshold invalido")

    data_b = read_json(IN_B)
    data_e = read_json(IN_E)

    paths = {
        release: safe_file(path)
        for release, path
        in data_e["calibration_files"].items()
    }

    for release, path in paths.items():
        expected = data_e["sha256"][release]

        if sha256(path) != expected:
            raise ValueError(
                f"SHA256 cambiado: {release}"
            )

    samples = {
        o["obs_id"]: o
        for o in data_e["observations"]
    }

    results = []

    with ExitStack() as stack:
        cal = {
            release: stack.enter_context(
                fits.open(path, memmap=True)
            )
            for release, path in paths.items()
        }

        for pair in data_b["pairs"]:
            try:
                ids = [
                    o["obs_id"]
                    for o in pair["exposures"]
                ]

                if any(
                    samples[i]["status"]
                    != "SAMPLED_REVIEW_REQUIRED"
                    for i in ids
                ):
                    raise ValueError(
                        "07E no completo ambas muestras"
                    )

                result = inspect_pair(
                    pair,
                    cal,
                    samples,
                    args.radius,
                    args.threshold,
                )

            except Exception as exc:
                result = {
                    "pair_id": pair["pair_id"],
                    "status": "ERROR",
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                    "real_zogy_authorized": False,
                }

            results.append(result)

            print(
                result["pair_id"],
                "->",
                result["status"],
                "| mediana:",
                result.get("median_mismatch"),
                "| P95:",
                result.get("p95_mismatch"),
                "| validos:",
                result.get("usable_points"),
            )

    output = {
        "schema_version": "morley.07f.v1",
        "evidence_type": (
            "real_spherex_spectral_footprint_diagnostic"
        ),
        "threshold_is_heuristic": True,
        "pairs": results,
        "real_zogy_authorized": False,
    }

    OUT.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    print("\nMORLEY 07F COMPLETADO")
    print("JSON:", OUT)
    print("ZOGY REAL: NO AUTORIZADO")


if __name__ == "__main__":
    main()
