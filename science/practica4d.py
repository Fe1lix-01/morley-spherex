"""ETER / MORLEY Frontier — Practice 04D.

Download official SPHEREx Level 2 FITS cutouts from IRSA.

Input:
    outputs/catalogs/epoch_pairs_ra295.40978_dec-15.22317.json

Output:
    outputs/data/irsa_cutouts/
    outputs/catalogs/irsa_cutout_download_manifest.json

This script does NOT perform spectral calibration,
ZOGY, variability analysis, or motion detection.
"""

from __future__ import annotations

import argparse
import hashlib
import json

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import numpy as np
import requests

from astropy.io import fits
from astropy.wcs import WCS

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =====================================================
# 1. CONFIGURATION
# =====================================================

ROOT = Path(__file__).resolve().parent

CATALOGS = ROOT / "outputs" / "catalogs"

CUTOUTS = ROOT / "outputs" / "observaciones"

DEFAULT_PAIRS = CATALOGS / (
    "epoch_pairs_ra295.40978_dec-15.22317.json"
)


# =====================================================
# 2. UTILITIES
# =====================================================

def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def sha256_file(path):

    digest = hashlib.sha256()

    with path.open("rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


# =====================================================
# 3. VALIDATE OFFICIAL ARCHIVE URL
# =====================================================

def archive_url(raw_url):
    """
    Only accept official IRSA SPHEREx Level 2
    FITS URLs from DR1 or QR3.
    """

    parsed = urlparse(str(raw_url).strip())

    sections = parsed.path.lower().split("/")

    valid = (
        parsed.scheme == "https"
        and parsed.netloc.lower()
        == "irsa.ipac.caltech.edu"
        and len(sections) >= 7
        and sections[1:4]
        == ["ibe", "data", "spherex"]
        and sections[4] in {"dr1", "qr3"}
        and sections[5] == "level2"
        and parsed.path.lower().endswith(".fits")
        and not parsed.username
        and not parsed.password
    )

    if not valid:
        raise ValueError(
            f"Not an allowed official Level 2 URL: "
            f"{raw_url}"
        )

    # Remove any existing cutout query parameters.
    return urlunparse((
        "https",
        parsed.netloc,
        parsed.path,
        "",
        "",
        "",
    ))


# =====================================================
# 4. VALIDATE DOWNLOADED FITS
# =====================================================

def verify_cutout(path, ra, dec):
    """
    Check FITS structure and target coverage.

    These checks do NOT establish scientific
    suitability for temporal image subtraction.
    """

    with fits.open(
        path,
        memmap=False,
    ) as hdul:

        required = (
            "IMAGE",
            "FLAGS",
            "VARIANCE",
            "EPSF",
            "WCS-WAVE",
        )

        missing = [
            key for key in required
            if key not in hdul
        ]

        if missing:
            raise ValueError(
                f"Missing FITS extensions: {missing}"
            )

        image = hdul["IMAGE"].data
        flags = hdul["FLAGS"].data
        variance = hdul["VARIANCE"].data

        if (
            image is None
            or image.ndim != 2
            or flags is None
            or variance is None
            or image.shape != flags.shape
            or image.shape != variance.shape
        ):
            raise ValueError(
                "Incompatible IMAGE/FLAGS/VARIANCE shapes"
            )

        spatial_wcs = WCS(
            hdul["IMAGE"].header,
            fobj=hdul,
        ).celestial

        x, y = spatial_wcs.world_to_pixel_values(
            ra,
            dec,
        )

        ny, nx = image.shape

        if not (
            np.isfinite(x)
            and np.isfinite(y)
            and 0 <= x < nx
            and 0 <= y < ny
        ):
            raise ValueError(
                "Target RA/Dec is outside "
                "the returned FITS image"
            )

        return {
            "image_shape": [
                int(ny),
                int(nx),
            ],
            "target_pixel_xy": [
                round(float(x), 3),
                round(float(y), 3),
            ],
            "date_obs": (
                hdul["IMAGE"].header.get(
                    "DATE-OBS"
                )
            ),
            "extensions_present": list(required),
        }


# =====================================================
# 5. NETWORK SESSION WITH RETRIES
# =====================================================

def create_session():

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Morley-ETER-educational-SPHEREx/1.0"
        )
    })

    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=1.0,
        status_forcelist=(
            429, 502, 503, 504
        ),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )

    session.mount(
        "https://",
        HTTPAdapter(max_retries=retry),
    )

    return session


