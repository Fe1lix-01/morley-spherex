
"""ÉTER / MORLEY Frontier — Practice 04.

Spectral prevalidation of SPHEREx epoch pairs.

Inputs:
    outputs/catalogs/epoch_pairs_*.json
    outputs/catalogs/candidatos_d6.csv
    outputs/data/recortes_morley/*.fits

Outputs:
    outputs/catalogs/spectral_pairs_checked.json
    outputs/catalogs/spectral_pairs_checked.csv

WCS-WAVE provides approximate wavelengths.
Passing this test NEVER authorizes ZOGY automatically.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS


# =====================================================
# 1. CONFIGURATION
# =====================================================

BASE = Path(__file__).resolve().parent

CATALOGS = BASE / "outputs" / "catalogs"

CUTOUTS = (
    BASE / "outputs" / "data" / "recortes_morley"
)

REFERENCE_IDS = (
    "2025W38_1A_0596_4",
    "2026W38_1A_0297_1",
)

# SOURCE (bit 21) is allowed.
BAD_BITS = (
    0, 1, 2, 6, 7, 9, 10, 11,
    14, 15, 17, 19, 20, 22,
)

BAD_MASK = sum(1 << n for n in BAD_BITS)


# =====================================================
# 2. UTILITY FUNCTIONS
# =====================================================

def scalar(value):
    return float(np.asarray(value).item())


def safe_archive_url(url):

    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname != "irsa.ipac.caltech.edu"
        or not parsed.path.startswith(
            "/ibe/data/spherex/"
        )
        or not parsed.path.endswith(".fits")
    ):
        raise ValueError(
            "URL no corresponde a un FITS "
            "SPHEREx de IRSA"
        )

    return parsed


def local_path(obs):

    parsed = safe_archive_url(
        obs["access_url"]
    )

    filename = Path(
        parsed.path
    ).name

    return CUTOUTS / filename


# =====================================================
# 3. OPTIONAL FITS DOWNLOAD
# =====================================================

def download_cutout(
    obs,
    ra,
    dec,
    size_deg
):

    import requests

    path = local_path(obs)

    if (
        path.exists()
        and path.stat().st_size > 2048
    ):
        return path

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary = path.with_suffix(".part")

    url = obs["access_url"].split(
        "?", 1
    )[0]

    try:

        with requests.get(
            url,
            params={
                "center": f"{ra:.8f},{dec:.8f}",
                "size": f"{size_deg:.4f}",
            },
            timeout=(15, 90),
            stream=True,
        ) as response:

            response.raise_for_status()

            written = 0

            with temporary.open("wb") as f:

                for chunk in response.iter_content(
                    256 * 1024
                ):

                    if not chunk:
                        continue

                    written += len(chunk)

                    if written > 30 * 1024 * 1024:
                        raise ValueError(
                            "Recorte demasiado grande"
                        )

                    f.write(chunk)

        # Validate the downloaded file.
        with fits.open(temporary) as hdul:

            required = (
                "IMAGE",
                "FLAGS",
                "VARIANCE",
                "WCS-WAVE",
            )

            if not all(
                name in hdul
                for name in required
            ):
                raise ValueError(
                    "FITS sin extensiones esperadas"
                )

        temporary.replace(path)

        return path

    except Exception:

        temporary.unlink(
            missing_ok=True
        )

        raise


# =====================================================
# 4. INSPECT ONE LEVEL 2 OBSERVATION
# =====================================================

def inspect(
    obs,
    ra,
    dec,
    margin
):

    path = local_path(obs)

    with fits.open(
        path,
        memmap=False
    ) as hdul:

        required = (
            "IMAGE",
            "FLAGS",
            "VARIANCE",
            "WCS-WAVE",
        )

        for name in required:

            if name not in hdul:
                raise ValueError(
                    f"Falta extensión {name}"
                )

        image = hdul["IMAGE"].data

        var = hdul["VARIANCE"].data

        flags = hdul["FLAGS"].data

        if (
            image.ndim != 2
            or image.shape != var.shape
            or image.shape != flags.shape
        ):
            raise ValueError(
                "Dimensiones FITS incompatibles"
            )

        header = hdul["IMAGE"].header

        # -----------------------------------------
        # Spatial WCS
        # -----------------------------------------

        spatial = WCS(
            header,
            fobj=hdul
        ).celestial

        x, y = spatial.world_to_pixel_values(
            ra,
            dec
        )

        x = scalar(x)
        y = scalar(y)

        ny, nx = image.shape

        if not (
            math.isfinite(x)
            and math.isfinite(y)
        ):
            raise ValueError(
                "Coordenadas WCS no finitas"
            )

        if not (
            margin <= x < nx - margin
            and margin <= y < ny - margin
        ):
            raise ValueError(
                "Objetivo fuera del margen: "
                f"({x:.2f}, {y:.2f})"
            )

        ix = int(round(x))
        iy = int(round(y))

        # -----------------------------------------
        # Local 5x5 quality window
        # -----------------------------------------

        small_image = image[
            iy-2:iy+3,
            ix-2:ix+3
        ]

        small_var = var[
            iy-2:iy+3,
            ix-2:ix+3
        ]

        small_flags = flags[
            iy-2:iy+3,
            ix-2:ix+3
        ].astype(np.int64)

        valid = (
            np.isfinite(small_image)
            & np.isfinite(small_var)
            & (small_var > 0)
            & (
                (small_flags & BAD_MASK) == 0
            )
        )

        valid_fraction = float(
            np.mean(valid)
        )

        # -----------------------------------------
        # Approximate wavelength WCS
        # -----------------------------------------

        wave = WCS(
            header,
            fobj=hdul,
            key="W"
        )

        wave.sip = None

        wavelength, bandwidth = (
            wave.pixel_to_world(x, y)
        )

        lam = scalar(
            wavelength.to_value(u.um)
        )

        band = scalar(
            bandwidth.to_value(u.um)
        )

        if not (
            math.isfinite(lam)
            and math.isfinite(band)
            and band > 0
        ):
            raise ValueError(
                "WCS-WAVE inválido"
            )

        return {

            "obs_id": obs["obs_id"],

            "fits_file": str(path),

            "date_obs": str(
                header.get("DATE-OBS", "")
            ),

            "x_px": round(x, 3),
            "y_px": round(y, 3),

            "wavelength_um": round(
                lam, 7
            ),

            "bandwidth_um": round(
                band, 7
            ),

            "valid_fraction_5x5": round(
                valid_fraction, 3
            ),

            "central_flags": int(
                flags[iy, ix]
            ),

            "central_good": bool(
                valid[2, 2]
            ),

            "image_shape": [ny, nx],

            "wavelength_source": (
                "approximate_WCS-WAVE"
            ),
        }


# =====================================================
# 5. RECOVER OUR ORIGINAL EPSF REFERENCE PAIR
# =====================================================

def reference_pair():

    csv_path = (
        CATALOGS / "candidatos_d6.csv"
    )

    if not csv_path.exists():
        return None

    with csv_path.open(
        newline="",
        encoding="utf-8-sig"
    ) as f:

        inventory = {
            row["obs_id"]: row
            for row in csv.DictReader(f)
        }

    if not all(
        key in inventory
        for key in REFERENCE_IDS
    ):
        return None

    def get_obs(key):

        row = inventory[key]

        return {
            "obs_id": key,
            "mjd": float(row["mjd"]),
            "access_url": row["url"],
            "detector": "SPHEREx-D6",
        }

    a = get_obs(REFERENCE_IDS[0])
    b = get_obs(REFERENCE_IDS[1])

    return {

        "pair_id": "REFERENCE_EPSF",

        "earlier": a,
        "later": b,

        "separation_days": round(
            b["mjd"] - a["mjd"],
            4
        ),

        "origin": "prior_epsf_validation",
    }


# =====================================================
# 6. MAIN
# =====================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "MORLEY spectral epoch prevalidation"
        )
    )

    parser.add_argument(
        "--pairs",
        type=Path,
        default=None
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.25
    )

    parser.add_argument(
        "--margin",
        type=int,
        default=4
    )

    parser.add_argument(
        "--min-valid",
        type=float,
        default=0.80
    )

    parser.add_argument(
        "--descargar",
        action="store_true"
    )

    parser.add_argument(
        "--max-descargas",
        type=int,
        default=4
    )

    parser.add_argument(
        "--size-deg",
        type=float,
        default=0.06
    )

    args = parser.parse_args()

    if not (
        0 < args.threshold < 10
        and 0 <= args.min_valid <= 1
        and args.margin >= 3
        and args.max_descargas >= 0
        and 0 < args.size_deg <= 0.2
    ):
        parser.error(
            "Parámetros inválidos"
        )

    # ---------------------------------------------
    # Load Practice 03 JSON
    # ---------------------------------------------

    manifests = sorted(
        CATALOGS.glob(
            "epoch_pairs_*.json"
        )
    )

    path = args.pairs or (
        manifests[-1]
        if manifests
        else None
    )

    if (
        path is None
        or not path.is_file()
    ):
        raise SystemExit(
            "Primero ejecuta la Práctica 03"
        )

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    ra = float(
        data["target"]["ra_deg"]
    )

    dec = float(
        data["target"]["dec_deg"]
    )

    pairs = list(
        data.get("pairs", [])
    )

    if not pairs:
        raise SystemExit(
            "El inventario de parejas está vacío"
        )

    # ---------------------------------------------
    # Add known reference pair
    # ---------------------------------------------

    ref = reference_pair()

    if ref:

        already_present = any(
            {
                pair["earlier"]["obs_id"],
                pair["later"]["obs_id"]
            } == set(REFERENCE_IDS)
            for pair in pairs
        )

        if not already_present:
            pairs.append(ref)

    # ---------------------------------------------
    # Inspect files
    # ---------------------------------------------

    measures = {}
    errors = {}
    results = []

    downloads = 0

    print("\n" + "=" * 62)

    print(
        "MORLEY — PRACTICE 04: SPECTRAL PREVALIDATION"
    )

    print("=" * 62)

    print(
        f"RA={ra:.7f}, Dec={dec:.7f}"
    )

    print(
        "Pairs to inspect:",
        len(pairs)
    )

    print(
        "Local FITS directory:",
        CUTOUTS
    )

    for pair in pairs:

        obs1 = pair["earlier"]
        obs2 = pair["later"]

        missing = []
        problems = []

        for obs in (obs1, obs2):

            obs_id = obs["obs_id"]

            if (
                obs_id in measures
                or obs_id in errors
            ):
                continue

            try:

                path_fits = local_path(obs)

                exists = (
                    path_fits.exists()
                    and path_fits.stat().st_size > 2048
                )

                if not exists:

                    if (
                        args.descargar
                        and downloads < args.max_descargas
                    ):

                        downloads += 1

                        print(
                            f"Downloading {obs_id}..."
                        )

                        download_cutout(
                            obs,
                            ra,
                            dec,
                            args.size_deg
                        )

                    else:

                        errors[obs_id] = (
                            "missing_local_fits"
                        )

                        continue

                measures[obs_id] = inspect(
                    obs,
                    ra,
                    dec,
                    args.margin
                )

            except Exception as error:

                errors[obs_id] = (
                    f"{type(error).__name__}: "
                    f"{error}"
                )

        # -----------------------------------------
        # Identify missing/invalid data
        # -----------------------------------------

        for obs in (obs1, obs2):

            obs_id = obs["obs_id"]

            if obs_id in measures:
                continue

            entry = {
                "obs_id": obs_id,
                "reason": errors.get(
                    obs_id,
                    "unknown"
                )
            }

            if (
                errors.get(obs_id)
                == "missing_local_fits"
            ):
                missing.append(entry)
            else:
                problems.append(entry)

        row = {

            "pair_id": pair["pair_id"],

            "earlier_obs_id": obs1["obs_id"],

            "later_obs_id": obs2["obs_id"],

            "separation_days": pair.get(
                "separation_days"
            ),

            "origin": pair.get(
                "origin",
                "practice_03"
            ),

            "wcs_wave_approximate": True,

            "cwave_cband_verified": False,

            "ready_for_zogy": False,
        }

        if missing or problems:

            row.update({

                "status": (
                    "unavailable_fits"
                    if missing
                    else "invalid_fits"
                ),

                "missing": missing,
                "problems": problems,

                "spectral_mismatch": None,

                "quality_passed": None,
            })

        else:

            a = measures[
                obs1["obs_id"]
            ]

            b = measures[
                obs2["obs_id"]
            ]

            # -------------------------------------
            # Spectral mismatch
            # -------------------------------------

            mean_width = (
                a["bandwidth_um"]
                + b["bandwidth_um"]
            ) / 2

            mismatch = abs(
                a["wavelength_um"]
                - b["wavelength_um"]
            ) / mean_width

            width_mismatch = abs(
                a["bandwidth_um"]
                - b["bandwidth_um"]
            ) / mean_width

            # -------------------------------------
            # Quality checks
            # -------------------------------------

            quality = (
                a["central_good"]
                and b["central_good"]
                and a["valid_fraction_5x5"]
                >= args.min_valid
                and b["valid_fraction_5x5"]
                >= args.min_valid
            )

            if not quality:

                status = "low_quality"

            elif mismatch <= args.threshold:

                status = (
                    "preliminary_spectral_match"
                )

            else:

                status = "spectral_mismatch"

            row.update({

                "status": status,

                "spectral_mismatch": round(
                    float(mismatch), 5
                ),

                "bandwidth_mismatch": round(
                    float(width_mismatch), 5
                ),

                "quality_passed": bool(
                    quality
                ),

                "earlier_measurement": a,

                "later_measurement": b,

                "missing": [],
                "problems": [],
            })

        results.append(row)

        metric = row.get(
            "spectral_mismatch"
        )

        print(
            f"{row['pair_id']}: "
            f"{row['status']}"
            + (
                f" | mismatch={metric:.4f}"
                if metric is not None
                else ""
            )
        )

    # ---------------------------------------------
    # Sort results
    # ---------------------------------------------

    results.sort(
        key=lambda row: (
            row["spectral_mismatch"] is None,
            row["spectral_mismatch"]
            if row["spectral_mismatch"] is not None
            else float("inf")
        )
    )

    summary = {
        status: sum(
            r["status"] == status
            for r in results
        )
        for status in sorted({
            r["status"]
            for r in results
        })
    }

    # =================================================
    # 7. JSON OUTPUT
    # =================================================

    payload = {

        "schema_version": (
            "morley.spectral_precheck.v1"
        ),

        "project": (
            "ÉTER / MORLEY Frontier"
        ),

        "created_at_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "source_pairs_manifest": (
            path.name
        ),

        "target": data["target"],

        "method": (
            "WCS-WAVE approximate + "
            "spatial WCS + "
            "IMAGE/VARIANCE/FLAGS"
        ),

        "threshold_exploratory": (
            args.threshold
        ),

        "observation_inventory_cached": (
            data.get("source_status")
            == "cached_fallback"
        ),

        "scientific_integrity": {

            "analysis_type": "exploratory",

            "simulation": False,

            "confirmed_motion": False,

            "executed_zogy": False,

            "ready_for_zogy": False,

            "note": (
                "WCS-WAVE does not replace "
                "science-grade CWAVE/CBAND, "
                "PSF/noise calibration or "
                "temporal validation."
            ),
        },

        "summary": {

            "total_pairs": len(results),

            "by_status": summary,

            "unique_fits_measured": (
                len(measures)
            ),

            "downloads_attempted": downloads,
        },

        "pairs": results,
    }

    # ---------------------------------------------
    # Save files
    # ---------------------------------------------

    CATALOGS.mkdir(
        parents=True,
        exist_ok=True
    )

    json_path = (
        CATALOGS
        / "spectral_pairs_checked.json"
    )

    csv_path = (
        CATALOGS
        / "spectral_pairs_checked.csv"
    )

    json_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    fields = [
        "pair_id",
        "earlier_obs_id",
        "later_obs_id",
        "origin",
        "separation_days",
        "status",
        "spectral_mismatch",
        "bandwidth_mismatch",
        "quality_passed",
        "ready_for_zogy",
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()

        writer.writerows(
            {
                key: row.get(key)
                for key in fields
            }
            for row in results
        )

    print("\n" + "=" * 62)

    print("SUMMARY:", summary)

    print(
        "FITS inspected:",
        len(measures)
    )

    print("JSON:", json_path)

    print("CSV:", csv_path)

    print(
        "SCIENTIFIC STATUS: "
        "PREVALIDATION ONLY"
    )

    print("ZOGY HAS NOT BEEN EXECUTED.")


if __name__ == "__main__":
    main()
