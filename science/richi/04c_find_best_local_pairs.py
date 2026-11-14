
"""
ETER / MORLEY Frontier
NASA Space Apps Challenge 2026

Practice 04C — Local Spectral Pair Ranking

Purpose:
    Discover local SPHEREx Level 2 FITS exposures
    and identify temporal pairs with approximately
    compatible spectral bands.

Scientific limitations:
    - Uses approximate WCS-WAVE calibration.
    - Does not verify science-grade CWAVE/CBAND.
    - Does not register images.
    - Does not perform photometric normalization.
    - Does not perform ePSF fitting or ZOGY.
    - Does not claim variability or motion detection.

All file paths exported in the JSON are relative
to this module's directory.

No external repositories or network services
are required for this practice.
"""

from __future__ import annotations

import argparse
import csv
import json
import re

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import astropy.units as u

from astropy.io import fits
from astropy.wcs import WCS


# =====================================================
# 1. CONFIGURATION
# =====================================================

ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "outputs" / "data"

CATALOGS_DIR = ROOT / "outputs" / "catalogs"

DEFAULT_RA = 295.4097841
DEFAULT_DEC = -15.2231692

# FITS example:
# level2_2025W38_1A_0596_1D6_spx_l2b-...
FILENAME_PATTERN = re.compile(
    r"level2_(?P<obs_id>\d{4}W\d+_[^D]+)"
    r"D(?P<detector>[1-6])_spx_",
    re.IGNORECASE,
)

# Exploratory bit mask.
# Bit 21 (SOURCE) is deliberately not rejected.
# This mask is NOT a substitute for a complete
# data-release-specific FLAGS interpretation.
BAD_BITS = (
    0, 1, 2, 6, 7, 9, 10, 11,
    14, 15, 17, 19, 20, 22,
)

BAD_MASK = sum(
    1 << bit for bit in BAD_BITS
)

MIN_VALID_FRACTION = 0.80

# Exploratory mismatch threshold, not a
# physically validated spectral tolerance.
DEFAULT_THRESHOLD = 0.25

# Allow enough room for a future ~33x33 PSF stamp.
MIN_EDGE_MARGIN = 3


# =====================================================
# 2. PORTABLE PATHS
# =====================================================

def relative_path(path: Path) -> str:
    """Return a path relative to science/richi."""

    return path.resolve().relative_to(
        ROOT.resolve()
    ).as_posix()


# =====================================================
# 3. DISCOVER LOCAL FITS
# =====================================================

def discover_files():
    """
    Find SPHEREx Level 2 FITS under outputs/data.

    Deduplicate by observation ID and detector.
    Prefer the largest local copy when duplicates
    exist, then inspect FITS content.
    """

    if not DATA_DIR.is_dir():
        raise FileNotFoundError(
            f"Data directory not found: {DATA_DIR}"
        )

    discovered = {}

    for path in DATA_DIR.rglob("*.fits"):

        match = FILENAME_PATTERN.search(
            path.name
        )

        if not match:
            continue

        obs_id = match.group("obs_id")

        detector = (
            f"D{match.group('detector')}"
        )

        key = (obs_id, detector)

        if (
            key not in discovered
            or path.stat().st_size
            > discovered[key].stat().st_size
        ):
            discovered[key] = path

    return discovered


# =====================================================
# 4. INSPECT ONE OBSERVATION
# =====================================================

