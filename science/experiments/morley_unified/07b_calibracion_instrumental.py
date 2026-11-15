
#!/usr/bin/env python3
"""MORLEY 07B: diagnosticos instrumentales SPHEREx.

- Lee las parejas reales aprobadas en 00D, 06 y 07.
- Localiza el objetivo dentro del detector original.
- Selecciona la ePSF correspondiente a su zona.
- Revisa varianzas, FLAGS y presencia de ZODI.
- Opcionalmente lee CWAVE/CBAND de un FITS de calibracion.

No descarga datos, no ajusta la ePSF y NO ejecuta ZOGY real.
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

CATALOG = (
    ROOT / "outputs" / "catalogs"
    / "candidate_pairs_multiepoch_05.json"
)

ROUTES = (
    ROOT / "outputs" / "validations"
    / "morley_science_routes.json"
)

AUDIT = (
    ROOT / "outputs" / "validations"
    / "morley_07_audit.json"
)

OUTPUT = (
    ROOT / "outputs" / "validations"
    / "morley_07b_instrumental.json"
)


def read_json(path):
    with path.open(encoding="utf-8-sig") as file:
        return json.load(file)


def local_file(path_str):
    if not path_str or not isinstance(path_str, str):
        raise ValueError("Ruta FITS vacia")

    path = Path(path_str)

    if path.is_absolute():
        raise ValueError("Solo se permiten rutas relativas")

    path = (ROOT / path).resolve()

    if (
        not path.is_relative_to(ROOT.resolve())
        or path.suffix.lower() != ".fits"
    ):
        raise ValueError("Ruta FITS invalida")

    if not path.is_file():
        raise FileNotFoundError(
            f"No existe: {path}"
        )

    return path


def finite(value):
    try:
        number = float(value)

        if math.isfinite(number):
            return number

    except (TypeError, ValueError, OverflowError):
        pass

    return None


def spectral_maps(path):
    """Leer mapas cientificos CWAVE y CBAND opcionales."""

    if path is None:
        return None

    with fits.open(path, memmap=False) as hdul:

        if "CWAVE" not in hdul or "CBAND" not in hdul:
            raise ValueError(
                "La calibracion no contiene CWAVE/CBAND"
            )

        wave = np.asarray(
            hdul["CWAVE"].data,
            dtype=float,
        )

        band = np.asarray(
            hdul["CBAND"].data,
            dtype=float,
        )

        if (
            wave.shape != (2040, 2040)
            or band.shape != wave.shape
        ):
            raise ValueError(
                "CWAVE/CBAND no tienen forma (2040, 2040)"
            )

        return {
            "wave": wave,
            "band": band,
            "file": str(path),
        }


def inspect_one(obs, ra, dec, calibration):

    result = {
        "obs_id": obs.get("obs_id"),
        "status": "BLOCKED",
        "epsf_selected": False,
        "target_cwave_cband_sampled": False,
        "epsf_fitted": False,
        "wcs_registered_between_epochs": False,
        "notes": [],
    }

    if obs.get("status") not in (
        "existing_verified",
        "downloaded_verified",
    ):
        result["notes"].append(
            "00D no verifico este FITS"
        )
        return result

    try:
        path = local_file(obs.get("cutout_file"))

        with fits.open(path, memmap=False) as hdul:

            required = (
                "IMAGE",
                "VARIANCE",
                "FLAGS",
                "EPSF",
            )

            if any(name not in hdul for name in required):
                raise ValueError(
                    "Faltan extensiones instrumentales"
                )

            image = hdul["IMAGE"].data
            variance = hdul["VARIANCE"].data
            flags = hdul["FLAGS"].data

            if (
                image is None
                or image.ndim != 2
                or variance.shape != image.shape
                or flags.shape != image.shape
            ):
                raise ValueError(
                    "Dimensiones FITS incompatibles"
                )

            header = hdul["IMAGE"].header

            wcs = WCS(
                header,
                fobj=hdul,
            ).celestial

            x, y = map(
                float,
                wcs.world_to_pixel_values(ra, dec),
            )

            ny, nx = image.shape

            if not (
                math.isfinite(x)
                and math.isfinite(y)
                and 5 <= x < nx - 5
                and 5 <= y < ny - 5
            ):
                raise ValueError(
                    "Objetivo fuera del margen de 5 pixeles"
                )

            ix = int(round(x))
            iy = int(round(y))

            region = np.s_[
                iy - 5:iy + 6,
                ix - 5:ix + 6,
            ]

            patch = np.asarray(image[region])
            vpatch = np.asarray(variance[region])
            fpatch = np.asarray(flags[region])

            if patch.shape != (11, 11):
                raise ValueError(
                    "Parche 11x11 truncado"
                )

            good = (
                np.isfinite(patch)
                & np.isfinite(vpatch)
                & (vpatch > 0)
                & (fpatch == 0)
            )

            positive = (
                np.isfinite(vpatch)
                & (vpatch > 0)
            )

            median_variance = (
                finite(np.median(vpatch[positive]))
                if positive.any()
                else None
            )

            result.update({
                "status": "INSPECTED_NOT_CALIBRATED",
                "detector": obs.get("detector"),
                "collection": obs.get("collection"),
                "file": obs.get("cutout_file"),
                "target_cutout_xy_0based": [
                    round(x, 4),
                    round(y, 4),
                ],
                "bunit": str(
                    header.get("BUNIT", "unknown")
                ),
                "valid_fraction_11x11": round(
                    float(good.mean()), 5
                ),
                "flagged_fraction_11x11": round(
                    float(np.mean(fpatch != 0)), 5
                ),
                "median_positive_variance_11x11": (
                    median_variance
                ),
                "zodi_present_not_subtracted": (
                    "ZODI" in hdul
                ),
                "approx_wcs_wave_um": finite(
                    obs.get("wavelength_um")
                ),
                "approx_wcs_band_um": finite(
                    obs.get("bandwidth_um")
                ),
            })

            # Posicion sobre el detector original.
            # Formula documentada por IRSA:
            # x_original = 1 + x_cutout - CRPIX1A

            if (
                "CRPIX1A" not in header
                or "CRPIX2A" not in header
            ):
                result["notes"].append(
                    "Faltan CRPIX1A/CRPIX2A"
                )
                result["status"] = "BLOCKED"
                return result

            xd = (
                1.0 + x - float(header["CRPIX1A"])
            )

            yd = (
                1.0 + y - float(header["CRPIX2A"])
            )

            result["target_detector_xy_0based"] = [
                round(xd, 4),
                round(yd, 4),
            ]

            if not (
                0 <= xd < 2040
                and 0 <= yd < 2040
            ):
                result["notes"].append(
                    "Coordenadas fuera del detector padre"
                )
                result["status"] = "BLOCKED"
                return result

            # Seleccionar ePSF por zona del detector.

            table = hdul["EPSF"].data

            if table is None or not getattr(
                table, "names", None
            ):
                result["notes"].append(
                    "Tabla EPSF no legible"
                )

            else:
                columns = {
                    name.upper(): name
                    for name in table.names
                }

                required_columns = {
                    "XCENTER",
                    "YCENTER",
                    "EPSF",
                }

                if not required_columns.issubset(columns):
                    result["notes"].append(
                        "EPSF sin columnas requeridas"
                    )

                else:
                    xs = np.asarray(
                        table[columns["XCENTER"]],
                        dtype=float,
                    )

                    ys = np.asarray(
                        table[columns["YCENTER"]],
                        dtype=float,
                    )

                    distances = (
                        (xs - xd) ** 2
                        + (ys - yd) ** 2
                    )

                    if np.isfinite(distances).any():

                        index = int(
                            np.nanargmin(distances)
                        )

                        stamp = np.asarray(
                            table[columns["EPSF"]][index],
                            dtype=float,
                        )

                        if (
                            stamp.ndim == 2
                            and np.isfinite(stamp).all()
                            and np.any(stamp != 0)
                        ):
                            result["epsf_selected"] = True

                            result["epsf_zone"] = {
                                "row_0based": index,
                                "center_detector_xy": [
                                    finite(xs[index]),
                                    finite(ys[index]),
                                ],
                                "distance_to_zone_center_pix": round(
                                    float(
                                        np.sqrt(distances[index])
                                    ),
                                    4,
                                ),
                                "oversampling_xy": [
                                    hdul["EPSF"].header.get(
                                        "OVSMPX"
                                    ),
                                    hdul["EPSF"].header.get(
                                        "OVSMPY"
                                    ),
                                ],
                                "stamp_shape": list(
                                    stamp.shape
                                ),
                                "sum_oversampled": finite(
                                    stamp.sum()
                                ),
                                "zone_cwave_um_not_target": (
                                    finite(
                                        table[columns["CWAVE"]][index]
                                    )
                                    if "CWAVE" in columns
                                    else None
                                ),
                                "zone_cband_um_not_target": (
                                    finite(
                                        table[columns["CBAND"]][index]
                                    )
                                    if "CBAND" in columns
                                    else None
                                ),
                            }

                            result["notes"].append(
                                "ePSF seleccionada, no ajustada"
                            )

                        else:
                            result["notes"].append(
                                "Stamp EPSF invalido"
                            )

            # Opcional: mapa cientifico de calibracion.
            # Los mapas deben corresponder a la version
            # de procesamiento de las exposiciones.

            if calibration is not None:

                xx = int(round(xd))
                yy = int(round(yd))

                if 0 <= xx < 2040 and 0 <= yy < 2040:

                    cw = finite(
                        calibration["wave"][yy, xx]
                    )

                    cb = finite(
                        calibration["band"][yy, xx]
                    )

                    if (
                        cw is not None
                        and cb is not None
                        and cb > 0
                    ):
                        result[
                            "target_cwave_cband_sampled"
                        ] = True

                        result[
                            "cwave_um_sampled_nearest_pixel"
                        ] = cw

                        result[
                            "cband_um_sampled_nearest_pixel"
                        ] = cb

                        result["calibration_file"] = (
                            calibration["file"]
                        )

                        result["notes"].append(
                            "Mapas leidos; version aun no cotejada"
                        )

            if result["valid_fraction_11x11"] < 0.80:
                result["notes"].append(
                    "Menos de 80% de pixeles validos"
                )

    except Exception as exc:
        result["status"] = "BLOCKED"
        result["notes"].append(
            f"{type(exc).__name__}: {exc}"
        )

    return result


def main():

    parser = argparse.ArgumentParser(
        description="MORLEY 07B - Calibracion instrumental"
    )

    parser.add_argument(
        "--pair-id",
        default=None,
    )

    parser.add_argument(
        "--spectral-cal",
        type=Path,
        default=None,
        help="FITS externo con CWAVE y CBAND",
    )

    args = parser.parse_args()

    for path in (CATALOG, ROUTES, AUDIT):
        if not path.is_file():
            parser.error(
                f"Falta {path.name}. Ejecutar 00D, 06 y 07."
            )

    catalog = read_json(CATALOG)
    routes = read_json(ROUTES)
    audit = read_json(AUDIT)

    if catalog.get("target") != routes.get("target"):
        parser.error(
            "Objetivos diferentes en 00D y 06"
        )

    ra = float(
        catalog["target"]["ra_deg"]
    )

    dec = float(
        catalog["target"]["dec_deg"]
    )

    if not (
        0 <= ra < 360
        and -90 <= dec <= 90
    ):
        parser.error("RA/Dec invalidas")

    try:
        calibration = spectral_maps(
            args.spectral_cal
        )

    except Exception as exc:
        parser.error(
            f"Calibracion espectral invalida: {exc}"
        )

    observations = {
        obs["obs_id"]: obs
        for obs in catalog["observations"]
        if obs.get("obs_id")
    }

    catalog_pairs = {
        pair["pair_id"]: pair
        for pair in catalog["pairs"]
    }

    route_pairs = {
        pair["pair_id"]: pair
        for pair in routes["pair_routes"]
    }

    audit_pairs = {
        pair["pair_id"]: pair
        for pair in audit["pairs"]
    }

    if args.pair_id:
        chosen = [args.pair_id]

    else:
        chosen = [
            key
            for key, value in route_pairs.items()
            if value.get("route")
            == "TEMPORAL_CALIBRATION_CANDIDATE"
        ]

    results = []

    for pair_id in chosen:

        pair = catalog_pairs.get(pair_id)
        route = route_pairs.get(pair_id)
        previous = audit_pairs.get(pair_id)

        if (
            pair is None
            or route is None
            or previous is None
        ):
            parser.error(
                f"{pair_id}: falta resultado anterior"
            )

        ids = [
            pair["earlier"]["obs_id"],
            pair["later"]["obs_id"],
        ]

        if (
            pair.get("status")
            != "PRECHECK_PASS_NEEDS_CALIBRATION"
            or route.get("route")
            != "TEMPORAL_CALIBRATION_CANDIDATE"
            or [
                route.get("earlier_obs_id"),
                route.get("later_obs_id"),
            ] != ids
            or previous.get("obs_ids") != ids
            or previous.get("status")
            != "CALIBRATION_REQUIRED"
        ):
            parser.error(
                f"{pair_id}: reportes inconsistentes. "
                "Ejecuta nuevamente 06 y 07."
            )

        inspected = [
            inspect_one(
                observations.get(obs_id, {}),
                ra,
                dec,
                calibration,
            )
            for obs_id in ids
        ]

        reasons = [
            "Verificar procedencia de CWAVE/CBAND",
            "Validar respuesta espectral completa",
            "Registrar astrometria entre epocas",
            "Remuestrear y ajustar las ePSF",
            "Calibrar fondo y escala fotometrica",
            "Caracterizar covarianza del ruido",
        ]

        blocked = any(
            obs["status"] == "BLOCKED"
            or not obs["epsf_selected"]
            for obs in inspected
        )

        if blocked:
            reasons.insert(
                0,
                "Alguna exposicion no pudo inspeccionarse "
                "o seleccionar su ePSF"
            )

        sampled = all(
            obs["target_cwave_cband_sampled"]
            for obs in inspected
        )

        mismatch = None

        if sampled:

            wa, wb = [
                obs["cwave_um_sampled_nearest_pixel"]
                for obs in inspected
            ]

            ba, bb = [
                obs["cband_um_sampled_nearest_pixel"]
                for obs in inspected
            ]

            mismatch = abs(wa - wb) / (
                (ba + bb) / 2.0
            )

        results.append({
            "pair_id": pair_id,
            "obs_ids": ids,
            "state": (
                "AUDIT_BLOCKED"
                if blocked
                else "INSTRUMENTAL_REVIEW"
            ),
            "exposures": inspected,
            "cwave_cband_sampled_both": sampled,
            "sampled_mismatch_not_verified": finite(
                mismatch
            ),
            "blocking_reasons": reasons,
            "ready_for_real_zogy": False,
            "real_zogy_executed": False,
            "motion_claimed": False,
        })

        print(
            f"{pair_id} -> {results[-1]['state']}"
        )

        print(
            "  ePSF zonas:",
            sum(
                obs["epsf_selected"]
                for obs in inspected
            ),
            "/2",
        )

        print(
            "  CWAVE/CBAND muestreados:",
            sum(
                obs["target_cwave_cband_sampled"]
                for obs in inspected
            ),
            "/2",
        )

        for obs in inspected:
            print(
                " ",
                obs.get("obs_id"),
                "->",
                obs["status"],
                "| detector_xy:",
                obs.get(
                    "target_detector_xy_0based",
                    "N/D",
                ),
            )

    report = {
        "schema_version": (
            "morley.instrumental_review.v1"
        ),
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "target": catalog["target"],
        "evidence_type": (
            "observed_instrumental_diagnostics"
        ),
        "calibration_completed": False,
        "real_zogy_executed": False,
        "pairs": results,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    print("\nMORLEY 07B COMPLETADO")
    print("JSON:", OUTPUT)
    print(
        "ZOGY REAL: BLOQUEADO. "
        "No se ha realizado fotometria diferencial."
    )


if __name__ == "__main__":
    main()
