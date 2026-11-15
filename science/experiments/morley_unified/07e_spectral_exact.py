
#!/usr/bin/env python3
"""MORLEY 07E v2 - CWAVE/CBAND por pixel.

Lee calibraciones DR1 y QR3 por separado.
Compara las tablas WCS-WAVE como diagnostico.
No ejecuta ZOGY real.
"""

from __future__ import annotations

import hashlib
import json

from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits


ROOT = Path(__file__).resolve().parent

NAME = (
    "spectral_wcs_D6_spx_"
    "cal-swcs-v5-2026-191.fits"
)

CAL = {
    release: (
        ROOT
        / "outputs"
        / "data"
        / "calibrations"
        / release
        / NAME
    )
    for release in ("dr1", "qr3")
}

BASE = ROOT / "outputs" / "validations"

INPUT = BASE / "morley_07b_instrumental.json"
PROV = BASE / "morley_07d_proveniencia_wcs.json"

CAT = (
    ROOT / "outputs" / "catalogs"
    / "candidate_pairs_multiepoch_05.json"
)

OUTPUT = BASE / "morley_07e_spectral_exact.json"


def digest(path):
    h = hashlib.sha256()

    with path.open("rb") as src:
        for chunk in iter(
            lambda: src.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def check_calibration(hdul, release):
    for name in ("CWAVE", "CBAND", "WCS-WAVE"):
        if name not in hdul:
            raise ValueError(
                f"{release}: falta {name}"
            )

    for name in ("CWAVE", "CBAND"):
        hdu = hdul[name]

        if (
            hdu.data is None
            or hdu.data.shape != (2040, 2040)
        ):
            raise ValueError(
                f"{release}: forma incorrecta en {name}"
            )

        detector = hdu.header.get(
            "ARRAY",
            hdu.header.get("DETECTOR"),
        )

        if (
            detector is not None
            and str(detector).strip() not in ("6", "D6")
        ):
            raise ValueError(
                f"{release}: detector {detector}, no D6"
            )


def interpolate(array, x, y):
    """Interpolacion bilineal en coordenadas 0-based."""

    ny, nx = array.shape

    if not (
        np.isfinite(x)
        and np.isfinite(y)
        and 0 <= x < nx - 1
        and 0 <= y < ny - 1
    ):
        raise ValueError(
            "Posicion fuera del mapa espectral"
        )

    x0 = int(np.floor(x))
    y0 = int(np.floor(y))

    tx = x - x0
    ty = y - y0

    p = np.asarray(
        array[y0:y0 + 2, x0:x0 + 2],
        dtype=float,
    )

    if (
        p.shape != (2, 2)
        or not np.isfinite(p).all()
    ):
        raise ValueError(
            "Valores espectrales no validos"
        )

    return float(
        (1 - tx) * (1 - ty) * p[0, 0]
        + tx * (1 - ty) * p[0, 1]
        + (1 - tx) * ty * p[1, 0]
        + tx * ty * p[1, 1]
    )


def lookup_comparison(image, calibration):
    """Comparacion diagnostica de WCS-WAVE.

    Una tabla modificada por el servicio de recortes
    podria diferir incluso con calibracion compatible.
    """

    if (
        "WCS-WAVE" not in image
        or "WCS-WAVE" not in calibration
    ):
        return None

    try:
        a = image["WCS-WAVE"].data
        b = calibration["WCS-WAVE"].data

        for field in ("X", "Y", "VALUES"):
            av = np.asarray(
                a[field][0], dtype=float
            )

            bv = np.asarray(
                b[field][0], dtype=float
            )

            if av.shape != bv.shape:
                return False

            tolerance = (
                1e-4 if field == "VALUES" else 1e-6
            )

            if not np.allclose(
                av,
                bv,
                rtol=0,
                atol=tolerance,
                equal_nan=True,
            ):
                return False

        return True

    except (
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        AttributeError,
    ):
        return None


def observed_path(value):
    if (
        not isinstance(value, str)
        or not value
    ):
        raise ValueError(
            "Ruta FITS ausente"
        )

    path = Path(value)

    if path.is_absolute():
        raise ValueError(
            "No se admiten rutas absolutas"
        )

    path = (ROOT / path).resolve()

    if (
        not path.is_relative_to(ROOT.resolve())
        or path.suffix.lower() != ".fits"
    ):
        raise ValueError(
            "Ruta FITS fuera del proyecto"
        )

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def main():
    for path in [
        INPUT,
        PROV,
        CAT,
        *CAL.values(),
    ]:
        if not path.is_file():
            raise SystemExit(
                f"Falta archivo: {path}"
            )

    source = json.loads(
        INPUT.read_text(encoding="utf-8-sig")
    )

    provenance = json.loads(
        PROV.read_text(encoding="utf-8-sig")
    )

    catalog = json.loads(
        CAT.read_text(encoding="utf-8-sig")
    )

    references = {
        o["obs_id"]: o.get("identifiers", [])
        for o in provenance.get("observations", [])
    }

    observations = {
        o["obs_id"]: o
        for pair in source["pairs"]
        for o in pair["exposures"]
    }

    collection_by_id = {
        o["obs_id"]: o.get("collection")
        for o in catalog["observations"]
    }

    hashes = {
        release: digest(path)
        for release, path in CAL.items()
    }

    print(
        "MORLEY 07E - "
        "CALIBRACION ESPECTRAL POR PIXEL"
    )

    print("SHA256 DR1:", hashes["dr1"])
    print("SHA256 QR3:", hashes["qr3"])

    same_files = (
        hashes["dr1"] == hashes["qr3"]
    )

    print(
        "Archivos identicos:",
        same_files,
    )

    samples = {}

    with ExitStack() as stack:
        hdus = {
            release: stack.enter_context(
                fits.open(path, memmap=True)
            )
            for release, path in CAL.items()
        }

        for release, hdul in hdus.items():
            check_calibration(
                hdul,
                release,
            )

        for obs_id, entry in observations.items():
            item = {
                "obs_id": obs_id,
                "status": "ERROR",
                "internal_references": (
                    references.get(obs_id, [])
                ),
            }

            try:
                collection = str(
                    entry.get("collection")
                    or collection_by_id.get(obs_id)
                    or ""
                ).lower()

                if collection not in (
                    "spherex_dr1",
                    "spherex_qr3",
                ):
                    raise ValueError(
                        f"Coleccion desconocida: "
                        f"{collection!r}"
                    )

                release = collection.removeprefix(
                    "spherex_"
                )

                x, y = map(
                    float,
                    entry[
                        "target_detector_xy_0based"
                    ],
                )

                cal = hdus[release]

                cw = interpolate(
                    cal["CWAVE"].data,
                    x,
                    y,
                )

                cb = interpolate(
                    cal["CBAND"].data,
                    x,
                    y,
                )

                if cw <= 0 or cb <= 0:
                    raise ValueError(
                        "CWAVE/CBAND no positivos"
                    )

                with fits.open(
                    observed_path(entry["file"]),
                    memmap=False,
                ) as image:

                    lookup = lookup_comparison(
                        image,
                        cal,
                    )

                item.update({
                    "status": (
                        "SAMPLED_REVIEW_REQUIRED"
                    ),
                    "release": release,
                    "calibration": str(
                        CAL[release].relative_to(ROOT)
                    ),
                    "target_detector_xy_0based": [
                        x,
                        y,
                    ],
                    "cwave_um": cw,
                    "cband_um": cb,
                    "lookup_table_identical_diagnostic": (
                        lookup
                    ),
                    "matched_calibration_registry": False,
                })

            except Exception as exc:
                item["error"] = (
                    f"{type(exc).__name__}: {exc}"
                )

            samples[obs_id] = item

            print(
                obs_id,
                "->",
                item["status"],
                "| CWAVE:",
                item.get("cwave_um"),
                "| lookup:",
                item.get(
                    "lookup_table_identical_diagnostic"
                ),
            )

    pairs = []

    for pair in source["pairs"]:
        a, b = [
            samples[o["obs_id"]]
            for o in pair["exposures"]
        ]

        valid = (
            a["status"]
            == b["status"]
            == "SAMPLED_REVIEW_REQUIRED"
        )

        mismatch = None

        if valid:
            mismatch = (
                abs(
                    a["cwave_um"]
                    - b["cwave_um"]
                )
                / (
                    (
                        a["cband_um"]
                        + b["cband_um"]
                    ) / 2.0
                )
            )

        pairs.append({
            "pair_id": pair["pair_id"],
            "observation_ids": [
                o["obs_id"]
                for o in pair["exposures"]
            ],
            "normalized_spectral_mismatch_diagnostic": (
                mismatch
            ),
            "passes_exploratory_threshold_0_25": (
                mismatch <= 0.25
                if mismatch is not None
                else None
            ),
            "status": (
                "SPECTRAL_DIAGNOSTIC_ONLY"
                if valid
                else "BLOCKED"
            ),
            "ready_for_real_zogy": False,
        })

        print(
            pair["pair_id"],
            "-> mismatch:",
            round(mismatch, 6)
            if mismatch is not None
            else "N/D",
        )

    payload = {
        "schema_version": "morley.07e.v2",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "calibration_files": {
            release: str(
                path.relative_to(ROOT)
            )
            for release, path in CAL.items()
        },
        "sha256": hashes,
        "dr1_qr3_byte_identical": same_files,
        "instrumental_version_correspondence_verified": False,
        "wcs_wave_table_comparison_is_diagnostic_only": True,
        "real_zogy_authorized": False,
        "observations": list(samples.values()),
        "pairs": pairs,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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
    print("ZOGY REAL: NO AUTORIZADO")


if __name__ == "__main__":
    main()
