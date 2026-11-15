"""Analytical synthetic tests; remote calls are stubbed, never bulk downloads."""
import json
from io import BytesIO

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS, Sip
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.services import roi
from science.pipeline.region import Region, centered_region
from science.pipeline.fits_roi import inspect_fits, extract_roi


@pytest.fixture
def sample(tmp_path):
    w = WCS(naxis=2)
    w.wcs.crpix = [60.5, 60.5]
    w.wcs.crval = [359.99, 70]
    w.wcs.cdelt = [-1/600, 1/600]
    angle = np.deg2rad(27)
    w.wcs.pc = [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    h = w.to_header(); h["BUNIT"] = "MJy/sr"
    yy, xx = np.indices((120, 120))
    data = (yy*120+xx).astype(float)
    data[60, 60] = np.nan
    flags = np.zeros_like(data, dtype=np.int16); flags[59, 59] = 1
    hits = np.ones_like(flags); hits[58, 58] = 0
    path = tmp_path / "test_D2_roi.fits"
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data, h, name="IMAGE"),
                  fits.ImageHDU(flags, h, name="FLAGS"), fits.ImageHDU(hits, h, name="NHITS"),
                  fits.ImageHDU(np.ones_like(data), h, name="VARIANCE")]).writeto(path)
    return path, w


@pytest.mark.parametrize("ra,dec", [(359.99,70),(.01,-80),(0,90),(180,-90)])
def test_region_wrap_poles(ra, dec):
    region = centered_region(ra, dec)
    assert region.width_arcmin == pytest.approx(10, abs=.001)
    assert region.contains(region.center.sky())
    assert region.center.sky().separation(region.boundary()).arcmin.max() < 7.08


def test_validation():
    with pytest.raises(ValidationError): centered_region(1, 0, 21)
    region = centered_region(0,0).model_dump()
    region["width_arcmin"] = 1
    with pytest.raises(ValidationError): Region.model_validate(region)
    region = centered_region(0,0).model_dump()
    region["corners"][1], region["corners"][2] = region["corners"][2], region["corners"][1]
    with pytest.raises(ValidationError): Region.model_validate(region)
    with pytest.raises(ValidationError): centered_region(float("nan"),0)


def test_pixels_wcs_and_quality(sample,tmp_path):
    path, original_wcs = sample
    output = tmp_path / "cut.fits"
    assert inspect_fits(path)["extensions"][1]["wcs"]["CTYPE1"] == "RA---TAN"
    result = extract_roi(path, centered_region(359.99,70,6),output,1)
    with fits.open(output) as cut, fits.open(path) as original:
        x0,y0 = result["pixel_origin"]
        h,w = cut["SCIENCE"].data.shape
        np.testing.assert_array_equal(cut["SCIENCE"].data,original["IMAGE"].data[y0:y0+h,x0:x0+w])
        for name in ["FLAGS","NHITS","VARIANCE"]:
            np.testing.assert_array_equal(cut[name].data,original[name].data[y0:y0+h,x0:x0+w])
        yy,xx=np.indices((h,w))
        new_wcs = WCS(cut["SCIENCE"].header)
        assert np.max(new_wcs.pixel_to_world(xx,yy).separation(original_wcs.pixel_to_world(xx+x0,yy+y0)).arcsec)<1e-6
        mask = cut["VALID_MASK"].data.astype(bool)
        assert result["statistics"]["median"] == np.median(cut["SCIENCE"].data[mask])
        assert result["statistics"]["std"] == np.std(cut["SCIENCE"].data[mask])
        assert result["statistics"]["roi_pixels"]-result["statistics"]["valid_pixels"] == 3
        assert not result["clipped_to_image"]
        assert cut["SCIENCE"].header["BUNIT"] == "MJy/sr"


def test_no_overlap_and_channel_bounds(sample,tmp_path):
    path,_=sample
    with pytest.raises(ValueError): extract_roi(path,centered_region(150,0),tmp_path/"no.fits",1)
    with pytest.raises(ValueError): extract_roi(path,centered_region(359.99,70),tmp_path/"no.fits",1,1)
    with pytest.raises(ValueError): extract_roi(path,centered_region(359.99,70),tmp_path/"no.fits",0)


