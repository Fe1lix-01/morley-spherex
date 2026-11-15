"""
ETER / MORLEY Frontier
NASA Space Apps Challenge 2026

Practice 01 — SPHEREx Traceback

Goal:
    Given RA and Dec:
    1. Read SPHEREx DR1 HiPS metadata.
    2. Identify the relevant HEALPix tile.
    3. Identify its 102 spectral channels.
    4. Search independent Level 2 observations.
    5. Export a JSON manifest for the backend.

Scientific integrity:
    - The cube is spectral, NOT temporal.
    - Level 2 results are candidates, not verified pairs.
    - This script does NOT run ZOGY.
    - This script does NOT claim motion detection.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import hpgeom
import numpy as np
import requests

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time

from astroquery.ipac.irsa import Irsa


# =====================================================
# 1. CONFIGURATION
# =====================================================

HIPS_URL = (
    "https://irsa.ipac.caltech.edu/data/hips/"
    "SPHEREx/spherex_allsky_cube"
)

CUBE_DATA_URL = (
    "https://irsa.ipac.caltech.edu/ibe/data/"
    "spherex/dr1/hips5_cube/hips_20261026"
)

COLLECTIONS = [
    "spherex_dr1",
    "spherex_qr3",
]

# SPHEREx DR1: channels 51 and 52 are empty.
# These indices are zero-based.
BLANK_CHANNELS = {50, 51}

SCRIPT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = (
    SCRIPT_DIR / "outputs" / "catalogs"
)


# =====================================================
# 2. UTILITIES
# =====================================================

def scalar(value):
    """Convert numpy/astropy values to JSON-safe data."""

    if value is None or np.ma.is_masked(value):
        return None

    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass

    if isinstance(value, bytes):
        value = value.decode(
            "utf-8",
            errors="replace"
        )

    if isinstance(value, (np.integer, int)):
        return int(value)

    if isinstance(value, (np.floating, float)):
        result = float(value)
        return result if np.isfinite(result) else None

    if isinstance(value, (str, bool)):
        return value

    return str(value)


def column_value(row, *names):
    """Read the first available SIA2 column."""

    for name in names:
        if name in row.colnames:
            value = scalar(row[name])

            if value is not None:
                return value

    return None


def mjd_to_iso(mjd):
    """Convert Modified Julian Date to UTC."""

    if mjd is None:
        return None

    try:
        return Time(
            float(mjd),
            format="mjd",
            scale="utc"
        ).isot

    except (ValueError, TypeError):
        return None


# =====================================================
# 3. READ HIPS METADATA
# =====================================================

def get_hips_properties():

    url = f"{HIPS_URL}/properties"

    print("\n[1] Reading SPHEREx HiPS metadata...")
    print("URL:", url)

    response = requests.get(
        url,
        timeout=(15, 45)
    )

    response.raise_for_status()

    properties = {}

    for line in response.text.splitlines():

        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        properties[key.strip()] = value.strip()

    required = [
        "hips_order",
        "hips_cube_depth",
        "data_cube_crval3_arr",
    ]

    for key in required:

        if key not in properties:
            raise ValueError(
                f"Missing HiPS property: {key}"
            )

    return properties


# =====================================================
# 4. SPECTRAL CHANNEL INVENTORY
# =====================================================

def get_spectral_channels(properties):

    depth = int(
        properties["hips_cube_depth"]
    )

    wavelengths = [
        float(v)
        for v in properties[
            "data_cube_crval3_arr"
        ].split()
    ]

    if len(wavelengths) != depth:
        raise ValueError(
            "HiPS channel metadata is inconsistent."
        )

    channels = []

    for index, wavelength in enumerate(wavelengths):

        band = index // 17 + 1
        detector_channel = index % 17 + 1

        channels.append({

            "index": index,

            "number": index + 1,

            "band": band,

            "detector_channel": detector_channel,

            "wavelength_um": wavelength,

            "has_data": (
                index not in BLANK_CHANNELS
            ),

            "axis": "wavelength",

        })

    return channels


# =====================================================
# 5. HEALPIX TILE LOOKUP
# =====================================================

def find_cube_tile(ra, dec, properties):

    print("\n[2] Locating HEALPix tile...")

    order = int(
        properties["hips_order"]
    )

    nside = 2 ** order

    pixel_index = int(
        hpgeom.angle_to_pixel(
            nside,
            ra,
            dec,
            nest=True,
            lonlat=True
        )
    )

    directory = (
        pixel_index // 10000
    ) * 10000

    tile_url = (
        f"{CUBE_DATA_URL}"
        f"/Norder{order}"
        f"/Dir{directory}"
        f"/Npix{pixel_index}_cube.fits"
    )

    print("HEALPix order:", order)
    print("HEALPix pixel:", pixel_index)
    print("FITS URL:", tile_url)

    return {

        "healpix_order": order,

        "nside": nside,

        "nested_pixel": pixel_index,

        "fits_url": tile_url,

    }


# =====================================================
# 6. LEVEL 2 OBSERVATION DISCOVERY
# =====================================================


def search_level2(ra, dec, radius_arcsec, limit):
    """
    Discover SPHEREx Level 2 observations using IRSA TAP.

    Initial science migration: detector D6 only.
    Uses a point-containment query, not a cone search.
    """

    print("\n[3] Searching SPHEREx Level 2 via TAP...")
    print("Detector: D6")
    print("Target:", ra, dec)

    query = f"""
    SELECT TOP {int(limit) + 1}
        a.uri AS access_path,
        p.time_bounds_lower,
        p.time_bounds_upper,
        p.energy_bandpassname
    FROM spherex.artifact a
    JOIN spherex.plane p
        ON a.planeid = p.planeid
    WHERE
        1 = CONTAINS(
            POINT('ICRS', {float(ra)}, {float(dec)}),
            p.poly
        )
        AND p.energy_bandpassname = 'SPHEREx-D6'
    ORDER BY p.time_bounds_lower
    """

    try:
        table = Irsa.query_tap(query)

    except Exception as error:
        print(
            "TAP query failed:",
            type(error).__name__,
            error
        )

        return {
            "status": "service_error",
            "method": "IRSA_TAP",
            "detector_filter": "SPHEREx-D6",
            "error": str(error),
            "total": None,
            "returned": 0,
            "truncated": False,
            "observations": [],
        }

    observations = []

    for row in list(table)[:limit]:

        path = str(row["access_path"])

        # Keep only DR1/QR3.
        if "/spherex/dr1/" in path.lower():
            collection = "spherex_dr1"

        elif "/spherex/qr3/" in path.lower():
            collection = "spherex_qr3"

        else:
            continue

        if path.startswith("http"):
            access_url = path
        else:
            access_url = (
                "https://irsa.ipac.caltech.edu/"
                + path.lstrip("/")
            )

        obs_id = Path(
            access_url.split("?")[0]
        ).stem

        start_mjd = scalar(
            row["time_bounds_lower"]
        )

        end_mjd = scalar(
            row["time_bounds_upper"]
        )

        band = scalar(
            row["energy_bandpassname"]
        )

        observations.append({
            "obs_id": obs_id,
            "collection": collection,
            "detector": band,
            "start_mjd": start_mjd,
            "end_mjd": end_mjd,
            "start_utc": mjd_to_iso(start_mjd),
            "end_utc": mjd_to_iso(end_mjd),
            "access_url": access_url,
            "source": "SPHEREx Level 2",
            "evidence_type": "observed",
            "verified_for_zogy": False,
        })

    print("TAP rows returned:", len(table))
    print("Eligible observations:", len(observations))

    return {
        "status": (
            "ok" if observations
            else "no_eligible_observations"
        ),
        "method": "IRSA_TAP",
        "detector_filter": "SPHEREx-D6",
        "search_geometry": "point_containment",
        "requested_radius_arcsec": radius_arcsec,
        "total": len(table),
        "returned": len(observations),
        "truncated": len(table) > limit,
        "observations": observations,
    }



# =====================================================
# 7. BUILD SCIENTIFIC MANIFEST
# =====================================================

def create_manifest(
    ra,
    dec,
    radius_arcsec,
    properties,
    tile,
    channels,
    level2
):

    return {

        "schema_version": "morley.traceback.v1",

        "project": "ETER / MORLEY Frontier",

        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "target": {

            "ra_deg": ra,

            "dec_deg": dec,

            "radius_arcsec": radius_arcsec,

            "coordinate_frame": "ICRS",

        },

        "cube": {

            "source": "SPHEREx DR1 HiPS",

            "evidence_type": "visualization",

            "hips_url": HIPS_URL,

            "hips_properties_url": (
                f"{HIPS_URL}/properties"
            ),

            "tile": tile,

            "channel_count": len(channels),

            "blank_channel_indices": [50, 51],

            "channels": channels,

            "axis_type": "spectral",

            "temporal_axis": False,

            "use": "sky_exploration",

        },

        "level2": level2,

        "temporal_analysis": {

            "ready_for_zogy": False,

            "status": (
                "requires_independent_"
                "compatible_epochs"
            ),

            "required_checks": [

                "Independent observation dates",

                "Same sky region",

                "Compatible spectral response",

                "Valid FLAGS and VARIANCE",

                "WCS alignment",

                "Photometric normalization",

                "Appropriate ePSF",

                "Background and noise model",

            ],

        },

        "scientific_integrity": {

            "motion_detected": False,

            "analysis_executed": False,

            "simulation": False,

            "data_discovery_only": True,

            "cube_is_not_temporal": True,

            "source_switching_requires_label": True,

        },

    }


# =====================================================
# 8. SAVE JSON
# =====================================================

def save_manifest(manifest, ra, dec):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = (
        f"traceback_"
        f"ra{ra:.5f}_"
        f"dec{dec:+.5f}.json"
    )

    output_path = OUTPUT_DIR / filename

    with output_path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            manifest,
            file,
            indent=2,
            ensure_ascii=False
        )

    return output_path


# =====================================================
# 9. MAIN
# =====================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "MORLEY SPHEREx HiPS and Level 2 Traceback"
        )
    )

    parser.add_argument(
        "--ra",
        type=float,
        default=295.4097841
    )

    parser.add_argument(
        "--dec",
        type=float,
        default=-15.2231692
    )

    parser.add_argument(
        "--radius-arcsec",
        type=float,
        default=30.0
    )

    parser.add_argument(
        "--max-observations",
        type=int,
        default=200
    )

    parser.add_argument(
        "--solo-cubo",
        action="store_true"
    )

    args = parser.parse_args()

    if not (
        0 <= args.ra < 360
        and -90 <= args.dec <= 90
    ):
        parser.error("Invalid RA/Dec.")

    if (
        args.radius_arcsec <= 0
        or args.max_observations <= 0
    ):
        parser.error(
            "Radius and max observations must be positive."
        )

    print("=" * 60)
    print("MORLEY — SPHEREx TRACEBACK")
    print("=" * 60)

    print(
        f"Target RA={args.ra}, Dec={args.dec}"
    )

    # Step 1: metadata
    properties = get_hips_properties()

    # Step 2: 102 channels
    channels = get_spectral_channels(properties)

    # Step 3: locate FITS cube tile
    tile = find_cube_tile(
        args.ra,
        args.dec,
        properties
    )

    # Step 4: search individual epochs
    if args.solo_cubo:

        level2 = {

            "status": "skipped",

            "reason": "--solo-cubo",

            "total": None,

            "returned": 0,

            "observations": [],

        }

    else:

        level2 = search_level2(
            args.ra,
            args.dec,
            args.radius_arcsec,
            args.max_observations
        )

    # Step 5: create science/backend manifest
    manifest = create_manifest(
        args.ra,
        args.dec,
        args.radius_arcsec,
        properties,
        tile,
        channels,
        level2
    )

    # Step 6: export JSON
    output = save_manifest(
        manifest,
        args.ra,
        args.dec
    )

    print("\n" + "=" * 60)
    print("TRACEBACK COMPLETE")
    print("=" * 60)

    print("Spectral channels:", len(channels))
    print("Blank channels:", [50, 51])
    print("Level 2 status:", level2["status"])
    print("Output:", output)

    print(
        "Scientific status: DISCOVERY_ONLY"
    )

    print(
        "ZOGY has NOT been executed."
    )


if __name__ == "__main__":
    main()