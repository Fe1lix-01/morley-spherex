"""Explicit product-specific quality policies; never infer flag meanings from pixel counts."""
import numpy as np

MOSAIC_FLAGS = {"OVERFLOW": 1 << 1, "OUTLIER": 1 << 19, "SOURCE": 1 << 21}
MOSAIC_REFERENCE = "https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/mosaic.html"


def flag_policy(hdul):
    declared = {}
    if "FLAGS" in hdul:
        header = hdul["FLAGS"].header
        for key in header:
            if key.startswith("MSKN"):
                mask = header.get("MSKM" + key[4:])
                if isinstance(mask, int):
                    declared[str(header[key]).strip().upper()] = mask
    mosaic = (all(declared.get(k) == v for k, v in MOSAIC_FLAGS.items())
              and "SPECTRAL_CHANNELS" in hdul and "WCS-WAVE" in hdul)
    return {"id": "spherex_mosaic_declared_v1" if mosaic else "generic_conservative_v1",
            "product_version": hdul[0].header.get("VERSION"),
            "declared_flags": declared,
            "rejected_flags": ["OVERFLOW", "OUTLIER"] if mosaic else ["any_nonzero_flag"],
            "retained_flags": ["SOURCE"] if mosaic else [],
            "unknown_bits": "reject_and_report",
            "reference": MOSAIC_REFERENCE if mosaic else None,
            "conditions": "FLAGS policy; MASK=0; finite NHITS>0; finite VARIANCE>=0 when present. VALID_MASK additionally requires finite science and ROI_MASK."}


def flags_good(data, policy):
    if not np.issubdtype(data.dtype, np.integer):
        raise ValueError("FLAGS debe ser una máscara de bits entera")
    if policy["id"] != "spherex_mosaic_declared_v1":
        return data == 0
    # SOURCE alone is informational. Unknown bits are not silently accepted.
    return (data.astype(np.int64) & ~MOSAIC_FLAGS["SOURCE"]) == 0


def flag_counts(data, inside, policy):
    f = data[inside].astype(np.int64)
    counts = {"zero": int(np.sum(f == 0))}
    if policy["id"] == "spherex_mosaic_declared_v1":
        for name, bit in MOSAIC_FLAGS.items():
            counts[name] = int(np.sum((f & bit) != 0))
        counts["SOURCE_ONLY"] = int(np.sum(f == MOSAIC_FLAGS["SOURCE"]))
        counts["unknown_bits"] = int(np.sum((f & ~sum(MOSAIC_FLAGS.values())) != 0))
    return counts
