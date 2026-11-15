
#!/usr/bin/env python3
"""MORLEY 07O: vecindario y correspondencia WCS de residuos extremos.

Utiliza 07B, 07K y 07M mas los FITS ya disponibles.
SOLO diagnostico: no edita FITS, no suprime pixeles, no mide
variabilidad ni autoriza ZOGY real.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


ROOT = Path(__file__).resolve().parent
VAL = ROOT / "outputs" / "validations"

SOURCE = VAL / "morley_07b_instrumental.json"
RESIDUAL = VAL / "morley_07k_residuals.json"
OUTLIERS = VAL / "morley_07m_field_audit.json"

SOURCE_BIT = 1 << 21


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def safe_file(raw: str, suffix: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Ruta de archivo vacia")

    path = Path(raw)

    if path.is_absolute() or path.suffix.lower() != suffix:
        raise ValueError(f"Se requiere ruta relativa {suffix}")

    full = (ROOT / path).resolve()

    if (
        not full.is_relative_to(ROOT.resolve())
        or not full.is_file()
    ):
        raise FileNotFoundError(full)

    return full


def pair_from(report: dict, pair_id: str) -> dict:
    match = next(
        (
            p for p in report.get("pairs", [])
            if p.get("pair_id") == pair_id
        ),
        None,
    )

    if match is None:
        raise ValueError(f"No existe {pair_id} en un reporte")

    return match


def load_epoch(ob: dict, residual: dict) -> dict:
    if residual.get("obs_id") != ob.get("obs_id"):
        raise ValueError("ID no coincide entre 07B y 07K")

    if residual.get("status") != "RESIDUAL_DIAGNOSTIC_ONLY":
        raise ValueError("07K no valido para esta exposicion")

    with fits.open(
        safe_file(ob["file"], ".fits"),
        memmap=False,
    ) as hdul:

        image = np.asarray(
            hdul["IMAGE"].data,
            dtype=float,
        ).copy()

        flags = np.asarray(
            hdul["FLAGS"].data,
        ).copy()

        variance = np.asarray(
            hdul["VARIANCE"].data,
            dtype=float,
        ).copy()

        wcs = WCS(
            hdul["IMAGE"].header,
            fobj=hdul,
        ).celestial

    with np.load(
        safe_file(residual["array_file"], ".npz"),
        allow_pickle=False,
    ) as data:

        z = np.asarray(
            data["residual_sigma"],
            dtype=float,
        ).copy()

        good = np.asarray(
            data["valid"],
            dtype=bool,
        ).copy()

    if (
        image.ndim != 2
        or variance.shape != image.shape
        or flags.shape != image.shape
    ):
        raise ValueError("Dimensiones FITS incompatibles")

    if (
        z.ndim != 2
        or z.shape != good.shape
        or not np.issubdtype(flags.dtype, np.integer)
    ):
        raise ValueError("NPZ o FLAGS invalidos")

    if (
        z.shape[0] % 2 != 1
        or z.shape[1] % 2 != 1
    ):
        raise ValueError("Ventana de residuos no es impar")

    xc, yc = map(
        float,
        ob["target_cutout_xy_0based"],
    )

    origin_x = round(xc) - z.shape[1] // 2
    origin_y = round(yc) - z.shape[0] // 2

    return {
        "obs_id": ob["obs_id"],
        "image": image,
        "flags": flags,
        "variance": variance,
        "wcs": wcs,
        "z": z,
        "good": good,
        "origin_xy": (origin_x, origin_y),
    }


def value_at(epoch: dict, x: int, y: int) -> dict | None:
    image = epoch["image"]

    if (
        x < 0
        or y < 0
        or y >= image.shape[0]
        or x >= image.shape[1]
    ):
        return None

    wx = x - epoch["origin_xy"][0]
    wy = y - epoch["origin_xy"][1]

    inside = (
        0 <= wx < epoch["z"].shape[1]
        and 0 <= wy < epoch["z"].shape[0]
    )

    valid_z = bool(
        inside
        and epoch["good"][wy, wx]
        and np.isfinite(epoch["z"][wy, wx])
    )

    flag = int(epoch["flags"][y, x]) & 0xFFFFFFFF
    variance = float(epoch["variance"][y, x])
    value = float(image[y, x])

    return {
        "xy_0based": [x, y],
        "z": (
            float(epoch["z"][wy, wx])
            if valid_z else None
        ),
        "valid_07k": valid_z,
        "in_residual_window": inside,
        "image_mjy_sr": (
            value if np.isfinite(value) else None
        ),
        "variance_mjy_sr_squared": (
            variance if np.isfinite(variance) else None
        ),
        "flag_active_bits": [
            bit
            for bit in range(32)
            if flag & (1 << bit)
        ],
        "source_bit21": bool(flag & SOURCE_BIT),
    }


def neighborhood(
    epoch: dict,
    x: int,
    y: int,
    radius: int,
) -> dict:

    rows = []
    patch = []

    for py in range(y - radius, y + radius + 1):
        row = []
        print_row = []

        for px in range(x - radius, x + radius + 1):
            item = value_at(epoch, px, py)

            row.append(item)

            if item is None or item["z"] is None:
                print_row.append("   --")
            else:
                print_row.append(
                    f"{item['z']:+5.1f}"
                )

        rows.append(row)
        patch.append(" ".join(print_row))

    center = value_at(epoch, x, y)

    neighbors = [
        cell
        for row in rows
        for cell in row
        if (
            cell is not None
            and cell["xy_0based"] != [x, y]
            and cell["z"] is not None
        )
    ]

    significant = [
        cell
        for cell in neighbors
        if abs(cell["z"]) >= 2.5
    ]

    center_sign = (
        np.sign(center["z"])
        if center is not None and center["z"] is not None
        else 0
    )

    same_sign = [
        cell
        for cell in significant
        if np.sign(cell["z"]) == center_sign
    ]

    return {
        "center": center,
        "radius_pixels": radius,
        "neighbors_with_abs_z_ge_2_5": len(significant),
        "same_sign_extreme_neighbors": len(same_sign),
        "neighborhood_source_flagged_count": sum(
            cell is not None and cell["source_bit21"]
            for row in rows
            for cell in row
        ),
        "residual_grid_rows_top_to_bottom": patch,
        "pixel_records": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "MORLEY 07O: vecindario de outliers y otra epoca"
        )
    )

    parser.add_argument(
        "--pair-id",
        choices=("C001", "C002", "C003"),
        default="C002",
    )

    parser.add_argument(
        "--epoch",
        choices=(1, 2),
        type=int,
        default=2,
    )

    parser.add_argument(
        "--radius",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--top",
        type=int,
        default=3,
    )

    args = parser.parse_args()

    if not 1 <= args.radius <= 3:
        parser.error("--radius debe estar entre 1 y 3")

    if not 1 <= args.top <= 5:
        parser.error("--top debe estar entre 1 y 5")

    source = pair_from(
        read_json(SOURCE),
        args.pair_id,
    )

    residual = pair_from(
        read_json(RESIDUAL),
        args.pair_id,
    )

    outliers = pair_from(
        read_json(OUTLIERS),
        args.pair_id,
    )

    obs_b = source["exposures"]
    obs_k = residual["observations"]
    obs_m = outliers["observations"]

    if any(
        len(group) != 2
        for group in (obs_b, obs_k, obs_m)
    ):
        raise ValueError(
            "Una pareja debe contener dos epocas"
        )

    for k in range(2):
        if (
            obs_b[k]["obs_id"] != obs_k[k]["obs_id"]
            or obs_b[k]["obs_id"] != obs_m[k]["obs_id"]
        ):
            raise ValueError(
                "IDs 07B/07K/07M no coinciden"
            )

    idx = args.epoch - 1
    other_idx = 1 - idx

    selected = load_epoch(
        obs_b[idx],
        obs_k[idx],
    )

    other = load_epoch(
        obs_b[other_idx],
        obs_k[other_idx],
    )

    tops = obs_m[idx].get(
        "largest_abs_residuals",
        [],
    )[:args.top]

    if not tops:
        raise ValueError(
            "07M no contiene pixeles extremos"
        )

    total_chi2 = float(
        np.sum(
            selected["z"][selected["good"]] ** 2
        )
    )

    entries = []

    print(
        f"{args.pair_id} | epoca {args.epoch} "
        f"| {selected['obs_id']}"
    )

    print(
        f"Otra epoca: {other['obs_id']}"
    )

    for rank, item in enumerate(tops, start=1):
        wx, wy = map(
            int,
            item["window_xy"],
        )

        x = wx + selected["origin_xy"][0]
        y = wy + selected["origin_xy"][1]

        current = neighborhood(
            selected, x, y, args.radius
        )

        center = current["center"]

        if center is None or center["z"] is None:
            raise ValueError(
                f"Pixel {x},{y} no valido en 07K"
            )

        ra, dec = selected[
            "wcs"
        ].pixel_to_world_values(
            float(x),
            float(y),
        )

        mx, my = other[
            "wcs"
        ].world_to_pixel_values(
            float(ra),
            float(dec),
        )

        if np.isfinite([mx, my]).all():
            ox = round(float(mx))
            oy = round(float(my))

            other_local = neighborhood(
                other,
                ox,
                oy,
                args.radius,
            )

            other_xy = [
                float(mx),
                float(my),
            ]
        else:
            other_local = None
            other_xy = None

        contribution = (
            center["z"] ** 2 / total_chi2
            if total_chi2 > 0
            else None
        )

        entries.append({
            "rank": rank,
            "selected_epoch_pixel_xy_0based": [
                x, y
            ],
            "sky_ra_dec_deg_wcs_only": [
                float(ra),
                float(dec),
            ],
            "selected_epoch": current,
            "other_epoch_predicted_xy_0based_wcs_only": (
                other_xy
            ),
            "other_epoch_nearest_pixel": other_local,
            "fraction_of_total_window_chi2": (
                contribution
            ),
            "same_sky_flux_or_variability_comparison_performed": (
                False
            ),
        })

        print(
            f"\n  #{rank} pixel=({x},{y}) "
            f"z={center['z']:+.2f} "
            f"SOURCE={center['source_bit21']} "
            f"aporte chi2={contribution:.1%}"
        )

        print(
            "  Vecinos |z|>=2.5:",
            current["neighbors_with_abs_z_ge_2_5"],
            "| mismo signo:",
            current["same_sign_extreme_neighbors"],
        )

        print(
            "  Residuo por pixel, epoca seleccionada:"
        )

        for line in current[
            "residual_grid_rows_top_to_bottom"
        ]:
            print("   ", line)

        if other_local is not None:
            other_center = other_local["center"]

            other_z = (
                None
                if other_center is None
                else other_center["z"]
            )

            print(
                "  Misma direccion segun WCS:",
                f"({mx:.2f}, {my:.2f})",
                "| z otra epoca:",
                other_z,
            )

            for line in other_local[
                "residual_grid_rows_top_to_bottom"
            ]:
                print("   ", line)

        else:
            print(
                "  Misma direccion no proyectable "
                "en la otra epoca"
            )

    report = {
        "schema_version": "morley.07o.neighborhood.v1",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "pair_id": args.pair_id,
        "selected_epoch": args.epoch,
        "selected_obs_id": selected["obs_id"],
        "other_obs_id": other["obs_id"],
        "wcs_cross_epoch_is_not_independent_astrometry": True,
        "unmodelled_spectral_and_photometric_changes": True,
        "outliers_masked_or_removed": False,
        "real_zogy_authorized": False,
        "parameters": vars(args),
        "pixels": entries,
    }

    dest = (
        VAL
        / f"morley_07o_{args.pair_id}_E{args.epoch}_neighbors.json"
    )

    dest.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    print("\nJSON:", dest)
    print(
        "Diagnostico exclusivamente. "
        "FITS y mascaras sin cambios. "
        "ZOGY real: NO"
    )


if __name__ == "__main__":
    main()
