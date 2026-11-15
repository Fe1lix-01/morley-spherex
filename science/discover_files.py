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