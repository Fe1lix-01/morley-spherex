"""Only invoked by the controlled job runner, never with client-provided paths."""
import json
import sys
from pathlib import Path
from app.services import local_fits, roi, science_analysis, ml_inputs
from science.pipeline.region import Region


def execute(body):
    kind=body['kind']
    if kind=='index':return local_fits.refresh()
    if kind=='extract':
        region=Region.model_validate(body['region'])
        from astropy.io import fits
        from science.pipeline.fits_roi import celestial
        import numpy as np
        with fits.open(roi.asset_path(body['asset_id']),memmap=True) as h:
            ext=h[body['hdu_index']];w=celestial(ext,h)
            x,y=w.world_to_pixel(region.center.sky());ny,nx=ext.shape[-2:]
            if not np.isfinite([x,y]).all() or not (-.5<=x<nx-.5 and -.5<=y<ny-.5):
                raise ValueError('El FITS no cubre el centro del objetivo/ROI; no se usará otra región')
        return roi.process(body['asset_id'],region,body['hdu_index'],body['channel'])
    if kind=='import_local':return local_fits.use(body['catalog_id'],Region.model_validate(body['region']))
    if kind=='analysis':return science_analysis.analyze(body['product_id'])
    if kind=='temporal':return science_analysis.temporal(Region.model_validate(body['region']))
    if kind=='inference':return ml_inputs.infer(body['product_id'],body['triplet_id'])
    if kind=='demo':
        from app.routers.ml import run_cnn_demo
        return run_cnn_demo()
    raise ValueError('Tipo de trabajo no permitido')

if __name__=='__main__':
    print(json.dumps(execute(json.loads(Path(sys.argv[1]).read_text())['request']),allow_nan=False))
