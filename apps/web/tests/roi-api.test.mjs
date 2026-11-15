import test from 'node:test';
import assert from 'node:assert/strict';
import {roiApi,RoiApiError} from '../src/services/roi-api.ts';
import {defaultRegion} from '../src/lib/roi.ts';
const region=defaultRegion({ra:359.99,dec:85});

test('SIA uses the selected region for center and polygon, and verifies the echoed geometry',async(t)=>{
  t.mock.method(globalThis,'fetch',async(url)=>{
    const q=new URL(url).searchParams;
    assert.equal(Number(q.get('ra')),region.center.ra);
    assert.equal(Number(q.get('dec')),region.center.dec);
    assert.deepEqual(JSON.parse(q.get('roi')),region);
    return Response.json({observations:[],query:{roi:q.get('roi')}});
  });
  assert.deepEqual((await roiApi.search(region,'SPHEREx-D2')).observations,[]);
});
test('processing sends exact displayed region and accepts only matching response',async(t)=>{
  t.mock.method(globalThis,'fetch',async(url,init)=>{
    const body=JSON.parse(init.body);
    assert.deepEqual(body.region,region);
    return Response.json({product_id:'test',region:body.region});
  });
  assert.deepEqual((await roiApi.process('asset',region,1,62)).region,region);
});
test('rejects scientific responses containing a different region',async(t)=>{
  t.mock.method(globalThis,'fetch',async()=>Response.json({region:defaultRegion({ra:10,dec:0})}));
  await assert.rejects(roiApi.process('asset',region,1,62),e=>e instanceof RoiApiError&&e.kind==='contract');
  await assert.rejects(roiApi.search(region,'SPHEREx-D2'),e=>e.kind==='contract');
});
test('network failure is distinguished from HTTP, IRSA, and FITS download errors',async(t)=>{
  const mock=t.mock.method(globalThis,'fetch',async()=>{throw new TypeError('Failed to fetch');});
  await assert.rejects(roiApi.config(),e=>e.kind==='connection');
  mock.mock.mockImplementation(async()=>Response.json({detail:'validation'},{status:422}));
  await assert.rejects(roiApi.config(),e=>e.kind==='http'&&e.status===422);
  mock.mock.mockImplementation(async()=>Response.json({detail:'unavailable'},{status:503}));
  await assert.rejects(roiApi.search(region,'SPHEREx-D2'),e=>e.kind==='irsa');
  await assert.rejects(roiApi.importRemote('https://example.test/a.fits'),e=>e.kind==='download');
});
