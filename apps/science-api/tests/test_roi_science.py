"""Regression against independent pixel slices, Cutout2D and published mosaic flag bits."""
import json
import os
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services import roi
from science.pipeline.fits_roi import extract_roi
from science.pipeline.quality import flags_good
from science.pipeline.region import centered_region
from science.pipeline.visualization import render_preview


@pytest.fixture
def real():
    source = os.getenv("ROI_TEST_FITS")
    if not source:
        pytest.skip("ROI_TEST_FITS no configurado; no se descarga ningún archivo")
    return Path(source)


@pytest.fixture
def product(real, tmp_path):
    with fits.open(real) as hdul:
        w = WCS(hdul["IMAGE"].header, hdul).celestial
        c = w.pixel_to_world(100, 100).icrs
    target = tmp_path / "science.fits"
    meta = extract_roi(real, centered_region(c.ra.deg, c.dec.deg), target, 1, 51)
    return target, meta


def test_independent_cutout_dimensions_all_channels_and_wcs(real, product):
    path, meta = product
    with fits.open(real) as source, fits.open(path) as result:
        w = WCS(source["IMAGE"].header, source).celestial
        center = SkyCoord(210.8022671*u.deg, 54.34895*u.deg)
        independent = Cutout2D(source["IMAGE"].data[51], center, (10*u.arcmin,10*u.arcmin), wcs=w)
        assert independent.shape == (67,67)
        assert result["SCIENCE"].shape == (102,67,67)
        assert meta["cube_shape"] == [102,67,67]
        assert meta["shape"] == [67,67]
        assert meta["channels_preserved"] == 102
        ys,xs = independent.slices_original
        assert [xs.start,ys.start] == meta["pixel_origin"] == [67,67]
        np.testing.assert_array_equal(result["SCIENCE"].data,source["IMAGE"].data[:,ys,xs])
        for name in ["FLAGS","NHITS"]:
            np.testing.assert_array_equal(result[name].data,source[name].data[:,ys,xs])
        for name in ["SPECTRAL_CHANNELS","WCS-WAVE"]:
            np.testing.assert_array_equal(result[name].data,source[name].data)
        outw = WCS(result["SCIENCE"].header,result)
        np.testing.assert_allclose(proj_plane_pixel_scales(outw.celestial)*3600,[9,9],atol=1e-10)
        assert outw.celestial.pixel_to_world(33,33).separation(center).arcsec < 1e-7
        yy,xx = np.indices((67,67))
        err = outw.celestial.pixel_to_world(xx,yy).separation(w.pixel_to_world(xx+67,yy+67)).arcsec
        assert np.max(err)<1e-7
        # Compare all spectral coordinates, including the bandwidth axis in this product.
        pixels = np.array([[33,33,k,0] for k in range(102)],dtype=float)
        original_pixels = pixels.copy();original_pixels[:,:2]+=67
        np.testing.assert_allclose(outw.all_pix2world(pixels,0),WCS(source["IMAGE"].header,source).all_pix2world(original_pixels,0),atol=1e-12)
        assert np.all(result["ROI_MASK"].data==1)
        assert result["SCIENCE"].header["BUNIT"]==source["IMAGE"].header["BUNIT"]


