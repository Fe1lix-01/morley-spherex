
"use client";

import { useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import { useTarget } from "./TargetContext";
import { MenuItem, TextField } from "@mui/material";
import Slider from "@mui/material/Slider";
import Typography from "@mui/material/Typography";
import type { AladinInstance, HiPSLayer } from "aladin-lite";
import { spherexFrameAddress } from "@/lib/spherex-hips";
import RoiWorkbench from "@/components/roi/RoiWorkbench";
import AnimatedButton from "@/components/ui/AnimatedButton";
import SegmentedControl from "@/components/ui/SegmentedControl";
import { eter, glassPanel } from "@/lib/theme";
import {
  useSimbadLayer,
  type SimbadAladinApi,
  type SimbadAladinView,
} from "@/hooks/useSimbadLayer";
import {
  SimbadCard,
  SimbadHint,
  SimbadSelectedRing,
  SimbadStatus,
  SimbadToggle,
} from "@/components/sky/SimbadUI";
import { CollapsiblePanel } from "@/components/preview/PreviewCard";
import SpherexChannelSelector from "./SpherexChannelSelector";
import { getSpherexChannel } from "@/data/spherexChannels";

type SkySource = "allwise" | "spherex";

const SURVEYS: Record<SkySource, string> = {
  // AllWISE alojado por NASA/IPAC IRSA.
  allwise: "/api/sky-hips",

  // Cubo espectral HiPS de SPHEREx DR1.
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
 * Visor SPHEREx DR1 (102 canales), con capa SIMBAD opcional.
 * Consolida el selector espectral de Kevin y los controles de Richi.
 */
export default function SpherexMosaic() {
  const shared = useTarget();
  const target = shared?.target;
  const aladinRef = useRef<AladinInstance | null>(null);

  const [ready, setReady] = useState(false);
  const [roiView, setRoiView] = useState<AladinInstance | null>(null);
  const [source, setSource] = useState<SkySource>("allwise");
  const [status, setStatus] = useState("Iniciando Aladin Lite...");

  const [mapInfo, setMapInfo] = useState<{
    A: SimbadAladinApi;
    view: SimbadAladinView;
    host: HTMLElement;
  } | null>(null);

  const [showObjects, setShowObjects] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);

  const simbad = useSimbadLayer({
    A: mapInfo?.A ?? null,
    view: mapInfo?.view ?? null,
    host: mapInfo?.host ?? null,
    enabled: showObjects,
  });

  const [brightness, setBrightness] = useState(0);
  const [contrast, setContrast] = useState(0);
  const [channel, setChannel] = useState(62);

  const spherexLayerRef = useRef<HiPSLayer | null>(null);
  const sourceRef = useRef<SkySource>("allwise");

  // Inicialización de Aladin Lite
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
          log: false,
        });

        aladinRef.current = aladin;
        setRoiView(aladin);

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

  useEffect(()=>{
    if(!roiView||!target)return;
    roiView.setProjection("SIN");roiView.gotoRaDec(target.ra,target.dec);roiView.setFoV(.5);
  },[roiView,target]);

  // Cambio de canal espectral SPHEREx
  useEffect(() => {
    if (source !== "spherex") return;

    const layer = spherexLayerRef.current;

    if (!layer) return;

    const info = getSpherexChannel(channel);

    if (!info.valid) return;

    const timer = window.setTimeout(() => {
      if (
        sourceRef.current !== "spherex" ||
        spherexLayerRef.current !== layer
      ) {
        return;
      }

      try {
        layer.setFrequency({
          value: spherexFrameAddress(channel),
          unit: "m",
        });

        setStatus(
          `Canal ${channel} · B${info.band} · ${info.wavelengthUm.toFixed(3)} µm solicitado`,
        );
      } catch (error) {
        console.error("Error al cambiar el canal:", error);
        setStatus("No se pudo cambiar el canal espectral.");
      }
    }, 120);

    return () => window.clearTimeout(timer);
  }, [channel, source]);

  // Cambio entre AllWISE y SPHEREx
  async function changeSource(next: SkySource) {
    const aladin = aladinRef.current;

    if (!aladin) return;

    try {
      if (next === "allwise") {
        sourceRef.current = "allwise";
        spherexLayerRef.current = null;

        aladin.setBaseImageLayer(SURVEYS.allwise);

        setSource("allwise");
        setStatus("AllWISE seleccionado.");

        return;
      }

      const { default: A } = await import("aladin-lite");

      if (aladinRef.current !== aladin) return;

      const spherexHiPS = A.HiPS(SURVEYS.spherex, {
        name: "SPHEREx DR1",
        imgFormat: "png",
        // PNG tiles are already stretched, and contain display values 0–255.
        // The product's physical 0–40 cut is not a second PNG display cut.
        minCut: 0,
        maxCut: 255,
        stretch: "linear",

        successCallback: (layer) => {
          if (sourceRef.current !== "spherex") return;

          spherexLayerRef.current = layer;
          layer.setBrightness(brightness);
          layer.setContrast(contrast);

          const info = getSpherexChannel(channel);

          if (info.valid) {
            layer.setFrequency({
              value: spherexFrameAddress(channel),
              unit: "m",
            });

            setStatus(`SPHEREx DR1: canal ${channel} solicitado.`);
          }
        },

        errorCallback: (error) => {
          console.error("Falló la carga de SPHEREx:", error);
          if (sourceRef.current !== "spherex") return;
          sourceRef.current = "allwise";
          spherexLayerRef.current = null;
          aladin.setBaseImageLayer(SURVEYS.allwise);
          setSource("allwise");
          setStatus("SPHEREx no disponible. Se muestra AllWISE como referencia, no como datos SPHEREx.");
        },
      });

      setStatus("Cargando SPHEREx DR1...");

      sourceRef.current = "spherex";
      spherexLayerRef.current = null;

      aladin.setBaseImageLayer(spherexHiPS);

      setSource("spherex");
    } catch (error) {
      console.error("Falló el cambio de fuente:", error);
      setStatus("No se pudo cambiar la fuente de imagen.");
    }
  }

  // Cambiar región visible
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
    <Box
      sx={{
        position: "fixed",
        inset: 0,
        backgroundColor: eter.ink,
      }}
    >
      {/* Visor principal */}
      <Box
        id="eter-mosaic-viewer"
        sx={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100dvh",
        }}
      />

      <RoiWorkbench view={roiView} />

      {/* Capa SIMBAD de Richi */}
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          overflow: "hidden",
        }}
      >
        <SimbadSelectedRing
          view={mapInfo?.view ?? null}
          object={simbad.selected}
        />

        {simbad.selected && (
          <SimbadCard
            key={simbad.selected.oid}
            object={simbad.selected}
            onClose={simbad.clearSelected}
          />
        )}

        <SimbadStatus status={simbad.status} />

        <SimbadToggle
          on={showObjects}
          loading={simbad.status === "loading"}
          onToggle={() => setShowObjects((value) => !value)}
          left={320}
        />

        {simbad.hovered && (
          <SimbadHint
            x={simbad.pointer.x}
            y={simbad.pointer.y}
          />
        )}
      </Box>

      {/* Etiqueta del visor */}
      <Box
        sx={{
          position: "fixed",
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
        ÉTER · {source === "spherex" ? "SPHEREx DR1" : "AllWISE (referencia)"}
      </Box>

      {/* Panel unificado de Fuente y Vista */}
      <Box
        sx={{
          position: "fixed",
          top: { xs: 100, md: "auto" },
          bottom: { xs: "auto", md: 84 },
          left: { xs: 12, md: 24 },
          width: {
            xs: "calc(100vw - 24px)",
            md: 300,
          },
          maxHeight: {
            xs: "32dvh",
            md: "calc(100dvh - 160px)",
          },
          overflowY: "auto",
          zIndex: 10,
        }}
      >
        <CollapsiblePanel
          open={panelOpen}
          onToggle={() => setPanelOpen((value) => !value)}
          label="controles del mosaico"
        >
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
            {shared&&<TextField select label="Elegir candidato" size="small" value={shared.objects.some(o=>o.id===target?.id)?target!.id:""} onChange={e=>shared.pick(e.target.value)}>
              {shared.objects.map(o=><MenuItem key={o.id} value={o.id}>{o.name??o.id}</MenuItem>)}
            </TextField>}
            {target&&<Typography variant="caption" data-testid="mosaic-target" data-target={JSON.stringify(target)}>{target.name} · ICRS {target.ra.toFixed(6)}°, {target.dec.toFixed(6)}° · {target.epoch?`época J${target.epoch}`:"época no verificada"}</Typography>}
            {/* Selector de fuente */}
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                gap: 0.75,
              }}
            >
              <Typography sx={eyebrowSx}>
                Fuente
              </Typography>

              <SegmentedControl
                value={source}
                onChange={(value) => void changeSource(value)}
                options={SOURCE_OPTIONS}
                ariaLabel="Fuente de imagen"
              />
            </Box>

            {/* Selector de vista */}
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                gap: 0.75,
              }}
            >
              <Typography sx={eyebrowSx}>
                Vista
              </Typography>

              <Box
                sx={{
                  display: "flex",
                  gap: 1,
                  flexWrap: "wrap",
                }}
              >
                <AnimatedButton
                  disabled={!ready}
                  onClick={() => changeView("all-sky")}
                >
                  Cielo completo
                </AnimatedButton>

                <AnimatedButton
                  disabled={!ready}
                  onClick={() => changeView("galactic-center")}
                >
                  Centro galáctico
                </AnimatedButton>
              </Box>
            </Box>

            {/* Estado del mosaico */}
            <Box>
              <Typography
                sx={{
                  fontSize: 13,
                  color: eter.textMuted,
                }}
              >
                {SOURCE_NOTE[source]}
              </Typography>

              <Typography
                sx={{
                  fontSize: 13,
                  color: eter.accent,
                }}
              >
                {status}
              </Typography>

              <Typography
                sx={{
                  mt: 0.5,
                  fontSize: 11,
                  color: eter.textFaint,
                }}
              >
                SPHEREx HiPS es solo para visualización.
                Seleccionar una fuente no garantiza que
                sus tiles hayan cargado.
              </Typography>
            </Box>
          </Box>
      {/* Selector de los 102 canales SPHEREx */}
      {source === "spherex" && (
        <Box
          sx={{ ...glassPanel, p: 2, mt: 1.5, borderRadius: "16px" }}
        >
          <Typography
            sx={{
              fontSize: 14,
              fontWeight: 600,
              mb: 2,
              color: "#fff",
            }}
          >
            Selector espectral SPHEREx DR1
          </Typography>

          <Typography variant="caption">Brillo visual (sin alterar FITS)</Typography>
          <Slider aria-label="Brillo del mosaico" min={-0.8} max={0.8} step={0.02} value={brightness}
            onChange={(_, value) => { setBrightness(value as number); spherexLayerRef.current?.setBrightness(value as number); }} />
          <Typography variant="caption">Contraste visual</Typography>
          <Slider aria-label="Contraste del mosaico" min={-0.8} max={0.8} step={0.02} value={contrast}
            onChange={(_, value) => { setContrast(value as number); spherexLayerRef.current?.setContrast(value as number); }} />
          <SpherexChannelSelector
            channel={channel}
            onChange={(nextChannel) => {
              setChannel(nextChannel);

              if (
                nextChannel === 51 ||
                nextChannel === 52
              ) {
                setStatus(
                  `Canal ${nextChannel}: sin datos válidos en DR1. ` +
                    "Se conserva la última imagen disponible.",
                );
              }
            }}
            disabled={!ready}
          />
        </Box>
      )}
        </CollapsiblePanel>
      </Box>


    </Box>
  );
}
