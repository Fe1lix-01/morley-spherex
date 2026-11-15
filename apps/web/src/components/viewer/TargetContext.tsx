"use client";
import {createContext,useCallback,useContext,useEffect,useMemo,useState,type ReactNode} from "react";
import {skyData} from "@/data/services";
import type {MovingObject} from "@/data/contracts";
import {workflowApi,type ScienceTarget} from "@/services/workflow-api";
export type SelectedTarget={id:string;name:string;ra:number;dec:number;epoch:number|null;source?:string;note?:string};
type State={target:SelectedTarget|null;targets:ScienceTarget[];objects:MovingObject[];error:string;choose:(target:SelectedTarget|null)=>void;pick:(id:string)=>void;openRoi:()=>void};
const Context=createContext<State|null>(null);
export const useTarget=()=>useContext(Context);
export function TargetProvider({children,onOpenRoi}:{children:ReactNode;onOpenRoi:()=>void}){
 const [target,choose]=useState<SelectedTarget|null>(null);
 const [targets,setTargets]=useState<ScienceTarget[]>([]),[legacy,setLegacy]=useState<MovingObject[]>([]),[error,setError]=useState("");
 useEffect(()=>{let active=true;skyData.getObjects().then(r=>{if(active)setLegacy(r.objects);}).catch(e=>{if(active)setError(String(e));});workflowApi.targets().then(r=>{if(active)setTargets(r);}).catch(e=>{if(active)setError(`Catálogo científico no disponible: ${e}`);});return()=>{active=false;};},[]);
 const objects=useMemo(()=>[...legacy,...targets.filter(t=>!legacy.some(o=>o.id===t.id)).map(t=>({id:t.id,name:t.name,kind:t.kind,summary:t.note,positions:[{epochId:"catalog",ra:t.ra,dec:t.dec}]}))], [legacy,targets]);
 const pick=useCallback((id:string)=>{const t=targets.find(t=>t.id===id);if(t){choose(t);return;}const o=objects.find(o=>o.id===id);const p=o?.positions[0];if(o&&p)choose({id:o.id,name:o.name??o.id,ra:p.ra,dec:p.dec,epoch:null,note:"Coordenadas de vista previa; época astrométrica no verificada."});},[targets,objects]);
 return <Context.Provider value={{target,targets,objects,error,choose,pick,openRoi:onOpenRoi}}>{children}</Context.Provider>;
}