def inspect_fits(
    path: Path,
    obs_id: str,
    detector: str,
    ra: float,
    dec: float,
):

    with fits.open(
        path,
        memmap=True,
    ) as hdul:

        required_extensions = (
            "IMAGE",
            "VARIANCE",
            "FLAGS",
            "WCS-WAVE",
        )

        for extension in required_extensions:

            if extension not in hdul:
                raise ValueError(
                    f"Missing {extension}"
                )

        image_hdu = hdul["IMAGE"]

        image = image_hdu.data
        variance = hdul["VARIANCE"].data
        flags = hdul["FLAGS"].data

        if (
            image is None
            or image.ndim != 2
            or image.shape != variance.shape
            or image.shape != flags.shape
        ):
            raise ValueError(
                "Incompatible IMAGE/VARIANCE/FLAGS"
            )

        header = image_hdu.header

        # -----------------------------------------
        # Spatial WCS
        # -----------------------------------------

        spatial_wcs = WCS(
            header,
            fobj=hdul,
        ).celestial

        x, y = spatial_wcs.world_to_pixel_values(
            ra,
            dec,
        )

        x = float(x)
        y = float(y)

        ny, nx = image.shape

        if not (
            np.isfinite(x)
            and np.isfinite(y)
            and MIN_EDGE_MARGIN <= x
            < nx - MIN_EDGE_MARGIN
            and MIN_EDGE_MARGIN <= y
            < ny - MIN_EDGE_MARGIN
        ):
            raise ValueError(
                "Target outside usable image area"
            )

        # -----------------------------------------
        # Spectral WCS
        # -----------------------------------------

        spectral_wcs = WCS(
            header,
            fobj=hdul,
            key="W",
        )

        # SIP applies to spatial astrometry,
        # not to the alternative spectral WCS.
        spectral_wcs.sip = None

        wavelength, bandwidth = (
            spectral_wcs.pixel_to_world(x, y)
        )

        lam = float(
            wavelength.to_value(u.um)
        )

        width = float(
            bandwidth.to_value(u.um)
        )

        if not (
            np.isfinite(lam)
            and np.isfinite(width)
            and width > 0
        ):
            raise ValueError(
                "Invalid WCS-WAVE calibration"
            )

        # -----------------------------------------
        # Local quality check
        # -----------------------------------------

        ix = int(round(x))
        iy = int(round(y))

        image_patch = np.asarray(
            image[
                iy - 2:iy + 3,
                ix - 2:ix + 3,
            ]
        )

        variance_patch = np.asarray(
            variance[
                iy - 2:iy + 3,
                ix - 2:ix + 3,
            ]
        )

        flags_patch = np.asarray(
            flags[
                iy - 2:iy + 3,
                ix - 2:ix + 3,
            ],
            dtype=np.uint64,
        )

        valid = (
            np.isfinite(image_patch)
            & np.isfinite(variance_patch)
            & (variance_patch > 0)
            & ((flags_patch & BAD_MASK) == 0)
        )

        valid_fraction = float(
            np.mean(valid)
        )

        central_good = bool(
            valid[2, 2]
        )

        return {

            "obs_id": obs_id,

            "year": int(obs_id[:4]),

            "detector": detector,

            "date_obs": header.get(
                "DATE-OBS"
            ),

            "file": relative_path(path),

            "image_shape": [ny, nx],

            "target_pixel": {
                "x": round(x, 3),
                "y": round(y, 3),
            },

            "wavelength_um": round(
                lam, 8
            ),

            "bandwidth_um": round(
                width, 8
            ),

            "valid_fraction_5x5": round(
                valid_fraction, 3
            ),

            "central_good": central_good,

            "central_flags": int(
                flags_patch[2, 2]
            ),

            "epsf_available": (
                "EPSF" in hdul
            ),

            "wavelength_method": (
                "approximate_WCS-WAVE"
            ),
        }


# =====================================================
# 5. COMPARE TWO OBSERVATIONS
# =====================================================

