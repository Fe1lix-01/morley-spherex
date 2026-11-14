"use client";

import { useEffect, useRef, useState, type PointerEvent, type ReactNode } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Add from "@mui/icons-material/Add";
import Remove from "@mui/icons-material/Remove";
import RestartAlt from "@mui/icons-material/RestartAlt";
import type { Frame } from "@/data/contracts";
import { ViewerCanvas } from "@/components/viewer/ViewerShell";
import { useSpectralScene } from "@/hooks/useSpectralScene";
import type { FilterDef } from "@/lib/viewer/types";
import { skyToImage } from "@/lib/model/projection";
import type { SkyPoint } from "@/lib/model/trajectory";

/* ------------------------------------------------------------------ */
/* EpochLayer: una época como capa propia                              */
/* ------------------------------------------------------------------ */

type EpochLayerProps = {
  imageUrl: string;
  filter: FilterDef;
  inten: number;
  gain: number;
  /** 0 = invisible, 1 = totalmente visible. Lo controla la animación. */
  opacity: number;
  onError: (message: string | null) => void;
};

/**
 * Una época como capa propia: su canvas con los mismos filtros del visor. Cada época
 * mantiene su imagen cargada todo el tiempo, y la animación solo cambia la opacidad,
 * así no hay recargas ni parpadeos al pasar de una a otra.
 */
