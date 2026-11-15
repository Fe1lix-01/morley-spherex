import json
import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException

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