def compare_pairs(
    earlier,
    later,
    threshold,
):

    lam_a = earlier["wavelength_um"]
    lam_b = later["wavelength_um"]

    width_a = earlier["bandwidth_um"]
    width_b = later["bandwidth_um"]

    mean_width = (
        width_a + width_b
    ) / 2

    delta_lambda = abs(
        lam_a - lam_b
    )

    relative_mismatch = (
        delta_lambda / mean_width
    )

    # Approximate both passbands as rectangles.
    lower_a = lam_a - width_a / 2
    upper_a = lam_a + width_a / 2

    lower_b = lam_b - width_b / 2
    upper_b = lam_b + width_b / 2

    overlap = max(
        0.0,
        min(upper_a, upper_b)
        - max(lower_a, lower_b)
    )

    overlap_fraction = (
        overlap / min(width_a, width_b)
    )

    quality_pass = (
        earlier["central_good"]
        and later["central_good"]
        and earlier["valid_fraction_5x5"]
        >= MIN_VALID_FRACTION
        and later["valid_fraction_5x5"]
        >= MIN_VALID_FRACTION
    )

    if not quality_pass:
        status = "local_quality_warning"

    elif relative_mismatch <= threshold:
        status = "approximate_spectral_match"

    else:
        status = "approximate_spectral_mismatch"

    date_a = earlier.get("date_obs")
    date_b = later.get("date_obs")

    separation_days = None

    if date_a and date_b:

        try:
            timestamp_a = datetime.fromisoformat(
                date_a.replace("Z", "+00:00")
            )

            timestamp_b = datetime.fromisoformat(
                date_b.replace("Z", "+00:00")
            )

            separation_days = round(
                (
                    timestamp_b - timestamp_a
                ).total_seconds() / 86400,
                4,
            )

        except (TypeError, ValueError):
            pass

    return {

        "pair_id": (
            f"{earlier['obs_id']}_{later['obs_id']}"
        ),

        "earlier_obs_id": earlier["obs_id"],

        "later_obs_id": later["obs_id"],

        "detector": earlier["detector"],

        "earlier_file": earlier["file"],

        "later_file": later["file"],

        "date_earlier": date_a,

        "date_later": date_b,

        "separation_days": separation_days,

        "wavelength_earlier_um": lam_a,

        "wavelength_later_um": lam_b,

        "delta_lambda_um": round(
            delta_lambda, 8
        ),

        "relative_mismatch": round(
            relative_mismatch, 6
        ),

        "approximate_overlap_fraction": round(
            overlap_fraction, 6
        ),

        "local_quality_pass": bool(
            quality_pass
        ),

        "status": status,

        "spectral_calibration_verified": False,

        "wcs_registered": False,

        "ready_for_zogy": False,

        "zogy_executed": False,

        "motion_detected": False,
    }


