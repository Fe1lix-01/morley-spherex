
#!/usr/bin/env python3
"""MORLEY 07C - Diagnostico de FLAGS en FITS reales.

Sin descargas, sin modificacion de FITS, sin ZOGY real.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits


ROOT = Path(__file__).resolve().parent

INPUT = (
    ROOT / "outputs" / "validations"
    / "morley_07b_instrumental.json"
)

OUTPUT = (
    ROOT / "outputs" / "validations"
    / "morley_07c_flags.json"
)

FLAG_BITS = {
    "TRANSIENT": 0,
    "OVERFLOW": 1,
    "SUR_ERROR": 2,
    "NONFUNC": 6,
    "DICHROIC": 7,
    "MISSING_DATA": 9,
    "HOT": 10,
    "COLD": 11,
    "FULLSAMPLE": 12,
    "PHANMISS": 14,
    "NONLINEAR": 15,
    "PERSIST": 17,
    "OUTLIER": 19,
    "CROSSTALK": 20,
    "SOURCE": 21,
    "GHOST": 22,
    "STREAK": 25,
    "BLOOM": 26,
    "SNOWBALL": 27,
    "HALO": 28,
    "SATELLITE_HALO": 29,
}

# Bits que la herramienta fotometrica de IRSA
# documenta como excluidos durante sus ajustes.
# Esto NO define una mascara adecuada para ZOGY.
IRSA_FIT_EXCLUDED = [
    "SUR_ERROR",
    "NONFUNC",
    "MISSING_DATA",
    "HOT",
    "COLD",
    "NONLINEAR",
    "PERSIST",
    "BLOOM",
    "SNOWBALL",
    "HALO",
    "SATELLITE_HALO",
]

EXCLUDED_MASK = sum(
    1 << FLAG_BITS[name]
    for name in IRSA_FIT_EXCLUDED
)


def resolve_fits(raw):
    if not isinstance(raw, str) or not raw:
        raise ValueError("Falta ruta FITS en 07B")

    p = Path(raw)

    if p.is_absolute():
        raise ValueError("Ruta absoluta no permitida")

    result = (ROOT / p).resolve()

    if (
        not result.is_relative_to(ROOT.resolve())
        or result.suffix.lower() != ".fits"
    ):
        raise ValueError("Ruta FITS invalida")

    if not result.is_file():
        raise FileNotFoundError(result)

    return result


def summarize(image, variance, flags, x, y, radius):
    ix = round(x)
    iy = round(y)

    ys = slice(iy - radius, iy + radius + 1)
    xs = slice(ix - radius, ix + radius + 1)

    im = image[ys, xs]
    va = variance[ys, xs]
    fl = flags[ys, xs].astype(np.int64)

    expected = 2 * radius + 1

    if im.shape != (expected, expected):
        raise ValueError("Region truncada")

    numeric = (
        np.isfinite(im)
        & np.isfinite(va)
        & (va > 0)
    )

    strict = numeric & (fl == 0)

    fit_like = numeric & (
        (fl & EXCLUDED_MASK) == 0
    )

    counts = {}

    for name, bit in FLAG_BITS.items():
        count = int(
            np.count_nonzero(fl & (1 << bit))
        )

        if count:
            counts[name] = count

    known_mask = sum(
        1 << bit
        for bit in FLAG_BITS.values()
    )

    return {
        "size": f"{expected}x{expected}",
        "pixels": int(im.size),
        "numeric_fraction": round(
            float(numeric.mean()), 5
        ),
        "strict_fraction": round(
            float(strict.mean()), 5
        ),
        "irsa_fit_excluded_bits_fraction": round(
            float(fit_like.mean()), 5
        ),
        "source_flag_fraction": round(
            float(np.mean(
                (fl & (1 << FLAG_BITS["SOURCE"])) != 0
            )), 5
        ),
        "fullsample_flag_fraction": round(
            float(np.mean(
                (fl & (1 << FLAG_BITS["FULLSAMPLE"])) != 0
            )), 5
        ),
        "unknown_flags_count": int(
            np.count_nonzero(fl & ~known_mask)
        ),
        "flag_counts": counts,
        "center_flag_value": int(flags[iy, ix]),
    }


def inspect(obs):
    result = {
        "obs_id": obs.get("obs_id"),
        "status": "ERROR",
    }

    try:
        path = resolve_fits(obs.get("file"))

        x, y = [
            float(v)
            for v in obs["target_cutout_xy_0based"]
        ]

        with fits.open(path, memmap=False) as hdul:
            im = np.asarray(
                hdul["IMAGE"].data,
                dtype=float,
            )

            va = np.asarray(
                hdul["VARIANCE"].data,
                dtype=float,
            )

            flags = np.asarray(
                hdul["FLAGS"].data
            )

            if (
                im.ndim != 2
                or im.shape != va.shape
                or im.shape != flags.shape
            ):
                raise ValueError(
                    "IMAGE, VARIANCE y FLAGS no alineados"
                )

            if not np.issubdtype(
                flags.dtype,
                np.integer,
            ):
                raise ValueError(
                    "FLAGS no tiene formato entero"
                )

            header = hdul["IMAGE"].header

            provenance = {
                str(k): str(v)[:150]
                for k, v in header.items()
                if any(
                    token in str(k).upper()
                    for token in (
                        "CAL",
                        "WCS",
                        "VERSION",
                        "DETECTOR",
                        "OBSID",
                        "SIP",
                    )
                )
                and str(k).upper()
                not in ("COMMENT", "HISTORY")
            }

            result.update({
                "status": "DIAGNOSTIC_ONLY",
                "regions": {
                    str(2 * r + 1): summarize(
                        im, va, flags, x, y, r
                    )
                    for r in (1, 3, 5)
                },
                "provenance_header": dict(
                    list(provenance.items())[:60]
                ),
            })

    except Exception as exc:
        result["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

    return result


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT,
    )

    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(
            "Falta MORLEY 07B"
        )

    report = json.loads(
        args.input.read_text(
            encoding="utf-8-sig"
        )
    )

    results = []
    seen = set()

    for pair in report["pairs"]:
        for obs in pair["exposures"]:
            obs_id = obs["obs_id"]

            if obs_id in seen:
                continue

            seen.add(obs_id)

            result = inspect(obs)
            results.append(result)

            if result["status"] == "ERROR":
                print(
                    obs_id,
                    "ERROR",
                    result.get("error"),
                )
                continue

            region = result["regions"]["11"]

            print(
                f"{obs_id}: "
                f"11x11 estricto="
                f"{region['strict_fraction']:.1%} "
                f"| bits IRSA="
                f"{region['irsa_fit_excluded_bits_fraction']:.1%} "
                f"| SOURCE="
                f"{region['source_flag_fraction']:.1%} "
                f"| FULLSAMPLE="
                f"{region['fullsample_flag_fraction']:.1%}"
            )

            print(
                "  FLAGS:",
                region["flag_counts"],
            )

    output = {
        "schema_version": (
            "morley.flags_diagnostic.v1"
        ),
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "irsa_excluded_bits": IRSA_FIT_EXCLUDED,
        "not_a_zogy_mask": True,
        "real_zogy_authorized": False,
        "observations": results,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\nMORLEY 07C COMPLETADO")
    print("JSON:", OUTPUT)
    print(
        "ZOGY real: NO AUTORIZADO"
    )


if __name__ == "__main__":
    main()
