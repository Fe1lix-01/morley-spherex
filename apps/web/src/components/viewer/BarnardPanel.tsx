"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { eter } from "@/lib/theme";
import type { BarnardPreview, CnnDemoResponse } from "@/contracts/science";
import { scienceApi } from "@/services/science-api";

/**
 * Panel lateral "Análisis de Barnard".
 *
 * Un botón fijo arriba a la izquierda abre un panel a la derecha, con scroll, que muestra lo que
 * entrega el backend científico (Marvin / Kevin), a través del cliente `scienceApi`:
 *   GET /api/v1/ml/barnard/preview          metadatos reales de la comparación temporal
 *   GET /api/v1/ml/barnard/preview/image    imagen comparativa
 *   GET /api/v1/ml/demo                     demostración de la CNN experimental (datos sintéticos)
 *
 * No calcula nada: solo pide y muestra. Todo lo que llega se presenta como EXPLORATORIO.
 * Los tipos vienen de `@/contracts/science` y las llamadas de `@/services/science-api` (de Marvin).
 */

/** Convierte el error del cliente en un mensaje claro para la persona que usa el visor. */
function describeError(error: unknown): string {
  const text = error instanceof Error ? error.message : "";
  const status = /^Science API (\d+)/.exec(text)?.[1];
  if (status === "503") return `Servicio no disponible: ${text.replace(/^Science API 503: /, "")}`;
  if (status === "404") return "El backend no encontró el archivo procesado de Barnard.";
  if (status === "504") return "La demostración tardó más del tiempo permitido en el servidor.";
  if (status === "502") return "El proceso científico del servidor falló. Revisa los logs del backend.";
  if (status) return `El backend respondió con HTTP ${status}.`;
  if (text.includes("Falta configurar") || text.includes("503")) return `Servicio no disponible: ${text}`;
  return "No se pudo conectar con el backend. Verifica que science-api esté corriendo y que NEXT_PUBLIC_API_URL apunte a él.";
}

// --- Textos en español --------------------------------------------------------------------------

const MODE_LABELS: Record<string, string> = {
  exploratory_wcs_aligned: "Exploratoria, alineada por WCS",
  synthetic_demo: "Demostración con datos sintéticos",
};

const LIMITATION_LABELS: Record<string, string> = {
  "Central region contains flagged pixels": "La región central tiene píxeles marcados como no válidos.",
  "PSF matching has not been performed": "Todavía no se igualó la PSF entre las dos observaciones.",
  "Difference image is exploratory": "La imagen de diferencia es exploratoria.",
  "No astrophysical movement detection is claimed": "No se afirma ninguna detección de movimiento astrofísico.",
};

// --- Piezas de la interfaz ----------------------------------------------------------------------

const buttonSx = {
  height: 40,
  px: 2,
  borderRadius: "12px",
  border: `1px solid ${eter.lineStrong}`,
  backgroundColor: eter.glass,
  backdropFilter: "blur(8px)",
  color: "#fff",
  fontSize: 13,
  textTransform: "none",
  "&:hover": { borderColor: eter.lineHover, backgroundColor: eter.hoverFill },
  "&:focus-visible": { outline: `2px solid ${eter.focusRing}`, outlineOffset: 2 },
} as const;

const cardSx = {
  border: `1px solid ${eter.line}`,
  borderRadius: "14px",
  backgroundColor: "rgba(255,255,255,0.03)",
  p: 2,
  mt: 1.5,
} as const;

function Tag({ children, warn = false }: { children: string; warn?: boolean }) {
  return (
    <Box
      component="span"
      sx={{
        display: "inline-block",
        px: 1.25,
        py: 0.25,
        mr: 0.75,
        mt: 0.75,
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        border: `1px solid ${warn ? eter.accent : eter.lineStrong}`,
        color: warn ? eter.accent : eter.textMuted,
        backgroundColor: warn ? eter.accentGlow : "transparent",
      }}
    >
      {children}
    </Box>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, py: 0.75, borderBottom: `1px solid ${eter.line}` }}>
      <Typography sx={{ fontSize: 13, color: eter.textMuted }}>{label}</Typography>
      <Typography sx={{ fontSize: 13, color: "#fff", textAlign: "right" }}>{value}</Typography>
    </Box>
  );
}

