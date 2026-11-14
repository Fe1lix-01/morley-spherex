"use client";

import { useEffect, useId, useRef, type ChangeEvent } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Slider from "@mui/material/Slider";
import Typography from "@mui/material/Typography";
import FileUploadOutlined from "@mui/icons-material/FileUploadOutlined";
import HelpOutlined from "@mui/icons-material/HelpOutlined";
import { eter, glassPanel, RING_ANGLE, selectedRing } from "@/lib/theme";
import { glowSliderParts } from "@/lib/glow";
import AnimatedButton from "@/components/ui/AnimatedButton";
import type { ControlOption } from "@/lib/viewer/types";

/* ------------------------------------------------------------------ */
/* Chips de filtros                                                    */
/* ------------------------------------------------------------------ */

type FilterChipsProps = {
  options: ControlOption[];
  /** Índice de la opción activa. */
  current: number;
  onSelect: (index: number) => void;
};

/** Fila de chips: uno activo a la vez, con scroll horizontal en pantallas pequeñas. */
export function FilterChips({ options, current, onSelect }: FilterChipsProps) {
  return (
    <Box
      role="group"
      aria-label="Filtros de luz"
      sx={{
        display: "flex",
        gap: 0.75,
        overflowX: "auto",
        mx: -0.5,
        px: 0.5,
        pb: 0,
        scrollbarWidth: "none",
        "&::-webkit-scrollbar": { display: "none" },
      }}
    >
      {options.map((f, i) => {
        const on = i === current;
        return (
          <Chip
            key={f.id}
            label={f.name}
            clickable
            aria-pressed={on}
            onClick={() => onSelect(i)}
            // Siempre "outlined": el seleccionado ya no se rellena, solo cambia el borde.
            variant="outlined"
            sx={{
              flexShrink: 0,
              height: 30,
              borderRadius: "999px",
              fontSize: 13,
              "& .MuiChip-label": { px: 1.5 },
              ...(on
                ? {
                    // El borde propio se oculta y lo reemplaza el aro de luz (-1px = cubre el borde).
                    ...selectedRing("-1px", "inherit"),
                    borderColor: "transparent",
                    backgroundColor: "transparent",
                    color: "#fff",
                    "&:hover": { backgroundColor: eter.hoverFill, borderColor: "transparent" },
                  }
                : {
                    borderColor: eter.lineStrong,
                    color: eter.textMuted,
                    "&:hover": {
                      backgroundColor: "transparent",
                      borderColor: eter.lineHover,
                      color: "#fff",
                    },
                  }),
            }}
          />
        );
      })}
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/* Slider con etiqueta                                                 */
/* ------------------------------------------------------------------ */

type LabeledSliderProps = {
  label: string;
  value: number;
  min: number;
  max: number;
  disabled?: boolean;
  /** Versión delgada: sin los números de mínimo y máximo. */
  compact?: boolean;
  onChange: (value: number) => void;
};

// Velocidad máxima del giro del aro de la perilla y qué tan rápido acelera o frena.
const SPIN_DEG_PER_SEC = 150;
const EASE_RATE = 6;
// Tras soltar, el aro sigue girando un momento mientras frena (también cubre el teclado).
const LINGER_MS = 400;

/** Slider con etiqueta, valor y límites mínimo y máximo. */
export function LabeledSlider({ label, value, min, max, disabled, compact, onChange }: LabeledSliderProps) {
  // useId liga la etiqueta con el slider para que los lectores de pantalla lo anuncien.
  const labelId = useId();

  const rootRef = useRef<HTMLSpanElement>(null);
  // Estado del giro. Vive en un ref porque cambia en cada fotograma y no debe redibujar React.
  const spin = useRef({ angle: RING_ANGLE, speed: 0, dir: 1, holding: false, until: 0 });
  // Arranca el bucle de animación si estaba detenido (lo asigna el efecto de abajo).
  const kick = useRef<() => void>(() => {});

  useEffect(() => {
    // Quien prefiere menos movimiento ve la perilla con el aro quieto.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let raf = 0;
    let last = 0;

    const frame = (now: number) => {
      const s = spin.current;
      const dt = Math.min((now - last) / 1000, 0.05); // tope: evita saltos si la pestaña estuvo en segundo plano
      last = now;

      const active = s.holding || now < s.until;
      const target = active ? s.dir * SPIN_DEG_PER_SEC : 0;
      // Acercamiento exponencial a la velocidad objetivo: arranca y frena sin tirones.
      s.speed += (target - s.speed) * (1 - Math.exp(-dt * EASE_RATE));
      s.angle = (s.angle + s.speed * dt) % 360;
      rootRef.current?.style.setProperty("--ring-angle", `${s.angle}deg`);

      // El bucle se detiene solo cuando el aro ya frenó del todo.
      raf = active || Math.abs(s.speed) > 0.5 ? requestAnimationFrame(frame) : 0;
    };

    kick.current = () => {
      if (raf) return;
      last = performance.now();
      raf = requestAnimationFrame(frame);
    };

    return () => cancelAnimationFrame(raf);
  }, []);

  // 0 en el mínimo, 1 en el máximo: sirve igual para 0–100 y para 10–300.
  const p = max > min ? Math.min(Math.max((value - min) / (max - min), 0), 1) : 0;

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <Typography id={labelId} sx={{ fontSize: compact ? 12 : 15, color: "rgba(255,255,255,0.9)" }}>
          {label}
        </Typography>
        <Typography sx={{ fontSize: compact ? 12 : 14, fontWeight: 500, color: "#fff" }}>{value} %</Typography>
      </Box>

      <Slider
        ref={rootRef}
        aria-labelledby={labelId}
        getAriaValueText={(v) => `${v} %`}
        value={value}
        min={min}
        max={max}
        disabled={disabled}
        valueLabelDisplay="off"
        // MUI entrega number | number[]; aquí siempre es un solo valor.
        onChange={(_, v) => {
          const next = Array.isArray(v) ? v[0] : v;
          const s = spin.current;
          // Derecha = sentido horario (+1), izquierda = antihorario (-1).
          if (next !== value) s.dir = next > value ? 1 : -1;
          s.holding = true;
          kick.current();
          onChange(next);
        }}
        onChangeCommitted={() => {
          const s = spin.current;
          s.holding = false;
          s.until = performance.now() + LINGER_MS;
          kick.current();
        }}
        sx={{
          height: 2,
          mt: compact ? 0 : 0.5,
          // Sin animación CSS: el giro del aro lo mueve el script de arriba, según la dirección.
          ...glowSliderParts(p, false),
          py: compact ? "6px" : undefined,
          "&.Mui-disabled": { opacity: 0.35 },
        }}
      />

      {!compact && (
        <Box sx={{ display: "flex", justifyContent: "space-between", mt: -0.5 }}>
          <Typography variant="caption" sx={{ color: "text.disabled" }}>
            {min} %
          </Typography>
          <Typography variant="caption" sx={{ color: "text.disabled" }}>
            {max} %
          </Typography>
        </Box>
      )}
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/* Panel de controles                                                  */
/* ------------------------------------------------------------------ */

// Estilo de los botones discretos (Ayuda, Escena demo). Está fuera del componente
// para que no se vuelva a crear en cada render.
const quietButton = {
  minWidth: 0,
  fontSize: { xs: 13, sm: 14 },
  color: eter.textMuted,
  "&:hover": { color: "#fff", backgroundColor: "transparent" },
} as const;

type Props = {
  /** Opciones que se muestran como chips (hoy los filtros de luz). */
  filters: ControlOption[];
  current: number;
  onSelect: (index: number) => void;
  /** Desactiva el slider "Aplicación del filtro" (p. ej. cuando no hay filtro activo). */
  intensityDisabled: boolean;
  inten: number;
  gain: number;
  onInten: (value: number) => void;
  onGain: (value: number) => void;
  onUpload: (file: File) => void;
  onDemo: () => void;
  onHelp: () => void;
  isDemo: boolean;
};

export default function ControlPanel({
  filters,
  current,
  onSelect,
  intensityDisabled,
  inten,
  gain,
  onInten,
  onGain,
  onUpload,
  onDemo,
  onHelp,
  isDemo,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    e.target.value = ""; // permite subir el mismo archivo otra vez
  };

  return (
    <Paper
      component="section"
      aria-label="Controles del visor"
      elevation={0}
      sx={{
        ...glassPanel,
        borderRadius: "22px",
        // MUI agrega un degradado claro a los Paper en modo oscuro; se anula para
        // que el vidrio se vea parejo.
        backgroundImage: "none",
        px: { xs: 1.5, sm: 2 },
        py: { xs: 1, sm: 1.25 },
        // Barra delgada en dos filas: filtros arriba; sliders y botones abajo.
        display: "flex",
        flexDirection: "column",
        gap: 1,
      }}
    >
      <FilterChips options={filters} current={current} onSelect={onSelect} />

      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", sm: "row" },
          alignItems: { xs: "stretch", sm: "center" },
          gap: { xs: 1, sm: 2.5 },
        }}
      >
        {/* Sliders */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: { xs: 2, sm: 3 },
            flex: "1 1 auto",
            minWidth: 0,
          }}
        >
          <LabeledSlider
            compact
            label="Aplicación del filtro"
            value={inten}
            min={0}
            max={100}
            disabled={intensityDisabled}
            onChange={onInten}
          />
          <LabeledSlider compact label="Intensidad de luz" value={gain} min={10} max={300} onChange={onGain} />
        </Box>

        {/* Ayuda · Subir imagen · Escena demo */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 1,
            flex: "0 0 auto",
          }}
        >
          <Button
            color="inherit"
            size="small"
            startIcon={<HelpOutlined />}
            onClick={onHelp}
            sx={{ ...quietButton, fontSize: 12, whiteSpace: "nowrap" }}
          >
            Ayuda
          </Button>

          <AnimatedButton
            onClick={() => fileRef.current?.click()}
            style={{ whiteSpace: "nowrap", padding: "6px 14px", fontSize: 12 }}
          >
            <FileUploadOutlined sx={{ fontSize: 16 }} />
            Subir imagen
          </AnimatedButton>

          <input ref={fileRef} type="file" accept="image/*" hidden onChange={handleFile} />

          <Button
            color="inherit"
            size="small"
            onClick={onDemo}
            // Indica a lectores de pantalla si la escena demo es la que está activa.
            aria-pressed={isDemo}
            startIcon={
              <Box
                component="span"
                sx={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  backgroundColor: isDemo ? "rgba(255,255,255,0.8)" : "rgba(255,255,255,0.25)",
                }}
              />
            }
            sx={{ ...quietButton, fontSize: 12, whiteSpace: "nowrap", color: "rgba(255,255,255,0.7)" }}
          >
            Escena demo
          </Button>
        </Box>
      </Box>
    </Paper>
  );
}