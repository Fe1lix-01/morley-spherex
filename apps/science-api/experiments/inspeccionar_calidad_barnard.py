from pathlib import Path         ## calcula un diagnóstico conservador de calidad e imprime la estructura de la calibración espectral

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u

CARPETA = Path(r"C:\Users\XOCEA\eter-ml-data\cutouts")

BARNARD = SkyCoord(
    ra=269.44627 * u.deg,
    dec=4.76820 * u.deg,
)

BITS = {
    0: "TRANSIENT",
    1: "OVERFLOW",
    2: "SUR_ERROR",
    6: "NONFUNC",
    7: "DICHROIC",
    9: "MISSING_DATA",
    10: "HOT",
    11: "COLD",
    14: "PHANMISS",
    15: "NONLINEAR",
    17: "PERSIST",
    19: "OUTLIER",
    20: "CROSSTALK",
    21: "SOURCE",
    22: "GHOST",
    25: "STREAK",
    26: "BLOOM",
    27: "SNOWBALL",
    28: "HALO",
    29: "SATELLITE_HALO",
}

# Mascara conservadora para diagnostico.
# SOURCE (21) es informativo, no se rechaza por defecto.
BITS_PROBLEMATICOS = [bit for bit in BITS if bit != 21]
MASCARA_MALA = sum(1 << bit for bit in BITS_PROBLEMATICOS)


def explicar_flag(valor):
    nombres = [
        nombre
        for bit, nombre in BITS.items()
        if int(valor) & (1 << bit)
    ]
    return ", ".join(nombres) if nombres else "SIN FLAGS CONOCIDOS"


for archivo in sorted(CARPETA.glob("*.fits")):
    print("\n" + "=" * 65)
    print("ARCHIVO:", archivo.name)

    try:
        with fits.open(archivo, memmap=False) as hdul:
            imagen = np.asarray(hdul["IMAGE"].data)
            flags = np.asarray(hdul["FLAGS"].data)
            varianza = np.asarray(hdul["VARIANCE"].data)

            wcs = WCS(hdul["IMAGE"].header).celestial

            x, y = wcs.world_to_pixel(BARNARD)
            x = float(np.asarray(x).item())
            y = float(np.asarray(y).item())

            print(f"Barnard (pixel): ({x:.2f}, {y:.2f})")

            cx, cy = int(round(x)), int(round(y))

            if not (0 <= cx < imagen.shape[1]
                    and 0 <= cy < imagen.shape[0]):
                print("Fuera de la imagen")
                continue

            # Region 7x7 cercana a las coordenadas.
            x0, x1 = max(0, cx - 3), min(imagen.shape[1], cx + 4)
            y0, y1 = max(0, cy - 3), min(imagen.shape[0], cy + 4)

            region = imagen[y0:y1, x0:x1]
            region_var = varianza[y0:y1, x0:x1]
            region_flags = flags[y0:y1, x0:x1].astype(np.int64)

            validos = (
                np.isfinite(region)
                & np.isfinite(region_var)
                & (region_var > 0)
            )

            sin_flags_problematicos = (
                (region_flags & MASCARA_MALA) == 0
            )

            aprovechables = validos & sin_flags_problematicos

            print("\n--- CALIDAD ---")
            print(f"Pixeles examinados: {region.size}")
            print(f"Datos y varianza validos: {validos.sum()}")
            print(
                "Sin flags problematicos:",
                sin_flags_problematicos.sum(),
            )
            print(
                "Candidatos utilizables:",
                aprovechables.sum(),
                "/",
                region.size,
            )

            valores, conteos = np.unique(
                region_flags, return_counts=True
            )

            print("\n--- FLAGS DETECTADOS ---")
            for valor, cantidad in zip(valores, conteos):
                print(
                    f"{int(valor)} ({cantidad} pixeles): "
                    f"{explicar_flag(valor)}"
                )

            print("\n--- WCS-WAVE ---")

            wave_hdu = hdul["WCS-WAVE"]
            print("Tipo:", type(wave_hdu).__name__)

            columnas = wave_hdu.columns.names
            print("Columnas:", columnas)

            for nombre in columnas:
                datos = np.asarray(wave_hdu.data[nombre][0])

                print(f"\nColumna {nombre}")
                print("Forma:", datos.shape)
                print("Tipo:", datos.dtype)
                print(
                    "Primeros valores:",
                    datos.ravel()[:8],
                )

    except Exception as exc:
        print("ERROR:", type(exc).__name__, str(exc))
