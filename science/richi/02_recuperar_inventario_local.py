
"""
ETER / MORLEY Frontier
Practice 02 — Offline SPHEREx Level 2 inventory recovery.

Recovers previously discovered observations when
IRSA SIA/TAP is temporarily unavailable.

IMPORTANT:
- Only valid for RA=295.4097841, Dec=-15.2231692.
- This is cached metadata, NOT a fresh archive query.
- Does not establish individual contributors to HiPS.
- Does not execute ZOGY or claim motion detection.
"""

import argparse
import csv
import json

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse


# =====================================================
# 1. CONFIGURATION
# =====================================================

ROOT = Path(__file__).resolve().parent
CATALOGS = ROOT / "outputs" / "catalogs"

INVENTORY_RA = 295.4097841
INVENTORY_DEC = -15.2231692


def iso_from_mjd(value):
    epoch = datetime(
        1858, 11, 17,
        tzinfo=timezone.utc
    )

    return (
        epoch + timedelta(days=float(value))
    ).isoformat()


# =====================================================
# 2. MAIN
# =====================================================

def main():

    parser = argparse.ArgumentParser(
        description="Recover cached SPHEREx Level 2 inventory"
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=CATALOGS / "candidatos_d6.csv"
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=CATALOGS / (
            "traceback_ra295.40978_dec-15.22317.json"
        )
    )

    args = parser.parse_args()

    if not args.csv.is_file():
        raise SystemExit(
            f"Missing inventory CSV: {args.csv}"
        )

    if not args.manifest.is_file():
        raise SystemExit(
            f"Missing traceback manifest: {args.manifest}"
        )

    # =================================================
    # 3. VALIDATE ORIGINAL TARGET
    # =================================================

    manifest = json.loads(
        args.manifest.read_text(encoding="utf-8")
    )

    target = manifest.get("target", {})

    ra = float(target.get("ra_deg", float("nan")))
    dec = float(target.get("dec_deg", float("nan")))

    if (
        abs(ra - INVENTORY_RA) > 1e-6
        or abs(dec - INVENTORY_DEC) > 1e-6
    ):
        raise SystemExit(
            "ERROR: cached inventory belongs to "
            "RA=295.4097841, Dec=-15.2231692. "
            "Cannot reuse it for another region."
        )

    # =================================================
    # 4. READ CACHED OBSERVATIONS
    # =================================================

    with args.csv.open(
        newline="",
        encoding="utf-8-sig"
    ) as file:
        rows = list(csv.DictReader(file))

    observations = []

    for n, row in enumerate(rows, 2):

        try:
            url = row["url"].strip()

            parsed = urlparse(url)

            if (
                parsed.scheme != "https"
                or parsed.netloc != "irsa.ipac.caltech.edu"
            ):
                raise ValueError(
                    "Unrecognized archive URL"
                )

            path = parsed.path.lower()

            if "/spherex/dr1/level2/" in path:
                collection = "spherex_dr1"

            elif "/spherex/qr3/level2/" in path:
                collection = "spherex_qr3"

            else:
                raise ValueError(
                    "Not a SPHEREx DR1/QR3 Level 2 file"
                )

            mjd = float(row["mjd"])
            obs_id = row["obs_id"].strip()

            if not obs_id:
                raise ValueError("Empty observation ID")

            observations.append({

                "obs_id": obs_id,
                "collection": collection,

                "detector": "SPHEREx-D6",

                "start_mjd": mjd,
                "end_mjd": None,

                "start_utc": iso_from_mjd(mjd),
                "end_utc": None,

                "access_url": url,

                "source": (
                    "SPHEREx Level 2 cached SIA discovery"
                ),

                "evidence_type": "archive_metadata",

                "verified_for_zogy": False,
                "coverage_reverified": False,
            })

        except (
            KeyError,
            TypeError,
            ValueError,
            OverflowError
        ) as error:

            raise SystemExit(
                f"Invalid CSV row {n}: {error}"
            ) from error

    if not observations:
        raise SystemExit(
            "The cached inventory is empty."
        )

    observations.sort(
        key=lambda obs: (
            obs["start_mjd"],
            obs["obs_id"]
        )
    )

    # =================================================
    # 5. PRESERVE THE SERVICE ERROR STATUS
    # =================================================

    previous_status = manifest.get(
        "level2", {}
    ).get("status", "unknown")

    manifest["level2"] = {

        "status": "cached_fallback",

        "live_query_status": previous_status,
        "live_query_succeeded": False,

        "method": "PREVIOUS_SIA_CSV_CACHE",

        "detector_filter": "SPHEREx-D6",

        "total": len(observations),
        "returned": len(observations),
        "truncated": False,

        "observations": observations,

        "provenance": {

            "source_csv": args.csv.name,

            "original_discovery_target_ra_deg": (
                INVENTORY_RA
            ),

            "original_discovery_target_dec_deg": (
                INVENTORY_DEC
            ),

            "original_query_date": "unknown",

            "requeried_at_runtime": False,

            "warning": (
                "Cached results are not fresh. "
                "They do not identify individual "
                "contributors to the HiPS cube."
            ),
        },
    }

    # =================================================
    # 6. SCIENTIFIC INTEGRITY
    # =================================================

    temporal = manifest.setdefault(
        "temporal_analysis", {}
    )

    temporal.update({

        "ready_for_zogy": False,

        "status": (
            "cached_candidates_require_validation"
        ),
    })

    manifest["scientific_integrity"] = {

        **manifest.get(
            "scientific_integrity", {}
        ),

        "analysis_executed": False,
        "motion_detected": False,

        "cached_inventory": True,
        "data_discovery_only": True,
    }

    manifest["cached_inventory_generated_at_utc"] = (
        datetime.now(timezone.utc).isoformat()
    )

    # =================================================
    # 7. EXPORT NEW MANIFEST
    # =================================================

    output = args.manifest.with_name(
        args.manifest.stem + "_cached.json"
    )

    output.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # =================================================
    # 8. REPORT
    # =================================================

    print("\n" + "=" * 60)
    print("MORLEY — OFFLINE LEVEL 2 FALLBACK")
    print("=" * 60)

    print("Source:", args.csv)

    print("Live service status:", previous_status)

    print(
        "Recovered observations:",
        len(observations)
    )

    years = sorted({
        obs["start_utc"][:4]
        for obs in observations
    })

    print("Years:", years)

    dr1 = sum(
        obs["collection"] == "spherex_dr1"
        for obs in observations
    )

    qr3 = sum(
        obs["collection"] == "spherex_qr3"
        for obs in observations
    )

    print("DR1:", dr1)
    print("QR3:", qr3)

    print("Output:", output)

    print(
        "Scientific status: CACHED_DISCOVERY_ONLY"
    )

    print("ZOGY HAS NOT BEEN EXECUTED.")


if __name__ == "__main__":
    main()
