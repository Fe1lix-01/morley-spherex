import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock

from fastapi import APIRouter, HTTPException, Response

from app.core.config import get_m101_fits_path
from app.services.m101 import generar_figura_m101


# Configuración del router de visualizaciones científicas.
router = APIRouter(
    prefix="/api/v1/science",
    tags=["Science"],
)

# Logger para registrar errores durante el procesamiento científico.
logger = logging.getLogger(__name__)

# Matplotlib necesita que sus operaciones se ejecuten de forma secuencial.
render_lock = Lock()


@router.get(
    "/m101/channel-63/preview",
    response_class=Response,
    summary="Visualización científica de M101",
    description=(
        "Genera una imagen PNG con la intensidad, cobertura y máscara "
        "de calidad del canal 63 de SPHEREx para M101."
    ),
    responses={
        200: {
            "description": "Figura científica generada correctamente.",
            "content": {
                "image/png": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                    }
                }
            },
        },
        503: {
            "description": "FITS no disponible o procesamiento fallido.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": (
                            "No fue posible generar la visualización "
                            "científica de M101"
                        )
                    }
                }
            },
        },
    },
)
def m101_channel_preview() -> Response:
    """
    Genera la imagen, la cobertura y la máscara del canal 63 de M101.
    """

    # Obtenemos la ruta del FITS desde la configuración centralizada.
    archivo = get_m101_fits_path()

    # Si no existe configuración, respondemos con un error controlado.
    if archivo is None:
        raise HTTPException(
            status_code=503,
            detail="El archivo científico de M101 no está configurado",
        )

    try:
        # Comprobamos que el archivo científico esté disponible.
        if not archivo.is_file():
            raise HTTPException(
                status_code=503,
                detail="El archivo científico de M101 no está disponible",
            )

        # Cada solicitud utiliza su propia carpeta temporal.
        with TemporaryDirectory(prefix="m101-") as carpeta:
            ruta_salida = Path(carpeta) / "canal_63.png"

            # Evitamos ejecuciones simultáneas de Matplotlib.
            with render_lock:
                generar_figura_m101(
                    archivo=archivo,
                    ruta_salida=ruta_salida,
                    canal=63,
                )

            # Leemos el PNG antes de eliminar la carpeta temporal.
            contenido = ruta_salida.read_bytes()

    except HTTPException:
        # Conservamos los errores HTTP controlados del endpoint.
        raise

    except (OSError, ValueError, KeyError, IndexError, TypeError):
        # Registramos el error real sin exponer detalles internos al cliente.
        logger.exception(
            "Error al generar la figura científica de M101"
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "No fue posible generar la visualización "
                "científica de M101"
            ),
        ) from None

    # Devolvemos el PNG como respuesta binaria.
    return Response(
        content=contenido,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )
