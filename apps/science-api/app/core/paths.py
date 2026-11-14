import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]

DEFAULT_FITS_DIR = PROJECT_ROOT / "data" / "local" / "fits"

FITS_DIR = Path(
    os.environ.get("MORLEY_FITS_DIR") or DEFAULT_FITS_DIR
).expanduser().resolve()