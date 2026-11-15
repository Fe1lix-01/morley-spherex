"""FITS ROI extraction without resampling; channel indices are zero based."""
from pathlib import Path
import re
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.nddata import Cutout2D
from .region import Region

MAX_PIXELS = 4_000_000
METADATA = ("TELESCOP", "INSTRUME", "DETECTOR", "OBS_ID", "DATE-OBS", "MJD-OBS",
            "BUNIT", "FILTER", "WAVELEN", "WAVELNTH", "CHANNEL", "CTYPE3", "CUNIT3",
            "CRVAL3", "CRPIX3", "CDELT3")


def celestial(hdu, hdul):
    w = WCS(hdu.header, fobj=hdul).celestial
    if not w.has_celestial:
        raise ValueError("La extensión no contiene WCS celestial")
    if any(getattr(w, key) is not None for key in ("cpdis1", "cpdis2", "det2im1", "det2im2")):
        raise ValueError("WCS con tablas de distorsión no soportada en este MVP")
    return w


def inspect_fits(path: Path):
    extensions = []
    with fits.open(path, memmap=True) as hdul:
        for i, hdu in enumerate(hdul):
            shape = list(hdu.shape) if isinstance(hdu, (fits.PrimaryHDU, fits.ImageHDU, fits.CompImageHDU)) else []
            supported, center, wcs_header = False, None, None
            if len(shape) in (2, 3):
                try:
                    w = celestial(hdu, hdul)
                    wcs_header = dict(w.to_header(relax=True))
                    # Cubes require the last two numpy axes to be the celestial plane.
                    full = WCS(hdu.header, fobj=hdul)
                    supported = full.wcs.lng == 0 and full.wcs.lat == 1
                    c = w.pixel_to_world((shape[-1]-1)/2, (shape[-2]-1)/2).icrs
                    center = {"ra": float(c.ra.deg), "dec": float(c.dec.deg)}
                except (ValueError, TypeError, KeyError):
                    pass
            extensions.append({"index": i, "name": hdu.name, "shape": shape,
                               "unit": hdu.header.get("BUNIT"), "processable": supported,
                               "center": center, "wcs": wcs_header, "channels": shape[0] if len(shape) == 3 else 1,
                               "metadata": {k: hdu.header[k] for k in METADATA if k in hdu.header}})
        primary = {k: hdul[0].header[k] for k in METADATA if k in hdul[0].header}
    return {"extensions": extensions, "metadata": primary,
            "product_kind": "spectral_cube" if any(len(e["shape"]) == 3 for e in extensions) else "image_2d",
            "note": "Los planos de un cubo no se interpretan como épocas temporales."}


def _cut_header(header, wcs2d, x0, y0, ndim):
    """Keep spectral WCS/table links for cubes; shift only spatial reference pixels."""
    out = header.copy()
    if ndim == 3:
        out["CRPIX1"] = float(header.get("CRPIX1", 0)) - x0
        out["CRPIX2"] = float(header.get("CRPIX2", 0)) - y0
    else:
        for key in list(out):
            if re.match(r"^(NAXIS\d|WCSAXES|CTYPE\d|CUNIT\d|CRPIX\d|CRVAL\d|CDELT\d|CROTA\d|CNAME\d|PC\d_\d|CD\d_\d|PV\d_\d|PS\d_\d)$", key):
                del out[key]
        out.update(wcs2d.to_header(relax=True))
    return out


def statistics(plane, inside, quality):
    finite = np.isfinite(plane) & inside
    valid = quality & finite
    values = np.asarray(plane[valid], dtype=float)
    total = int(inside.sum())
    return {"roi_pixels": total, "finite_pixels": int(finite.sum()),
            "quality_pixels": int((quality & inside).sum()),
            "valid_pixels": int(valid.sum()), "masked_percent": float(100*(1-valid.sum()/total)),
            "median": float(np.median(values)) if values.size else None,
            "std": float(np.std(values)) if values.size else None,
            "mad": float(np.median(np.abs(values-np.median(values)))) if values.size else None}


