import assert from 'node:assert/strict';
import { test } from 'node:test';
import { GET } from '../src/app/api/sky-hips/[...path]/route.ts';

test('HiPS deduplicates, preserves bytes/provenance, falls back and rejects arbitrary paths', async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async url => {
    calls.push(String(url));
    if (String(url).includes('irsa.ipac')) throw new Error('offline');
    return new Response(new Uint8Array([255,216,255,217]));
  };
  const request = new Request('http://localhost/api/sky-hips/Norder3/Allsky.jpg');
  const context = {params: Promise.resolve({path:['Norder3','Allsky.jpg']})};
  try {
    const results = await Promise.all([GET(request,context),GET(request,context)]);
    assert.equal(calls.length,2);
    for (const response of results) {
      assert.equal(response.status,200);
      assert.equal(response.headers.get('X-HiPS-Survey'),'AllWISE RGB-W4-W2-W1');
      assert.match(response.headers.get('X-HiPS-Upstream'),/china-vo/);
      assert.deepEqual([...new Uint8Array(await response.arrayBuffer())],[255,216,255,217]);
    }
    await GET(request,context); assert.equal(calls.length,2);
    assert.equal((await GET(request,{params:Promise.resolve({path:['..','secret']})})).status,400);
    globalThis.fetch = async()=>{throw new Error('offline');};
    assert.equal((await GET(request,{params:Promise.resolve({path:['properties']})})).status,503);
  } finally { globalThis.fetch = original; }
});

test('SPHEREx frame addressing covers all 102 native indices without changing physical labels', async () => {
  const {spherexFrameAddress} = await import('../src/lib/spherex-hips.ts');
  const {getSpherexChannel} = await import('../src/data/spherexChannels.ts');
  for (let channel = 1; channel <= 102; channel++) {
    const address = spherexFrameAddress(channel);
    const bin = Math.floor((1/address - 1/5.009e-6) / (1/7.43e-7 - 1/5.009e-6) * 102);
    assert.equal(bin,channel-1);
  }
  assert.equal(getSpherexChannel(62).wavelengthUm,3.204);
  assert.equal(getSpherexChannel(63).wavelengthUm,3.293);
  assert.throws(()=>spherexFrameAddress(0),RangeError);
  assert.throws(()=>spherexFrameAddress(103),RangeError);
});
