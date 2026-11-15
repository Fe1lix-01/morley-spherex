"""Offline FITS index. Paths are server-owned; associations require real WCS."""
import hashlib
import json
import os
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from app.core.paths import PROJECT_ROOT, FITS_DIR
from app.services import roi
from science.pipeline.fits_roi import inspect_fits

EXPERIMENT = PROJECT_ROOT / 'science/experiments/morley_unified'
INDEX = PROJECT_ROOT / 'data/science-mvp/catalog.json'
MAX_FILES = 256


def inventory():
    roots = [FITS_DIR, roi.CACHE, EXPERIMENT / 'outputs/data/candidates_05']
    roots += [Path(p) for p in os.getenv('MORLEY_FITS_ROOTS', '').split(os.pathsep) if p]
    result = []
    for root in roots:
        if root.is_dir(): result.extend(sorted(root.glob('*.fits')))
    explicit = os.getenv('M101_FITS_PATH')
    if explicit and Path(explicit).is_file(): result.append(Path(explicit))
    return list(dict.fromkeys(p.resolve() for p in result))[:MAX_FILES]


def refresh():
    known = {}
    pair_file = EXPERIMENT / 'outputs/catalogs/candidate_pairs_multiepoch_05.json'
    if pair_file.exists():
        known = {Path(r['cutout_file']).name:r for r in json.loads(pair_file.read_text(encoding='utf-8-sig'))['observations'] if r.get('cutout_file')}
    entries, skipped, hashes = [], [], set()
    for path in inventory():
        try:
            if path.stat().st_size > roi.MAX_BYTES: raise ValueError('Supera el límite FITS configurado')
            info = inspect_fits(path)
            ext = next(e for e in info['extensions'] if e['processable'] and e['name'] in ('IMAGE','SCIENCE','PRIMARY'))
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest in hashes: continue
            hashes.add(digest)
            record = known.get(path.name, {})
            meta = {**info['metadata'], **ext['metadata']}
            with fits.open(path, memmap=True) as hdus:
                derived = 'PROVENANCE' in hdus or path.name.startswith('product-')
                footprint = WCS(ext['wcs']).calc_footprint(axes=(ext['shape'][-1],ext['shape'][-2])).tolist()
            if not record and path.parent == (EXPERIMENT/'outputs/data/candidates_05').resolve():
                record={'obs_id':path.name.split('level2_',1)[-1].split('D6_',1)[0],
                        'detector':'D'+str(meta.get('DETECTOR','unknown')),
                        'date_obs':meta.get('DATE-OBS'),'status':'existing_verified',
                        'cutout_file':str(path.relative_to(EXPERIMENT.resolve())),
                        'wavelength_source':'unavailable: no verified spectral metadata',
                        'wavelength_um':None,'bandwidth_um':None}
            entries.append({'id':digest,'path':str(path),'filename':path.name,'bytes':path.stat().st_size,
                'mtime_ns':path.stat().st_mtime_ns,'hdu_index':ext['index'],'shape':ext['shape'],
                'wcs':ext['wcs'],'footprint_icrs':footprint,'center':ext['center'],
                'kind':info['product_kind'],'derived':derived,'date_obs':meta.get('DATE-OBS'),
                'detector':str(meta.get('DETECTOR',record.get('detector','unknown'))),
                'unit':ext['unit'],'wavelength_um_approx':record.get('wavelength_um'),
                'bandwidth_um_approx':record.get('bandwidth_um'),
                'provenance':{'sha256':digest,'origin':'local_verified_roi' if derived else 'local_fits',
                    'access_url':record.get('access_url'),'collection':record.get('collection'),
                    'spectral_source':record.get('wavelength_source')},'offline_record':record})
        except (ValueError,TypeError,KeyError,StopIteration,OSError) as e:
            skipped.append({'filename':path.name,'reason':str(e) or 'Sin imagen científica celestial'})
    roi.atomic_write(INDEX,json.dumps({'entries':entries,'skipped':skipped},allow_nan=False).encode())
    return {'indexed':len(entries),'skipped':skipped}


def entries():
    if not INDEX.exists(): return []
    return json.loads(INDEX.read_text())['entries']


def resolve(key):
    entry = next((e for e in entries() if e['id']==key),None)
    if not entry: raise FileNotFoundError('Producto no indexado; actualiza el catálogo local')
    path=Path(entry['path'])
    if not path.is_file() or path.stat().st_size!=entry['bytes'] or path.stat().st_mtime_ns!=entry['mtime_ns']:
        raise ValueError('El FITS cambió después de indexarse; actualiza el catálogo')
    return entry,path


def coverage(entry, ra, dec, region=None):
    from astropy.coordinates import SkyCoord
    from astropy import units as u
    center=SkyCoord(entry['center']['ra']*u.deg,entry['center']['dec']*u.deg)
    corners=np.asarray(entry['footprint_icrs'])
    radius=float(center.separation(SkyCoord(corners[:,0]*u.deg,corners[:,1]*u.deg)).deg.max())
    if center.separation(SkyCoord(ra*u.deg,dec*u.deg)).deg > radius + .02:
        return {'target_inside':False,'region_covered':False,'status':'BLOCKED','reason':'El objetivo está fuera de la cobertura WCS'}
    w=WCS(entry['wcs']);ny,nx=entry['shape'][-2:]
    x,y=w.world_to_pixel_values(ra,dec)
    point=bool(np.isfinite([x,y]).all() and -.5 <= x < nx-.5 and -.5 <= y < ny-.5)
    full=point
    if region is not None:
        xx,yy=w.world_to_pixel(region.boundary())
        full=bool(point and np.isfinite([xx,yy]).all() and np.all((xx>=-.5)&(xx<nx-.5)&(yy>=-.5)&(yy<ny-.5)))
    return {'target_inside':point,'region_covered':full,'status':'PASS' if full else 'PARTIAL' if point else 'BLOCKED',
            'reason':None if full else 'La ROI excede la huella del FITS' if point else 'El objetivo está fuera de la cobertura WCS'}


def search(ra,dec,region=None,target_id=None):
    from app.services.science_targets import targets
    from astropy.time import Time
    target=next((t for t in targets() if t['id']==target_id),None) if target_id else None
    if target_id and target is None:raise ValueError('Objetivo astrométrico desconocido')
    found=[]
    for entry in entries():
        c=coverage(entry,ra,dec,region)
        at=None
        if target and c['target_inside']:
            epoch=float(Time(entry['date_obs']).jyear) if entry['date_obs'] else 2026.
            at=next(t for t in targets(epoch) if t['id']==target_id)
            if not coverage(entry,at['ra'],at['dec'])['target_inside']:continue
            at={k:at[k] for k in ('id','ra','dec','epoch','propagation')}
        if c['target_inside']:
            found.append({**{k:v for k,v in entry.items() if k not in ('path','offline_record','wcs','mtime_ns')},'coverage':c,'target_at_observation':at})
    return {'status':'PASS' if any(x['coverage']['status']=='PASS' for x in found) else 'PARTIAL' if found else 'BLOCKED',
            'reason':None if found else 'No hay FITS locales indexados que cubran este objetivo. No se sustituyen por otra región.',
            'products':found,'indexed':len(entries())}


def use(key,region):
    entry,path=resolve(key)
    if not coverage(entry,region.center.ra,region.center.dec,region)['target_inside']:
        raise ValueError('El FITS no cubre el centro seleccionado')
    result=roi.register(path.read_bytes())
    return {**result,'suggested_hdu':entry['hdu_index']}
