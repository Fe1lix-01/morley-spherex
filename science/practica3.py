"""
ETER / MORLEY Frontier
Practice 03 — Temporal Epoch Pair Selection

Input:
    Cached SPHEREx Level 2 discovery manifest.

Output:
    JSON and CSV with candidate epoch pairs.

Scientific integrity:
    - No FITS downloads.
    - No wavelength compatibility verification.
    - No WCS registration.
    - No motion detection.
    - No ZOGY execution.

The ranking prioritizes observation time separation,
NOT scientific suitability.
"""

from __future__ import annotations

import argparse
import csv
import json
import math

from datetime import datetime, timedelta, timezone
from pathlib import Path


# =====================================================
# 1. CONFIGURATION
# =====================================================

ROOT = Path(__file__).resolve().parent

CATALOGS = ROOT / "outputs" / "catalogs"

DEFAULT_MANIFEST = CATALOGS / (
    "traceback_ra295.40978_dec-15.22317_cached.json"
)

MJD_ZERO = datetime(
    1858, 11, 17,
    tzinfo=timezone.utc
)


def date_from_mjd(mjd):
    return MJD_ZERO + timedelta(days=mjd)


# =====================================================
# 2. LOAD AND VALIDATE THE INVENTORY
# =====================================================

def load_inventory(path):

    if not path.is_file():
        raise SystemExit(
            f"ERROR: Manifest not found: {path}"
        )

    manifest = json.loads(
        path.read_text(encoding="utf-8")
    )

    inventory = manifest.get("level2", {})
    status = inventory.get("status")

    if status not in {"cached_fallback", "ok"}:
        raise SystemExit(
            f"Invalid inventory status: {status}. "
            "Execute Practice 02 first."
        )

    target = manifest.get("target", {})

    if not all(
        key in target
        for key in ("ra_deg", "dec_deg")
    ):
        raise SystemExit(
            "Missing target RA/Dec."
        )

    # Cached observations must belong to
    # the exact astronomical region requested.
    if status == "cached_fallback":

        provenance = inventory.get(
            "provenance", {}
        )

        required = (
            "original_discovery_target_ra_deg",
            "original_discovery_target_dec_deg",
        )

        if not all(
            key in provenance
            for key in required
        ):
            raise SystemExit(
                "Missing cached inventory provenance."
            )

        dra = abs(
            float(target["ra_deg"])
            - float(provenance[required[0]])
        )

        ddec = abs(
            float(target["dec_deg"])
            - float(provenance[required[1]])
        )

        if dra > 1e-6 or ddec > 1e-6:
            raise SystemExit(
                "Cached inventory belongs "
                "to another sky region."
            )

    observations = []
    seen = set()

    for row in inventory.get("observations", []):

        try:
            obs_id = str(
                row["obs_id"]
            ).strip()

            mjd = float(
                row["start_mjd"]
            )

            url = str(
                row["access_url"]
            ).strip()

            detector = str(
                row.get("detector", "unknown")
            )

            if (
                not obs_id
                or not url
                or not math.isfinite(mjd)
            ):
                continue

            if obs_id in seen:
                continue

            seen.add(obs_id)

            date = date_from_mjd(mjd)

            observations.append({
                "obs_id": obs_id,
                "mjd": mjd,
                "utc": date.isoformat(),
                "year": date.year,
                "url": url,
                "detector": detector,
                "collection": row.get("collection"),
            })

        except (
            KeyError,
            TypeError,
            ValueError,
            OverflowError
        ):
            continue

    if not observations:
        raise SystemExit(
            "No valid observations found."
        )

    observations.sort(
        key=lambda row: (
            row["mjd"],
            row["obs_id"]
        )
    )

    return manifest, observations


# =====================================================
# 3. SEPARATE OBSERVING CAMPAIGNS
# =====================================================

def split_campaigns(observations, gap_days):

    groups = []

    for obs in observations:

        if (
            not groups
            or obs["mjd"] - groups[-1][-1]["mjd"]
            > gap_days
        ):
            groups.append([])

        groups[-1].append(obs)

    return groups


# =====================================================
# 4. SELECT CANDIDATE EPOCH PAIRS
# =====================================================

