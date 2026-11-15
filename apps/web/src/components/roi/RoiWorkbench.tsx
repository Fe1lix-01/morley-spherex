"use client";
import { useEffect, useState } from "react";
import { Alert, Box, Button, Checkbox, FormControlLabel, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { coordinate, defaultRegion, focusRegion, type Region, type RoiView } from "@/lib/roi";
import { roiApi, RoiApiError, type FitsAsset, type Observation, type RoiProduct } from "@/services/roi-api";
import RoiSelection from "./RoiSelection";

/** Mounted in the same positioned container as the existing Aladin view. */
export default function RoiWorkbench({view}: {view: RoiView | null}) {
  const [region,setRegion]=useState<Region|null>(null);
  const [drawing,setDrawing]=useState(false);
  const [editing,setEditing]=useState(false);
  const [confirmed,setConfirmed]=useState(false);
  const [destinationDirty,setDestinationDirty]=useState(false);
  const [apiStatus,setApiStatus]=useState("Comprobando backend local…");
  const [collapsed,setCollapsed]=useState(false);
  const [config,setConfig]=useState({max_arcmin:20,default_arcmin:10,max_fits_bytes:128*1024**2});
  const [error,setError]=useState("");
  const [busy,setBusy]=useState("");
  const [observations,setObservations]=useState<Observation[]|null>(null);
  const [selected,setSelected]=useState("");
  const [consent,setConsent]=useState(false);
  const [asset,setAsset]=useState<FitsAsset|null>(null);
  const [hdu,setHdu]=useState(0);
  const [channel,setChannel]=useState(0);
  const [product,setProduct]=useState<RoiProduct|null>(null);
  const [stretch,setStretch]=useState<"asinh"|"linear">("asinh");
  const [band,setBand]=useState("SPHEREx-D2");
  const [ra,setRa]=useState(""), [dec,setDec]=useState("");
  function checkApi(){
    roiApi.config().then(c=>{setConfig(c);setApiStatus("Backend conectado");}).catch(e=>setApiStatus(e.message));
  }
  useEffect(()=>{checkApi();},[]);
  function changeRegion(r:Region|null){
    setRegion(r);setConfirmed(false);setProduct(null);setObservations(null);setSelected("");setConsent(false);setDestinationDirty(false);
    if(r){setRa(String(r.center.ra));setDec(String(r.center.dec));}
    else{setRa("");setDec("");setEditing(false);setDrawing(false);}
  }
  async function run(label:string, action:()=>Promise<void>){setBusy(label);setError("");try{await action();setApiStatus("Backend conectado");}catch(e){if(e instanceof RoiApiError&&e.kind==="connection")setApiStatus(e.message);setError(e instanceof Error?e.message:String(e));}finally{setBusy("");}}
  function acceptAsset(next:FitsAsset){setAsset(next);setHdu(next.extensions.find(e=>e.processable)?.index??0);setChannel(0);setProduct(null);}
  const extension=asset?.extensions.find(e=>e.index===hdu);
  function centerRegion(center:{ra:number;dec:number},size=config.default_arcmin){
    const next=defaultRegion(center,size,config.max_arcmin);
    changeRegion(next);setEditing(true);setError("");
    if(view){const dimensions=view.getSize?.()??[1,1];focusRegion(view,next,config.max_arcmin,dimensions[0]/dimensions[1]);}
  }
  function activateSelection(){
    try{
      const center=destinationDirty?coordinate([Number(ra),Number(dec)]):view?coordinate(view.getRaDec()):region?.center;
      if(!center)throw new Error("El visor aún no está disponible. También puedes abrir un FITS local.");
      if(destinationDirty&&(!ra.trim()||!dec.trim()))throw new Error("Indica RA y Dec del destino.");
      centerRegion(center);
      if(window.innerWidth<700)setCollapsed(true);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
  }
  return <>
    <RoiSelection view={view} region={region} drawing={drawing && !busy} editing={editing && !busy && !destinationDirty} max={config.max_arcmin} onChange={changeRegion} onDone={()=>setDrawing(false)} onError={setError}/>
    <Box component="section" aria-label="Procesamiento de región FITS" sx={{position:"absolute",right:12,top:60,zIndex:3,width:{xs:"min(340px, calc(100% - 24px))",md:350},maxHeight:"calc(100% - 80px)",overflowY:"auto",p:2,borderRadius:2,color:"#eef3ff",background:"rgba(9,18,33,.95)",border:"1px solid #3a5269",pointerEvents:"auto",
      "& .MuiInputBase-root":{color:"#eef3ff"},"& .MuiInputLabel-root":{color:"#b9cadc"},
      "& .MuiOutlinedInput-notchedOutline":{borderColor:"#64809a"},"& .MuiSvgIcon-root":{color:"#b9cadc"}
    }}>
      <Stack direction="row" sx={{alignItems:"center",justifyContent:"space-between"}}>
        <Typography variant="subtitle1">Región científica · FITS</Typography>
        <Button size="small" onClick={()=>drawing?setDrawing(false):setCollapsed(v=>!v)}>{drawing?"Cancelar dibujo":collapsed?"Abrir":"Ocultar"}</Button>
      </Stack>
      <Stack spacing={1.5} sx={{display:drawing||collapsed?"none":"flex",mt:1}}>
        <Typography variant="caption">{apiStatus} <Button size="small" disabled={!!busy} onClick={checkApi}>Comprobar conexión</Button></Typography>
        <Typography variant="caption">ICRS · máximo {config.max_arcmin}′ × {config.max_arcmin}′. El mosaico HiPS orienta la selección; los datos se extraen del FITS.</Typography>
        <Typography variant="caption">Destino ICRS: aplica los campos antes de confirmar la región.</Typography>
        <Stack direction="row" spacing={1}>
          <TextField disabled={!!busy} label="RA (°)" size="small" type="number" value={ra} onChange={e=>{setRa(e.target.value);setDestinationDirty(true);setConfirmed(false);}} />
          <TextField disabled={!!busy} label="Dec (°)" size="small" type="number" value={dec} onChange={e=>{setDec(e.target.value);setDestinationDirty(true);setConfirmed(false);}} />
        </Stack>
        <Button disabled={!!busy} onClick={()=>{try{if(!ra.trim()||!dec.trim())throw new Error("Indica RA y Dec");centerRegion(coordinate([Number(ra),Number(dec)]));}catch(e){setError(String(e));}}}>Aplicar centro</Button>
        <Button disabled={!view||!!busy} variant="contained" onClick={activateSelection}>Seleccionar región</Button>
        <Stack direction="row" spacing={1}>
          <Button variant={drawing?"contained":"outlined"} disabled={!view||!region||!!busy||destinationDirty} onClick={()=>{
            const dimensions=view!.getSize?.()??[1,1];focusRegion(view!,region!,config.max_arcmin,dimensions[0]/dimensions[1]);
            setConfirmed(false);setEditing(true);setDrawing(v=>!v);
          }}>{drawing?"Cancelar dibujo":"Dibujar / reemplazar"}</Button>
          <Button disabled={!region||!!busy} onClick={()=>changeRegion(null)}>Eliminar</Button>
        </Stack>
        {region && <>
          <Typography variant="caption">Marco dorado: {config.max_arcmin}′ × {config.max_arcmin}′ centrado en la selección. Arrastra el interior para moverla o las esquinas para cambiar su tamaño.</Typography>
          <Stack direction="row" spacing={1}>
            <Button disabled={!!busy||destinationDirty} onClick={()=>centerRegion(region.center,config.max_arcmin)}>Usar tamaño máximo</Button>
            <Button disabled={!!busy||destinationDirty} onClick={()=>centerRegion(region.center,config.default_arcmin)}>Restablecer {config.default_arcmin}′ × {config.default_arcmin}′</Button>
          </Stack>
          <Button disabled={!!busy||destinationDirty||confirmed} variant="outlined" onClick={()=>{setConfirmed(true);setEditing(false);setDrawing(false);}}>Confirmar región</Button>
          {confirmed&&<Typography role="status">Región confirmada para consulta y extracción.</Typography>}
          <Button disabled={!!busy||destinationDirty} onClick={()=>{setEditing(true);setConfirmed(false);}}>Editar región</Button>
        </>}
        {region && <Box data-testid="roi-coordinates" data-region={JSON.stringify(region)}>
          <Typography variant="body2">Centro {region.center.ra.toFixed(6)}°, {region.center.dec.toFixed(6)}° · {region.width_arcmin.toFixed(2)}′ × {region.height_arcmin.toFixed(2)}′</Typography>
          <details><summary>Cuatro esquinas ICRS</summary>{region.corners.map((c,i)=><Typography key={i} variant="caption" sx={{display:"block"}}>{i+1}: {c.ra.toFixed(6)}°, {c.dec.toFixed(6)}°</Typography>)}</details>
        </Box>}
        <TextField select label="Detector SPHEREx" size="small" value={band} disabled={!!busy} onChange={e=>{setBand(e.target.value);setObservations(null);setSelected("");setConsent(false);}}>{[1,2,3,4,5,6].map(i=><MenuItem key={i} value={`SPHEREx-D${i}`}>D{i}</MenuItem>)}</TextField>
        <Button disabled={!region||!confirmed||destinationDirty||!!busy} onClick={()=>void run("Consultando IRSA…",async()=>{setSelected("");setConsent(false);setObservations((await roiApi.search(region!,band)).observations);})}>Consultar observaciones</Button>
        {observations && <>
          <Typography variant="caption">{observations.length===0?"Región sin observaciones para este detector.":`${observations.length} observaciones individuales SIA (hasta 20).`} La intersección no garantiza cobertura completa.</Typography>
          {observations.length>0 && <>
            <TextField select label="Producto FITS remoto" size="small" value={selected} disabled={!!busy} onChange={e=>{setSelected(e.target.value);setConsent(false);}}>
              {observations.filter(o=>o.access_format.toLowerCase().includes("fits")).map(o=><MenuItem key={o.product_id} value={o.access_url}>{o.start_utc} · {o.observation_id}</MenuItem>)}
            </TextField>
            <FormControlLabel control={<Checkbox checked={consent} onChange={e=>setConsent(e.target.checked)}/>} label={`Confirmo descargar este FITS (máximo ${Math.round(config.max_fits_bytes/1024**2)} MiB; tamaño remoto desconocido).`}/>
            <Button disabled={!selected||!consent||!!busy} onClick={()=>void run("Descargando FITS…",async()=>acceptAsset(await roiApi.importRemote(selected)))}>Descargar e inspeccionar</Button>
          </>}
        </>}
        <Button component="label" variant="outlined" disabled={!!busy}>Abrir FITS local
          <input hidden type="file" accept=".fits,.fit,.fts" onChange={e=>{const file=e.target.files?.[0];e.target.value="";if(!file)return;if(file.size>config.max_fits_bytes){setError("El archivo supera el límite de transferencia.");return;}void run("Inspeccionando FITS…",async()=>acceptAsset(await roiApi.upload(file)));}}/>
        </Button>
        {asset && <>
          <Typography variant="caption">{asset.product_kind === "spectral_cube"?"Cubo espectral: sus canales no son épocas.":"Imagen 2D: consulta las fechas en los metadatos del producto."}</Typography>
          <TextField select label="Extensión científica" size="small" disabled={!!busy} value={hdu} onChange={e=>{setHdu(Number(e.target.value));setChannel(0);setProduct(null);}}>
            {asset.extensions.filter(e=>e.processable).map(e=><MenuItem key={e.index} value={e.index}>{e.index}: {e.name} [{e.shape.join(" × ")}] {e.unit??"sin unidad"}</MenuItem>)}
          </TextField>
          <TextField label={`Canal (índice 0–${(extension?.channels??1)-1})`} size="small" type="number" value={channel} disabled={!!busy} onChange={e=>{setChannel(Number(e.target.value));setProduct(null);}} slotProps={{htmlInput:{min:0,max:(extension?.channels??1)-1,step:1}}}/>
          <Button disabled={!extension?.center||!!busy} onClick={()=>{try{centerRegion(extension!.center!);}catch(e){setError(String(e));}}}>Seleccionar centro del FITS</Button>
          <Button variant="contained" disabled={!region||!confirmed||destinationDirty||!!busy||!Number.isInteger(channel)||channel<0||channel>=(extension?.channels??1)} onClick={()=>void run("Extrayendo región…",async()=>{setProduct(null);setProduct(await roiApi.process(asset.asset_id,region!,hdu,channel));})}>Extraer región</Button>
        </>}
        {busy && <Typography role="status">{busy}</Typography>}
        {error && <Alert severity="error" onClose={()=>setError("")}>{error}</Alert>}
        {product && <>
          <Typography variant="body2">Canal índice {product.channel_index} (ordinal {product.channel_index+1}). El FITS conserva {product.channels_preserved} planos: {product.cube_shape.join(" × ")} en orden NumPy.</Typography>
          <TextField select label="Escala de visualización" size="small" value={stretch} onChange={e=>setStretch(e.target.value as "asinh"|"linear")}>
            <MenuItem value="asinh">Asinh (estructuras débiles)</MenuItem><MenuItem value="linear">Lineal</MenuItem>
          </TextField>
          <Typography variant="caption">Las dos vistas científicas usan los mismos límites de percentil 0.5–99.5 de la imagen original. Cambiar la escala no modifica el FITS, las máscaras ni las estadísticas.</Typography>
          {([
            ["raw","Imagen científica original"],
            ["masked","Imagen con máscara de calidad aplicada"],
            ["quality","Máscara binaria de calidad"],
          ] as const).map(([view,label])=><Box key={view} component="figure" sx={{m:0}}>
            <Typography component="figcaption" variant="caption">{label}{view==="quality"?" · blanco: aceptado; negro: rechazado":""}</Typography>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={roiApi.productUrl(product.product_id,"png",view,stretch)} alt={label} style={{width:"100%",imageRendering:"pixelated"}}/>
          </Box>)}
          <Typography variant="caption">Matriz contenedora mínima: {product.shape.join(" × ")} píxeles · {product.unit??"unidad no declarada"}. {product.clipped_to_image?"Cobertura parcial: recorte limitado al archivo.":"Región dentro del archivo."}</Typography>
          <Typography variant="caption">Escala WCS: {product.pixel_scale_arcsec.map(v=>v.toFixed(3)).join(" × ")} arcsec/píxel. Política: {product.mask_policy.id}. SOURCE se conserva solo si la política del producto lo identifica como informativo; OUTLIER/OVERFLOW y los controles de cobertura/calidad se evalúan por separado.</Typography>
          {product.statistics.flags&&<Typography variant="caption">FLAGS=0: {product.statistics.flags.zero}; SOURCE: {product.statistics.flags.SOURCE??"no definido"}; OUTLIER: {product.statistics.flags.OUTLIER??"no definido"}; OVERFLOW: {product.statistics.flags.OVERFLOW??"no definido"}. Los bits pueden coexistir.</Typography>}
          {product.statistics.roi_pixels!==product.shape[0]*product.shape[1]&&<Typography variant="caption">La ROI está inclinada respecto a la rejilla: ROI_MASK delimita los píxeles de la selección dentro de esta matriz.</Typography>}
          <Typography variant="body2">Válidos: {product.statistics.valid_pixels}/{product.statistics.roi_pixels}; finitos: {product.statistics.finite_pixels}; enmascarados: {product.statistics.masked_percent.toFixed(2)}%.</Typography>
          <Typography variant="body2">Mediana: {product.statistics.median?.toPrecision(5)??"sin datos"} · σ: {product.statistics.std?.toPrecision(5)??"sin datos"} · MAD: {product.statistics.mad?.toPrecision(5)??"sin datos"}</Typography>
          <Stack direction="row" spacing={2}><a href={roiApi.productUrl(product.product_id,"fits")}>Descargar FITS completo</a><a href={roiApi.productUrl(product.product_id,"json")}>Metadatos JSON</a></Stack>
        </>}
      </Stack>
    </Box>
  </>;
}
