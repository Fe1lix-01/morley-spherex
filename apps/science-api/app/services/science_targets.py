"""Single versioned astrometric catalog shared by both viewers via the API."""
import json
from functools import lru_cache
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from app.core.paths import PROJECT_ROOT


@lru_cache(maxsize=256)
def targets(epoch=2026.0):
    rows = json.loads((PROJECT_ROOT / 'resources/science/targets.json').read_text())
    for row in rows:
        if row['kind'] == 'region':
            row.update(epoch=None, propagation='Fixed ICRS region; no proper motion applied')
            continue
        c = SkyCoord(ra=row['ra']*u.deg, dec=row['dec']*u.deg,
                     pm_ra_cosdec=row['pm_ra_cosdec_masyr']*u.mas/u.yr,
                     pm_dec=row['pm_dec_masyr']*u.mas/u.yr,
                     obstime=Time(row['reference_epoch'], format='jyear'))
        at = c.apply_space_motion(new_obstime=Time(epoch, format='jyear'))
        row['reference_ra'], row['reference_dec'] = row['ra'], row['dec']
        row.update(ra=float(at.ra.deg), dec=float(at.dec.deg), epoch=epoch,
                   propagation='ICRS angular proper motion; no parallax, radial velocity or binary orbit; targeting only')
    return rows
