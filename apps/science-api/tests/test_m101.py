from pathlib import Path

import matplotlib
import numpy as np
import pytest
from astropy.io import fits

from app.services.m101 import (
    crear_mascara_m101,
    generar_figura_m101,
)

# Evitamos que Matplotlib intente utilizar una interfaz gráfica.
matplotlib.use("Agg")


@pytest.fixture
def fits_valido(tmp_path: Path) -> Path:
    """
    Construye un FITS sintético con las extensiones necesarias
    para probar la generación de figuras de M101.
    """

    # Creamos un cubo de tres canales con una imagen de 10 x 10 píxeles.
    imagen = np.ones((3, 10, 10), dtype=np.float32)

    # Introducimos variaciones para que la imagen tenga contraste.
    imagen[:, 0, 0] = 2.0
    imagen[:, 1, 1] = 5.0
    imagen[:, 2, 2] = 10.0

    # Cada píxel tiene inicialmente cobertura positiva.
    hits = np.ones((3, 10, 10), dtype=np.int16)

    # Inicialmente no existen banderas de calidad activadas.
    flags = np.zeros((3, 10, 10), dtype=np.int32)

    # Definimos las longitudes de onda correspondientes a los canales.
    canales = fits.BinTableHDU.from_columns(
        [
            fits.Column(
                name="WAVELENGTH",
                format="E",
                array=np.array([0.75, 0.85, 0.95], dtype=np.float32),
            )
        ],
        name="SPECTRAL_CHANNELS",
    )

    # Creamos las extensiones principales del archivo FITS.
    hdul = fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.ImageHDU(data=imagen, name="IMAGE"),
            fits.ImageHDU(data=hits, name="NHITS"),
            fits.ImageHDU(data=flags, name="FLAGS"),
            canales,
        ]
    )

    # Guardamos el FITS temporal para utilizarlo en las pruebas.
    ruta = tmp_path / "m101_sintetico.fits"
    hdul.writeto(ruta)

    return ruta


def test_genera_png_correctamente(
    fits_valido: Path,
    tmp_path: Path,
) -> None:
    """Comprueba que se genere una imagen PNG para un canal válido."""

    # Definimos la ruta de salida de la figura.
    salida = tmp_path / "resultados" / "m101.png"

    # Generamos la figura utilizando el tercer canal.
    generar_figura_m101(fits_valido, salida, canal=3)

    # Verificamos que el archivo exista y contenga datos.
    assert salida.exists()
    assert salida.stat().st_size > 0

    # Comprobamos la firma binaria de un archivo PNG.
    with salida.open("rb") as archivo:
        assert archivo.read(8) == b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize("canal", [0, -1])
def test_rechaza_canales_menores_a_uno(
    fits_valido: Path,
    tmp_path: Path,
    canal: int,
) -> None:
    """Comprueba que no se acepten números de canal inválidos."""

    # Un canal debe comenzar en uno, no en cero.
    with pytest.raises(ValueError, match="entero mayor o igual a 1"):
        generar_figura_m101(fits_valido, tmp_path / "salida.png", canal)


def test_rechaza_canal_fuera_de_rango(
    fits_valido: Path,
    tmp_path: Path,
) -> None:
    """Comprueba que no se soliciten canales inexistentes."""

    # El FITS sintético solamente contiene tres canales.
    with pytest.raises(ValueError, match="solamente 3 canales"):
        generar_figura_m101(fits_valido, tmp_path / "salida.png", canal=4)


def test_rechaza_extension_faltante(
    fits_valido: Path,
    tmp_path: Path,
) -> None:
    """Comprueba que se detecte una extensión FITS obligatoria ausente."""

    # Abrimos el archivo y construimos una copia sin la extensión FLAGS.
    with fits.open(fits_valido) as hdul:
        extensiones = [
            hdu.copy()
            for hdu in hdul
            if hdu.name != "FLAGS"
        ]

    archivo_incompleto = tmp_path / "sin_flags.fits"
    fits.HDUList(extensiones).writeto(archivo_incompleto)

    # La función debe informar qué extensión falta.
    with pytest.raises(ValueError, match="FLAGS"):
        generar_figura_m101(
            archivo_incompleto,
            tmp_path / "salida.png",
        )


