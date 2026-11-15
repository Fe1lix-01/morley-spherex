from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u

CARPETA = Path(r"C:\Users\XOCEA\eter-ml-data\cutouts")
SALIDA = Path(r"C:\Users\XOCEA\eter-ml-data\imagenes")
SALIDA.mkdir(parents=True, exist_ok=True)

REFERENCIA = CARPETA / "barnard_2026W34_1A_0363_1_D2.fits"
SCIENCE = CARPETA / "barnard_2026W39_1A_0371_1_D2.fits"

OBJETO = SkyCoord(
    ra=269.44627 * u.deg,
    dec=4.76820 * u.deg,
    frame="icrs",
)

TAMANO = 63

# Banderas que descartamos para la vista exploratoria.
# El bit SOURCE no se descarta por sí mismo.
BITS_MALOS = [
    0, 1, 2, 6, 7, 9, 10, 11, 14, 15,
    17, 19, 20, 22, 25, 26, 27, 28, 29,
]
MASCARA_MALA = sum(1 << bit for bit in BITS_MALOS)


def cargar(ruta):
    with fits.open(ruta, memmap=False) as h:
        imagen = np.asarray(h["IMAGE"].data, dtype=float)
        varianza = np.asarray(h["VARIANCE"].data, dtype=float)
        flags = np.asarray(h["FLAGS"].data, dtype=np.int64)

        wcs = WCS(h["IMAGE"].header).celestial

        valido = (
            np.isfinite(imagen)
            & np.isfinite(varianza)
            & (varianza > 0)
            & ((flags & MASCARA_MALA) == 0)
        )

        x, y = wcs.world_to_pixel(OBJETO)
        x = float(np.asarray(x).item())
        y = float(np.asarray(y).item())

        return {
            "imagen": imagen,
            "valido": valido,
            "wcs": wcs,
            "x": x,
            "y": y,
        }


def interpolar_bilineal(datos, x, y):
    alto, ancho = datos.shape

    ix = np.floor(x).astype(int)
    iy = np.floor(y).astype(int)

    dentro = (
        np.isfinite(x)
        & np.isfinite(y)
        & (ix >= 0)
        & (iy >= 0)
        & (ix + 1 < ancho)
        & (iy + 1 < alto)
    )

    ix_seg = np.clip(ix, 0, ancho - 2)
    iy_seg = np.clip(iy, 0, alto - 2)

    dx = x - ix
    dy = y - iy

    a = datos[iy_seg, ix_seg]
    b = datos[iy_seg, ix_seg + 1]
    c = datos[iy_seg + 1, ix_seg]
    d = datos[iy_seg + 1, ix_seg + 1]

    valores = (
        a * (1 - dx) * (1 - dy)
        + b * dx * (1 - dy)
        + c * (1 - dx) * dy
        + d * dx * dy
    )

    # Evitar NaN en regiones validas por vecinos invalidos.
    valores = np.where(dentro, valores, np.nan)

    return valores, dentro, (ix_seg, iy_seg)


ref = cargar(REFERENCIA)
sci = cargar(SCIENCE)

# Cuadricula de 63x63 centrada en Barnard,
# definida en los pixeles de la referencia.
x0 = int(round(ref["x"])) - TAMANO // 2
y0 = int(round(ref["y"])) - TAMANO // 2

alto, ancho = ref["imagen"].shape

if (
    x0 < 0 or y0 < 0
    or x0 + TAMANO > ancho
    or y0 + TAMANO > alto
):
    raise RuntimeError("El recorte de referencia no cabe en el FITS.")

yy, xx = np.mgrid[
    y0:y0 + TAMANO,
    x0:x0 + TAMANO,
]

ref_img = ref["imagen"][
    y0:y0 + TAMANO,
    x0:x0 + TAMANO,
]

ref_valid = ref["valido"][
    y0:y0 + TAMANO,
    x0:x0 + TAMANO,
]

# Transformar cada pixel de referencia al cielo
# y del cielo a pixeles de la observacion Science.
coords_cielo = ref["wcs"].pixel_to_world(xx, yy)
sx, sy = sci["wcs"].world_to_pixel(coords_cielo)

sx = np.asarray(sx, dtype=float)
sy = np.asarray(sy, dtype=float)

# Solo interpolamos pixeles validos; los demas quedan NaN.
imagen_segura = np.where(
    sci["valido"],
    sci["imagen"],
    np.nan,
)

sci_img, dentro, _ = interpolar_bilineal(
    imagen_segura, sx, sy
)

# Se requieren datos finitos en ambas observaciones.
validos = (
    dentro
    & ref_valid
    & np.isfinite(ref_img)
    & np.isfinite(sci_img)
)

ref_final = np.where(validos, ref_img, np.nan)
sci_final = np.where(validos, sci_img, np.nan)

# Resta exploratoria, NO ZOGY ni diferencia calibrada.
diferencia = sci_final - ref_final

central_valido = bool(validos[TAMANO // 2, TAMANO // 2])
cantidad = int(validos.sum())
total = validos.size

print("Pixeles comparables:", cantidad, "/", total)
print("Fraccion comparable:", f"{cantidad / total:.2%}")
print("Pixel central utilizable:", central_valido)

npz = SALIDA / "barnard_triplete_real_exploratorio.npz"

np.savez_compressed(
    npz,
    science_masked=sci_final,
    reference_masked=ref_final,
    difference_masked=diferencia,
    valid_mask=validos,
    scientifically_validated=False,
)

print("Datos guardados:", npz)

if cantidad == 0:
    raise SystemExit("No hay pixeles comparables para visualizar.")

try:
    import matplotlib.pyplot as plt
except ImportError:
    raise SystemExit(
        "Se guardo el NPZ, pero falta matplotlib para crear el PNG."
    )

valores = np.concatenate([
    ref_final[np.isfinite(ref_final)],
    sci_final[np.isfinite(sci_final)],
])

vmin, vmax = np.percentile(valores, [2, 98])
maxdiff = max(
    float(np.percentile(np.abs(diferencia[validos]), 98)),
    1e-6,
)

fig, axes = plt.subplots(1, 3, figsize=(13, 4))

axes[0].imshow(
    np.ma.masked_invalid(ref_final),
    cmap="gray",
    origin="lower",
    vmin=vmin,
    vmax=vmax,
)

axes[1].imshow(
    np.ma.masked_invalid(sci_final),
    cmap="gray",
    origin="lower",
    vmin=vmin,
    vmax=vmax,
)

axes[2].imshow(
    np.ma.masked_invalid(diferencia),
    cmap="bwr",
    origin="lower",
    vmin=-maxdiff,
    vmax=maxdiff,
)

titulos = [
    "Reference - 18 Ago",
    "Science - 22 Sep",
    "Difference - Exploratoria",
]

for ax, titulo in zip(axes, titulos):
    ax.set_title(titulo)
    ax.set_xlabel("Pixel X")
    ax.set_ylabel("Pixel Y")

fig.suptitle(
    "SPHEREx D2 - Barnard | WCS alineado, pixeles enmascarados"
)

fig.tight_layout()

png = SALIDA / "barnard_triplete_real_exploratorio.png"
fig.savefig(png, dpi=160)
plt.close(fig)

print("Imagen guardada:", png)

if not central_valido:
    print(
        "ADVERTENCIA: pixel central no valido. "
        "NO usar esta resta para afirmar variabilidad o movimiento."
    )

print(
    "NO enviar este triplete a la CNN como una deteccion "
    "cientificamente validada."
)