export function EpochLayer({ imageUrl, filter, inten, gain, opacity, onError }: EpochLayerProps) {
  const { canvasRef, error } = useSpectralScene(filter, inten, gain, imageUrl);

  useEffect(() => {
    if (error) onError(error);
  }, [error, onError]);

  return (
    <Box sx={{ position: "absolute", inset: 0, opacity }}>
      <ViewerCanvas canvasRef={canvasRef} />
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/* MarkerLayer: marcadores sobre el canvas                             */
/* ------------------------------------------------------------------ */

export type Marker = { id: string; label: string; ra: number; dec: number };

/**
 * Capa de marcadores encima del canvas del visor. Usa porcentajes, así que se acomoda
 * sola al tamaño de la pantalla, igual que el canvas que se estira a toda la pantalla.
 */
export function MarkerLayer({ frame, markers }: { frame: Frame; markers: Marker[] }) {
  return (
    <Box sx={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {markers.map((m) => {
        const p = skyToImage(m.ra, m.dec, frame);
        if (!p) return null;
        return (
          <Box
            key={m.id}
            sx={{
              position: "absolute",
              left: `${p.x * 100}%`,
              top: `${p.y * 100}%`,
              transform: "translate(-50%, -50%)",
              width: 18,
              height: 18,
              border: "2px solid #FFD54F",
              borderRadius: "50%",
            }}
          >
            <Box
              component="span"
              sx={{ position: "absolute", left: 22, top: -4, color: "#FFD54F", fontSize: 12, whiteSpace: "nowrap" }}
            >
              {m.label}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/* PanZoom: arrastrar y ampliar                                        */
/* ------------------------------------------------------------------ */

type View = { scale: number; x: number; y: number };

const MIN_SCALE = 1;
const MAX_SCALE = 8;
const START: View = { scale: 1, x: 0, y: 0 };

/** Mantiene la imagen cubriendo la pantalla: no deja ver los bordes vacíos. */
const clamp = (v: View, w: number, h: number): View => ({
  scale: v.scale,
  x: Math.min(0, Math.max(w - w * v.scale, v.x)),
  y: Math.min(0, Math.max(h - h * v.scale, v.y)),
});

/** Cambia el zoom multiplicando por `factor`, manteniendo fijo el punto (cx, cy). */
const zoomView = (v: View, factor: number, cx: number, cy: number, w: number, h: number): View => {
  const s = Math.min(MAX_SCALE, Math.max(MIN_SCALE, v.scale * factor));
  const k = s / v.scale;
  return clamp({ scale: s, x: cx - (cx - v.x) * k, y: cy - (cy - v.y) * k }, w, h);
};

const zoomButtonSx = {
  color: "#fff",
  border: "1px solid rgba(255,255,255,0.25)",
  backgroundColor: "rgba(0,0,0,0.45)",
  backdropFilter: "blur(6px)",
  "&:hover": { backgroundColor: "rgba(255,255,255,0.18)" },
};

/**
 * Hace que todo lo que lleva dentro (canvas + marcadores) se pueda arrastrar y ampliar.
 * Rueda o dos dedos en el touchpad = zoom hacia el cursor. Arrastrar = mover.
 * Botones + / − / reiniciar a un costado. Doble clic = volver al inicio.
 */
export function PanZoom({ children }: { children: ReactNode }) {
  const [view, setView] = useState<View>(START);
  const box = useRef<HTMLDivElement>(null);
  const drag = useRef<{ px: number; py: number; x: number; y: number } | null>(null);

  // El listener va "a mano" para poder bloquear el scroll de la página con preventDefault.
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      // deltaMode 1 = líneas (algunos navegadores): se convierte a píxeles.
      const dy = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
      // El pellizco del touchpad llega con ctrlKey y deltas pequeños: se amplifica.
      const speed = e.ctrlKey ? 0.012 : 0.003;
      setView((v) => zoomView(v, Math.exp(-dy * speed), e.clientX - r.left, e.clientY - r.top, r.width, r.height));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const zoomFromCenter = (factor: number) => {
    const el = box.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setView((v) => zoomView(v, factor, r.width / 2, r.height / 2, r.width, r.height));
  };

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { px: e.clientX, py: e.clientY, x: view.x, y: view.y };
  };

  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    const el = box.current;
    if (!d || !el) return;
    const r = el.getBoundingClientRect();
    setView((v) =>
      clamp({ scale: v.scale, x: d.x + e.clientX - d.px, y: d.y + e.clientY - d.py }, r.width, r.height),
    );
  };

  const endDrag = () => {
    drag.current = null;
  };

  return (
    <Box
      ref={box}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onDoubleClick={() => setView(START)}
      sx={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        touchAction: "none",
        cursor: "grab",
        "&:active": { cursor: "grabbing" },
      }}
    >
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          transformOrigin: "0 0",
          transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})`,
        }}
      >
        {children}
      </Box>

      {/* Botones de zoom. Detienen el clic para que no cuente como arrastre de la imagen. */}
      <Box
        onPointerDown={(e) => e.stopPropagation()}
        onDoubleClick={(e) => e.stopPropagation()}
        sx={{
          position: "absolute",
          left: 16,
          top: "50%",
          transform: "translateY(-50%)",
          display: "flex",
          flexDirection: "column",
          gap: 1,
          cursor: "default",
        }}
      >
        <IconButton aria-label="Acercar" onClick={() => zoomFromCenter(1.5)} sx={zoomButtonSx}>
          <Add />
        </IconButton>
        <IconButton aria-label="Alejar" onClick={() => zoomFromCenter(1 / 1.5)} sx={zoomButtonSx}>
          <Remove />
        </IconButton>
        <IconButton aria-label="Reiniciar vista" onClick={() => setView(START)} sx={zoomButtonSx}>
          <RestartAlt />
        </IconButton>
      </Box>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/* TrailLayer: rastro del objeto                                       */
/* ------------------------------------------------------------------ */

type TrailLayerProps = {
  frame: Frame;
  /** Posiciones medidas del objeto, una por época en la que se detectó. */
  points: (SkyPoint & { index: number })[];
  /** Instante actual de la animación (0 = primera época). */
  t: number;
};

/**
 * Rastro del objeto: línea punteada por donde se mueve y un punto por cada época.
 * Los puntos se rellenan cuando la animación ya pasó por esa época.
 */
export function TrailLayer({ frame, points, t }: TrailLayerProps) {
  const placed = points.flatMap((p) => {
    const pos = skyToImage(p.ra, p.dec, frame);
    return pos ? [{ ...p, ...pos }] : [];
  });
  if (placed.length === 0) return null;

  const line = placed.map((p) => `${p.x * 100},${p.y * 100}`).join(" ");

  return (
    <Box sx={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {placed.length > 1 && (
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          style={{ position: "absolute", inset: 0 }}
        >
          <polyline
            points={line}
            fill="none"
            stroke="rgba(255,213,79,0.6)"
            strokeWidth={1.5}
            strokeDasharray="5 5"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      )}
      {placed.map((p) => (
        <Box
          key={p.index}
          sx={{
            position: "absolute",
            left: `${p.x * 100}%`,
            top: `${p.y * 100}%`,
            width: 8,
            height: 8,
            transform: "translate(-50%, -50%)",
            borderRadius: "50%",
            border: "1.5px solid #FFD54F",
            bgcolor: t >= p.index - 0.001 ? "#FFD54F" : "transparent",
          }}
        />
      ))}
    </Box>
  );
}