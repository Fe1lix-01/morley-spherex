"""Only operations absent from the existing SIA/observations/preview routers."""
import re
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.clients.irsa import IrsaResponseError, IrsaTimeoutError, IrsaUnavailableError
from app.services import roi
from science.pipeline.visualization import render_preview
from science.pipeline.region import Region, MAX_ARCMIN

router = APIRouter(prefix="/api/v1/science/roi", tags=["Science ROI"])


def operation(fn, *args):
    try:
        return fn(*args)
    except PermissionError as error:
        raise HTTPException(409, str(error)) from None
    except FileNotFoundError:
        raise HTTPException(404, "FITS o producto no encontrado") from None
    except IrsaTimeoutError:
        raise HTTPException(504, "Tiempo de espera de IRSA agotado") from None
    except IrsaUnavailableError:
        raise HTTPException(503, "IRSA no disponible; puedes cargar un FITS local") from None
    except IrsaResponseError:
        raise HTTPException(502, "IRSA rechazó la descarga o excedió el límite de bytes") from None
    except (ValueError, OSError, KeyError, IndexError, TypeError) as error:
        raise HTTPException(422, str(error)) from None


@router.get("/config")
def config():
    return {"max_arcmin": MAX_ARCMIN, "default_arcmin": min(10, MAX_ARCMIN), "max_fits_bytes": roi.MAX_BYTES}


@router.post("/files")
async def upload(request: Request):
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > roi.MAX_BYTES:
            raise HTTPException(413, "FITS supera el límite de bytes")
        content.extend(chunk)
    return await run_in_threadpool(operation, roi.register, bytes(content))


class ImportRequest(BaseModel):
    url: str | None = None
    filename: str | None = None
    confirm_download: bool = False


@router.post("/files/import")
def import_file(body: ImportRequest):
    if bool(body.url) == bool(body.filename):
        raise HTTPException(422, "Indica una URL o un nombre del catálogo local")
    return operation(roi.import_remote, body.url, body.confirm_download) if body.url else operation(roi.import_local, body.filename)


class ProcessRequest(BaseModel):
    asset_id: str
    region: Region
    hdu_index: int = Field(default=0, ge=0)
    channel: int = Field(default=0, ge=0)


@router.post("/products")
def process(body: ProcessRequest):
    return operation(roi.process, body.asset_id, body.region, body.hdu_index, body.channel)


@router.get("/products/{product_id}/{format}")
def product(product_id: str, format: str, view: Literal["raw", "masked", "quality"] = "masked",
            stretch: Literal["asinh", "linear"] = "asinh"):
    if not re.fullmatch(r"[0-9a-f]{64}", product_id) or format not in ("fits", "json", "png"):
        raise HTTPException(404, "Producto no encontrado")
    path = roi.CACHE / f"product-{product_id}.{'fits' if format == 'png' else format}"
    if not path.is_file():
        raise HTTPException(404, "Producto no encontrado")
    if format == "png":
        return Response(operation(render_preview, path, view, stretch), media_type="image/png")
    return FileResponse(path, media_type="application/fits" if format == "fits" else "application/json", filename=f"roi-{product_id[:12]}.{format}")
