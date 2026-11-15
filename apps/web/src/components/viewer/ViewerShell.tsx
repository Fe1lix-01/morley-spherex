"use client";

import type { ReactNode, RefObject } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import FiberManualRecord from "@mui/icons-material/FiberManualRecord";
import { CrosshairIcon } from "@/components/ui/CustomIcons";
import { eter } from "@/lib/theme";
import { H, W } from "@/lib/viewer/constants";

/* ------------------------------------------------------------------ */
/* Fondo con filtros (canvas)                                          */
/* ------------------------------------------------------------------ */

/** Fondo con filtros: dibuja la escena en un canvas que cubre toda la pantalla. */
export function ViewerCanvas({ canvasRef }: { canvasRef: RefObject<HTMLCanvasElement | null> }) {
  return (
    <canvas
      ref={canvasRef}
      width={W}
      height={H}
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }}
    />
  );
}

/* ------------------------------------------------------------------ */
/* Encabezado: título, chip del filtro y botón del menú                */
/* ------------------------------------------------------------------ */

// Movimiento de cada línea al abrir el menú: la de arriba y la de abajo giran
// hacia el centro formando una X, y la del medio desaparece.
const OPEN_LINE_STYLE = [
  { transform: "translateY(6px) rotate(45deg)" },
  { opacity: 0 },
  { transform: "translateY(-6px) rotate(-45deg)" },
];

type HeaderProps = {
  /** Texto del chip, por ejemplo "Visible · 0.38–0.75 µm". */
  filterLabel: string;
  menuOpen: boolean;
  onOpenMenu: () => void;
};

