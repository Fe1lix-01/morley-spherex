import json
import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(
    prefix="/api/v1/ml",
    tags=["Experimental ML"],
)

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "eter_cnn_mvp.py"
)


@router.get("/demo")
def run_cnn_demo():
    """
    Ejecuta una inferencia CNN con un triplete sintético.

    Utiliza un entorno Python independiente del backend.
    No constituye validación científica con SPHEREx.
    """

    python_path = os.getenv("ETER_ML_PYTHON")
    weights_path = os.getenv("ETER_ML_WEIGHTS")
    sample_path = os.getenv("ETER_ML_SAMPLE")

    if not all([python_path, weights_path, sample_path]):
        raise HTTPException(
            status_code=503,
            detail="Las variables del módulo ML no están configuradas.",
        )

    if not Path(python_path).is_file():
        raise HTTPException(
            status_code=503,
            detail="No se encontró el intérprete Python de ML.",
        )

    if not SCRIPT_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail="No se encontró el script de inferencia.",
        )

    if (
        not Path(weights_path).is_file()
        or Path(weights_path).stat().st_size == 0
    ):
        raise HTTPException(
            status_code=503,
            detail="El checkpoint no existe o está vacío.",
        )

    if not Path(sample_path).is_file():
        raise HTTPException(
            status_code=503,
            detail="No se encontró el triplete de prueba.",
        )

    try:
        process = subprocess.run(
            [
                python_path,
                str(SCRIPT_PATH),
                "infer",
                "--input",
                sample_path,
                "--weights",
                weights_path,
            ],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="La inferencia excedió el tiempo permitido.",
        ) from None

    except OSError:
        raise HTTPException(
            status_code=503,
            detail="No se pudo ejecutar el entorno ML.",
        ) from None

    if process.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail="El proceso de inferencia falló. Revisa los logs del backend.",
        )

    try:
        result = json.loads(process.stdout)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="La CNN devolvió una respuesta inválida.",
        ) from None

    return {
        "status": "success",
        "mode": "synthetic_demo",
        "scientifically_validated": False,
        "result": result,
    }


@router.get("/barnard/preview")
def obtener_preview_barnard():
    """
    Metadatos de una comparación exploratoria de
    observaciones SPHEREx de Barnard.

    No ejecuta la CNN ni confirma una detección.
    """
    import numpy as np

    directorio = os.getenv("ETER_BARNARD_ARTIFACTS_DIR")

    if not directorio:
        raise HTTPException(
            status_code=503,
            detail="Directorio de resultados de Barnard no configurado.",
        )

    ruta = (
        Path(directorio)
        / "barnard_triplete_real_exploratorio.npz"
    )

    if not ruta.is_file():
        raise HTTPException(
            status_code=404,
            detail="No se encontró el triplete procesado.",
        )

    with np.load(ruta, allow_pickle=False) as datos:
        mascara = np.asarray(datos["valid_mask"], dtype=bool)

    alto, ancho = mascara.shape
    validos = int(mascara.sum())
    total = int(mascara.size)

    return {
        "object": "Barnard",
        "source": "SPHEREx",
        "detector": "D2",
        "mode": "exploratory_wcs_aligned",
        "reference_date": "2026-08-18",
        "science_date": "2026-09-22",
        "wavelength_um_approx": 1.511,
        "image_url": "/api/v1/ml/barnard/preview/image",
        "shape": [alto, ancho],
        "valid_pixels": validos,
        "total_pixels": total,
        "valid_fraction": round(validos / total, 4),
        "center_pixel_valid": bool(
            mascara[alto // 2, ancho // 2]
        ),
        "cnn_inference_performed": False,
        "scientifically_validated": False,
        "limitations": [
            "Central region contains flagged pixels",
            "PSF matching has not been performed",
            "Difference image is exploratory",
            "No astrophysical movement detection is claimed",
        ],
    }


@router.get("/barnard/preview/image")
def obtener_imagen_barnard():
    """Devuelve la visualización PNG del triplete."""

    directorio = os.getenv("ETER_BARNARD_ARTIFACTS_DIR")

    if not directorio:
        raise HTTPException(
            status_code=503,
            detail="Directorio de resultados no configurado.",
        )

    ruta = (
        Path(directorio)
        / "barnard_triplete_real_exploratorio.png"
    )

    if not ruta.is_file():
        raise HTTPException(
            status_code=404,
            detail="No se encontró la imagen procesada.",
        )

    return FileResponse(
        path=ruta,
        media_type="image/png",
        filename="barnard_spherex_comparison.png",
    )