def make_pairs(
    early,
    later,
    min_days,
    cadence_days,
    limit,
    group_index
):

    candidates = []

    for a in early:

        for b in later:

            delta_days = (
                b["mjd"] - a["mjd"]
            )

            if delta_days < min_days:
                continue

            if a["obs_id"] == b["obs_id"]:
                continue

            # Same detector is required here,
            # but is NOT sufficient to establish
            # spectral compatibility.
            if a["detector"] != b["detector"]:
                continue

            priority = abs(
                delta_days - cadence_days
            )

            candidates.append((
                priority,
                -delta_days,
                a,
                b
            ))

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2]["obs_id"],
            item[3]["obs_id"]
        )
    )

    selected = []

    used_early = set()
    used_late = set()

    for _, _, a, b in candidates:

        # Avoid repeating the same observation
        # within each campaign's shortlist.
        if (
            a["obs_id"] in used_early
            or b["obs_id"] in used_late
        ):
            continue

        used_early.add(a["obs_id"])
        used_late.add(b["obs_id"])

        selected.append({

            "pair_id": (
                f"P{group_index:02d}_"
                f"{len(selected) + 1:02d}"
            ),

            "candidate_campaign": (
                f"{b['year']}_campaign_{group_index}"
            ),

            "earlier": {
                "obs_id": a["obs_id"],
                "mjd": a["mjd"],
                "utc": a["utc"],
                "access_url": a["url"],
                "collection": a["collection"],
                "detector": a["detector"],
            },

            "later": {
                "obs_id": b["obs_id"],
                "mjd": b["mjd"],
                "utc": b["utc"],
                "access_url": b["url"],
                "collection": b["collection"],
                "detector": b["detector"],
            },

            "separation_days": round(
                b["mjd"] - a["mjd"], 4
            ),

            "rank_basis": "time_baseline_only",

            "spectral_match": None,

            "wcs_overlap_verified": False,

            "quality_flags_checked": False,

            "variance_checked": False,

            "epsf_checked": False,

            "ready_for_zogy": False,

            "status": (
                "needs_fits_and_spectral_validation"
            ),
        })

        if len(selected) >= limit:
            break

    return len(candidates), selected


# =====================================================
# 5. MAIN
# =====================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "MORLEY temporal epoch pair preselection"
        )
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST
    )

    parser.add_argument(
        "--early-year",
        type=int,
        default=2025
    )

    parser.add_argument(
        "--late-year",
        type=int,
        default=2026
    )

    parser.add_argument(
        "--min-days",
        type=float,
        default=180
    )

    parser.add_argument(
        "--cadence-days",
        type=float,
        default=365
    )

    parser.add_argument(
        "--campaign-gap-days",
        type=float,
        default=45
    )

    parser.add_argument(
        "--max-per-campaign",
        type=int,
        default=8
    )

    args = parser.parse_args()

    if args.early_year >= args.late_year:
        parser.error(
            "The earlier year must precede "
            "the later year."
        )

    if (
        args.max_per_campaign <= 0
        or args.min_days <= 0
        or args.campaign_gap_days <= 0
    ):
        parser.error(
            "Selection limits must be positive."
        )

    # ---------------------------------------------
    # Load observations
    # ---------------------------------------------

    manifest, observations = load_inventory(
        args.manifest
    )

    early = [
        obs for obs in observations
        if obs["year"] == args.early_year
    ]

    late = [
        obs for obs in observations
        if obs["year"] == args.late_year
    ]

    if not early or not late:
        raise SystemExit(
            "Missing observations in one epoch."
        )

    # ---------------------------------------------
    # Separate observing campaigns
    # ---------------------------------------------

    campaigns = split_campaigns(
        late,
        args.campaign_gap_days
    )

    output_pairs = []
    statistics = []

    for index, group in enumerate(
        campaigns, start=1
    ):

        total, selected = make_pairs(
            early,
            group,
            args.min_days,
            args.cadence_days,
            args.max_per_campaign,
            index
        )

        statistics.append({

            "campaign": index,

            "from_utc": group[0]["utc"],

            "to_utc": group[-1]["utc"],

            "observations": len(group),

            "possible_pairs_after_metadata_filter": (
                total
            ),

            "selected_for_next_inspection": (
                len(selected)
            ),
        })

        output_pairs.extend(selected)

    if not output_pairs:
        raise SystemExit(
            "No temporal pairs meet the "
            "metadata selection criteria."
        )

    # ---------------------------------------------
    # Output filenames
    # ---------------------------------------------

    ra = float(
        manifest["target"]["ra_deg"]
    )

    dec = float(
        manifest["target"]["dec_deg"]
    )

    stem = (
        f"epoch_pairs_"
        f"ra{ra:.5f}_"
        f"dec{dec:+.5f}"
    )

    CATALOGS.mkdir(
        parents=True,
        exist_ok=True
    )

    json_path = CATALOGS / f"{stem}.json"
    csv_path = CATALOGS / f"{stem}.csv"

    # ---------------------------------------------
    # Backend JSON
    # ---------------------------------------------

    payload = {

        "schema_version": "morley.epoch_pairs.v1",

        "project": "ETER / MORLEY Frontier",

        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "target": manifest["target"],

        "source_manifest": args.manifest.name,

        "source_status": (
            manifest["level2"]["status"]
        ),

        "fresh_archive_query": False,

        "evidence_type": "archive_metadata",

        "status": "candidate_selection_only",

        "scientific_note": (
            "Pairs ranked only by time interval "
            "and matching detector. "
            "Spectral response, WCS overlap, "
            "image quality, flux scale and noise "
            "have not been verified."
        ),

        "summary": {

            "inventory_total": len(observations),

            "earlier_year": args.early_year,

            "earlier_observations": len(early),

            "later_year": args.late_year,

            "later_observations": len(late),

            "campaigns": statistics,

            "selected_pairs": len(output_pairs),
        },

        "pairs": output_pairs,

        "temporal_science": {

            "ready_for_zogy": False,

            "next_step": (
                "download_cutouts_and_validate_"
                "spectral_response"
            ),
        },
    }

    json_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # ---------------------------------------------
    # Export CSV
    # ---------------------------------------------

    fields = [
        "pair_id",
        "campaign",
        "obs_early",
        "obs_late",
        "delta_days",
        "early_url",
        "late_url",
        "status",
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )

        writer.writeheader()

        for pair in output_pairs:

            writer.writerow({

                "pair_id": pair["pair_id"],

                "campaign": (
                    pair["candidate_campaign"]
                ),

                "obs_early": (
                    pair["earlier"]["obs_id"]
                ),

                "obs_late": (
                    pair["later"]["obs_id"]
                ),

                "delta_days": (
                    pair["separation_days"]
                ),

                "early_url": (
                    pair["earlier"]["access_url"]
                ),

                "late_url": (
                    pair["later"]["access_url"]
                ),

                "status": pair["status"],
            })

    # ---------------------------------------------
    # Console report
    # ---------------------------------------------

    print("\n" + "=" * 62)
    print(
        "MORLEY — OFFLINE EPOCH PAIR PRESELECTION"
    )
    print("=" * 62)

    print(
        f"Observations: {len(observations)} "
        f"| {args.early_year}: {len(early)} "
        f"| {args.late_year}: {len(late)}"
    )

    for stat in statistics:

        print(
            f"Campaign {stat['campaign']}: "
            f"{stat['from_utc'][:10]} to "
            f"{stat['to_utc'][:10]} "
            f"| observations={stat['observations']} "
            f"| combinations="
            f"{stat['possible_pairs_after_metadata_filter']} "
            f"| selected="
            f"{stat['selected_for_next_inspection']}"
        )

    print(
        "\nCandidate pairs:",
        len(output_pairs)
    )

    for pair in output_pairs[:5]:

        print(
            f"{pair['pair_id']}: "
            f"{pair['earlier']['obs_id']} / "
            f"{pair['later']['obs_id']} "
            f"({pair['separation_days']:.1f} days)"
        )

    print("\nJSON:", json_path)
    print("CSV:", csv_path)

    print(
        "\nSCIENTIFIC STATUS: METADATA_ONLY"
    )

    print(
        "NO SPECTRAL VALIDATION — NO ZOGY"
    )


if __name__ == "__main__":
    main()