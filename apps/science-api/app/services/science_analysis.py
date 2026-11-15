"""Scientific adapters: original pixel statistics and existing offline diagnostics."""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_area
from app.services import roi, local_fits
from science.pipeline.region import Region


def product_files(product_id):
    if len(product_id)!=64 or any(c not in '0123456789abcdef' for c in product_id): raise ValueError('Producto inválido')
    path=roi.CACHE / f'product-{product_id}.fits'
    meta=json.loads((roi.CACHE / f'product-{product_id}.json').read_text())
    return path,meta


def analyze(product_id):
    path,meta=product_files(product_id)
    rows=[]
    with fits.open(path,memmap=False) as h:
        science=h['SCIENCE'].data;valid=h['VALID_MASK'].data.astype(bool)
        if science.ndim==2:science=science[None];valid=valid[None]
        area=float(proj_plane_pixel_area(WCS(h['SCIENCE'].header,h).celestial))*(np.pi/180)**2
        table=h['SPECTRAL_CHANNELS'] if 'SPECTRAL_CHANNELS' in h else None
        for k,(plane,mask) in enumerate(zip(science,valid)):
            v=np.asarray(plane[mask],dtype=float)
            row={'channel_index':k,'channel_ordinal':k+1,'valid_pixels':int(v.size),
                 'mean':float(v.mean()) if v.size else None,'median':float(np.median(v)) if v.size else None,
                 'sum_image_units':float(v.sum()) if v.size else None,
                 'integrated_valid_pixels_mJy':float(v.sum()*area*1e9) if v.size and str(meta['unit']).replace(' ','').lower()=='mjy/sr' else None}
            if table is not None:
                row['spectral_metadata']={c.name:{'value':np.asarray(table.data[k][c.name]).tolist(),'unit':c.unit} for c in table.columns}
            rows.append(row)
    return {'status':'PASS' if any(r['valid_pixels'] for r in rows) else 'BLOCKED',
        'kind':'spectral_roi_summary' if len(rows)>1 else 'spatial_roi_summary',
        'product_id':product_id,'fits_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'region':meta['region'],'mask_policy':meta['mask_policy'],'unit':meta['unit'],'channels':rows,
        'scientifically_validated':False,'limitations':['Resumen de los píxeles válidos de la ROI, no fotometría total de una fuente.',
          'No corrección de apertura/PSF ni sustracción de fondo para la suma regional.',
          'Cada canal usa su máscara; cambia el área válida. Canales espectrales no son épocas.'],
        'temporal':temporal(Region.model_validate(meta['region'])),
        'ml':__import__('app.services.ml_inputs',fromlist=['eligibility']).eligibility(product_id)}


def temporal(region):
    # Run the generic functions of 06, not its CLI/global fixed-target reports.
    spec=importlib.util.spec_from_file_location('morley_routes',local_fits.EXPERIMENT/'06_science_routes.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    candidates=[]
    for entry in local_fits.entries():
        if entry['derived'] or entry['kind']!='image_2d': continue
        if not local_fits.coverage(entry,region.center.ra,region.center.dec)['target_inside']:continue
        record=entry['offline_record']
        if not record:continue
        local_fits.resolve(entry['id'])
        record=dict(record)
        # Old wavelength estimates belong to the offline target, not arbitrary pixels.
        from astropy.coordinates import SkyCoord
        from astropy import units as u
        sep=SkyCoord(region.center.ra*u.deg,region.center.dec*u.deg).separation(SkyCoord(295.4097841*u.deg,-15.2231692*u.deg)).arcsec
        if sep>1:record.update(wavelength_um=None,bandwidth_um=None)
        candidates.append((entry,record))
    measurements=[]
    for entry,record in candidates[:24]:
        result=module.measure_single_cutout(record,region.center.ra,region.center.dec,3.,5.,8.)
        result.pop('file',None);result['catalog_id']=entry['id'];measurements.append(result)
    pairs=[];mapped={r['obs_id']:r for r in measurements}
    for (_,a),(_,b) in itertools.combinations(candidates[:24],2):
        if a.get('detector')!=b.get('detector'):continue
        try:dt=abs(float((Time(a['date_obs'])-Time(b['date_obs'])).to_value('day')))
        except (ValueError,KeyError,TypeError):continue
        if dt<=0:continue
        wa,wb=a.get('wavelength_um'),b.get('wavelength_um')
        mismatch=abs(wa-wb)/min(wa,wb) if wa and wb else None
        earlier,later=sorted([a,b],key=lambda r:r['date_obs'])
        pair=module.decide_pair({'pair_id':earlier['obs_id']+'__'+later['obs_id'],
          'earlier':earlier,'later':later,'detector':a['detector'],'relative_mismatch':mismatch,'separation_days':dt},mapped,.01,1.)
        ua=str(mapped.get(a['obs_id'],{}).get('bunit','')).replace(' ','').lower()
        ub=str(mapped.get(b['obs_id'],{}).get('bunit','')).replace(' ','').lower()
        if not ua or not ub or ua!=ub:
            pair.update(route='INCOMPATIBLE_UNITS',reasons=['Unidades ausentes o distintas; no se comparan flujos temporalmente'])
        pairs.append(pair)
    return {'status':'PARTIAL' if pairs else 'BLOCKED','target':region.center.model_dump(),
      'reason':'Diagnósticos exploratorios; faltan validación CWAVE/CBAND, registro y PSF para variabilidad.' if pairs else 'No hay dos épocas reales compatibles indexadas que cubran el objetivo.',
      'observations':measurements,'pairs':pairs,'real_zogy_executed':False,'temporal_variability_claimed':False,
      'algorithm':'morley_unified/06_science_routes.py: measure_single_cutout + decide_pair',
      'quality_policy':'Level-2 conservadora FLAGS=0, varianza>0; no aplica la excepción SOURCE del mosaico'}
