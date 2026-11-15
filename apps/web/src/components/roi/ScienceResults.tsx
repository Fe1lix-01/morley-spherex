"use client";
import {useState} from "react";
import {Alert,Button,Typography,Box} from "@mui/material";
import type {RoiProduct} from "@/services/roi-api";
import {workflowApi,type ScienceAnalysis} from "@/services/workflow-api";

export default function ScienceResults({product}:{product:RoiProduct}){
 const [analysis,setAnalysis]=useState<ScienceAnalysis|null>(null),[jobId,setJobId]=useState("");
 const [state,setState]=useState(""),[error,setError]=useState("");
 const [inference,setInference]=useState<unknown>(null);
 const running=state==="QUEUED"||state==="RUNNING";
 async function run(){setError("");try{
  const job=await workflowApi.run<ScienceAnalysis>({kind:"analysis",product_id:product.product_id},j=>{setState(j.status);setJobId(j.id);});setAnalysis(job.result);
 }catch(e){setState("FAILED");setError(String(e));}}
 return <Box>
  <Button disabled={running} onClick={()=>void run()}>Analizar FITS y comprobar épocas</Button>
  {state&&<Typography role="status">Análisis: {state}</Typography>}
  {error&&<Alert severity="error">{error}</Alert>}
  {analysis&&<>
   <Typography>Resumen científico: {analysis.status} · {analysis.channels.length} planos</Typography>
   <Typography variant="caption">Medianas y sumas regionales calculadas sobre la máscara científica; sin ajustes visuales.</Typography>
   <details><summary>Tabla espectral / fotométrica de la ROI</summary>
    <Box sx={{maxHeight:240,overflow:"auto"}}><table><thead><tr><th>Canal</th><th>λ (µm)</th><th>Válidos</th><th>Mediana ({analysis.unit})</th><th>Suma (mJy)</th></tr></thead><tbody>
     {analysis.channels.map(r=><tr key={r.channel_index}><td>{r.channel_ordinal}</td><td>{typeof r.spectral_metadata?.WAVELENGTH?.value==="number"?r.spectral_metadata.WAVELENGTH.value.toFixed(3):"—"}</td><td>{r.valid_pixels}</td><td>{r.median?.toPrecision(5)??"—"}</td><td>{r.integrated_valid_pixels_mJy?.toPrecision(5)??"—"}</td></tr>)}
    </tbody></table></Box>
   </details>
   {analysis.limitations.map(t=><Typography key={t} variant="caption" sx={{display:"block"}}>{t}</Typography>)}
   <Typography>Multiepoca: {analysis.temporal.status}</Typography>
   <Typography variant="caption">{analysis.temporal.reason}</Typography>
   <Typography>{analysis.temporal.observations.length} observaciones · {analysis.temporal.pairs.length} pares evaluados</Typography>
   <Typography>CNN: {analysis.ml.status}</Typography>
   <Typography variant="caption">{analysis.ml.reason} {analysis.ml.missing.join(", ")}</Typography>
   {analysis.ml.status==="PASS"&&analysis.ml.compatible_triplets.map(id=><Button key={id} disabled={running} onClick={()=>{
    void workflowApi.run({kind:"inference",product_id:product.product_id,triplet_id:id},j=>setState(j.status)).then(j=>setInference(j.result)).catch(e=>{setState("FAILED");setError(String(e));});
   }}>Inferencia experimental: {id}</Button>)}
   {inference!==null&&<pre>{JSON.stringify(inference,null,2)}</pre>}
   <a href={workflowApi.resultUrl(jobId)}>Descargar análisis JSON</a>
  </>}
 </Box>;
}
