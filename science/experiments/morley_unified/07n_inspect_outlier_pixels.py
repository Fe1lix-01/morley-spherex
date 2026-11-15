
#!/usr/bin/env python3
"""MORLEY 07N: inspeccion de pixeles extremos del diagnostico 07M.

Lectura solamente: no cambia FITS, mascaras ni residuos.
Los FLAGS se muestran como numeros de bit, sin asignarles significado
instrumental salvo SOURCE (bit 21) y la mascara diagnostica de 07J.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


ROOT = Path(__file__).resolve().parent
VAL = ROOT / "outputs" / "validations"

IN_B = VAL / "morley_07b_instrumental.json"
IN_K = VAL / "morley_07k_residuals.json"
IN_M = VAL / "morley_07m_field_audit.json"

BAD_BITS = (
    0, 1, 2, 6, 7, 9, 10, 11, 14, 15,
    17, 19, 20, 22, 25, 26, 27, 28, 29,
)

BAD_MASK = sum(1 << bit for bit in BAD_BITS)
SOURCE_BIT = 1 << 21


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)

    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def safe_path(raw: str, suffix: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Ruta ausente")

    p = Path(raw)

    if p.is_absolute() or p.suffix.lower() != suffix:
        raise ValueError(
            f"Ruta relativa {suffix} requerida"
        )

    resolved = (ROOT / p).resolve()

    if (
        not resolved.is_relative_to(ROOT.resolve())
        or not resolved.is_file()
    ):
        raise FileNotFoundError(
            f"Fuera del proyecto o inexistente: {raw}"
        )

    return resolved


def choose_observation(
    report: dict,
    pair_id: str,
    epoch: int,
) -> dict:
    pair = next(
        (
            p for p in report.get("pairs", [])
            if p.get("pair_id") == pair_id
        ),
        None,
    )

    if pair is None:
        raise ValueError(
            f"No existe {pair_id} en uno de los reportes"
        )

    observations = pair.get(
        "observations",
        pair.get("exposures", []),
    )

    if len(observations) != 2:
        raise ValueError(
            f"{pair_id} no tiene dos exposiciones"
        )

    return observations[epoch - 1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MORLEY 07N: revisar residuos extremos"
    )

    parser.add_argument(
        "--pair-id",
        choices=("C001", "C002", "C003"),
        default="C002",
    )

    parser.add_argument(
        "--epoch",
        type=int,
        choices=(1, 2),
        default=2,
    )

    args = parser.parse_args()

    # Cargar reportes anteriores.
    obs = choose_observation(
        read_json(IN_B),
        args.pair_id,
        args.epoch,
    )

    prior_k = choose_observation(
        read_json(IN_K),
        args.pair_id,
        args.epoch,
    )

    prior_m = choose_observation(
        read_json(IN_M),
        args.pair_id,
        args.epoch,
    )

    obs_id = obs["obs_id"]

    # Verificar consistencia de observaciones.
    if (
        obs_id != prior_k.get("obs_id")
        or obs_id != prior_m.get("obs_id")
    ):
        raise ValueError(
            "Los IDs de 07B, 07K y 07M no coinciden"
        )

    if prior_k.get("status") != "RESIDUAL_DIAGNOSTIC_ONLY":
        raise ValueError(
            "07K no completo esta exposicion"
        )

    if prior_m.get("status") != "FIELD_AUDIT_DIAGNOSTIC_ONLY":
        raise ValueError(
            "07M no completo esta exposicion"
        )

    # Leer residuos previamente calculados.
    with np.load(
        safe_path(prior_k["array_file"], ".npz"),
        allow_pickle=False,
    ) as data:

        z = np.asarray(
            data["residual_sigma"],
            dtype=float,
        )

        valid = np.asarray(
            data["valid"],
            dtype=bool,
        )

        image_window = np.asarray(
            data["image_mjy_sr"],
            dtype=float,
        )

        predicted = np.asarray(
            data["predicted_mjy_sr"],
            dtype=float,
        )

    if (
        z.ndim != 2
        or z.shape != valid.shape
        or z.shape != image_window.shape
        or z.shape != predicted.shape
        or z.shape[0] % 2 != 1
        or z.shape[1] % 2 != 1
    ):
        raise ValueError(
            "NPZ incompatible con la ventana de 07K"
        )

    x_target, y_target = map(
        float,
        obs["target_cutout_xy_0based"],
    )

    x_start = (
        round(x_target) - z.shape[1] // 2
    )

    y_start = (
        round(y_target) - z.shape[0] // 2
    )

    top = prior_m.get(
        "largest_abs_residuals",
        [],
    )

    if not top:
        raise ValueError(
            "07M no guardo pixeles extremos"
        )

    rows = []

    # Abrir FITS original sin modificarlo.
    with fits.open(
        safe_path(obs["file"], ".fits"),
        memmap=False,
    ) as hdul:

        image = np.asarray(
            hdul["IMAGE"].data,
            dtype=float,
        )

        variance = np.asarray(
            hdul["VARIANCE"].data,
            dtype=float,
        )

        flags = np.asarray(
            hdul["FLAGS"].data,
        )

        if (
            image.ndim != 2
            or image.shape != variance.shape
            or image.shape != flags.shape
            or not np.issubdtype(
                flags.dtype,
                np.integer,
            )
        ):
            raise ValueError(
                "Extensiones IMAGE/VARIANCE/FLAGS invalidas"
            )

        wcs = WCS(
            hdul["IMAGE"].header,
            fobj=hdul,
        ).celestial

        # Mediana local para estudiar posibles
        # anomalias de escala en VARIANCE.
        local_variance = variance[
            max(0, y_start):min(
                image.shape[0],
                y_start + z.shape[0],
            ),
            max(0, x_start):min(
                image.shape[1],
                x_start + z.shape[1],
            ),
        ]

        usable_v = local_variance[
            np.isfinite(local_variance)
            & (local_variance > 0)
        ]

        median_v = (
            float(np.median(usable_v))
            if usable_v.size
            else None
        )

        # Analizar cada pixel extremo de 07M.
        for item in top:
            wx, wy = map(
                int,
                item["window_xy"],
            )

            if not (
                0 <= wy < z.shape[0]
                and 0 <= wx < z.shape[1]
            ):
                raise ValueError(
                    "Coordenada fuera de la ventana residual"
                )

            x = x_start + wx
            y = y_start + wy

            if not (
                0 <= y < image.shape[0]
                and 0 <= x < image.shape[1]
            ):
                raise ValueError(
                    "Coordenada fuera del FITS"
                )

            if not valid[wy, wx]:
                raise ValueError(
                    "07M selecciono un pixel invalido en 07K"
                )

            v = float(variance[y, x])

            # Interpretar el valor como mascara de 32 bits.
            flag = int(flags[y, x]) & 0xFFFFFFFF

            ra, dec = wcs.pixel_to_world_values(
                float(x),
                float(y),
            )

            row = {
                "window_x": wx,
                "window_y": wy,

                "cutout_x_0based": x,
                "cutout_y_0based": y,

                "distance_to_target_px": float(
                    math.hypot(
                        x - x_target,
                        y - y_target,
                    )
                ),

                "ra_deg_wcs": float(ra),
                "dec_deg_wcs": float(dec),

                "residual_sigma": float(
                    z[wy, wx]
                ),

                "image_mjy_sr": float(
                    image[y, x]
                ),

                "predicted_mjy_sr": float(
                    predicted[wy, wx]
                ),

                "variance_mjy_sr_squared": v,

                "sigma_formal_mjy_sr": (
                    float(math.sqrt(v))
                    if v > 0 and np.isfinite(v)
                    else None
                ),

                "variance_ratio_to_local_median": (
                    float(v / median_v)
                    if median_v and np.isfinite(v)
                    else None
                ),

                "flag_value_unsigned32": flag,

                "flag_active_bits": [
                    bit
                    for bit in range(32)
                    if flag & (1 << bit)
                ],

                "source_bit21": bool(
                    flag & SOURCE_BIT
                ),

                "rejected_by_07j_flag_mask": bool(
                    flag & BAD_MASK
                ),

                "in_07m_region": item.get(
                    "region"
                ),
            }

            # Comprobar consistencia entre 07K y FITS.
            row["npz_image_matches_fits"] = bool(
                np.isclose(
                    image_window[wy, wx],
                    image[y, x],
                    rtol=1e-6,
                    atol=1e-9,
                )
            )

            rows.append(row)

    # Generar reporte de auditoria.
    report = {
        "schema_version": "morley.07n.pixel_audit.v1",

        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "pair_id": args.pair_id,
        "epoch": args.epoch,
        "obs_id": obs_id,

        "local_median_variance": median_v,

        "outer_mean_z2": prior_m.get(
            "outer", {}
        ).get("mean_z2"),

        "outer_trimmed_mean_z2": prior_m.get(
            "outer_trimmed_mean_z2"
        ),

        "top5_fraction_total_chi2": prior_m.get(
            "top5_pixel_fraction_of_total_chi2"
        ),

        "pixels": rows,

        "quality_flags_diagnostic_only": True,
        "outliers_not_automatically_masked": True,
        "real_zogy_authorized": False,
    }

    dest = (
        VAL
        / f"morley_07n_{args.pair_id}_E{args.epoch}_pixel_audit.json"
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

    # Resumen en consola.
    print(
        f"{args.pair_id} / epoca {args.epoch}: {obs_id}"
    )

    for r in rows:
        ratio = r[
            "variance_ratio_to_local_median"
        ]

        ratio_text = (
            "N/D"
            if ratio is None
            else f"{ratio:.3f}"
        )

        print(
            f"  pixel=("
            f"{r['cutout_x_0based']},"
            f"{r['cutout_y_0based']}) "

            f"r={r['distance_to_target_px']:.1f}px "

            f"z={r['residual_sigma']:+.2f} "

            f"variance/mediana={ratio_text} "

            f"FLAGS={r['flag_active_bits']} "

            f"SOURCE={r['source_bit21']}"
        )

    print("JSON:", dest)
    print(
        "Sin modificar mascaras, FITS ni ZOGY"
    )


if __name__ == "__main__":
    main()
