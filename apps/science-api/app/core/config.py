"""
Configuración centralizada del backend ÉTER.

Lee las variables de entorno utilizadas por la aplicación
y proporciona valores predeterminados para desarrollo local.
"""

import os
from pathlib import Path


# Orígenes permitidos por defecto durante el desarrollo local.
DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def get_cors_origins() -> list[str]:
    """
    Obtiene los orígenes autorizados para solicitudes CORS.

    CORS_ORIGINS acepta varios orígenes separados por comas.
    Si no está configurada, utiliza los orígenes locales.
    """

    # Leemos la variable en tiempo de ejecución.
    origins_env = os.getenv("CORS_ORIGINS", "").strip()

    # Si no existe configuración, usamos los orígenes locales.
    if not origins_env:
        return list(DEFAULT_CORS_ORIGINS)

    # Separamos los orígenes y eliminamos espacios innecesarios.
    origins = [
        origin.strip()
        for origin in origins_env.split(",")
        if origin.strip()
    ]

    # Si la lista está vacía, utilizamos los valores predeterminados.
    if not origins:
        return list(DEFAULT_CORS_ORIGINS)

    # No permitimos comodines porque CORS utiliza credenciales.
    if "*" in origins:
        raise ValueError(
            "CORS_ORIGINS no puede contener '*' cuando "
            "allow_credentials está habilitado."
        )

    return origins


def get_m101_fits_path() -> Path | None:
    """
    Obtiene la ubicación del FITS científico de M101.

    Devuelve None cuando no existe una ruta configurada.
    """

    # Leemos la variable de entorno en cada llamada.
    fits_path = os.getenv("M101_FITS_PATH", "").strip()

    if not fits_path:
        return None

    # Expandimos rutas que utilicen el símbolo de directorio personal.
    return Path(fits_path).expanduser()
