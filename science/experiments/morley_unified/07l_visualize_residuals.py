
#!/usr/bin/env python3
"""MORLEY 07L - visualizacion de residuos calculados por 07K.

No modifica FITS, no registra imagenes,
no resta epocas y no ejecuta ZOGY real.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    import matplotlib.pyplot as plt
except ImportError as exc:
    raise SystemExit(
        "Falta matplotlib. Instala con: "
        "..\\.venv\\Scripts\\python.exe -m pip install matplotlib"
    ) from exc


ROOT = Path(__file__).resolve().parent
VAL = ROOT / "outputs" / "validations"

INPUT = VAL / "morley_07k_residuals.json"
FIGURES = VAL / "figures_07l"
OUTPUT = VAL / "morley_07l_visual_summary.json"


def safe_npz(value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Falta ruta .npz en 07K")

    relative = Path(value)

    if relative.is_absolute() or relative.suffix.lower() != ".npz":
        raise ValueError("Ruta NPZ invalida")

    full = (ROOT / relative).resolve()

    if not full.is_relative_to(ROOT.resolve()) or not full.is_file():
        raise FileNotFoundError(
            f"NPZ no encontrado dentro del proyecto: {value}"
        )

    return full


def load_residuals(
    observation: dict,
) -> tuple[np.ndarray, np.ndarray]:

    if observation.get("status") != "RESIDUAL_DIAGNOSTIC_ONLY":
        raise ValueError("07K no termino esta exposicion")

    if observation.get("chi2_reproduced") is not True:
        raise ValueError("07K no pudo reproducir chi2 de 07J")

    path = safe_npz(observation.get("array_file"))

    with np.load(path, allow_pickle=False) as archive:
        z = np.asarray(
            archive["residual_sigma"], dtype=float
        )
        valid = np.asarray(
            archive["valid"], dtype=bool
        )

    if (
        z.ndim != 2
        or z.shape != valid.shape
        or min(z.shape) < 3
    ):
        raise ValueError("Dimensiones de residuales invalidas")

    if valid.sum() < 10 or not np.isfinite(z[valid]).all():
        raise ValueError("Insuficientes residuos finitos")

    return z, valid


def format_num(value, decimals=3):
    if value is None:
        return "N/D"

    return f"{float(value):.{decimals}f}"


def plot_pair(pair: dict, scale: float, dpi: int) -> dict:

    records = pair.get("observations", [])

    if len(records) != 2:
        raise ValueError(
            "Se requieren dos exposiciones por pareja"
        )

    arrays = [
        load_residuals(item)
        for item in records
    ]

    fig, axs = plt.subplots(
        2, 2,
        figsize=(11, 8),
        constrained_layout=True,
    )

    colormap = plt.get_cmap("RdBu_r").copy()
    colormap.set_bad("#777777")

    heatmap = None
    stats = []

    for index, (record, (z, good)) in enumerate(
        zip(records, arrays)
    ):
        heatmap = axs[0, index].imshow(
            np.ma.masked_where(~good, z),
            origin="lower",
            interpolation="nearest",
            cmap=colormap,
            vmin=-scale,
            vmax=scale,
        )

        axs[0, index].set_title(
            f"{record['obs_id']}\n"
            f"chi2 reducido = "
            f"{format_num(record.get('chi2_reduced_recomputed'))}"
        )

        axs[0, index].set_xlabel("X (pixel de ventana)")
        axs[0, index].set_ylabel("Y (pixel de ventana)")

        values = z[good]

        limit = max(
            5.0,
            float(np.ceil(np.max(np.abs(values)))),
        )

        bins = np.linspace(
            -limit, limit, 31
        )

        axs[1, index].hist(
            values,
            bins=bins,
            density=True,
            alpha=0.65,
            label="Residuos validos",
        )

        x = np.linspace(-limit, limit, 300)

        gaussian = (
            np.exp(-0.5 * x**2)
            / np.sqrt(2.0 * np.pi)
        )

        axs[1, index].plot(
            x,
            gaussian,
            "k--",
            label="N(0,1), referencia",
        )

        axs[1, index].set_xlabel(
            "Residual / sigma del FITS"
        )

        axs[1, index].set_ylabel(
            "Densidad descriptiva"
        )

        axs[1, index].legend(fontsize=8)

        core = record.get(
            "mean_squared_residual_core_r_le_3px"
        )

        outer = record.get(
            "mean_squared_residual_outer_r_gt_3px"
        )

        axs[1, index].set_title(
            f"N={int(good.sum())}; "
            f"std={np.std(values, ddof=1):.2f}\n"
            f"media z² nucleo={format_num(core)}; "
            f"exterior={format_num(outer)}",
            fontsize=10,
        )

        stats.append({
            "obs_id": record["obs_id"],
            "chi2_reduced_07k": record.get(
                "chi2_reduced_recomputed"
            ),
            "core_mean_z2": core,
            "outer_mean_z2": outer,
            "neighbor_x_corr": record.get(
                "neighbor_x", {}
            ).get("correlation"),
            "neighbor_y_corr": record.get(
                "neighbor_y", {}
            ).get("correlation"),
            "valid_pixels": int(good.sum()),
        })

    fig.colorbar(
        heatmap,
        ax=list(axs[0, :]),
        shrink=0.78,
        label="Residuo normalizado (sigma)",
    )

    fig.suptitle(
        f"MORLEY 07L | {pair['pair_id']} "
        "| residuos de ePSF (SIN ZOGY)",
        fontsize=13,
    )

    FIGURES.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = FIGURES / f"{pair['pair_id']}_residuals.png"

    fig.savefig(path, dpi=dpi)
    plt.close(fig)

    return {
        "pair_id": pair["pair_id"],
        "status": "VISUAL_DIAGNOSTIC_ONLY",
        "png": str(path.relative_to(ROOT)),
        "observations": stats,
        "real_zogy_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MORLEY 07L - graficas de residuos"
    )

    parser.add_argument(
        "--pair-id",
        choices=["C001", "C002", "C003"],
    )

    parser.add_argument(
        "--scale",
        type=float,
        default=4.0,
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=160,
    )

    args = parser.parse_args()

    if (
        not np.isfinite(args.scale)
        or args.scale <= 0
        or not 75 <= args.dpi <= 400
    ):
        parser.error(
            "--scale y --dpi deben ser validos"
        )

    if not INPUT.is_file():
        parser.error(
            "Falta morley_07k_residuals.json; "
            "ejecuta 07K primero"
        )

    report = json.loads(
        INPUT.read_text(encoding="utf-8-sig")
    )

    summaries = []

    for pair in report.get("pairs", []):
        if (
            args.pair_id
            and pair.get("pair_id") != args.pair_id
        ):
            continue

        if pair.get("status") != "RESIDUALS_COMPUTED":
            print(
                pair.get("pair_id"),
                "-> omitido: 07K incompleto",
            )
            continue

        try:
            summary = plot_pair(
                pair,
                args.scale,
                args.dpi,
            )

        except (
            ValueError,
            KeyError,
            FileNotFoundError,
            OSError,
        ) as exc:
            print(
                pair.get("pair_id"),
                "-> ERROR:",
                exc,
            )

            summaries.append({
                "pair_id": pair.get("pair_id"),
                "status": "ERROR",
                "error": str(exc),
            })
            continue

        summaries.append(summary)

        print(
            pair["pair_id"],
            "->",
            summary["png"],
        )

        for obs in summary["observations"]:
            print(
                " ",
                obs["obs_id"],
                "| z2 nucleo:",
                format_num(obs["core_mean_z2"]),
                "| z2 exterior:",
                format_num(obs["outer_mean_z2"]),
                "| corr X/Y:",
                format_num(obs["neighbor_x_corr"]),
                format_num(obs["neighbor_y_corr"]),
            )

    if not summaries:
        parser.error(
            "No hubo parejas validas para visualizar"
        )

    payload = {
        "schema_version": "morley.07l.visual.v1",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source": str(
            INPUT.relative_to(ROOT)
        ),
        "visualization_is_not_scientific_validation": True,
        "real_zogy_authorized": False,
        "pairs": summaries,
    }

    OUTPUT.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nResumen:", OUTPUT)
    print(
        "Registro, calibracion fisica y "
        "ZOGY real: PENDIENTES"
    )


if __name__ == "__main__":
    main()
