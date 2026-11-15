
#!/usr/bin/env python3
"""MORLEY 07D: procedencia de calibraciones en FITS locales.

No descarga datos, no modifica FITS y no ejecuta ZOGY.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from astropy.io import fits


ROOT = Path(__file__).resolve().parent

SOURCE = (
    ROOT / "outputs" / "validations"
    / "morley_07b_instrumental.json"
)

DEST = (
    ROOT / "outputs" / "validations"
    / "morley_07d_proveniencia_wcs.json"
)

TOKENS = (
    "spectral_wcs",
    "cal-wcs",
    "cwave",
    "cband",
    "wav",
    "spectral",
    "calibration source",
    "calib",
)


def local_fits(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Ruta FITS ausente")

    path = Path(value)

    if path.is_absolute():
        raise ValueError("Solo rutas relativas")

    path = (ROOT / path).resolve()

    if (
        not path.is_relative_to(ROOT.resolve())
        or path.suffix.lower() != ".fits"
    ):
        raise ValueError("Ruta FITS invalida")

    if not path.is_file():
        raise FileNotFoundError(str(path))

    return path


def inspect(obs):
    entry = {
        "obs_id": obs.get("obs_id"),
        "file": obs.get("file"),
        "status": "ERROR",
        "matches": [],
        "identifiers": [],
    }

    try:
        path = local_fits(obs.get("file"))
        found = []

        with fits.open(path, memmap=False) as hdul:
            for hdu in hdul:
                label = hdu.name

                for card in hdu.header.cards:
                    key = str(card.keyword)
                    value = str(card.value)

                    line = f"{key}: {value}"

                    if any(
                        token in line.lower()
                        for token in TOKENS
                    ):
                        item = f"{label} | {line[:230]}"

                        if item not in found:
                            found.append(item)

        identifiers = []

        pattern = (
            r"(?i)"
            r"(?:spectral_wcs[^\s\"',;]*\.fits"
            r"|cal-wcs-v\d+[-\w.]*)"
        )

        for item in found:
            for match in re.findall(pattern, item):
                if match not in identifiers:
                    identifiers.append(match)

        entry.update({
            "status": "INSPECTED",
            "matches": found,
            "identifiers": identifiers,
            "matching_cards_total": len(found),
        })

    except Exception as exc:
        entry["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

    return entry


def main():
    if not SOURCE.is_file():
        raise SystemExit(
            "Falta morley_07b_instrumental.json"
        )

    source = json.loads(
        SOURCE.read_text(encoding="utf-8-sig")
    )

    observations = {}

    for pair in source.get("pairs", []):
        for obs in pair.get("exposures", []):
            observations[obs["obs_id"]] = obs

    records = [
        inspect(obs)
        for obs in observations.values()
    ]

    payload = {
        "schema_version": "morley.provenance.v1",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "evidence_type": "local_fits_header_audit",
        "calibration_mapping_verified": False,
        "real_zogy_authorized": False,
        "observations": records,
    }

    DEST.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    DEST.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "MORLEY 07D - REFERENCIAS DE CALIBRACION"
    )

    for rec in records:
        print(
            f"\n{rec['obs_id']} | {rec['status']}"
        )

        if rec["status"] != "INSPECTED":
            print(" ERROR:", rec.get("error"))
            continue

        for ref in rec["identifiers"][:6]:
            print(" IDENTIFICADOR:", ref)

        if rec["matches"]:
            for line in rec["matches"][:8]:
                print(" ", line)
        else:
            print(
                " No se encontraron referencias "
                "espectrales explicitas"
            )

        if len(rec["matches"]) > 8:
            extra = len(rec["matches"]) - 8
            print(
                f" ... otras {extra} lineas en JSON"
            )

    print("\nJSON:", DEST)
    print(
        "Calibraciones aun no verificadas."
    )
    print(
        "ZOGY real: NO AUTORIZADO"
    )


if __name__ == "__main__":
    main()
