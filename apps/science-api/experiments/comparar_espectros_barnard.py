from pathlib import Path
from itertools import combinations

import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord


CARPETA = Path(r"C:\Users\XOCEA\eter-ml-data\cutouts")

BARNARD = SkyCoord(
    ra=269.44627 * u.deg,
    dec=4.76820 * u.deg,
    frame="icrs",
)

FLAGS_IMPORTANTES = {
    0: "TRANSIENT",
    1: "OVERFLOW",
    2: "SUR_ERROR",
    6: "NONFUNC",
    21: "SOURCE",
    26: "BLOOM",
}


def escalar(valor):
    return float(np.asarray(valor).reshape(-1)[0])


def explicar_flags(valor):
    activos = [
        nombre
        for bit, nombre in FLAGS_IMPORTANTES.items()
        if int(valor) & (1 << bit)
    ]
    return ", ".join(activos) if activos else "Ninguno de los seleccionados"


resultados = []

for archivo in sorted(CARPETA.glob("*.fits")):
    print("\n" + "=" * 65)
    print("ARCHIVO:", archivo.name)

    try:
        with fits.open(archivo, memmap=False) as hdul:
            header = hdul["IMAGE"].header
            imagen = np.asarray(hdul["IMAGE"].data)
            flags = np.asarray(hdul["FLAGS"].data)
            varianza = np.asarray(hdul["VARIANCE"].data)

            # WCS espacial
            spatial_wcs = WCS(header).celestial
            x, y = spatial_wcs.world_to_pixel(BARNARD)

            x = escalar(x)
            y = escalar(y)

            cx = int(round(x))
            cy = int(round(y))

            if not (0 <= cx < imagen.shape[1] and
                    0 <= cy < imagen.shape[0]):
                print("Barnard fuera de la imagen.")
                continue

            # WCS espectral oficial de SPHEREx
            spectral_wcs = WCS(
                header,
                fobj=hdul,
                key="W",
            )
            spectral_wcs.sip = None

            longitud_onda, ancho_banda = (
                spectral_wcs.pixel_to_world(x, y)
            )

            longitud_um = escalar(
                longitud_onda.to_value(u.um)
            )
            ancho_um = escalar(
                ancho_banda.to_value(u.um)
            )

            flag_central = int(flags[cy, cx])
            valor_central = float(imagen[cy, cx])
            varianza_central = float(varianza[cy, cx])

            print(f"Posicion WCS: x={x:.3f}, y={y:.3f}")
            print(f"Longitud de onda: {longitud_um:.6f} um")
            print(f"Ancho de banda: {ancho_um:.6f} um")
            print(f"Pixel central IMAGE: {valor_central}")
            print(f"Pixel central VARIANCE: {varianza_central}")
            print(f"Flag central: {flag_central}")
            print("Interpretacion:", explicar_flags(flag_central))

            resultados.append({
                "archivo": archivo.name,
                "longitud_um": longitud_um,
                "ancho_um": ancho_um,
                "flag_central": flag_central,
            })

    except Exception as exc:
        print("ERROR:", type(exc).__name__, str(exc))


print("\n" + "=" * 65)
print("COMPARACION ESPECTRAL ENTRE OBSERVACIONES")

for a, b in combinations(resultados, 2):
    diferencia = abs(
        a["longitud_um"] - b["longitud_um"]
    )

    ancho_minimo = min(
        a["ancho_um"],
        b["ancho_um"],
    )

    relacion = (
        diferencia / ancho_minimo
        if ancho_minimo > 0
        else float("nan")
    )

    print(f"\n{a['archivo']}")
    print(f"VS {b['archivo']}")
    print(f"Diferencia espectral: {diferencia:.6f} um")
    print(f"Diferencia / ancho de banda: {relacion:.3f}")
    print("Nota: esto no valida aun la comparabilidad fotometrica.")
