import test from "node:test";
import assert from "node:assert/strict";
import {coordinate, defaultRegion, screenRegion, separation} from "../src/lib/roi.ts";

test("spherical separation crosses RA zero along short arc",()=>{
  assert.ok(Math.abs(separation({ra:359.99,dec:0},{ra:.01,dec:0})-1.2)<1e-8);
  assert.equal(coordinate([-1,0]).ra,359);
});
test("programmatic squares are ten arcminutes at equator and poles",()=>{
  for(const dec of [0,80,-80,90,-90]){
    const r=defaultRegion({ra:359.99,dec});
    assert.ok(Math.abs(r.width_arcmin-10)<.001);
    assert.ok(Math.abs(r.height_arcmin-10)<.001);
  }
});
test("screen drag converts four corners and center using explicit ICRS",()=>{
  const calls=[];
  const view={pix2world:(x,y,frame)=>{calls.push([x,y,frame]);return [359.99+x*.001,y*.001];}};
  const r=screenRegion(view,[20,20],[0,0]);
  assert.equal(calls.length,5);
  assert.ok(calls.every(c=>c[2]==="ICRS"));
  assert.ok(r.center.ra<.001 || r.center.ra>359.999);
  assert.ok(Math.abs(r.width_arcmin-1.2)<.001);
  assert.deepEqual(calls.slice(1).map(c=>c.slice(0,2)),[[0,0],[20,0],[20,20],[0,20]]);
});
test("invalid projections and size violations are rejected",()=>{
  assert.throws(()=>coordinate([0,NaN]));
  assert.throws(()=>coordinate(null));
  assert.throws(()=>defaultRegion({ra:0,dec:0},21));
  assert.throws(()=>defaultRegion({ra:0,dec:0},10,5));
  assert.throws(()=>screenRegion({pix2world:()=>[1,1]},[0,0],[0,0]));
});

const {moveRegion,resizeRegion,focusRegion}=await import('../src/lib/roi.ts');
test('moving a region preserves spherical dimensions at RA wrap and high declination',()=>{
  for(const dec of [0,85,89.95,-89.95]){
    const original=defaultRegion({ra:359.98,dec},10);
    const moved=moveRegion(original,{ra:.02,dec:Math.min(89.99,dec+.01)});
    assert.ok(Math.abs(original.width_arcmin-moved.width_arcmin)<1e-8);
    assert.ok(Math.abs(original.height_arcmin-moved.height_arcmin)<1e-8);
    assert.equal(moved.center.ra,.02);
  }
});
test('corner resize clamps at maximum while preserving opposite celestial corner',()=>{
  for(const dec of [0,85,89.95,-89.95])for(let index=0;index<4;index++){
    const original=defaultRegion({ra:359.99,dec},10);
    const pointer=defaultRegion(original.center,60,61).corners[index];
    const resized=resizeRegion(original,index,pointer);
    assert.ok(resized.width_arcmin<=20);
    assert.ok(resized.height_arcmin<=20);
    assert.ok(resized.width_arcmin>19.99);
    assert.ok(separation(resized.corners[(index+2)%4],original.corners[(index+2)%4])<1e-8);
  }
});
test('zoom preserves the region and adapts margin for landscape view',()=>{
  const region=defaultRegion({ra:359.99,dec:85});
  const before=JSON.stringify(region),calls=[];
  focusRegion({gotoRaDec:(...a)=>calls.push(a),setFoV:v=>calls.push(v)},region,20,2);
  assert.equal(JSON.stringify(region),before);
  assert.deepEqual(calls[0],[359.99,85]);
  assert.equal(calls[1],1.2);
});
