"""Bounded, content-addressed local store. No arbitrary filesystem paths via HTTP."""
import hashlib
import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from urllib.parse import urlsplit

from app.core.paths import PROJECT_ROOT, FITS_DIR
from app.clients.irsa_cutouts import _fetch_cutout, CUTOUT_TIMEOUT

from app.core.science import Region
from science.pipeline.fits_roi import inspect_fits, extract_roi

CACHE = Path(os.getenv("ROI_CACHE_DIR", str(PROJECT_ROOT / "data" / "roi-cache")))
MAX_BYTES = int(os.getenv("ROI_MAX_FITS_BYTES", str(128 * 1024 * 1024)))
CACHE_BYTES = int(os.getenv("ROI_CACHE_MAX_BYTES", str(1024 * 1024 * 1024)))
store_lock = Lock()


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(content)
        name = Path(tmp.name)
    try:
        name.replace(path)
    finally:
        name.unlink(missing_ok=True)


def capacity(extra):
    CACHE.mkdir(parents=True, exist_ok=True)
    used = sum(p.stat().st_size for p in CACHE.iterdir() if p.is_file())
    if used + extra > CACHE_BYTES:
        raise ValueError("Caché ROI llena; elimina productos antiguos antes de continuar")


def asset_path(asset_id):
    if not re.fullmatch(r"[0-9a-f]{64}", asset_id):
        raise ValueError("Identificador FITS inválido")
    path = CACHE / f"{asset_id}.fits"
    if not path.is_file():
        raise FileNotFoundError("FITS no encontrado")
    return path


def register(content):
    if not content or len(content) > MAX_BYTES or not content.startswith(b"SIMPLE  ="):
        raise ValueError("Se requiere un FITS sin comprimir dentro del límite configurado")
    key = hashlib.sha256(content).hexdigest()
    path = CACHE / f"{key}.fits"
    with store_lock:
        if not path.exists():
            capacity(len(content))
            atomic_write(path, content)
            try:
                info = inspect_fits(path)
                if not any(e["processable"] for e in info["extensions"]):
                    raise ValueError("FITS sin imagen celestial compatible")
            except Exception:
                path.unlink(missing_ok=True)
                raise
    return {"asset_id": key, "bytes": len(content), **inspect_fits(path)}


def import_remote(url, confirmed):
    if not confirmed:
        raise PermissionError("Confirma la transferencia del FITS (máximo configurado: %d MiB)" % (MAX_BYTES // 1024**2))
    p = urlsplit(url)
    if (p.scheme != "https" or p.netloc != "irsa.ipac.caltech.edu" or
        not p.path.startswith(("/ibe/data/spherex/", "/data/SPHEREx/")) or
        not p.path.lower().endswith(".fits") or p.query or p.fragment or
        any(part in ("..", ".") for part in p.path.split("/")) or "%" in p.path):
        raise ValueError("Solo se permiten productos FITS SPHEREx del servidor IRSA autorizado")
    index = CACHE / ("url-" + hashlib.sha256(url.encode()).hexdigest() + ".json")
    if index.exists():
        asset = json.loads(index.read_text())["asset_id"]
        path = asset_path(asset)
        return {"asset_id": asset, "bytes": path.stat().st_size, **inspect_fits(path)}
    # Reuses Marvin's bounded downloader, with no redirects or automatic bulk download.
    result = register(_fetch_cutout(url, {}, CUTOUT_TIMEOUT, MAX_BYTES))
    atomic_write(index, json.dumps({"asset_id": result["asset_id"]}).encode())
    return result


def import_local(filename):
    if Path(filename).name != filename or not filename.endswith(".fits"):
        raise ValueError("Nombre local inválido")
    path = (FITS_DIR / filename).resolve()
    if path.parent != FITS_DIR.resolve() or not path.is_file():
        raise FileNotFoundError("FITS local no encontrado")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("FITS supera el límite de tamaño")
    return register(path.read_bytes())


def process(asset_id, region: Region, hdu_index, channel):
    path = asset_path(asset_id)
    spec = {"asset_id": asset_id, "region": region.model_dump(), "hdu": hdu_index, "channel": channel, "pipeline": 2}
    key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    output = CACHE / f"product-{key}.fits"
    metadata = CACHE / f"product-{key}.json"
    with store_lock:
        if metadata.exists() and output.exists():
            return json.loads(metadata.read_text())
        capacity(MAX_BYTES)
        try:
            result = extract_roi(path, region, output, hdu_index, channel,
                                 provenance={"product_id": key, "asset_id": asset_id})
            if output.stat().st_size > MAX_BYTES:
                raise ValueError("El producto multicanal supera el límite de bytes configurado")
            atomic_write(metadata, json.dumps(result, allow_nan=False).encode())
        except Exception:
            output.unlink(missing_ok=True)
            raise
    return result