def test_partial_coverage(sample,tmp_path):
    path,w=sample
    c=w.pixel_to_world(10,60).icrs
    result=extract_roi(path,centered_region(c.ra.deg,c.dec.deg,10),tmp_path/"partial.fits",1)
    assert result["clipped_to_image"]


def test_cube_channel_and_sip(tmp_path):
    w=WCS(naxis=2);w.wcs.crpix=[30,30];w.wcs.crval=[10,-20];w.wcs.cdelt=[-.002,.002];w.wcs.ctype=["RA---TAN-SIP","DEC--TAN-SIP"]
    a=np.zeros((3,3));a[2,0]=1e-5
    w.sip=Sip(a,np.zeros((3,3)),None,None,w.wcs.crpix)
    p=tmp_path/"sip.fits"
    fits.PrimaryHDU(np.ones((60,60)),w.to_header(relax=True)).writeto(p)
    result=extract_roi(p,centered_region(10,-20,3),tmp_path/"sip-cut.fits")
    with fits.open(tmp_path/"sip-cut.fits") as h:
        cw=WCS(h["SCIENCE"].header);x,y=result["pixel_origin"]
        assert cw.pixel_to_world(2,3).separation(w.pixel_to_world(2+x,3+y)).arcsec<1e-6
    w.sip=None;w.wcs.ctype=["RA---TAN","DEC--TAN"]
    p=tmp_path/"cube.fits"
    fits.PrimaryHDU(np.stack([np.ones((60,60)),np.full((60,60),7)]),w.to_header()).writeto(p)
    result=extract_roi(p,centered_region(10,-20,3),tmp_path/"cube-cut.fits",channel=1)
    assert result["statistics"]["median"] == 7
    assert result["source"]["product_kind"] == "spectral_cube"


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(roi,"CACHE",tmp_path/"cache")
    return TestClient(app)


def test_endpoints_local_roundtrip(client,sample):
    path,_=sample
    r=client.post("/api/v1/science/roi/files",content=path.read_bytes())
    assert r.status_code == 200,r.text
    payload={"asset_id":r.json()["asset_id"],"region":centered_region(359.99,70,6).model_dump(),"hdu_index":1}
    r=client.post("/api/v1/science/roi/products",json=payload)
    assert r.status_code==200,r.text
    assert client.post("/api/v1/science/roi/products",json=payload).json()==r.json()
    key=r.json()["product_id"]
    for format,mime in [("fits","application/fits"),("json","application/json"),("png","image/png")]:
        response=client.get(f"/api/v1/science/roi/products/{key}/{format}")
        assert response.status_code==200
        assert response.headers["content-type"].startswith(mime)
    payload["region"]["width_arcmin"]=21
    assert client.post("/api/v1/science/roi/products",json=payload).status_code==422


def test_upload_limits_and_bad_fits(client,monkeypatch):
    assert client.post("/api/v1/science/roi/files",content=b"invalid").status_code==422
    monkeypatch.setattr(roi,"MAX_BYTES",3)
    assert client.post("/api/v1/science/roi/files",content=b"1234").status_code==413


def test_remote_consent_allowlist_and_cache(client,sample,monkeypatch):
    url="https://irsa.ipac.caltech.edu/ibe/data/spherex/test.fits"
    calls=[]
    monkeypatch.setattr(roi,"_fetch_cutout",lambda *args:(calls.append(args) or sample[0].read_bytes()))
    route="/api/v1/science/roi/files/import"
    assert client.post(route,json={"url":url}).status_code==409
    assert calls==[]
    for bad in ["http://127.0.0.1/x.fits","https://irsa.ipac.caltech.edu.evil/data/SPHEREx/x.fits",url+"?x=1",url.replace("test.fits","../x.fits")]:
        assert client.post(route,json={"url":bad,"confirm_download":True}).status_code==422
    for _ in range(2):
        assert client.post(route,json={"url":url,"confirm_download":True}).status_code==200
    assert len(calls)==1


def test_local_import_reuses_observations(client,sample,monkeypatch):
    monkeypatch.setattr(roi,"FITS_DIR",sample[0].parent)
    assert client.post("/api/v1/science/roi/files/import",json={"filename":sample[0].name}).status_code==200
    assert client.post("/api/v1/science/roi/files/import",json={"filename":"../secret.fits"}).status_code==422


def test_sia_roi_validation(client):
    response=client.get("/api/v1/sia/observations",params={"ra":0,"dec":0,"roi":"{}"})
    assert response.status_code==422


