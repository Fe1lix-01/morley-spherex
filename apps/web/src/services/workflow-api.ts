import type { Region } from "@/lib/roi";
const base=(process.env.NEXT_PUBLIC_API_URL??"http://127.0.0.1:8000/api/v1").replace(/\/$/,"")+"/science/workflow";
export type ScienceTarget={id:string;name:string;kind:"star"|"brown_dwarf";identity:string;ra:number;dec:number;epoch:number;reference_epoch:number;source:string;propagation:string;note:string};
export type LocalProduct={id:string;filename:string;shape:number[];kind:string;derived:boolean;date_obs:string|null;detector:string;unit:string|null;coverage:{status:string;reason:string|null};provenance:{sha256:string;collection:string|null}};
export type LocalSearch={status:string;reason:string|null;indexed:number;products:LocalProduct[]};
export type Job<T=unknown>={id:string;status:"QUEUED"|"RUNNING"|"SUCCEEDED"|"FAILED";result:T;error:string|null};
export type MlCompatibility={status:string;model_available:boolean;missing:string[];compatible_triplets:string[];reason:string|null};
export type TemporalResult={status:string;reason:string;observations:Record<string,unknown>[];pairs:Record<string,unknown>[];real_zogy_executed:boolean};
export type ScienceAnalysis={status:string;kind:string;unit:string;channels:{channel_index:number;channel_ordinal:number;valid_pixels:number;mean:number|null;median:number|null;integrated_valid_pixels_mJy:number|null;spectral_metadata?:Record<string,{value:unknown;unit:string|null}>}[];limitations:string[];temporal:TemporalResult;ml:MlCompatibility;product_id:string};
async function request<T>(path:string,body?:unknown):Promise<T>{
 const r=await fetch(base+path,{method:body===undefined?"GET":"POST",headers:{"Content-Type":"application/json"},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(15000)});
 if(!r.ok){const b=await r.json().catch(()=>({}));throw new Error(typeof b.detail==="string"?b.detail:`HTTP ${r.status}: ${JSON.stringify(b.detail)}`);}
 return r.json();
}
export const workflowApi={
 targets:()=>request<ScienceTarget[]>("/targets"),
 search:(region:Region,target_id?:string)=>request<LocalSearch>("/catalog/search",{region,target_id}),
 start:<T>(body:unknown)=>request<Job<T>>("/jobs",body),
 job:<T>(id:string)=>request<Job<T>>(`/jobs/${id}`),
 resultUrl:(id:string)=>`${base}/jobs/${id}/result`,
 compatibility:(id:string)=>request<MlCompatibility>(`/ml/compatibility?product_id=${encodeURIComponent(id)}`),
 async run<T>(body:unknown,onState?:(job:Job<T>)=>void):Promise<Job<T>>{
  let job=await workflowApi.start<T>(body);onState?.(job);
  const deadline=Date.now()+600000;
  while(job.status==="QUEUED"||job.status==="RUNNING"){
   if(Date.now()>deadline)throw new Error(`Trabajo ${job.id}: consulta su estado; la espera local terminó.`);
   await new Promise(r=>setTimeout(r,600));job=await workflowApi.job<T>(job.id);onState?.(job);
  }
  if(job.status==="FAILED")throw new Error(job.error??"El trabajo científico falló");
  return job;
 }
};
