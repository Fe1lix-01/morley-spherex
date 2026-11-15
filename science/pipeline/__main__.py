"""Offline extraction: python -m science.pipeline input.fits output.fits --hdu 1 --channel 62"""
import argparse
import json
from pathlib import Path
from .fits_roi import extract_roi, inspect_fits
from .region import centered_region

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("input", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--hdu", type=int, default=0)
parser.add_argument("--channel", type=int, default=0)
parser.add_argument("--ra", type=float)
parser.add_argument("--dec", type=float)
parser.add_argument("--size", type=float, default=10)
args = parser.parse_args()
if args.input.resolve() == args.output.resolve():
    parser.error("El archivo de salida debe ser diferente del original")
info = inspect_fits(args.input)
center = info["extensions"][args.hdu]["center"]
if center is None:
    parser.error("Selecciona una extensión con WCS celestial")
region = centered_region(args.ra if args.ra is not None else center["ra"],
                         args.dec if args.dec is not None else center["dec"], args.size)
result = extract_roi(args.input, region, args.output, args.hdu, args.channel)
args.output.with_suffix(".json").write_text(json.dumps(result, indent=2, allow_nan=False))
print(json.dumps(result["statistics"], indent=2))
