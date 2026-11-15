"""
ETER / MORLEY Frontier
Practice 04B — Local D6 spectral comparison.

Uses real local SPHEREx Level 2 FITS.
WCS-WAVE is approximate, not science-grade calibration.
No ZOGY or motion detection is performed.
"""

from pathlib import Path
from datetime import datetime, timezone
import json

import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS


ROOT = Path(__file__).resolve().parent
FITS_DIR = ROOT / "outputs" / "data" / "recortes_morley"
CATALOGS = ROOT / "outputs" / "catalogs"

RA = 295.4097841
DEC = -15.2231692

OBSERVATIONS = {
    "2025": "2025W38_1A_0596_1D6",
    "2026": "2026W39_2A_0324_4D6",
}

# Conservative quality mask.
# SOURCE (bit 21) is not rejected.
BAD_BITS = (
    0, 1, 2, 6, 7, 9, 10, 11,
    14, 15, 17, 19, 20,
    22, 23, 24, 25, 26,
)
BAD_MASK = sum(1 << bit for bit in BAD_BITS)

MIN_VALID_FRACTION = 0.80
EXPLORATORY_THRESHOLD = 0.25


def find_fits(obs_id):
    matches = list(
        FITS_DIR.glob(f"*{obs_id}*.fits")
    )

    if not matches:
        raise FileNotFoundError(
            f"Falta el FITS {obs_id} en {FITS_DIR}"
        )

    # Prefer larger files, then validate contents.
    return max(
        matches,
        key=lambda p: p.stat().st_size
    )


def inspect_fits(path, obs_id):

    with fits.open(path, memmap=True) as hdul:

        required = (
            "IMAGE", "VARIANCE",
            "FLAGS", "WCS-WAVE", "EPSF"
        )

        for ext in required:
            if ext not in hdul:
                raise ValueError(
                    f"{path.name}: falta {ext}"
                )

        header = hdul["IMAGE"].header
        image = hdul["IMAGE"].data
        variance = hdul["VARIANCE"].data
        flags = hdul["FLAGS"].data

        if (
            image is None
            or image.ndim != 2
            or image.shape != variance.shape
            or image.shape != flags.shape
        ):
            raise ValueError(
                "Dimensiones FITS incompatibles"
            )

        detector = str(
            header.get("DETECTOR", "")
        )

        if detector and detector.upper() not in (
            "6", "D6"
        ):
            raise ValueError(
                f"Detector incorrecto: {detector}"
            )

        # --------------------------------------
        # Spatial WCS: sky coordinates -> pixel
        # --------------------------------------

        spatial = WCS(
            header,
            fobj=hdul
        ).celestial

        x, y = spatial.world_to_pixel_values(
            RA, DEC
        )

        x = float(x)
        y = float(y)

        ny, nx = image.shape
        margin = 5

        if not (
            np.isfinite(x)
            and np.isfinite(y)
            and margin <= x < nx - margin
            and margin <= y < ny - margin
        ):
            raise ValueError(
                "Objetivo fuera de la imagen "
                "o demasiado cerca del borde"
            )

        # --------------------------------------
        # Spectral WCS: pixel -> wavelength
        # --------------------------------------

        spectral = WCS(
            header=header,
            fobj=hdul,
            key="W"
        )

        # Official IRSA recommendation:
        # SIP distortion does not apply here.
        spectral.sip = None

        wavelength, bandwidth = (
            spectral.pixel_to_world(x, y)
        )

        lam = float(
            wavelength.to_value(u.um)
        )

        bw = float(
            bandwidth.to_value(u.um)
        )

        if not (
            np.isfinite(lam)
            and np.isfinite(bw)
            and bw > 0
        ):
            raise ValueError(
                "Datos WCS-WAVE inválidos"
            )

        # --------------------------------------
        # Local quality check: 5 x 5 pixels
        # --------------------------------------

        ix = int(round(x))
        iy = int(round(y))

        patch = np.asarray(
            image[iy-2:iy+3, ix-2:ix+3]
        )

        patch_var = np.asarray(
            variance[iy-2:iy+3, ix-2:ix+3]
        )

        patch_flags = np.asarray(
            flags[iy-2:iy+3, ix-2:ix+3],
            dtype=np.uint64
        )

        valid = (
            np.isfinite(patch)
            & np.isfinite(patch_var)
            & (patch_var > 0)
            & ((patch_flags & BAD_MASK) == 0)
        )

        return {
            "obs_id": obs_id,
            "filename": path.name,
            "date_obs": header.get("DATE-OBS"),
            "bunit": header.get("BUNIT"),
            "detector": detector,
            "image_shape": [ny, nx],
            "x_px": round(x, 3),
            "y_px": round(y, 3),
            "wavelength_um": round(lam, 8),
            "bandwidth_um": round(bw, 8),
            "valid_fraction_5x5": round(
                float(np.mean(valid)), 3
            ),
            "central_good": bool(valid[2, 2]),
            "central_flags": int(
                patch_flags[2, 2]
            ),
            "wavelength_method": (
                "approximate_WCS-WAVE"
            ),
        }


