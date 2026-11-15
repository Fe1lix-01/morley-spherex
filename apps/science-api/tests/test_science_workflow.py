"""End-to-end scientific workflow gates; no mock data are reported as observations."""
import json
import os
import time
from pathlib import Path
import numpy as np
import pytest
from astropy.io import fits
from fastapi.testclient import TestClient
from app.main import app
from app.services import local_fits, science_targets, science_analysis, science_jobs, ml_inputs, roi
from science.pipeline.region import centered_region

client=TestClient(app)
REAL=Path(os.getenv('ROI_TEST_FITS','/missing/mosaic_cube.fits'))

@pytest.fixture
def index(tmp_path,monkeypatch):
    monkeypatch.setattr(local_fits,'INDEX',tmp_path/'index.json')
    return tmp_path

@pytest.mark.parametrize('target_id',['barnard','epsilon-indi-b','wise0855','rw-aur','r-dra'])
def test_five_targets_verified_and_not_associated_to_m101(target_id,index,monkeypatch):
    if not REAL.exists():pytest.skip('ROI_TEST_FITS required')
    monkeypatch.setattr(local_fits,'inventory',lambda:[REAL])
    local_fits.refresh()
    target=next(r for r in science_targets.targets() if r['id']==target_id)
    assert target['epoch']==2026 and target['reference_epoch']==2000
    assert target['source'].startswith('https://simbad.')
    assert local_fits.search(target['ra'],target['dec'])['status']=='BLOCKED'
    if target_id=='epsilon-indi-b':
        assert 331.09<target['ra']<331.10
        assert target['identity']=='* eps Ind B'
    if target_id=='barnard':
        assert target['dec']-target['reference_dec']>.07

@pytest.mark.skipif(not REAL.exists(),reason='ROI_TEST_FITS required')
def test_catalog_checks_point_region_integrity_and_provenance(index,monkeypatch):
    monkeypatch.setattr(local_fits,'inventory',lambda:[REAL])
    local_fits.refresh()
    region=centered_region(210.8022671,54.34895,10)
    result=local_fits.search(region.center.ra,region.center.dec,region)
    assert result['status']=='PASS' and len(result['products'])==1
    entry=result['products'][0]
    assert len(entry['provenance']['sha256'])==64
    assert 'path' not in entry
    with pytest.raises(ValueError,match='no cubre'):
        local_fits.use(entry['id'],centered_region(269.446,4.768,10))
    assert local_fits.search(210.8022671,54.34895,centered_region(210.8022671,54.34895,20))['status']=='PASS'

@pytest.mark.skipif(not REAL.exists(),reason='ROI_TEST_FITS required')
def test_controlled_job_real_m101_channel_one_analysis_and_download(tmp_path,monkeypatch,index):
    cache=tmp_path/'cache';monkeypatch.setattr(roi,'CACHE',cache);monkeypatch.setenv('ROI_CACHE_DIR',str(cache))
    monkeypatch.setattr(science_jobs,'ROOT',tmp_path/'jobs')
    asset=roi.register(REAL.read_bytes())
    region=centered_region(210.8022671,54.34895,10)
    response=client.post('/api/v1/science/workflow/jobs',json={'kind':'extract','asset_id':asset['asset_id'],'region':region.model_dump(),'hdu_index':1,'channel':0})
    assert response.status_code==202
    job_id=response.json()['id'];deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        job=client.get('/api/v1/science/workflow/jobs/'+job_id).json()
        if job['status'] not in ('QUEUED','RUNNING'):break
        assert client.get('/api/v1/health').status_code==200
        time.sleep(.1)
    assert job['status']=='SUCCEEDED',job
    product=job['result'];assert product['cube_shape']==[102,67,67]
    assert product['statistics']['valid_pixels']==3750
    assert product['statistics']['roi_pixels']==4489
    report=science_analysis.analyze(product['product_id'])
    assert len(report['channels'])==102
    assert report['channels'][0]['valid_pixels']==3750
    assert report['temporal']['status']=='BLOCKED'
    assert not report['temporal']['real_zogy_executed']
    assert report['ml']['status']=='BLOCKED'
    with fits.open(cache/f"product-{product['product_id']}.fits") as h:
        data=h['SCIENCE'].data[0];mask=h['VALID_MASK'].data[0].astype(bool)
        assert np.median(data[mask])==report['channels'][0]['median']
        np.testing.assert_allclose(np.sum(data[mask],dtype=float),report['channels'][0]['sum_image_units'])
    assert client.get(f'/api/v1/science/workflow/jobs/{job_id}/result').json()==product


