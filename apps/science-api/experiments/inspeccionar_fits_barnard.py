from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u

DIRECTORIO = Path(
    r"C:\Users\XOCEA\eter-ml-data\cutouts"
)

BARNARD = SkyCoord(
    ra=269.44627 * u.deg,
    dec=4.76820 * u.deg,
    frame="icrs",
)

for archivo in sorted(DIRECTORIO.glob("*.fits")):
    print(f"\n{'=' * 60}")
    print("ARCHIVO:", archivo.name)

    try:
        with fits.open(archivo, memmap=False) as hdul:
            print("Extensiones:")

            for hdu in hdul:
                shape = getattr(hdu.data, "shape", None)
                print(f"  {hdu.name}: {shape}")

            imagen_hdu = hdul["IMAGE"]
            imagen = np.asarray(imagen_hdu.data)

            if imagen.ndim != 2:
                print("Imagen con dimensiones inesperadas")
                continue

            wcs = WCS(imagen_hdu.header).celestial
            x, y = wcs.world_to_pixel(BARNARD)

            # Convertir los valores de NumPy a escalares de Python
            x = float(np.asarray(x).reshape(-1)[0])
            y = float(np.asarray(y).reshape(-1)[0])

            alto, ancho = imagen.shape

            dentro = (
                np.isfinite(x)
                and np.isfinite(y)
                and 0 <= x < ancho
                and 0 <= y < alto
            )

            print(f"Tamano IMAGE: {ancho} x {alto}")
            print(f"Barnard pixel X: {x:.2f}")
            print(f"Barnard pixel Y: {y:.2f}")
            print(f"Coordenada dentro: {dentro}")

            if dentro:
                px = int(round(x))
                py = int(round(y))

                x0 = max(0, px - 3)
                x1 = min(ancho, px + 4)
                y0 = max(0, py - 3)
                y1 = min(alto, py + 4)

                region = imagen[y0:y1, x0:x1]

                print(
                    "Pixeles finitos cercanos:",
                    int(np.isfinite(region).sum()),
                    "/",
                    region.size,
                )

                if "FLAGS" in hdul:
                    flags = hdul["FLAGS"].data
                    print(
                        "Flags en region:",
                        np.unique(flags[y0:y1, x0:x1]).tolist(),
                    )

                if "VARIANCE" in hdul:
                    var = hdul["VARIANCE"].data
                    region_var = var[y0:y1, x0:x1]
                    print(
                        "Varianza finita:",
                        int(np.isfinite(region_var).sum()),
                        "/",
                        region_var.size,
                    )

    except Exception as exc:
        print("ERROR:", type(exc).__name__, str(exc))
