from pathlib import Path
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

BASE = Path(__file__).resolve().parent
FOLDER = BASE / "outputs" / "data" / "recortes_morley"

RA = 295.4097841
DEC = -15.2231692

files = sorted(FOLDER.rglob("*.fits"))

print("=" * 60)
print("MORLEY — LOCAL FITS INSPECTION")
print("=" * 60)

if not files:
    raise SystemExit("No se encontraron archivos FITS.")

for path in files:
    if "D6" not in path.name:
        continue

    print(f"\nArchivo: {path.name}")

    try:
        with fits.open(path, memmap=False) as hdul:
            print("Extensiones:", [
                h.name for h in hdul
            ])

            if "IMAGE" not in hdul:
                print("Estado: sin extensión IMAGE")
                continue

            image = hdul["IMAGE"]
            data = image.data

            if data is None or data.ndim != 2:
                print("Estado: imagen 2D no disponible")
                continue

            wcs = WCS(
                image.header,
                fobj=hdul
            ).celestial

            x, y = wcs.world_to_pixel_values(
                RA, DEC
            )

            ny, nx = data.shape

            inside = (
                np.isfinite(x)
                and np.isfinite(y)
                and 0 <= x < nx
                and 0 <= y < ny
            )

            print("Dimensiones:", data.shape)
            print("Fecha:", image.header.get(
                "DATE-OBS", "No disponible"
            ))
            print(f"Posición: x={x:.2f}, y={y:.2f}")
            print("Cubre RA/Dec:", bool(inside))

            for ext in ("VARIANCE", "FLAGS",
                        "WCS-WAVE", "EPSF"):
                print(
                    f"{ext}:",
                    "Sí" if ext in hdul else "No"
                )

    except Exception as error:
        print(
            "Error:",
            type(error).__name__,
            str(error)
        )