def extract_roi(path: Path, region: Region, output: Path, hdu_index=0, channel=0, provenance=None):
    """Preserve every input plane; channel selects statistics/preview, not FITS contents."""
    import json
    from astropy.wcs.utils import proj_plane_pixel_scales
    from .quality import flag_policy, flags_good, flag_counts
    from .visualization import display_scale
    inspection = inspect_fits(path)
    if not 0 <= hdu_index < len(inspection["extensions"]) or not inspection["extensions"][hdu_index]["processable"]:
        raise ValueError("Extensión no compatible con una imagen celestial 2D o cubo (canal,y,x)")
    selected = inspection["extensions"][hdu_index]
    if not 0 <= channel < selected["channels"]:
        raise ValueError("Canal fuera de rango")
    with fits.open(path, memmap=False) as hdul:
        hdu = hdul[hdu_index]
        w = celestial(hdu, hdul)
        shape = tuple(selected["shape"][-2:])
        x, y = w.world_to_pixel(region.boundary())
        if not np.all(np.isfinite([x, y])):
            raise ValueError("Región fuera de la proyección del FITS")
        # Temporary envelope only; remove every exterior row/column before writing.
        x0, y0 = int(np.floor(x.min())) - 1, int(np.floor(y.min())) - 1
        x1, y1 = int(np.ceil(x.max())) + 2, int(np.ceil(y.max())) + 2
        clipped = x.min() < -.5 or y.min() < -.5 or x.max() > shape[1]-.5 or y.max() > shape[0]-.5
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(shape[1], x1), min(shape[0], y1)
        if x1 <= x0 or y1 <= y0:
            raise ValueError("La región no intersecta el FITS")
        if (x1-x0)*(y1-y0) > MAX_PIXELS:
            raise ValueError("El recorte supera 4 millones de píxeles espaciales")
        yy, xx = np.indices((y1-y0, x1-x0))
        inside = region.contains(w.pixel_to_world(xx+x0, yy+y0))
        iy, ix = np.nonzero(inside)
        if not ix.size:
            raise ValueError("La región no contiene centros de píxel del FITS")
        left, right, bottom, top = int(ix.min()), int(ix.max())+1, int(iy.min()), int(iy.max())+1
        inside = inside[bottom:top, left:right]
        x1, y1 = x0+right, y0+top
        x0, y0 = x0+left, y0+bottom
        dummy = np.broadcast_to(np.uint8(0), shape)
        cut = Cutout2D(dummy, ((x0+x1-1)/2, (y0+y1-1)/2),
                       inside.shape, wcs=w, mode="strict")
        channels = selected["channels"]
        # Bound voxel memory as well as spatial size now that all channels are retained.
        if channels * inside.size > 16_000_000:
            raise ValueError("El cubo recortado supera 16 millones de vóxeles")
        result = fits.HDUList([fits.PrimaryHDU(header=hdul[0].header)])
        preserved, omitted, arrays = [], [], {}
        science = None
        science_header = None
        policy = flag_policy(hdul)
        for i, ext in enumerate(hdul):
            if isinstance(ext, fits.BinTableHDU) and ext.name in ("SPECTRAL_CHANNELS", "WCS-WAVE"):
                result.append(ext.copy())
                preserved.append(ext.name)
                continue
            if not isinstance(ext, (fits.PrimaryHDU, fits.ImageHDU, fits.CompImageHDU)) or len(ext.shape) not in (2, 3):
                if i != 0: omitted.append({"name": ext.name, "reason": "No es un plano compatible"})
                continue
            if tuple(ext.shape[-2:]) != shape or (len(ext.shape) == 3 and ext.shape[0] != channels):
                if ext.name.upper() in ("FLAGS", "MASK", "NHITS", "VARIANCE"):
                    raise ValueError(f"Dimensiones de calidad incompatibles: {ext.name}")
                omitted.append({"name": ext.name, "reason": "Dimensiones diferentes"})
                continue
            try:
                ew = WCS(ext.header, fobj=hdul)
                if ew.has_celestial:
                    ew = celestial(ext, hdul)
                    a, b = ew.world_to_pixel(w.pixel_to_world(np.array([0, shape[1]-1, shape[1]/2]), np.array([0, shape[0]-1, shape[0]/2])))
                    if not np.allclose([a, b], [[0, shape[1]-1, shape[1]/2], [0, shape[0]-1, shape[0]/2]], atol=1e-4):
                        raise ValueError("WCS no alineada")
                elif i != hdu_index and ext.name.upper() not in ("FLAGS", "MASK", "VARIANCE", "NHITS", "WAVELENGTH"):
                    raise ValueError("No hay WCS ni asociación de calidad conocida")
            except ValueError as error:
                # A quality extension cannot be silently ignored when it affects statistics.
                if ext.name.upper() in ("FLAGS", "MASK", "NHITS", "VARIANCE"):
                    raise ValueError(f"Extensión de calidad incompatible: {ext.name}: {error}") from error
                omitted.append({"name": ext.name, "reason": str(error)})
                continue
            data = ext.section[:, y0:y1, x0:x1] if len(ext.shape) == 3 else ext.section[y0:y1, x0:x1]
            header = _cut_header(ext.header, cut.wcs, x0, y0, data.ndim)
            header["ROICHAN"] = (channel, "Preview index; all planes retained")
            name = "SCIENCE" if i == hdu_index else (ext.name or f"HDU{i}")
            result.append(fits.ImageHDU(data=data, header=header, name=name))
            preserved.append(name)
            arrays[ext.name.upper()] = data
            if i == hdu_index:
                science, science_header = data, header
        if science is None:
            raise ValueError("No se pudo conservar la extensión científica")
        quality = np.ones(science.shape, dtype=bool)
        for name, data in arrays.items():
            if name == "FLAGS": quality &= flags_good(data, policy)
            elif name == "MASK": quality &= np.isfinite(data) & (data == 0)
            elif name == "NHITS": quality &= np.isfinite(data) & (data > 0)
            elif name == "VARIANCE": quality &= np.isfinite(data) & (data >= 0)
        valid = quality & np.isfinite(science) & inside
        quality_header = science_header.copy()
        quality_header["BUNIT"] = "1"
        result.append(fits.ImageHDU(inside.astype("uint8"), header=cut.wcs.to_header(relax=True), name="ROI_MASK"))
        result.append(fits.ImageHDU(quality.astype("uint8"), header=quality_header, name="QUALITY_MASK"))
        result.append(fits.ImageHDU(valid.astype("uint8"), header=quality_header, name="VALID_MASK"))
        result[0].header.add_history("MORLEY ROI v2: tight pixel-center bounds; all channels; no resampling")
        per_channel = []
        for k in range(channels):
            plane = science[k] if science.ndim == 3 else science
            q = quality[k] if quality.ndim == 3 else quality
            item = {"channel_index": k, **statistics(plane, inside, q)}
            if "FLAGS" in arrays:
                flags = arrays["FLAGS"]
                item["flags"] = flag_counts(flags[k] if flags.ndim == 3 else flags, inside, policy)
            per_channel.append(item)
        spectral = {"index": channel, "ordinal": channel+1, "axis_type": hdu.header.get("CTYPE3"), "wavelength": None}
        if "SPECTRAL_CHANNELS" in hdul and len(hdul["SPECTRAL_CHANNELS"].data) == channels:
            table = hdul["SPECTRAL_CHANNELS"]
            spectral["table_row"] = {col.name: {"value": np.asarray(table.data[channel][col.name]).tolist(), "unit": col.unit} for col in table.columns}
        elif science.ndim == 3:
            full = WCS(hdu.header, fobj=hdul)
            if full.wcs.spec >= 0:
                pixels = [float(v-1) for v in full.wcs.crpix]
                pixels[2] = channel
                spectral["wavelength"] = float(full.all_pix2world([pixels], 0)[0][full.wcs.spec])
                spectral["unit"] = str(full.wcs.cunit[full.wcs.spec])
        center = cut.wcs.pixel_to_world((inside.shape[1]-1)/2, (inside.shape[0]-1)/2).icrs
        metadata = {"pipeline_version": 2, "region": region.model_dump(), "hdu_index": hdu_index, "channel_index": channel,
                    "source": inspection, "spectral": spectral, "statistics": per_channel[channel],
                    "visualization": display_scale(science[channel] if science.ndim == 3 else science, inside),
                    "statistics_by_channel": per_channel, "shape": list(inside.shape), "cube_shape": list(science.shape),
                    "channels_preserved": channels, "unit": hdu.header.get("BUNIT"), "clipped_to_image": bool(clipped),
                    "preserved": preserved, "omitted": omitted, "mask_policy": policy,
                    "pixel_origin": [x0, y0], "pixel_scale_arcsec": (proj_plane_pixel_scales(cut.wcs)*3600).tolist(),
                    "cutout_center": {"ra": float(center.ra.deg), "dec": float(center.dec.deg)},
                    "spatial_wcs": dict(cut.wcs.to_header(relax=True)), "resampled": False,
                    "geometry_policy": "Minimal bounding array of pixel centers inside spherical ROI; ROI_MASK excludes exterior pixels for rotated selections. Native pixels have finite area, not an exact continuous-sky footprint.",
                    **(provenance or {})}
        encoded = json.dumps(metadata, allow_nan=False, sort_keys=True).encode("utf-8")
        result.append(fits.ImageHDU(np.frombuffer(encoded, dtype="uint8"), name="PROVENANCE"))
        result.writeto(output, overwrite=True, checksum=True)
        return metadata
