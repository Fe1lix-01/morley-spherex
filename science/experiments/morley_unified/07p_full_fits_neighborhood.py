#!/usr/bin/env python3
"""MORLEY 07P: inspeccion del vecindario COMPLETO en FITS L2.

Lee 07B y 07N; muestra un parche 7x7 de IMAGE y FLAGS en dos epocas.
El WCS solo relaciona direcciones; NO compara flujo calibrado ni resta imagenes.
No modifica archivos, banderas o mascaras. ZOGY real: NO.
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
VALID = ROOT / "outputs" / "validations"
BAD_BITS = (0, 1, 2, 6, 7, 9, 10, 11, 14, 15, 17, 19, 20, 22, 25, 26, 27, 28, 29)
BAD_MASK = sum(1 << bit for bit in BAD_BITS)
SOURCE_BIT = 1 << 21


def json_file(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def fitspath(raw: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Ruta FITS vacia")
    relative = Path(raw)
    if relative.is_absolute() or relative.suffix.lower() != ".fits":
        raise ValueError("Se necesita un FITS con ruta relativa")
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise FileNotFoundError(path)
    return path


def load_epoch(ob: dict) -> dict:
    with fits.open(fitspath(ob["file"]), memmap=False) as hdul:
        for name in ("IMAGE", "VARIANCE", "FLAGS"):
            if name not in hdul:
                raise ValueError(f"Falta {name} en {ob['obs_id']}")
        image = np.asarray(hdul["IMAGE"].data, dtype=float).copy()
        variance = np.asarray(hdul["VARIANCE"].data, dtype=float).copy()
        flags = np.asarray(hdul["FLAGS"].data).copy()
        wcs = WCS(hdul["IMAGE"].header, fobj=hdul).celestial
    if (image.ndim != 2 or image.shape != variance.shape or image.shape != flags.shape
            or not np.issubdtype(flags.dtype, np.integer)):
        raise ValueError(f"IMAGE, VARIANCE o FLAGS invalidos: {ob['obs_id']}")
    return {"obs_id": ob["obs_id"], "image": image, "variance": variance,
            "flags": flags, "wcs": wcs}


def flag_bits(flag: int) -> list[int]:
    return [bit for bit in range(32) if flag & (1 << bit)]


def inspect_patch(epoch: dict, x: int, y: int, radius: int) -> dict:
    image, variance, flags = epoch["image"], epoch["variance"], epoch["flags"]
    ny, nx = image.shape
    if not (0 <= x < nx and 0 <= y < ny):
        return {"status": "OUTSIDE_FITS", "center_xy": [x, y]}

    image_rows, flag_rows = [], []
    neighbors, background = [], []
    good_count = 0
    source_count = 0
    for yy in range(y - radius, y + radius + 1):
        im_row, fl_row = [], []
        for xx in range(x - radius, x + radius + 1):
            if not (0 <= xx < nx and 0 <= yy < ny):
                im_row.append("   --   ")
                fl_row.append("-")
                continue
            value = float(image[yy, xx])
            var = float(variance[yy, xx])
            flag = int(flags[yy, xx]) & 0xFFFFFFFF
            good = np.isfinite(value) and np.isfinite(var) and var > 0 and not (flag & BAD_MASK)
            im_row.append(f"{value:+8.3f}" if np.isfinite(value) else "   nan  ")
            fl_row.append("!" if flag & BAD_MASK else "S" if flag & SOURCE_BIT else ".")
            good_count += int(good)
            source_count += int(bool(flag & SOURCE_BIT))
            distance = float(np.hypot(xx - x, yy - y))
            if good and 0 < distance <= np.sqrt(2.0) + 1e-8:
                neighbors.append(value)
            if good and not (flag & SOURCE_BIT) and 2 <= distance <= radius:
                background.append(value)
        image_rows.append(" ".join(im_row))
        flag_rows.append(" ".join(fl_row))

    center = float(image[y, x])
    variance_center = float(variance[y, x])
    flag_center = int(flags[y, x]) & 0xFFFFFFFF
    median8 = float(np.median(neighbors)) if len(neighbors) >= 4 else None
    background_median = float(np.median(background)) if len(background) >= 5 else None
    return {
        "status": "FULL_FITS_PATCH_DIAGNOSTIC",
        "center_xy_0based": [x, y],
        "center_image_mjy_sr": center if np.isfinite(center) else None,
        "center_variance_mjy_sr_squared": variance_center if np.isfinite(variance_center) else None,
        "center_flag_bits": flag_bits(flag_center),
        "center_source_bit21": bool(flag_center & SOURCE_BIT),
        "eight_neighbor_count": len(neighbors),
        "eight_neighbor_median_mjy_sr": median8,
        "center_minus_eight_neighbor_median_mjy_sr": (
            float(center - median8) if median8 is not None and np.isfinite(center) else None
        ),
        "center_greater_than_all_valid_eight_neighbors": (
            bool(center > max(neighbors)) if len(neighbors) == 8 and np.isfinite(center) else None
        ),
        "unflagged_non_source_background_count": len(background),
        "background_median_mjy_sr_diagnostic": background_median,
        "usable_pixels_7x7_or_smaller": good_count,
        "source_flagged_pixels": source_count,
        "image_rows_mjy_sr_top_to_bottom": image_rows,
        "flag_rows_top_to_bottom": flag_rows,
        "flags_legend": "S=SOURCE; !=otra bandera excluida por 07J; .=sin esas banderas; -=fuera de FITS",
    }


def show(label: str, entry: dict) -> None:
    print(f"\n{label}: {entry['status']}")
    if entry["status"] != "FULL_FITS_PATCH_DIAGNOSTIC":
        return
    print(f"  Centro {entry['center_xy_0based']}; FLAGS={entry['center_flag_bits']}")
    print(f"  Diferencia contra mediana de 8 vecinos (MJy/sr): "
          f"{entry['center_minus_eight_neighbor_median_mjy_sr']}")
    print("  IMAGE original (MJy/sr), toda la vecindad:")
    for line in entry["image_rows_mjy_sr_top_to_bottom"]:
        print("   ", line)
    print("  FLAGS: S=SOURCE, !=otra bandera, .=sin bandera, -=fuera de FITS")
    for line in entry["flag_rows_top_to_bottom"]:
        print("   ", line)


def main() -> None:
    parser = argparse.ArgumentParser(description="MORLEY 07P: vecindario completo FITS")
    parser.add_argument("--pair-id", choices=("C001", "C002", "C003"), default="C002")
    parser.add_argument("--epoch", type=int, choices=(1, 2), default=2)
    parser.add_argument("--rank", type=int, choices=(1, 2, 3, 4, 5), default=1)
    parser.add_argument("--radius", type=int, choices=(2, 3, 4), default=3)
    args = parser.parse_args()

    source = json_file(VALID / "morley_07b_instrumental.json")
    audit = json_file(VALID / f"morley_07n_{args.pair_id}_E{args.epoch}_pixel_audit.json")
    pair = next((p for p in source["pairs"] if p["pair_id"] == args.pair_id), None)
    if pair is None or len(pair["exposures"]) != 2:
        raise ValueError("Par ausente o incompleto en 07B")
    epochs = pair["exposures"]
    index = args.epoch - 1
    if audit.get("obs_id") != epochs[index]["obs_id"]:
        raise ValueError("07N no corresponde a la observacion de 07B")
    if len(audit.get("pixels", [])) < args.rank:
        raise ValueError("07N no contiene el pixel solicitado")
    item = audit["pixels"][args.rank - 1]
    x, y = int(item["cutout_x_0based"]), int(item["cutout_y_0based"])

    current = load_epoch(epochs[index])
    other = load_epoch(epochs[1 - index])
    ra, dec = current["wcs"].pixel_to_world_values(float(x), float(y))
    ox, oy = other["wcs"].world_to_pixel_values(float(ra), float(dec))
    if not np.isfinite([ox, oy]).all():
        raise ValueError("Proyeccion WCS no finita")

    a = inspect_patch(current, x, y, args.radius)
    b = inspect_patch(other, round(float(ox)), round(float(oy)), args.radius)
    print(f"MORLEY 07P | {args.pair_id} E{args.epoch} | rank {args.rank}")
    print(f"07N: pixel=({x},{y}) z={item['residual_sigma']:+.2f}")
    print(f"Otra epoca: WCS=({ox:.3f},{oy:.3f}) ")
    show(f"E{args.epoch} {current['obs_id']}", a)
    show(f"E{2 if args.epoch == 1 else 1} {other['obs_id']}", b)

    dest = VALID / f"morley_07p_{args.pair_id}_E{args.epoch}_rank{args.rank}.json"
    report = {
        "schema_version": "morley.07p.full_fits_morphology.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pair_id": args.pair_id,
        "epoch": args.epoch,
        "rank": args.rank,
        "selected_residual_sigma_07n": float(item["residual_sigma"]),
        "sky_ra_dec_deg_wcs": [float(ra), float(dec)],
        "other_epoch_fractional_xy_wcs_only": [float(ox), float(oy)],
        "selected_epoch": a,
        "other_epoch": b,
        "source_bit_not_bad_pixel_proof": True,
        "comparison_of_flux_or_variability_calibrated": False,
        "real_zogy_authorized": False,
    }
    dest.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print("\nJSON:", dest)
    print("Solo diagnostico: sin cambios en FITS ni ZOGY real")


if __name__ == "__main__":
    main()
