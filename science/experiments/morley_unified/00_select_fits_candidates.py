#!/usr/bin/env python3
"""Inspector FITS usado por MORLEY 00D.

Adaptado de la funcion inspect_fits de la version previa de
00_select_fits_candidates.py. Conserva firma y campos esperados por 00D.
NO equivale al antiguo selector completo 00 con CLI TAP/samples.
No hace calibracion ePSF, WCS fino ni ZOGY.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


def inspect_fits(path, ra, dec):
    with fits.open(path, memmap=False) as hdul:
        required = ('IMAGE', 'VARIANCE', 'FLAGS', 'EPSF', 'WCS-WAVE')
        for ext in required:
            if ext not in hdul:
                raise ValueError(f'Missing FITS extension: {ext}')
        image = hdul['IMAGE'].data
        var = hdul['VARIANCE'].data
        flags = hdul['FLAGS'].data
        if (image is None or var is None or flags is None or image.ndim != 2
                or image.shape != var.shape or image.shape != flags.shape):
            raise ValueError('Invalid IMAGE/VARIANCE/FLAGS shapes')
        header = hdul['IMAGE'].header
        spatial = WCS(header, fobj=hdul).celestial
        x, y = map(float, spatial.world_to_pixel_values(ra, dec))
        ny, nx = image.shape
        if not (np.isfinite(x) and np.isfinite(y) and 4 <= x < nx - 4 and 4 <= y < ny - 4):
            raise ValueError(f'RA/Dec outside 7x7 usable region: ({x:.2f},{y:.2f}), {nx}x{ny}')
        spectral = WCS(header, fobj=hdul, key='W')
        spectral.sip = None
        wavelength, bandwidth = spectral.pixel_to_world(x, y)
        lam = float(wavelength.to_value(u.um))
        bw = float(bandwidth.to_value(u.um))
        if not (np.isfinite(lam) and np.isfinite(bw) and bw > 0):
            raise ValueError('Invalid approximate WCS-WAVE values')
        iy, ix = int(round(y)), int(round(x))
        patch = np.asarray(image[iy-3:iy+4, ix-3:ix+4])
        vpatch = np.asarray(var[iy-3:iy+4, ix-3:ix+4])
        fpatch = np.asarray(flags[iy-3:iy+4, ix-3:ix+4], dtype=np.uint64)
        if patch.shape != (7, 7):
            raise ValueError('Truncated quality patch')
        good = np.isfinite(patch) & np.isfinite(vpatch) & (vpatch > 0)
        date_obs = header.get('DATE-OBS') or hdul[0].header.get('DATE-OBS')
        if not date_obs:
            raise ValueError('Missing DATE-OBS')
        return {
            'date_obs': str(date_obs),
            'wavelength_um': round(lam, 8),
            'bandwidth_um': round(bw, 8),
            'pixel_xy': [round(x, 3), round(y, 3)],
            'shape': [ny, nx],
            'finite_variance_fraction_7x7': round(float(good.mean()), 4),
            'central_good': bool(good[3, 3]),
            'central_flag_raw': int(fpatch[3, 3]),
            'nonzero_flags_fraction_7x7': round(float(np.mean(fpatch != 0)), 4),
            'epsf_extension_present': True,
            'wavelength_source': 'approximate_WCS-WAVE',
        }


def main():
    p = argparse.ArgumentParser(description='Inspector FITS para MORLEY 00D (no realiza seleccion)')
    p.add_argument('--file', type=Path, required=True)
    p.add_argument('--ra', type=float, default=295.4097841)
    p.add_argument('--dec', type=float, default=-15.2231692)
    a = p.parse_args()
    import json
    print(json.dumps(inspect_fits(a.file, a.ra, a.dec), indent=2))


if __name__ == '__main__':
    main()