def test_temporal_does_not_reuse_fixed_target_report(index):
    result=science_analysis.temporal(centered_region(269.446,4.768,10))
    assert result['status']=='BLOCKED' and not result['observations'] and not result['pairs']
    assert not result['temporal_variability_claimed']


def test_ml_contract_finite_triplet_and_provenance(tmp_path,monkeypatch):
    stamp=tmp_path/'stamp.npz';np.savez(stamp,stamp=np.ones((3,63,63)))
    assert ml_inputs.read_stamp(stamp).shape==(3,63,63)
    manifest=tmp_path/'ml.json'
    record={'id':'registered','path':str(stamp),'product_ids':['product'],'wcs_aligned':True,'psf_matched':True,'band_compatible':True,'quality_applied':True,'real_epochs':True}
    manifest.write_text(json.dumps([record]));monkeypatch.setenv('MORLEY_ML_TRIPLETS',str(manifest))
    monkeypatch.delenv('ETER_ML_WEIGHTS',raising=False);monkeypatch.delenv('ETER_ML_PYTHON',raising=False)
    state=ml_inputs.eligibility('product')
    assert state['compatible_triplets']==['registered'] and not state['model_available']
    assert ml_inputs.eligibility('unrelated')['compatible_triplets']==[]
    record['real_epochs']=False;manifest.write_text(json.dumps([record]))
    assert ml_inputs.eligibility('product')['compatible_triplets']==[]
    np.savez(stamp,stamp=np.ones((102,67,67)))
    with pytest.raises(ValueError,match='3,63,63'):ml_inputs.read_stamp(stamp)
    a=np.ones((3,63,63));a[0,0,0]=np.nan;np.savez(stamp,stamp=a)
    with pytest.raises(ValueError,match='finitos'):ml_inputs.read_stamp(stamp)


def test_job_validation_and_restart_recovery(tmp_path,monkeypatch):
    monkeypatch.setattr(science_jobs,'ROOT',tmp_path)
    assert client.post('/api/v1/science/workflow/jobs',json={'kind':'train'}).status_code==422
    assert client.post('/api/v1/science/workflow/jobs',json={'kind':'extract'}).status_code==422
    science_jobs.write({'id':'a'*32,'status':'RUNNING','result':None})
    assert science_jobs.get('a'*32)['status']=='FAILED'
    assert client.get('/api/v1/science/workflow/jobs/not-a-job').status_code==404


def test_catalog_epoch_association_checks_observation_position(index,monkeypatch):
    from astropy.wcs import WCS
    w=WCS(naxis=2);w.wcs.ctype=['RA---TAN','DEC--TAN'];w.wcs.crval=[269.44626788,4.76820441];w.wcs.crpix=[50,50];w.wcs.cdelt=[-1/3600,1/3600]
    entry={'id':'x','path':'/not/exposed','filename':'epoch.fits','shape':[100,100],'wcs':dict(w.to_header()),'center':{'ra':269.44626788,'dec':4.76820441},'footprint_icrs':w.calc_footprint(axes=(100,100)).tolist(),'date_obs':'2000-01-01T12:00:00','mtime_ns':0,'offline_record':{}}
    monkeypatch.setattr(local_fits,'entries',lambda:[entry])
    # The 2026 point is in the image, but Barnard's actual 2000 location is outside.
    assert local_fits.search(269.44626788,4.76820441)['products']
    assert not local_fits.search(269.44626788,4.76820441,target_id='barnard')['products']

@pytest.mark.skipif(not REAL.exists(),reason='ROI_TEST_FITS required')
def test_worker_rejects_different_region_before_extracting(tmp_path,monkeypatch):
    from app.services.science_worker import execute
    monkeypatch.setattr(roi,'CACHE',tmp_path/'cache')
    asset=roi.register(REAL.read_bytes())
    with pytest.raises(ValueError,match='no cubre'):
        execute({'kind':'extract','asset_id':asset['asset_id'],'region':centered_region(269.446,4.768,10).model_dump(),'hdu_index':1,'channel':0})