function ViewerHeader({ filterLabel, menuOpen, onOpenMenu }: HeaderProps) {
  return (
    <Box
      component="header"
      sx={{
        pointerEvents: "none",
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 2,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        p: { xs: 2, sm: 3.5 },
      }}
    >
      <Box sx={{ pointerEvents: "auto" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Typography
            component="h1"
            sx={{
              // Se ajusta según la pantalla: móvil (xs), tablet (sm) y PC (md).
              fontSize: { xs: 26, sm: 34, md: 40 },
              fontWeight: 400,
              lineHeight: 1.1,
              letterSpacing: "0.03em",
              // Evita desbordamientos si la pantalla es extremadamente pequeña.
              wordBreak: "break-word",
            }}
          >
            Project Morley
          </Typography>
          <Box sx={{ lineHeight: 1.25, mt: 0.5 }}>
            <Typography
              sx={{
                fontSize: { xs: 9, sm: 10 },
                textTransform: "uppercase",
                letterSpacing: "0.14em",
                color: eter.textFaint,
              }}
            >
              Visor espectral
            </Typography>
            <Typography sx={{ fontSize: { xs: 12, sm: 14 }, color: "rgba(255,255,255,0.8)" }}>SPHEREx</Typography>
          </Box>
        </Box>

        <Chip
          variant="outlined"
          icon={<FiberManualRecord />}
          label={filterLabel}
          sx={{
            mt: 1.5,
            height: 34,
            color: "#fff",
            borderColor: eter.lineStrong,
            backgroundColor: eter.glass,
            backdropFilter: "blur(8px)",
            "& .MuiChip-icon": { fontSize: 8, ml: 1.5, mr: -0.5, color: eter.accent },
            "& .MuiChip-label": { fontSize: 14 },
          }}
        />
      </Box>

      {/* Botón de tres líneas */}
      <IconButton
        onClick={onOpenMenu}
        aria-label="Abrir menú"
        aria-expanded={menuOpen}
        sx={{
          pointerEvents: "auto",
          width: { xs: 48, sm: 56 },
          height: { xs: 48, sm: 56 },
          borderRadius: "16px",
          border: `1px solid ${eter.lineStrong}`,
          backgroundColor: eter.glass,
          backdropFilter: "blur(8px)",
          "&:hover": { backgroundColor: "rgba(255,255,255,0.1)" },
        }}
      >
        {/* Las tres líneas se superponen para poder girarlas hacia una X */}
        <Box component="span" sx={{ position: "relative", width: 20, height: 13 }}>
          {[0, 1, 2].map((n) => (
            <Box
              key={n}
              component="span"
              sx={{
                position: "absolute",
                left: 0,
                top: n * 6,
                width: 20,
                height: "1px",
                backgroundColor: "#fff",
                transition: "transform 350ms ease, opacity 200ms ease",
                // Si el usuario pide menos movimiento, el cambio es instantáneo.
                "@media (prefers-reduced-motion: reduce)": { transition: "none" },
                ...(menuOpen ? OPEN_LINE_STYLE[n] : null),
              }}
            />
          ))}
        </Box>
      </IconButton>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/* Frase de abajo                                                      */
/* ------------------------------------------------------------------ */

function ViewerTagline({ sourceLabel }: { sourceLabel: string }) {
  return (
    <Box>
      <Typography sx={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.14em", color: eter.textFaint }}>
        Exploración infrarroja
      </Typography>
      <Typography
        component="h2"
        sx={{
          mt: 0.5,
          fontSize: { xs: 24, lg: 28 },
          fontWeight: 300,
          textShadow: "0 1px 14px rgba(0,0,0,0.6)",
        }}
      >
        Entre el polvo y la luz.
      </Typography>
      <Typography sx={{ mt: 0.5, fontSize: 12, color: "rgba(255,255,255,0.5)" }}>
        {sourceLabel} · Visualización ilustrativa
      </Typography>
    </Box>
  );
}

/* ------------------------------------------------------------------ */
/* Marco de diseño                                                     */
/* ------------------------------------------------------------------ */

type Props = {
  /** Fondo a pantalla completa: el canvas con filtros, el mosaico de Aladin, etc. */
  background: ReactNode;
  /** Panel de controles que va abajo. */
  controls: ReactNode;
  /** Elementos que flotan sobre todo: menú lateral, avisos... */
  overlays?: ReactNode;
  /** Texto del chip del encabezado, por ejemplo "Visible · 0.38–0.75 µm". */
  filterLabel: string;
  /** Texto bajo la frase, por ejemplo "Escena demo". */
  sourceLabel: string;
  menuOpen: boolean;
  onOpenMenu: () => void;
  /** Reemplaza la frase de abajo. Si no se pasa, se muestra la de siempre; con null no se muestra nada. */
  tagline?: ReactNode;
};

/**
 * Marco de diseño de ÉTER: encabezado, frase y panel de controles sobre un fondo
 * intercambiable. El fondo solo necesita llenar el 100 % de su contenedor.
 */
export default function ViewerShell({
  background,
  controls,
  overlays,
  filterLabel,
  sourceLabel,
  menuOpen,
  onOpenMenu,
  tagline,
}: Props) {
  return (
    <Box component="main" sx={{ position: "relative", height: "100%", width: "100%", overflow: "hidden" }}>
      {/* Fondo: ocupa toda la pantalla */}
      <Box sx={{ position: "absolute", inset: 0 }}>{background}</Box>

      {/* Sombras suaves para que el texto se lea sobre cualquier imagen */}
      <Box
        sx={{
          pointerEvents: "none",
          position: "absolute",
          inset: 0,
          background: "linear-gradient(to bottom, rgba(0,0,0,0.5), transparent 30%, transparent 60%, rgba(0,0,0,0.5))",
        }}
      />

      {/* Retícula central */}
      <CrosshairIcon
        sx={{
          pointerEvents: "none",
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%)",
          fontSize: 28,
          color: "rgba(255,255,255,0.4)",
        }}
      />

      <ViewerHeader filterLabel={filterLabel} menuOpen={menuOpen} onOpenMenu={onOpenMenu} />

      {/* Zona inferior: frase + panel de controles */}
      <Box
        sx={{
          pointerEvents: "none",
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 2,
          display: "flex",
          flexDirection: "column",
          alignItems: { lg: "center" },
          p: { xs: 2, sm: 3 },
          pb: { xs: "max(16px, env(safe-area-inset-bottom))", lg: 5 },
        }}
      >
        <Box
          sx={{
            width: { xs: "100%", lg: "56%" },
            maxWidth: { lg: 896 },
            display: "flex",
            flexDirection: "column",
            gap: 2,
          }}
        >
          {tagline !== undefined ? tagline : <ViewerTagline sourceLabel={sourceLabel} />}
          <Box sx={{ pointerEvents: "auto" }}>{controls}</Box>
        </Box>
      </Box>

      {overlays}
    </Box>
  );
}