# =====================================================
# 6. DOWNLOAD ONE OBSERVATION
# =====================================================

def download_one(
    session,
    obs,
    ra,
    dec,
    size_deg,
    max_mb,
):

    source_url = archive_url(
        obs["access_url"]
    )

    stem = Path(
        urlparse(source_url).path
    ).stem

    # Include target position in filename.
    # This prevents mixing cutouts of different
    # sky regions or cutout sizes.
    tag = (
        f"ra{ra:.5f}_"
        f"dec{dec:+.5f}_"
        f"size{size_deg:.4f}"
    )

    tag = (
        tag.replace(".", "p")
        .replace("+", "pos")
        .replace("-", "neg")
    )

    destination = CUTOUTS / (
        f"{stem}__cutout_{tag}.fits"
    )

    relative = destination.relative_to(
        ROOT
    ).as_posix()

    params = {
        "center": f"{ra:.8f},{dec:.8f}",
        "size": f"{size_deg:.5f}",
    }

    prepared_url = requests.Request(
        "GET",
        source_url,
        params=params,
    ).prepare().url

    record = {
        "obs_id": obs["obs_id"],
        "collection": obs.get("collection"),
        "archive_url": source_url,
        "cutout_request_url": prepared_url,
        "file": relative,
        "downloaded_at_utc": None,
        "sha256": None,
        "status": "pending",
        "ready_for_zogy": False,
    }

    # -----------------------------------------
    # Reuse existing verified cutout
    # -----------------------------------------

    if destination.is_file():

        try:
            info = verify_cutout(
                destination,
                ra,
                dec,
            )

            record.update(
                status="existing_verified",
                sha256=sha256_file(destination),
                **info,
            )

        except Exception as exc:
            record.update(
                status="invalid_existing_fits",
                error=str(exc),
            )

        return record

    # -----------------------------------------
    # Download to temporary file
    # -----------------------------------------

    partial = destination.with_suffix(
        ".fits.part"
    )

    partial.unlink(
        missing_ok=True
    )

    max_bytes = max_mb * 1024 * 1024

    try:

        with session.get(
            source_url,
            params=params,
            timeout=(15, 60),
            stream=True,
        ) as response:

            response.raise_for_status()

            record["cutout_request_url"] = (
                response.url
            )

            count = 0

            with partial.open("wb") as out:

                for chunk in response.iter_content(
                    chunk_size=256 * 1024
                ):

                    if not chunk:
                        continue

                    count += len(chunk)

                    if count > max_bytes:
                        raise ValueError(
                            "Cutout exceeded "
                            f"{max_mb} MB limit"
                        )

                    out.write(chunk)

        # Do not rename until the downloaded
        # FITS passes basic validation.
        info = verify_cutout(
            partial,
            ra,
            dec,
        )

        partial.replace(destination)

        record.update(
            status="downloaded_verified",
            downloaded_at_utc=utc_now(),
            sha256=sha256_file(destination),
            bytes=destination.stat().st_size,
            **info,
        )

    except Exception as exc:

        record.update(
            status="download_error",
            error=(
                f"{type(exc).__name__}: {exc}"
            ),
        )

        partial.unlink(
            missing_ok=True
        )

    return record