def test_sia_polygon_and_cache(client,monkeypatch):
    from app.clients.sia import SiaClient
    from app.schemas.sia import SiaResponse
    from app.services import sia
    calls=[]
    monkeypatch.setattr(SiaClient,"fetch_observations",lambda self,q:(calls.append(q) or None))
    monkeypatch.setattr(sia,"transform_sia_results",lambda t,q:SiaResponse(collection=q.collection,query=q,count=0,observations=[]))
    params={"ra":359.99,"dec":70,"roi":centered_region(359.99,70).model_dump_json()}
    for _ in range(2): assert client.get("/api/v1/sia/observations",params=params).status_code==200
    assert len(calls)==1


def test_real_fits_when_configured(tmp_path):
    import os
    from pathlib import Path
    source=os.getenv("ROI_TEST_FITS")
    if not source:
        pytest.skip("ROI_TEST_FITS no configurado; no se descargan datos para esta prueba")
    source=Path(source)
    info=inspect_fits(source)
    ext=next(e for e in info["extensions"] if e["processable"] and e["name"]=="IMAGE")
    region=centered_region(**ext["center"])
    output=tmp_path/"real.fits"
    channel=min(62,ext["channels"]-1)
    result=extract_roi(source,region,output,ext["index"],channel)
    with fits.open(source) as original, fits.open(output) as cut:
        x0,y0=result["pixel_origin"];ny,nx=cut["SCIENCE"].shape[-2:]
        image=original[ext["index"]]
        expected=image.section[:,y0:y0+ny,x0:x0+nx] if len(image.shape)==3 else image.section[y0:y0+ny,x0:x0+nx]
        np.testing.assert_array_equal(cut["SCIENCE"].data,expected)
        yy,xx=np.indices((ny,nx))
        error=WCS(cut["SCIENCE"].header,cut).celestial.pixel_to_world(xx,yy).separation(WCS(image.header,original).celestial.pixel_to_world(xx+x0,yy+y0)).arcsec
        assert error.max()<1e-6
        for name in ("FLAGS","NHITS","VARIANCE"):
            if name in original:
                assert name in cut
                h=original[name]
                expected=h.section[:,y0:y0+ny,x0:x0+nx] if len(h.shape)==3 else h.section[y0:y0+ny,x0:x0+nx]
                np.testing.assert_array_equal(cut[name].data,expected)


def test_all_masked_result_is_json_safe(client,sample):
    path,_=sample
    with fits.open(path,mode="update") as h:
        h["FLAGS"].data[:]=1
    asset=client.post("/api/v1/science/roi/files",content=path.read_bytes()).json()
    r=client.post("/api/v1/science/roi/products",json={"asset_id":asset["asset_id"],"hdu_index":1,"region":centered_region(359.99,70,6).model_dump()})
    assert r.status_code==200,r.text
    assert r.json()["statistics"]["median"] is None
    assert r.json()["statistics"]["masked_percent"]==100
    assert client.get('/api/v1/science/roi/products/'+r.json()["product_id"]+'/png').status_code==200


def test_sia_client_sends_real_polygon_parameter(monkeypatch):
    import httpx
    from astropy.table import Table
    from app.clients import sia as client_module
    from app.schemas.sia import SiaQuery
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,content=b"stub VOTable")
    http_client=httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(client_module.httpx,"Client",lambda **kwargs:http_client)
    monkeypatch.setattr(client_module,"parse_sia_response",lambda content:Table())
    region=centered_region(359.99,70)
    client_module.SiaClient().fetch_observations(SiaQuery(ra=359.99,dec=70,roi=region.model_dump_json()))
    assert requests[0].url.params["POS"] == "POLYGON " + " ".join(f"{c.ra} {c.dec}" for c in region.corners)


def test_sia_rejects_reference_fields_different_from_region(client,monkeypatch):
    from app.clients.sia import SiaClient
    def no_network(*args):
        pytest.fail("Inconsistent geometry must fail before contacting IRSA")
    monkeypatch.setattr(SiaClient,"fetch_observations",no_network)
    region=centered_region(1.746153,-2.373896)
    response=client.get('/api/v1/sia/observations',params={'ra':210.8023,'dec':54.349,'roi':region.model_dump_json()})
    assert response.status_code==422
    assert 'no coinciden' in response.text
