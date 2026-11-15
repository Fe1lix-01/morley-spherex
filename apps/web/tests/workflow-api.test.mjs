import test from 'node:test';
import assert from 'node:assert/strict';
import {workflowApi} from '../src/services/workflow-api.ts';

test('controlled workflow submits once and polls to scientific result',async t=>{
 let posts=0,polls=0;
 t.mock.method(globalThis,'fetch',async(url,init)=>{
  if(init.method==='POST'){posts++;assert.equal(JSON.parse(init.body).kind,'analysis');return Response.json({id:'job',status:'QUEUED',result:null});}
  polls++;return Response.json({id:'job',status:'SUCCEEDED',result:{channels:102}});
 });
 const states=[];const job=await workflowApi.run({kind:'analysis',product_id:'p'},j=>states.push(j.status));
 assert.equal(posts,1);assert.equal(polls,1);assert.deepEqual(states,['QUEUED','SUCCEEDED']);assert.equal(job.result.channels,102);
});
test('job failures and unavailable data remain explicit',async t=>{
 t.mock.method(globalThis,'fetch',async()=>Response.json({id:'j',status:'FAILED',error:'No compatible epochs'}));
 await assert.rejects(workflowApi.run({kind:'temporal'}),/No compatible epochs/);
});