def test_rechaza_dimensiones_incompatibles(
    fits_valido: Path,
    tmp_path: Path,
) -> None:
    """Comprueba que los tres cubos tengan dimensiones compatibles."""

    # Reconstruimos el archivo con una extensión NHITS de tamaño diferente.
    with fits.open(fits_valido) as hdul:
        extensiones = [hdu.copy() for hdu in hdul]

    extensiones[2] = fits.ImageHDU(
        data=np.ones((3, 8, 8), dtype=np.int16),
        name="NHITS",
    )

    archivo_incompatible = tmp_path / "dimensiones_incompatibles.fits"
    fits.HDUList(extensiones).writeto(archivo_incompatible)

    # La función debe rechazar los cubos incompatibles.
    with pytest.raises(ValueError, match="dimensiones incompatibles"):
        generar_figura_m101(
            archivo_incompatible,
            tmp_path / "salida.png",
        )


def test_rechaza_canal_sin_pixeles_validos(
    fits_valido: Path,
    tmp_path: Path,
) -> None:
    """Comprueba que no se genere una figura sin píxeles utilizables."""

    # Activamos la bandera overflow en todos los píxeles del primer canal.
    with fits.open(fits_valido) as hdul:
        extensiones = [hdu.copy() for hdu in hdul]

    extensiones[3].data[0, :, :] = 1 << 1

    archivo_sin_pixeles = tmp_path / "sin_pixeles_validos.fits"
    fits.HDUList(extensiones).writeto(archivo_sin_pixeles)

    # Ningún píxel debe superar la máscara de calidad.
    with pytest.raises(ValueError, match="No hay píxeles válidos"):
        generar_figura_m101(
            archivo_sin_pixeles,
            tmp_path / "salida.png",
            canal=1,
        )


def test_rechaza_longitud_de_onda_no_finita(
    fits_valido: Path,
    tmp_path: Path,
) -> None:
    """Comprueba que se rechacen longitudes de onda no finitas."""

    # Sustituimos la longitud de onda del tercer canal por NaN.
    with fits.open(fits_valido) as hdul:
        extensiones = [hdu.copy() for hdu in hdul]

    extensiones[4].data["WAVELENGTH"][2] = np.nan

    archivo_onda_invalida = tmp_path / "onda_invalida.fits"
    fits.HDUList(extensiones).writeto(archivo_onda_invalida)

    # La longitud de onda debe ser finita y positiva.
    with pytest.raises(ValueError, match="finito y positivo"):
        generar_figura_m101(
            archivo_onda_invalida,
            tmp_path / "salida.png",
            canal=3,
        )

def test_mascara_rechaza_dimensiones_incompatibles() -> None:
    """Comprueba que los arreglos tengan las mismas dimensiones."""

    # Creamos arreglos donde FLAGS tiene dimensiones diferentes.
    imagen = np.ones((2, 2))
    hits = np.ones((2, 2))
    flags = np.zeros((3, 3), dtype=np.uint32)

    # La función debe rechazar arreglos incompatibles.
    with pytest.raises(ValueError, match="dimensiones compatibles"):
        crear_mascara_m101(imagen, hits, flags)


def test_mascara_rechaza_flags_no_enteros() -> None:
    """Comprueba que FLAGS utilice un tipo de dato entero."""

    # Creamos FLAGS con valores decimales para provocar el rechazo.
    imagen = np.ones((2, 2))
    hits = np.ones((2, 2))
    flags = np.zeros((2, 2), dtype=np.float64)

    # La función debe exigir un arreglo de tipo entero.
    with pytest.raises(ValueError, match="valores enteros"):
        crear_mascara_m101(imagen, hits, flags)

def test_mascara_excluye_overflow_y_outlier() -> None:
    """Comprueba que se excluyan los bits de calidad correspondientes."""

    # Creamos cuatro píxeles con distintas condiciones de calidad.
    imagen = np.array([[10.0, 20.0, 30.0, 40.0]])
    hits = np.array([[1, 1, 1, 0]])
    flags = np.array([[
        0,
        1 << 1,
        1 << 19,
        0,
    ]], dtype=np.int32)

    # Generamos la máscara de calidad.
    resultado = crear_mascara_m101(imagen, hits, flags)

    # Solamente el primer píxel debe considerarse válido.
    np.testing.assert_array_equal(
        resultado,
        [[True, False, False, False]],
    )


def test_mascara_excluye_valores_no_finitos() -> None:
    """Comprueba que se excluyan valores NaN e infinitos."""

    # Creamos datos con valores no finitos.
    imagen = np.array([[10.0, np.nan, 30.0]])
    hits = np.array([[1.0, 1.0, np.inf]])
    flags = np.zeros((1, 3), dtype=np.int32)

    # Generamos la máscara de calidad.
    resultado = crear_mascara_m101(imagen, hits, flags)

    # Solamente el primer píxel debe ser válido.
    np.testing.assert_array_equal(
        resultado,
        [[True, False, False]],
    )
