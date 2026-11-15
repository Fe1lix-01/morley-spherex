import type { Region } from "@/lib/roi";
const base=(process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/$/,"");
export type FitsExtension={index:number;name:string;shape:number[];unit:string|null;processable:boolean;center:{ra:number;dec:number}|null;channels:number};
export type FitsAsset={asset_id:string;extensions:FitsExtension[];product_kind:string};
export type RoiProduct={pipeline_version:number;cube_shape:number[];channels_preserved:number;channel_index:number;pixel_scale_arcsec:number[];mask_policy:{id:string;retained_flags:string[]};visualization:{vmin:number;vmax:number};region:Region;product_id:string;shape:number[];unit:string|null;clipped_to_image:boolean;statistics:{roi_pixels:number;finite_pixels:number;valid_pixels:number;masked_percent:number;median:number|null;std:number|null;mad:number|null;quality_pixels:number;flags?:Record<string,number>}};
export type Observation={product_id:string;observation_id:string;band:string;start_utc:string;access_url:string;access_format:string};
export class RoiApiError extends Error {
  readonly kind:"connection"|"http"|"irsa"|"download"|"contract";
  readonly status?:number;
  constructor(message:string, kind:RoiApiError["kind"], status?:number){super(message);this.kind=kind;this.status=status;}
}
export function sameRegion(a:Region,b:Region):boolean {
  return !!a && !!b && a.corners?.length===4 && b.corners?.length===4 &&
    Math.abs(a.center.ra-b.center.ra)<1e-8 && Math.abs(a.center.dec-b.center.dec)<1e-8 &&
    Math.abs(a.width_arcmin-b.width_arcmin)<1e-8 && Math.abs(a.height_arcmin-b.height_arcmin)<1e-8 &&
    a.corners.every((c,i)=>Math.abs(c.ra-b.corners[i].ra)<1e-8&&Math.abs(c.dec-b.corners[i].dec)<1e-8);
}
async function request<T>(path:string, init?:RequestInit):Promise<T>{
  let response:Response;
  try{response=await fetch(`${base}${path}`,init);}
  catch{throw new RoiApiError(`No se pudo conectar con el backend en ${base}. Comprueba que FastAPI esté activo, el puerto y CORS. No se recibió una respuesta de IRSA.`,"connection");}
  if(!response.ok){
    const body=await response.json().catch(()=>null);
    const detail=typeof body?.detail==="string"?body.detail:JSON.stringify(body?.detail??"Sin detalles");
    const download=path.endsWith("/files/import");
    const irsa=path.startsWith("/sia/")&&[502,503,504].includes(response.status);
    const label=download?"Descarga FITS fallida":irsa?"Error del servicio IRSA":"Error HTTP del backend";
    throw new RoiApiError(`${label} (HTTP ${response.status}): ${detail}`,download?"download":irsa?"irsa":"http",response.status);
  }
  return response.json();
}
const post=<T>(path:string,body:unknown)=>request<T>(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
export const roiApi={
  config:()=>request<{max_arcmin:number;default_arcmin:number;max_fits_bytes:number}>("/science/roi/config"),
  search:async(region:Region,band:string)=>{
    const snapshot=structuredClone(region);
    const result=await request<{observations:Observation[];query:{roi:string}}>(`/sia/observations?${new URLSearchParams({ra:String(snapshot.center.ra),dec:String(snapshot.center.dec),roi:JSON.stringify(snapshot),band,limit:"20"})}`);
    let echoed:Region|null=null;
    try{echoed=JSON.parse(result.query?.roi);}catch{}
    if(!echoed||!sameRegion(snapshot,echoed))throw new RoiApiError("La región devuelta por SIA no coincide con la selección enviada.","contract");
    return result;
  },
  upload:(file:File)=>request<FitsAsset>("/science/roi/files",{method:"POST",headers:{"Content-Type":"application/fits"},body:file}),
  importRemote:(url:string)=>post<FitsAsset>("/science/roi/files/import",{url,confirm_download:true}),
  process:async(asset_id:string,region:Region,hdu_index:number,channel:number)=>{
    const snapshot=structuredClone(region);
    const result=await post<RoiProduct>("/science/roi/products",{asset_id,region:snapshot,hdu_index,channel});
    if(!sameRegion(snapshot,result.region))throw new RoiApiError("La región del producto FITS no coincide con la selección enviada.","contract");
    return result;
  },
  productUrl:(id:string,format:"fits"|"json"|"png",view:"raw"|"masked"|"quality"="masked",stretch:"asinh"|"linear"="asinh")=>`${base}/science/roi/products/${id}/${format}${format==="png"?`?view=${view}&stretch=${stretch}`:""}`,
};
