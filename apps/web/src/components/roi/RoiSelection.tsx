"use client";
import { useEffect, useRef, useState, type PointerEvent } from "react";
import { coordinate, defaultRegion, dragRegion, resizeRegion, screenRegion, type Coordinate, type Region, type RoiView } from "@/lib/roi";

type Gesture = { original: Region | null; start: number[]; sky: Coordinate; corner: number | null; mode: "draw" | "move" | "resize" };
type Projection = { points: number[][]; limit: string };

/** Visual-only interaction. The astronomical region is never derived from zoom/FOV. */
export default function RoiSelection({view,region,drawing,editing,max,onChange,onDone,onError}: {
  view: RoiView | null; region: Region | null; drawing: boolean; editing: boolean; max: number;
  onChange: (r: Region) => void; onDone: () => void; onError: (message: string) => void;
}) {
  const gesture=useRef<Gesture|null>(null);
  const [drag,setDrag]=useState<number[][]|null>(null);
  const [projection,setProjection]=useState<Projection>({points:[],limit:""});
  useEffect(()=>{
    if(!view || !region)return;
    let frame=0;
    const project=(r:Region)=>r.corners.map(c=>view.world2pix(c.ra,c.dec));
    function tick(){
      try{
        const points=project(region!);
        const limit=project(defaultRegion(region!.center,max,max));
        const valid=(ps:(number[]|null|undefined)[])=>ps.every(p=>p && p.every(Number.isFinite));
        const next={points:valid(points)?points as number[][]:[],limit:valid(limit)?limit.map(p=>p!.join(",")).join(" "):""};
        setProjection(prev=>JSON.stringify(prev)===JSON.stringify(next)?prev:next);
      }catch{setProjection(prev=>prev.points.length?{points:[],limit:""}:prev);}
      frame=requestAnimationFrame(tick);
    }
    frame=requestAnimationFrame(tick);
    return ()=>cancelAnimationFrame(frame);
  },[view,region,max]);
  function local(e:PointerEvent<SVGSVGElement>){const r=e.currentTarget.getBoundingClientRect();return [e.clientX-r.left,e.clientY-r.top];}
  function update(e:PointerEvent<SVGSVGElement>){
    const g=gesture.current;
    if(!g||!view)return;
    const p=local(e);
    if(g.mode==="draw"){setDrag([g.start,p]);return;}
    try{
      const sky=coordinate(view.pix2world(p[0],p[1],"ICRS"));
      onChange(g.mode==="move"?dragRegion(g.original!,g.sky,sky,max):resizeRegion(g.original!,g.corner!,sky,max));
    }catch(error){onError(error instanceof Error?error.message:String(error));}
  }
  const polygon=projection.points.map(p=>p.join(",")).join(" ");
  return <svg aria-label="Selección rectangular del cielo" width="100%" height="100%"
    style={{position:"absolute",inset:0,pointerEvents:drawing?"auto":"none",touchAction:"none",cursor:drawing?"crosshair":undefined,zIndex:2}}
    onPointerDown={e=>{
      if(!view||(!drawing&&!editing)||e.button!==0)return;
      const target=e.target as SVGElement, corner=target.getAttribute("data-corner"), movable=target.getAttribute("data-move");
      if(!drawing&&corner===null&&!movable)return;
      const p=local(e);
      try{
        gesture.current={original:region,start:p,sky:coordinate(view.pix2world(p[0],p[1],"ICRS")),corner:corner===null?null:Number(corner),mode:drawing?"draw":corner!==null?"resize":"move"};
        e.currentTarget.setPointerCapture(e.pointerId);e.stopPropagation();e.preventDefault();
        if(drawing)setDrag([p,p]);
      }catch(error){onError(String(error));}
    }}
    onPointerMove={update}
    onPointerCancel={()=>{const original=gesture.current?.original;gesture.current=null;setDrag(null);if(original)onChange(original);onDone();}}
    onPointerUp={e=>{
      const g=gesture.current;if(!g)return;
      update(e);gesture.current=null;setDrag(null);
      if(g.mode==="draw"&&view){
        try{onChange(screenRegion(view,g.start,local(e),max));}catch(error){onError(error instanceof Error?error.message:String(error));}
        onDone();
      }
      e.currentTarget.releasePointerCapture(e.pointerId);
    }}>
    {region&&projection.limit&&<polygon aria-label={`Límite ${max} minutos de arco`} points={projection.limit} fill="none" stroke="#ffcf70" strokeWidth={1.5} strokeDasharray="6 4"/>}
    {region&&polygon&&<polygon data-move="true" aria-label="Mover región" points={polygon} fill="rgba(71,220,211,.15)" stroke="#47dcd3" strokeWidth={2} style={{pointerEvents:editing?"auto":"none",cursor:"move"}}/>}
    {region&&editing&&projection.points.map((p,i)=><circle key={i} data-corner={i} aria-label={`Redimensionar esquina ${i+1}`} cx={p[0]} cy={p[1]} r={7} fill="#47dcd3" stroke="#081321" strokeWidth={2} style={{pointerEvents:"auto",cursor:i%2?"nesw-resize":"nwse-resize"}}/>)}
    {drag&&<rect x={Math.min(drag[0][0],drag[1][0])} y={Math.min(drag[0][1],drag[1][1])} width={Math.abs(drag[1][0]-drag[0][0])} height={Math.abs(drag[1][1]-drag[0][1])} fill="rgba(71,220,211,.15)" stroke="#47dcd3" strokeDasharray="5 3"/>}
  </svg>;
}
