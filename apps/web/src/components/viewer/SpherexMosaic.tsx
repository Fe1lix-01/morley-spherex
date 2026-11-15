"use client";

import { useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { AladinInstance } from "aladin-lite";
import AnimatedButton from "@/components/ui/AnimatedButton";
import SegmentedControl from "@/components/ui/SegmentedControl";
import { eter, glassPanel } from "@/lib/theme";
import { useSimbadLayer, type SimbadAladinApi, type SimbadAladinView } from "@/hooks/useSimbadLayer";
import { SimbadCard, SimbadHint, SimbadSelectedRing, SimbadStatus, SimbadToggle } from "@/components/sky/SimbadUI";
import { CollapsiblePanel } from "@/components/preview/PreviewCard";

type SkySource = "allwise" | "spherex";

const SURVEYS: Record<SkySource, string> = {
  // AllWISE alojado por NASA/IPAC IRSA (evita depender del registro MOCServer de CDS).
  allwise: "https://irsa.ipac.caltech.edu/data/hips/CDS/AllWISE/RGB-W4-W2-W1",
  // Cubo espectral HiPS de todo el cielo de SPHEREx DR1.
  spherex: "https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube",
};

const SOURCE_OPTIONS = [
  { value: "allwise", label: "AllWISE" },
  { value: "spherex", label: "SPHEREx DR1" },
] as const;

const SOURCE_NOTE: Record<SkySource, string> = {
  allwise: "AllWISE — referencia infrarroja de todo el cielo",
  spherex: "SPHEREx DR1 — mosaico espectral (un canal a la vez)",
};

const eyebrowSx = {
  fontSize: 11,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: eter.textFaint,
} as const;

/**
 * Visor del mosaico SPHEREx DR1 con el diseño de ÉTER. Misma lógica de Aladin que
 * SkyComparison (de Felix), pero con panel de vidrio y controles propios.
 */
export default function SpherexMosaic() {
  const aladinRef = useRef<AladinInstance | null>(null);
  const [ready, setReady] = useState(false);
  const [source, setSource] = useState<SkySource>("allwise");
  const [status, setStatus] = useState("Iniciando Aladin Lite...");

    // Aladin, su API y el contenedor, en estado: el hook de SIMBAD necesita enterarse cuando ya existen.
  const [mapInfo, setMapInfo] = useState<{ A: SimbadAladinApi; view: SimbadAladinView; host: HTMLElement } | null>(null);
  // Interruptor de la capa de objetos de SIMBAD: empieza apagado para que el cielo arranque limpio.
  const [showObjects, setShowObjects] = useState(false);
    // Mostrar u ocultar el panel de Fuente y Vista, igual que los filtros del visor ÉTER.
  const [panelOpen, setPanelOpen] = useState(true);

  // Capa SIMBAD: marcas de objetos conocidos, aviso al pasar el cursor y objeto elegido con clic.
  const simbad = useSimbadLayer({
    A: mapInfo?.A ?? null,
    view: mapInfo?.view ?? null,
    host: mapInfo?.host ?? null,
    enabled: showObjects,
  });

  useEffect(() => {
    let cancelled = false;

    async function initialize() {
      try {
        const { default: A } = await import("aladin-lite");
        await A.init;
        if (cancelled) return;

        const aladin = A.aladin("#eter-mosaic-viewer", {
          survey: SURVEYS.allwise,
          target: "0 +0",
          fov: 360,
          projection: "AIT",
          cooFrame: "equatorial",
          log: false, // sin telemetría a CDS
        });

        aladinRef.current = aladin;
        // Se le entrega el mapa a la capa SIMBAD. Aladin trae más métodos de los que declaran los
        // tipos de Felix (que no se tocan), por eso se convierte a los tipos del hook.
        const host = document.getElementById("eter-mosaic-viewer");
        if (host) {
          setMapInfo({
            A: A as unknown as SimbadAladinApi,
            view: aladin as unknown as SimbadAladinView,
            host,
          });
        }
        setReady(true);
        setStatus("Visor listo.");
      } catch (error) {
        if (!cancelled) {
          console.error(error);
          setStatus("No se pudo iniciar Aladin Lite.");
        }
      }
    }

    void initialize();

    return () => {
      cancelled = true;
      aladinRef.current?.remove();
      aladinRef.current = null;
      setMapInfo(null);
    };
  }, []);

  async function changeSource(next: SkySource) {
    const aladin = aladinRef.current;
    if (!aladin) return;

    try {
      if (next === "allwise") {
        aladin.setBaseImageLayer(SURVEYS.allwise);
        setSource("allwise");
        setStatus("AllWISE seleccionado.");
        return;
      }

      const { default: A } = await import("aladin-lite");
      if (aladinRef.current !== aladin) return;

      // SPHEREx es un cubo HiPS multicanal.
      const spherexHiPS = A.HiPS(SURVEYS.spherex, {
        name: "SPHEREx DR1",
        imgFormat: "png",
        successCallback: (layer) => {
          // Se evitan los canales 50 y 51, documentados como vacíos.
          layer.setSliceNumber(62);
          setStatus("SPHEREx DR1: canal 62 solicitado. Revisando tiles...");
        },
        errorCallback: (error) => {
          console.error("Falló la carga de SPHEREx:", error);
          setStatus("No se pudo cargar SPHEREx HiPS.");
        },
      });

      setStatus("Cargando SPHEREx DR1...");
      aladin.setBaseImageLayer(spherexHiPS);
      setSource("spherex");
    } catch (error) {
      console.error("Falló el cambio de fuente:", error);
      setStatus("No se pudo cambiar la fuente de imagen.");
    }
  }

  function changeView(mode: "all-sky" | "galactic-center") {
    const aladin = aladinRef.current;
    if (!aladin) return;

    if (mode === "all-sky") {
      aladin.setProjection("AIT");
      aladin.gotoRaDec(0, 0);
      aladin.setFoV(360);
    } else {
      aladin.setProjection("SIN");
      aladin.gotoRaDec(266.4168, -29.0078);
      aladin.setFoV(10);
    }
  }

  return (
    <Box sx={{ position: "fixed", inset: 0, backgroundColor: eter.ink }}>
      <Box id="eter-mosaic-viewer" sx={{ position: "absolute", top: 0, left: 0, width: "100vw", height: "100dvh" }} />

      {/* Capa de SIMBAD: no recibe clics (solo el botón del interruptor), así el mapa sigue arrastrable. */}
      <Box sx={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden" }}>
        <SimbadSelectedRing view={mapInfo?.view ?? null} object={simbad.selected} />
        {simbad.selected && (
          <SimbadCard key={simbad.selected.oid} object={simbad.selected} onClose={simbad.clearSelected} />
        )}
        <SimbadStatus status={simbad.status} />
        <SimbadToggle
          on={showObjects}
          loading={simbad.status === "loading"}
          onToggle={() => setShowObjects((v) => !v)}
          left={320}
        />
        {simbad.hovered && <SimbadHint x={simbad.pointer.x} y={simbad.pointer.y} />}
      </Box>

      <Box
        sx={{
          position: "fixed",
          // Arriba a la izquierda Aladin pone sus coordenadas; la etiqueta va a la derecha, debajo
          // de sus botones de proyección y pantalla completa.
          top: 58,
          right: 16,
          px: 1.5,
          py: 0.5,
          borderRadius: "999px",
          backgroundColor: eter.glass,
          border: `1px solid ${eter.lineStrong}`,
          color: "#fff",
          fontSize: 13,
          pointerEvents: "none",
        }}
      >
        ÉTER · Mosaico SPHEREx
      </Box>

            {/* Panel de Fuente y Vista. El envoltorio fija la posición; el CollapsiblePanel trae la flecha
          de ocultar, que queda debajo del panel. */}
      <Box
        sx={{
          position: "fixed",
          // En pantallas grandes el selector de visores va abajo al centro; esto sube el conjunto
          // (panel y flecha) para no tapar ese selector.
          bottom: { xs: 16, lg: 68 },
          left: "50%",
          transform: "translateX(-50%)",
          width: "min(92vw, 560px)",
        }}
      >
        <CollapsiblePanel open={panelOpen} onToggle={() => setPanelOpen((o) => !o)} label="controles del mosaico">
          <Box
            sx={{
              ...glassPanel,
              p: 2,
              borderRadius: "16px",
              display: "flex",
              flexDirection: "column",
              gap: 1.5,
              opacity: ready ? 1 : 0.7,
            }}
          >
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
              <Typography sx={eyebrowSx}>Fuente</Typography>
              <SegmentedControl
                value={source}
                onChange={(v) => void changeSource(v)}
                options={SOURCE_OPTIONS}
                ariaLabel="Fuente de imagen"
              />
            </Box>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
              <Typography sx={eyebrowSx}>Vista</Typography>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                <AnimatedButton disabled={!ready} onClick={() => changeView("all-sky")}>
                  Cielo completo
                </AnimatedButton>
                <AnimatedButton disabled={!ready} onClick={() => changeView("galactic-center")}>
                  Centro galáctico
                </AnimatedButton>
              </Box>
            </Box>

            <Box>
              <Typography sx={{ fontSize: 13, color: eter.textMuted }}>{SOURCE_NOTE[source]}</Typography>
              <Typography sx={{ fontSize: 13, color: eter.accent }}>{status}</Typography>
              <Typography sx={{ mt: 0.5, fontSize: 11, color: eter.textFaint }}>
                SPHEREx HiPS es solo para visualización. Seleccionar una fuente no garantiza que sus
                tiles hayan cargado.
              </Typography>
            </Box>
          </Box>
        </CollapsiblePanel>
      </Box>
    </Box>
  );
}