# =====================================================
# 6. MAIN
# =====================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "MORLEY local SPHEREx spectral pair ranking"
        )
    )

    parser.add_argument(
        "--ra",
        type=float,
        default=DEFAULT_RA,
    )

    parser.add_argument(
        "--dec",
        type=float,
        default=DEFAULT_DEC,
    )

    parser.add_argument(
        "--early-year",
        type=int,
        default=2025,
    )

    parser.add_argument(
        "--late-year",
        type=int,
        default=2026,
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
    )

    args = parser.parse_args()

    if not (
        0 <= args.ra < 360
        and -90 <= args.dec <= 90
    ):
        parser.error("Invalid RA/Dec")

    if not (
        0 < args.threshold < 10
        and args.early_year < args.late_year
    ):
        parser.error(
            "Invalid comparison parameters"
        )

    print("=" * 64)
    print(
        "MORLEY — LOCAL SPECTRAL PAIR RANKING"
    )
    print("=" * 64)

    print(
        f"Target: RA={args.ra}, Dec={args.dec}"
    )

    print(
        "Data directory:",
        DATA_DIR
    )

    # -----------------------------------------
    # Discover files
    # -----------------------------------------

    inventory = discover_files()

    print(
        "\nUnique local observations:",
        len(inventory)
    )

    # -----------------------------------------
    # Inspect observations
    # -----------------------------------------

    inspected = []
    rejected = []

    for (
        obs_id, detector
    ), path in sorted(inventory.items()):

        try:

            result = inspect_fits(
                path,
                obs_id,
                detector,
                args.ra,
                args.dec,
            )

            inspected.append(result)

            print(
                f"[OK] {obs_id} {detector} "
                f"| wavelength="
                f"{result['wavelength_um']:.6f} um"
            )

        except Exception as error:

            rejected.append({

                "obs_id": obs_id,

                "detector": detector,

                "file": relative_path(path),

                "reason": (
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            })

            print(
                f"[SKIP] {obs_id} {detector}: "
                f"{error}"
            )

    print(
        "\nUsable observations:",
        len(inspected)
    )

    print(
        "Rejected observations:",
        len(rejected)
    )

    # -----------------------------------------
    # Separate epochs
    # -----------------------------------------

    early = [
        obs for obs in inspected
        if obs["year"] == args.early_year
    ]

    late = [
        obs for obs in inspected
        if obs["year"] == args.late_year
    ]

    # -----------------------------------------
    # Compare matching detectors
    # -----------------------------------------

    pairs = []

    for a in early:

        for b in late:

            if a["detector"] != b["detector"]:
                continue

            pair = compare_pairs(
                a,
                b,
                args.threshold,
            )

            pairs.append(pair)

    # Rank by:
    # 1. Local quality.
    # 2. Smallest approximate spectral mismatch.

    pairs.sort(
        key=lambda pair: (
            not pair["local_quality_pass"],
            pair["relative_mismatch"],
        )
    )

    print(
        "\nSame-detector temporal pairs:",
        len(pairs)
    )

    # -----------------------------------------
    # Show top candidates
    # -----------------------------------------

    print("\nTOP CANDIDATES")
    print("-" * 64)

    if not pairs:
        print(
            "No local temporal pairs available."
        )

    for rank, pair in enumerate(
        pairs[:10],
        start=1,
    ):

        print(
            f"{rank:02d} | "
            f"{pair['earlier_obs_id']} / "
            f"{pair['later_obs_id']} "
            f"| {pair['detector']} "
            f"| mismatch="
            f"{pair['relative_mismatch']:.4f} "
            f"| overlap="
            f"{pair['approximate_overlap_fraction']:.1%} "
            f"| status={pair['status']}"
        )

    # =================================================
    # 7. EXPORT JSON
    # =================================================

    CATALOGS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = (
        CATALOGS_DIR
        / "local_spectral_pair_ranking.json"
    )

    csv_path = (
        CATALOGS_DIR
        / "local_spectral_pair_ranking.csv"
    )

    summary = {

        "unique_observations": len(inventory),

        "usable_observations": len(inspected),

        "rejected_observations": len(rejected),

        "early_year_observations": len(early),

        "late_year_observations": len(late),

        "temporal_pairs": len(pairs),

        "approximate_matches": sum(
            p["status"]
            == "approximate_spectral_match"
            for p in pairs
        ),
    }

    payload = {

        "schema_version": (
            "morley.local_pair_ranking.v1"
        ),

        "project": "ETER / MORLEY Frontier",

        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "target": {

            "ra_deg": args.ra,

            "dec_deg": args.dec,

            "coordinate_frame": "ICRS",
        },

        "data_source": (
            "local SPHEREx Level 2 FITS"
        ),

        "evidence_type": "observed",

        "data_directory": (
            "outputs/data"
        ),

        "method": (
            "Approximate WCS-WAVE "
            "spectral comparison"
        ),

        "scientific_integrity": {

            "spectral_calibration_verified": False,

            "cwave_cband_verified": False,

            "wcs_registered": False,

            "photometric_normalization_done": False,

            "epsf_fitted": False,

            "zogy_executed": False,

            "ready_for_zogy": False,

            "motion_detected": False,

            "note": (
                "Candidate ranking only. "
                "A spectral match does not confirm "
                "motion, variability, or readiness "
                "for image subtraction."
            ),
        },

        "summary": summary,

        "files_inspected": inspected,

        "files_rejected": rejected,

        "pairs_ranked": pairs,
    }

    json_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # -----------------------------------------
    # Export compact CSV
    # -----------------------------------------

    fields = [
        "pair_id",
        "earlier_obs_id",
        "later_obs_id",
        "detector",
        "separation_days",
        "relative_mismatch",
        "approximate_overlap_fraction",
        "local_quality_pass",
        "status",
        "ready_for_zogy",
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )

        writer.writeheader()

        for pair in pairs:

            writer.writerow({
                field: pair.get(field)
                for field in fields
            })

    print("\n" + "=" * 64)
    print("SUMMARY")
    print("=" * 64)

    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\nJSON:", json_path)
    print("CSV:", csv_path)

    print(
        "\nSCIENTIFIC STATUS: "
        "SPECTRAL PRECHECK ONLY"
    )

    print("ZOGY BLOCKED")


if __name__ == "__main__":
    main()
