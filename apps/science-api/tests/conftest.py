"""Fixtures compartidos para las pruebas del backend ÉTER."""

import numpy as np
import pytest
from astropy.io import fits

from app.services import frames as frames_service
from app.services import frame_images as frame_images_service
from app.services import observations as observations_service


@pytest.fixture
def fits_sinteticos(tmp_path, monkeypatch):
    """
    Genera seis imágenes FITS sintéticas con WCS válido.

    Cada archivo representa un detector D1-D6.
    Estos datos son exclusivamente de prueba.
    """
    fits_dir = tmp_path / "fits"
    fits_dir.mkdir()

    for detector in range(1, 7):
        # Imagen 16x16 con intensidades finitas.
        data = np.arange(
            256,
            dtype=np.float32,
        ).reshape(16, 16)

        data = data + detector

        # Encabezado WCS celestial.
        header = fits.Header()

        header["CTYPE1"] = "RA---TAN"
        header["CTYPE2"] = "DEC--TAN"

        header["CUNIT1"] = "deg"
        header["CUNIT2"] = "deg"

        # Centro de la imagen.
        header["CRPIX1"] = 8.5
        header["CRPIX2"] = 8.5

        # Coordenadas sintéticas.
        header["CRVAL1"] = 24.24125
        header["CRVAL2"] = 9.56307

        # Escala de 0.002 grados por píxel.
        header["CDELT1"] = -0.002
        header["CDELT2"] = 0.002

        header["RADESYS"] = "ICRS"

        # Nombre compatible con el patrón de detectores.
        filename = (
            f"test_D{detector}_100_arcsec_cutout.fits"
        )

        fits.PrimaryHDU(
            data=data,
            header=header,
        ).writeto(fits_dir / filename)

    # Los servicios importan FITS_DIR directamente.
    # Por eso configuramos cada módulo individualmente.
    monkeypatch.setattr(
        frames_service,
        "FITS_DIR",
        fits_dir,
    )

    monkeypatch.setattr(
        frame_images_service,
        "FITS_DIR",
        fits_dir,
    )

    monkeypatch.setattr(
        observations_service,
        "FITS_DIR",
        fits_dir,
    )

    return fits_dir
