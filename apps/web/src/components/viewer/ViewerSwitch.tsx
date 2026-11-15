"use client";

import { useState } from "react";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import PreviewPanel from "@/components/preview/PreviewPanel";
import SpherexMosaic from "./SpherexMosaic";
import {TargetProvider} from "./TargetContext";
import BarnardPanel from "./BarnardPanel";

type Visor = "eter" | "spherex";

/** Alterna entre el visor ÉTER (filtros, épocas, SIMBAD) y el mosaico SPHEREx DR1 de Felix. */
export default function ViewerSwitch() {
  const [mosaicOpened, setMosaicOpened] = useState(false);
  const [visor, setVisor] = useState<Visor>("eter");

  return (
    <TargetProvider onOpenRoi={()=>{setMosaicOpened(true);setVisor("spherex");}}>
      <Box
        sx={{
          position: "fixed",
          top: visor === "eter" ? { xs: 12, lg: "auto" } : 12, bottom: visor === "eter" ? { xs: "auto", lg: 14 } : "auto",
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 2000,
          bgcolor: "rgba(10, 16, 32, 0.85)",
          backdropFilter: "blur(8px)",
          borderRadius: 999,
        }}
      >
        <ToggleButtonGroup
          exclusive
          size="small"
          value={visor}
          onChange={(_, v: Visor | null) => {
            if (v) { setVisor(v); if(v==="spherex")setMosaicOpened(true); requestAnimationFrame(()=>window.dispatchEvent(new Event("resize"))); }
          }}
          aria-label="Cambiar de visor"
        >
          <ToggleButton value="eter">Visor ÉTER</ToggleButton>
          <ToggleButton value="spherex">Mosaico SPHEREx DR1</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <div style={{display:visor==="eter"?"block":"none",height:"100%"}}><PreviewPanel active={visor==="eter"} /></div>
      {mosaicOpened&&<div style={{display:visor==="spherex"?"block":"none",height:"100%"}}><SpherexMosaic /></div>}

      <BarnardPanel />
    </TargetProvider>
  );
}