def test_quality_and_statistics_match_independent_counts(real,product):
    path, meta = product
    with fits.open(real) as source, fits.open(path) as result:
        # Independent, literal bits from the header/documentation, not the implementation helper.
        data = source["IMAGE"].data[51,67:134,67:134]
        flags = source["FLAGS"].data[51,67:134,67:134]
        hits = source["NHITS"].data[51,67:134,67:134]
        expected = np.isfinite(data)&(hits>0)&((flags & ((1<<19)|(1<<1)))==0)
        assert data.size==4489
        assert np.isfinite(data).sum()==4488
        assert (flags==0).sum()==828
        assert (((flags==0)&np.isfinite(data)&(hits>0)).sum())==827
        assert ((flags&(1<<21))!=0).sum()==3486
        assert ((flags&(1<<19))!=0).sum()==264
        assert ((flags&(1<<1))!=0).sum()==0
        assert expected.sum()==4224
        np.testing.assert_array_equal(result["VALID_MASK"].data[51],expected)
        stats=meta["statistics"]
        assert stats["roi_pixels"]==4489 and stats["finite_pixels"]==4488 and stats["valid_pixels"]==4224
        assert stats["median"]==np.median(data[expected].astype(float))
        assert stats["std"]==np.std(data[expected].astype(float))
        assert stats["flags"]["SOURCE_ONLY"]==3397
        assert meta["mask_policy"]["retained_flags"]==["SOURCE"]
        for k in range(102):
            good=result["VALID_MASK"].data[k].astype(bool)
            assert meta["statistics_by_channel"][k]["valid_pixels"]==int(good.sum())
        embedded=json.loads(result["PROVENANCE"].data.tobytes())
        assert embedded==meta


def test_source_combinations_unknown_and_generic_policy():
    source,outlier,overflow=1<<21,1<<19,1<<1
    data=np.array([0,source,outlier,overflow,source|outlier,source|overflow,source|8,-1])
    np.testing.assert_array_equal(flags_good(data,{"id":"spherex_mosaic_declared_v1"}),[1,1,0,0,0,0,0,0])
    np.testing.assert_array_equal(flags_good(data,{"id":"generic_conservative_v1"}),[1,0,0,0,0,0,0,0])


def test_visualization_does_not_modify_science_and_uses_shared_scale(product):
    path, meta=product
    original=path.read_bytes()
    images={view:np.array(Image.open(BytesIO(render_preview(path,view,"asinh")))) for view in ["raw","masked","quality"]}
    with fits.open(path) as hdul:
        valid=np.flipud(hdul["VALID_MASK"].data[51].astype(bool))
        quality=np.flipud(hdul["QUALITY_MASK"].data[51].astype(bool))
        np.testing.assert_array_equal(images["raw"][valid],images["masked"][valid])
        assert np.all(images["masked"][~valid]==0)
        np.testing.assert_array_equal(images["quality"],quality.astype("uint8")*255)
        assert all(v.shape==(67,67) for v in images.values())
        assert np.any(images["raw"]!=images["masked"])
    assert render_preview(path,"raw","linear")!=render_preview(path,"raw","asinh")
    assert path.read_bytes()==original
    assert meta["statistics"]["valid_pixels"]==4224


def test_downloads_match_returned_metadata_and_real_fits(real,tmp_path,monkeypatch):
    monkeypatch.setattr(roi,"CACHE",tmp_path/"cache")
    client=TestClient(app)
    uploaded=client.post('/api/v1/science/roi/files',content=real.read_bytes()).json()
    region=centered_region(210.8022671,54.34895).model_dump()
    request={"asset_id":uploaded["asset_id"],"region":region,"hdu_index":1,"channel":51}
    response=client.post('/api/v1/science/roi/products',json=request)
    assert response.status_code==200,response.text
    meta=response.json();base='/api/v1/science/roi/products/'+meta['product_id']
    assert meta['pipeline_version']==2
    assert meta['statistics']['valid_pixels']==4224
    assert client.get(base+'/json').json()==meta
    content=client.get(base+'/fits').content
    with fits.open(BytesIO(content),checksum=True) as hdul:
        assert hdul['SCIENCE'].shape==(102,67,67)
        assert int(hdul['VALID_MASK'].data[51].sum())==meta['statistics']['valid_pixels']
        assert json.loads(hdul['PROVENANCE'].data.tobytes())==meta
        for hdu in hdul:
            assert hdu.verify_checksum()==1
    for view in ['raw','masked','quality']:
        r=client.get(base+'/png',params={'view':view,'stretch':'asinh'})
        assert r.status_code==200
        assert Image.open(BytesIO(r.content)).size==(67,67)
    assert client.get(base+'/png',params={'view':'invalid'}).status_code==422
    assert client.post('/api/v1/science/roi/products',json=request).json()==meta
