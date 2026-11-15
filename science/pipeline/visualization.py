"""Quick-look rendering only. Never write stretched values back to scientific arrays."""
from io import BytesIO
import json

import numpy as np
from astropy.io import fits
from PIL import Image


def display_scale(data, inside):
    values = np.asarray(data)[inside & np.isfinite(data)]
    low, high = np.percentile(values, [0.5, 99.5]) if values.size else (0., 1.)
    return {"interval": "percentile", "percentiles": [0.5, 99.5],
            "vmin": float(low), "vmax": float(high), "default_stretch": "asinh",
            "asinh_a": 0.1, "reference": "finite original science inside ROI, before quality masking",
            "origin": "lower", "changes_scientific_values": False}


def render_preview(path, view="masked", stretch="asinh"):
    with fits.open(path, memmap=False) as hdul:
        if "PROVENANCE" in hdul:
            meta = json.loads(hdul["PROVENANCE"].data.tobytes().decode("utf-8"))
        else:
            meta = {"channel_index": 0}  # Legacy v1 products stored only their selected plane.
        index = meta["channel_index"]
        science = hdul["SCIENCE"].data
        data = (science[index] if science.ndim == 3 else science).astype(float)
        inside = hdul["ROI_MASK"].data.astype(bool)
        mask_name = "QUALITY_MASK" if view == "quality" and "QUALITY_MASK" in hdul else "VALID_MASK"
        mask = hdul[mask_name].data
        mask = (mask[index] if mask.ndim == 3 else mask).astype(bool) & inside
        if view == "quality":
            pixels = mask.astype("uint8") * 255
        else:
            scale = meta.get("visualization") or display_scale(data, inside)
            low, high = scale["vmin"], scale["vmax"]
            good = np.isfinite(data) & inside
            if view == "masked": good &= mask
            pixels = np.zeros(data.shape, dtype="uint8")
            normalized = np.clip((data[good]-low)/(high-low), 0, 1) if high > low else np.full(int(good.sum()), .5)
            if stretch == "asinh":
                a = scale["asinh_a"]
                normalized = np.arcsinh(normalized/a)/np.arcsinh(1/a)
            pixels[good] = np.rint(normalized*255).astype("uint8")
        output = BytesIO()
        Image.fromarray(np.flipud(pixels)).save(output, format="PNG")
        return output.getvalue()
