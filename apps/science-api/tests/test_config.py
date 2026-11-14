
"""
Pruebas para la configuración centralizada del backend ÉTER.

Verifican los valores predeterminados, las variables de entorno
y el tratamiento de las rutas de archivos científicos.
"""

import pytest
from pathlib import Path

# Funciones y constantes de configuración que vamos a probar.
from app.core.config import (
    DEFAULT_CORS_ORIGINS,
    get_cors_origins,
    get_m101_fits_path,
)


# Comprueba los orígenes predeterminados de desarrollo.
def test_cors_usa_origenes_predeterminados(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert get_cors_origins() == list(DEFAULT_CORS_ORIGINS)


# Comprueba que se interpreten varios orígenes personalizados.
def test_cors_admite_origenes_personalizados(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://eter.example.com, https://frontend.example.com",
    )

    assert get_cors_origins() == [
        "https://eter.example.com",
        "https://frontend.example.com",
    ]


# Comprueba que una lista vacía utilice los valores predeterminados.
def test_cors_usa_default_si_la_lista_esta_vacia(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " , ")

    assert get_cors_origins() == list(DEFAULT_CORS_ORIGINS)


# Comprueba que se rechace el comodín cuando se utilizan credenciales.
def test_cors_rechaza_comodin(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValueError, match="no puede contener"):
        get_cors_origins()


# Comprueba que una ruta FITS no configurada devuelva None.
def test_m101_fits_devuelve_none_si_no_esta_configurado(monkeypatch):
    monkeypatch.delenv("M101_FITS_PATH", raising=False)

    assert get_m101_fits_path() is None


# Comprueba que se eliminen espacios de la ruta configurada.
def test_m101_fits_limpia_espacios(monkeypatch):
    monkeypatch.setenv("M101_FITS_PATH", "  ./data/M101.fits  ")

    # Comparamos objetos Path para respetar los separadores del sistema operativo.
    assert get_m101_fits_path() == Path("data") / "M101.fits"


# Comprueba que se expanda correctamente el directorio personal.
def test_m101_fits_expande_directorio_personal(monkeypatch):
    monkeypatch.setenv("M101_FITS_PATH", "~/data/M101.fits")

    ruta = get_m101_fits_path()

    assert ruta is not None
    assert ruta == Path.home() / "data" / "M101.fits"