# =====================================================
# 7. MAIN
# =====================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Download official IRSA SPHEREx "
            "Level 2 FITS cutouts"
        )
    )

    parser.add_argument(
        "--pairs",
        type=Path,
        default=DEFAULT_PAIRS,
    )

    parser.add_argument(
        "--campaign",
        choices=("1", "2", "all"),
        default="2",
    )

    parser.add_argument(
        "--pair-id",
        default=None,
        help="Download one pair, e.g. P02_01",
    )

    parser.add_argument(
        "--max-pairs",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--size-deg",
        type=float,
        default=0.06,
    )

    parser.add_argument(
        "--max-mb",
        type=int,
        default=25,
    )

    args = parser.parse_args()

    if not (
        1 <= args.max_pairs <= 8
        and 0 < args.size_deg <= 0.2
        and 1 <= args.max_mb <= 200
    ):
        parser.error(
            "Invalid download parameters"
        )

    if not args.pairs.is_file():
        parser.error(
            f"Missing Practice 03 JSON: "
            f"{args.pairs}"
        )

    # -----------------------------------------
    # Read candidates from Practice 03
    # -----------------------------------------

    pairs_data = json.loads(
        args.pairs.read_text(
            encoding="utf-8"
        )
    )

    if (
        pairs_data.get("schema_version")
        != "morley.epoch_pairs.v1"
    ):
        parser.error(
            "Unexpected candidate JSON schema"
        )

    ra = float(
        pairs_data["target"]["ra_deg"]
    )

    dec = float(
        pairs_data["target"]["dec_deg"]
    )

    if not (
        0 <= ra < 360
        and -90 <= dec <= 90
    ):
        parser.error(
            "Invalid target coordinates"
        )

    pairs = pairs_data.get(
        "pairs", []
    )

    # -----------------------------------------
    # Select candidate pairs
    # -----------------------------------------

    if args.pair_id:

        selected = [
            pair for pair in pairs
            if pair["pair_id"] == args.pair_id
        ]

    else:

        selected = [
            pair for pair in pairs
            if (
                args.campaign == "all"
                or pair["pair_id"].startswith(
                    f"P0{args.campaign}_"
                )
            )
        ][:args.max_pairs]

    if not selected:
        parser.error(
            "No candidate pairs found"
        )

    # Do not download duplicate observations.
    unique_obs = {}

    for pair in selected:

        for phase in (
            "earlier",
            "later",
        ):

            obs = pair[phase]

            unique_obs[obs["obs_id"]] = obs

    CUTOUTS.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 64)
    print(
        "MORLEY — IRSA LEVEL 2 CUTOUT DOWNLOAD"
    )
    print("=" * 64)

    print("Target:", ra, dec)

    print(
        "Pairs:",
        ", ".join(
            p["pair_id"]
            for p in selected
        )
    )

    print(
        "Unique files to request:",
        len(unique_obs)
    )

    print(
        "Source: Official IRSA IBE"
    )

    # -----------------------------------------
    # Download
    # -----------------------------------------

    results = []

    with create_session() as session:

        for index, obs in enumerate(
            unique_obs.values(),
            start=1,
        ):

            print(
                f"\n[{index}/{len(unique_obs)}] "
                f"{obs['obs_id']}"
            )

            try:

                result = download_one(
                    session,
                    obs,
                    ra,
                    dec,
                    args.size_deg,
                    args.max_mb,
                )

            except Exception as exc:

                result = {
                    "obs_id": obs["obs_id"],
                    "status": "input_error",
                    "error": str(exc),
                }

            results.append(result)

            print(
                "Status:",
                result["status"]
            )

            if "error" in result:
                print(
                    "Reason:",
                    result["error"]
                )

            if result.get("sha256"):
                print(
                    "SHA-256:",
                    result["sha256"]
                )

    # -----------------------------------------
    # Generate provenance manifest
    # -----------------------------------------

    success = sum(
        r["status"] in {
            "downloaded_verified",
            "existing_verified",
        }
        for r in results
    )

    payload = {
        "schema_version": (
            "morley.irsa_cutouts.v1"
        ),

        "generated_at_utc": utc_now(),

        "target": pairs_data["target"],

        "source_pair_manifest": (
            args.pairs.name
        ),

        "selected_pair_ids": [
            p["pair_id"]
            for p in selected
        ],

        "discovery_provenance": (
            "cached_archive_metadata_"
            "from_previous_discovery"
        ),

        "archive_source": (
            "IRSA SPHEREx DR1/QR3 Level 2"
        ),

        "cutout_size_deg": args.size_deg,

        "summary": {
            "requested": len(results),
            "verified": success,
            "failed": len(results) - success,
        },

        "scientific_integrity": {
            "download_verification_only": True,
            "spectral_calibration_verified": False,
            "wcs_registered": False,
            "zogy_executed": False,
            "ready_for_zogy": False,
            "motion_detected": False,
        },

        "files": results,
    }

    CATALOGS.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = CATALOGS / (
        "irsa_cutout_download_manifest.json"
    )

    output.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 64)
    print(
        f"VERIFIED: {success}/{len(results)}"
    )
    print("Manifest:", output)
    print(
        "Next: rerun 04c_find_best_local_pairs.py"
    )
    print(
        "NO ZOGY; NO MOTION DETECTION"
    )


if __name__ == "__main__":
    main()