def main():

    print("=" * 60)
    print("MORLEY — LOCAL D6 SPECTRAL PRECHECK")
    print("=" * 60)

    print(f"RA={RA}, Dec={DEC}")

    observations = {}

    for year, obs_id in OBSERVATIONS.items():

        path = find_fits(obs_id)

        result = inspect_fits(path, obs_id)
        observations[year] = result

        print(f"\n[{year}] {path.name}")
        print("Fecha:", result["date_obs"])

        print(
            "Pixel:",
            result["x_px"],
            result["y_px"]
        )

        print(
            "Wavelength:",
            f"{result['wavelength_um']:.6f} um"
        )

        print(
            "Bandwidth:",
            f"{result['bandwidth_um']:.6f} um"
        )

        print(
            "Valid fraction:",
            result["valid_fraction_5x5"]
        )

        print(
            "Central pixel good:",
            result["central_good"]
        )

    # --------------------------------------
    # Compare spectral response
    # --------------------------------------

    a = observations["2025"]
    b = observations["2026"]

    lam_a = a["wavelength_um"]
    lam_b = b["wavelength_um"]

    bw_a = a["bandwidth_um"]
    bw_b = b["bandwidth_um"]

    delta = abs(lam_a - lam_b)

    mean_width = (bw_a + bw_b) / 2

    mismatch = delta / mean_width

    # Approximate top-hat bandpass intersection.
    overlap = max(
        0,
        min(
            lam_a + bw_a / 2,
            lam_b + bw_b / 2
        )
        - max(
            lam_a - bw_a / 2,
            lam_b - bw_b / 2
        )
    )

    overlap_fraction = (
        overlap / min(bw_a, bw_b)
    )

    quality = all(
        obs["central_good"]
        and obs["valid_fraction_5x5"]
        >= MIN_VALID_FRACTION
        for obs in observations.values()
    )

    if not quality:
        status = "quality_warning"

    elif mismatch <= EXPLORATORY_THRESHOLD:
        status = "approximate_spectral_match"

    else:
        status = "approximate_spectral_mismatch"

    # --------------------------------------
    # Create JSON for backend
    # --------------------------------------

    output = {
        "schema_version": (
            "morley.local_spectral_precheck.v1"
        ),
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "target": {
            "ra_deg": RA,
            "dec_deg": DEC,
            "frame": "ICRS"
        },
        "source": "local SPHEREx Level 2 FITS",
        "evidence_type": "observed_archive_products",
        "observations": observations,
        "comparison": {
            "delta_lambda_um": round(delta, 8),
            "spectral_mismatch": round(mismatch, 6),
            "bandpass_overlap_fraction": round(
                overlap_fraction, 6
            ),
            "quality_passed": bool(quality),
            "exploratory_threshold": (
                EXPLORATORY_THRESHOLD
            ),
            "status": status
        },
        "scientific_integrity": {
            "wavelength_method": (
                "approximate_WCS-WAVE"
            ),
            "cwave_cband_verified": False,
            "wcs_registered": False,
            "epsf_fitted": False,
            "zogy_executed": False,
            "ready_for_zogy": False,
            "motion_detected": False
        }
    }

    CATALOGS.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        CATALOGS /
        "local_pair_d6_spectral_precheck.json"
    )

    output_path.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("SPECTRAL COMPARISON")
    print("=" * 60)

    print(
        f"Delta wavelength: {delta:.6f} um"
    )

    print(
        f"Mismatch: {mismatch:.4f}"
    )

    print(
        f"Approximate overlap: "
        f"{overlap_fraction:.1%}"
    )

    print("Quality passed:", quality)
    print("Status:", status)
    print("Ready for ZOGY: False")
    print("JSON:", output_path)


if __name__ == "__main__":
    main()