function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Box sx={{ mt: 1.5 }}>
      <Typography role="alert" sx={{ fontSize: 13, color: eter.danger }}>
        {message}
      </Typography>
      {onRetry && (
        <Button onClick={onRetry} sx={{ ...buttonSx, height: 34, mt: 1 }}>
          Reintentar
        </Button>
      )}
    </Box>
  );
}

// --- Panel --------------------------------------------------------------------------------------

export default function BarnardPanel() {
  const [open, setOpen] = useState(false);

  const [preview, setPreview] = useState<BarnardPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  const [demo, setDemo] = useState<CnnDemoResponse | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);

  const loadPreview = useCallback(async () => {
    setPreviewLoading(true);
    setPreviewError(null);
    setImageFailed(false);
    try {
      setPreview(await scienceApi.getBarnardPreview());
    } catch (error) {
      setPreviewError(describeError(error));
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  // Los datos se piden solo la primera vez que se abre el panel; si falla, el botón "Reintentar" los vuelve a pedir.
  const requested = useRef(false);
  useEffect(() => {
    if (!open || requested.current) return;
    requested.current = true;
    void loadPreview();
  }, [open, loadPreview]);

  // La CNN corre un proceso en el servidor (hasta 90 s), por eso solo se pide con el botón.
  const runDemo = async () => {
    setDemoLoading(true);
    setDemoError(null);
    try {
      setDemo(await scienceApi.getCnnDemo());
    } catch (error) {
      setDemoError(describeError(error));
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <>
      <Button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls="barnard-panel"
        sx={{ ...buttonSx, position: "fixed", top: 136, left: 24, zIndex: 1250 }}
      >
        {open ? "Cerrar análisis" : "Análisis Barnard"}
      </Button>

      <Drawer
        id="barnard-panel"
        anchor="right"
        variant="persistent"
        open={open}
        slotProps={{
          paper: {
            sx: {
              width: { xs: "100vw", sm: 440 },
              boxSizing: "border-box",
              backgroundColor: eter.panelGlass,
              backdropFilter: "blur(24px)",
              borderLeft: `1px solid ${eter.lineStrong}`,
              color: "#fff",
              overflowY: "auto",
              zIndex: 1250,
            },
          },
        }}
      >
        <Box sx={{ p: 2.5, pb: 4 }}>
          <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 1 }}>
            <Box>
              <Typography sx={{ fontSize: 18, fontWeight: 600 }}>Análisis de Barnard</Typography>
              <Typography sx={{ fontSize: 13, color: eter.textMuted, mt: 0.25 }}>
                Datos del backend científico de ÉTER
              </Typography>
            </Box>
            <IconButton size="small" aria-label="Cerrar panel" onClick={() => setOpen(false)} sx={{ color: "#fff" }}>
              <Box component="span" sx={{ fontSize: 16, lineHeight: 1 }}>
                ✕
              </Box>
            </IconButton>
          </Box>

          <Box sx={{ ...cardSx, borderColor: eter.accent, backgroundColor: eter.accentGlow }}>
            <Typography sx={{ fontSize: 13, fontWeight: 600, color: eter.accent }}>Resultado exploratorio</Typography>
            <Typography sx={{ fontSize: 13, mt: 0.5 }}>
              Esta comparación todavía no está validada científicamente y no afirma ninguna detección. La CNN es
              experimental.
            </Typography>
          </Box>

          {/* ---- Comparación temporal ---- */}
          <Typography sx={{ fontSize: 15, fontWeight: 600, mt: 3 }}>Comparación temporal SPHEREx</Typography>

          {previewLoading && (
            <Typography sx={{ fontSize: 13, color: eter.textMuted, mt: 1.5 }}>Cargando datos de Barnard…</Typography>
          )}
          {previewError && <ErrorNote message={previewError} onRetry={() => void loadPreview()} />}

          {preview && (
            <>
              <Box sx={cardSx}>
                {imageFailed ? (
                  <Typography role="alert" sx={{ fontSize: 13, color: eter.danger }}>
                    No se pudo cargar la imagen comparativa.
                  </Typography>
                ) : (
                  <Box
                    component="img"
                    src={scienceApi.getBarnardImageUrl(preview)}
                    alt="Comparación temporal de Barnard con SPHEREx"
                    onError={() => setImageFailed(true)}
                    sx={{ display: "block", width: "100%", height: "auto", borderRadius: "10px" }}
                  />
                )}
                <Typography sx={{ fontSize: 12, color: eter.textFaint, mt: 1 }}>
                  Imagen científica comparativa entre dos observaciones de SPHEREx.
                </Typography>
              </Box>

              <Box sx={{ ...cardSx, py: 1 }}>
                <Row label="Objeto" value={preview.object} />
                <Row label="Fuente / detector" value={`${preview.source} · ${preview.detector}`} />
                <Row label="Modo" value={MODE_LABELS[preview.mode] ?? preview.mode} />
                <Row label="Observación de referencia" value={preview.reference_date} />
                <Row label="Observación de ciencia" value={preview.science_date} />
                <Row label="Longitud de onda aprox." value={`${preview.wavelength_um_approx} µm`} />
                <Row label="Tamaño del recorte" value={`${preview.shape[1]} × ${preview.shape[0]} px`} />
                <Row
                  label="Píxeles válidos"
                  value={`${preview.valid_pixels.toLocaleString("es-MX")} de ${preview.total_pixels.toLocaleString("es-MX")} (${(
                    preview.valid_fraction * 100
                  ).toFixed(1)} %)`}
                />
                <Row label="Píxel central válido" value={preview.center_pixel_valid ? "Sí" : "No"} />
              </Box>

              <Box>
                <Tag warn={!preview.scientifically_validated}>
                  {preview.scientifically_validated ? "Validado científicamente" : "No validado científicamente"}
                </Tag>
                <Tag>{preview.cnn_inference_performed ? "CNN ejecutada" : "CNN no ejecutada aquí"}</Tag>
              </Box>

              <Typography sx={{ fontSize: 14, fontWeight: 600, mt: 2.5 }}>Limitaciones</Typography>
              <Box component="ul" sx={{ m: 0, mt: 0.75, pl: 2.5, fontSize: 13, color: eter.textMuted }}>
                {preview.limitations.map((text) => (
                  <Box component="li" key={text} sx={{ mb: 0.5 }}>
                    {LIMITATION_LABELS[text] ?? text}
                  </Box>
                ))}
              </Box>
            </>
          )}

          {/* ---- CNN ---- */}
          <Typography sx={{ fontSize: 15, fontWeight: 600, mt: 4 }}>CNN experimental</Typography>
          <Typography sx={{ fontSize: 13, color: eter.textMuted, mt: 0.5 }}>
            Demostración con un triplete sintético, no con datos reales de SPHEREx. Puede tardar hasta 90 segundos.
          </Typography>

          <Button onClick={() => void runDemo()} disabled={demoLoading} sx={{ ...buttonSx, mt: 1.5 }}>
            {demoLoading ? "Ejecutando…" : demo ? "Ejecutar de nuevo" : "Ejecutar demostración"}
          </Button>

          {demoError && <ErrorNote message={demoError} />}

          {demo && (
            <>
              <Box sx={{ ...cardSx, py: 1 }}>
                <Row label="Modelo" value={demo.result.model} />
                <Row label="Entrenada con" value={demo.result.trained_on} />
                <Row label="Puntaje «parece real»" value={demo.result.score_real_like.toFixed(4)} />
                <Row label="Modo" value={MODE_LABELS[demo.mode] ?? demo.mode} />
              </Box>
              <Box>
                <Tag warn>Experimental</Tag>
                <Tag warn>Datos sintéticos</Tag>
                <Tag warn={!demo.scientifically_validated}>
                  {demo.scientifically_validated ? "Validado" : "No validado"}
                </Tag>
              </Box>
              <Typography sx={{ fontSize: 12, color: eter.textFaint, mt: 1 }}>
                El puntaje de la CNN no es la probabilidad de que algo sea astrofísicamente real.
              </Typography>
            </>
          )}
        </Box>
      </Drawer>
    </>
  );
}
