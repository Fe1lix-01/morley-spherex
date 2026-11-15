"use client";

import { useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";

import type { Epoch, Frame, MovingObject } from "@/data/contracts";
import type { RemoteObservation, SiaResponse } from "@/contracts/api";
import { eterApiService } from "@/services/eter-api";

import ControlPanel from "@/components/viewer/ControlPanel";
import ViewerShell from "@/components/viewer/ViewerShell";
import MenuDrawer from "@/components/menu/MenuDrawer";
import { SvgDefs } from "@/components/phenomena/PhenomenonArt";
import { FILTERS } from "@/lib/viewer/engine/filters";
import AladinBackground from "@/components/sky/AladinBackground";
import { ALLWISE_HIPS_URL, skyCssFilter } from "@/lib/aladin";
import { skyData } from "@/data/services";

import {
  EpochLayer,
  MarkerLayer,
  PanZoom,
  TrailLayer,
  type Marker,
} from "./EpochLayers";

import PreviewCard, {
  CollapsiblePanel,
  PreviewCredit,
} from "./PreviewCard";

import { skyToImage } from "@/lib/model/projection";
import TopRightTools from "./TopRightTools";
import PlaybackBar, {
  ModeToggle,
  type ViewMode,
} from "./PlaybackBar";

import SkyStage from "@/components/sky/SkyStage";
import { useEpochClock } from "@/hooks/useEpochClock";

import {
  epochsForObject,
  hasOwnImages,
  positionAt,
  trackPoints,
} from "@/lib/model/trajectory";

type SkyTarget = {
  raDeg: number;
  decDeg: number;
  fovDeg: number;
  nonce: number;
};

const ALL_SKY: SkyTarget = {
  raDeg: 0,
  decDeg: 0,
  fovDeg: 360,
  nonce: 0,
};

const CLOSE_UP_FOV_DEG = 1.5;
const TEST_LABEL = "Prueba";
const REAL_PATCH_FOV_DEG = 0.08;
const REAL_CLOSE_UP_FOV_DEG = 0.14;

// Configuración inicial para las consultas SIA.
const SEARCH_RADIUS_ARCSEC = 100;
const SEARCH_BAND = "SPHEREx-D2" as const;
const SEARCH_COLLECTION = "spherex_qr3" as const;
const SEARCH_LIMIT = 20;

const layerOpacity = (i: number, t: number) =>
  i === 0
    ? 1
    : Math.min(Math.max(t - (i - 1), 0), 1);

type SiaStatus = "idle" | "loading" | "success" | "error";

type SearchCoordinates = {
  ra: number;
  dec: number;
};

/**
 * Vista previa de ÉTER.
 *
 * Conserva:
 * - Mosaico AllWISE mediante Aladin
 * - Filtros y controles visuales
 * - Animación de épocas
 * - Candidatos con imágenes propias
 * - Imágenes de demostración
 *
 * Incorpora:
 * - Búsqueda RA/Dec mediante FastAPI
 * - Consulta de observaciones SPHEREx en IRSA SIA
 * - Visualización de metadatos
 * - Centrado en Aladin
 *
 * La búsqueda SIA devuelve metadatos, no píxeles FITS.
 */
export default function PreviewPanel() {
  const [frames, setFrames] = useState<Frame[] | null>(null);
  const [objects, setObjects] = useState<MovingObject[]>([]);
  const [epochs, setEpochs] = useState<Epoch[]>([]);

  const [loadError, setLoadError] = useState<string | null>(null);
  const [sceneError, setSceneError] = useState<string | null>(null);

  const [filterIndex, setFilterIndex] = useState(0);
  const [inten, setInten] = useState(72);
  const [gain, setGain] = useState(110);

  const [marker, setMarker] = useState<Marker | null>(null);
  const [outside, setOutside] = useState(false);

  const [selected, setSelected] = useState<MovingObject | null>(null);
  const [cardOpen, setCardOpen] = useState(true);

  const [epochsOpen, setEpochsOpen] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuSection, setMenuSection] = useState<number | null>(0);
  const [filtersOpen, setFiltersOpen] = useState(true);

  const [revision, setRevision] = useState(0);
  const [mode, setMode] = useState<ViewMode>("sky");

  const [skyTarget, setSkyTarget] = useState<SkyTarget>(ALL_SKY);
  const [skyOpened, setSkyOpened] = useState(true);
  const [skyFailed, setSkyFailed] = useState(false);

  // Estados de la búsqueda científica real.
  const [searchCoordinates, setSearchCoordinates] =
    useState<SearchCoordinates | null>(null);

  const [siaResult, setSiaResult] = useState<SiaResponse | null>(null);

  const [siaStatus, setSiaStatus] = useState<SiaStatus>("idle");

  const [siaError, setSiaError] = useState<string | null>(null);

  // Impide que las respuestas anteriores sobrescriban una nueva búsqueda.
  const siaRequestId = useRef(0);

  // Cargar los datos utilizados en la vista previa.
  useEffect(() => {
    let active = true;

    Promise.all([
      skyData.getFrames(),
      skyData.getObjects(),
      skyData.getEpochs(),
    ])
      .then(([f, o, e]) => {
        if (!active) return;

        setFrames(f);
        setObjects(o.objects);
        setEpochs(e);
      })
      .catch(() => {
        if (active) {
          setLoadError(
            "No se pudieron cargar los datos de la vista previa."
          );
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const frame = frames?.[0] ?? null;
  const filter = FILTERS[filterIndex];
  const skyMode = mode === "sky";
  const coordinateSearch = searchCoordinates !== null;

  const realObject =
    selected && hasOwnImages(selected) ? selected : null;

  const track = selected ? trackPoints(selected) : [];

  const epochCount = realObject
    ? realObject.positions.length
    : frames?.length ?? 0;

  const clock = useEpochClock(epochCount, 3);

  const shownEpochs = epochsForObject(realObject, epochs);

  /**
   * Cambia entre el mapa astronómico y las épocas simuladas.
   */
  const changeMode = (next: ViewMode) => {
    if (next === "sky") {
      setSkyOpened(true);
    }

    setMode(next);
  };

  /**
   * Centra el mosaico de Aladin.
   */
  const goSky = (
    raDeg: number,
    decDeg: number,
    fovDeg: number
  ) => {
    setSkyTarget((current) => ({
      raDeg,
      decDeg,
      fovDeg,
      nonce: current.nonce + 1,
    }));
  };

  /**
   * Activa el visor alternativo cuando falla SkyStage.
   */
  const onSkyFail = (message: string) => {
    setSkyFailed(true);
    setSceneError(
      `${message} Se usa el visor básico de Aladin.`
    );
  };

  /**
   * Limpia los resultados de búsqueda científica.
   */
  const clearSiaSearch = () => {
    siaRequestId.current += 1;

    setSearchCoordinates(null);
    setSiaResult(null);
    setSiaError(null);
    setSiaStatus("idle");
  };

  /**
   * Busca observaciones SPHEREx por RA/Dec.
   */
  const search = (ra: number, dec: number) => {
    const requestId = ++siaRequestId.current;

    setSearchCoordinates({ ra, dec });
    setSiaResult(null);
    setSiaError(null);
    setSiaStatus("loading");

    // No seleccionar automáticamente candidatos simulados.
    setSelected(null);
    setCardOpen(false);
    setOutside(false);

    clock.pause();
    clock.seek(0);

    setMarker({
      id: `${ra},${dec}`,
      label: `${ra.toFixed(4)}, ${dec.toFixed(4)}`,
      ra,
      dec,
    });

    // Mostrar inmediatamente la región solicitada.
    changeMode("sky");
    goSky(ra, dec, CLOSE_UP_FOV_DEG);

    // Consultar observaciones científicas reales.
    void eterApiService
      .searchSiaObservations({
        ra,
        dec,
        radiusArcsec: SEARCH_RADIUS_ARCSEC,
        band: SEARCH_BAND,
        collection: SEARCH_COLLECTION,
        limit: SEARCH_LIMIT,
      })
      .then((response) => {
        if (requestId !== siaRequestId.current) {
          return;
        }

        setSiaResult(response);
        setSiaStatus("success");
      })
      .catch((error: unknown) => {
        if (requestId !== siaRequestId.current) {
          return;
        }

        setSiaError(
          error instanceof Error
            ? error.message
            : "No se pudo consultar IRSA SIA."
        );

        setSiaStatus("error");
      });
  };

  /**
   * Centra Aladin en una observación encontrada.
   */
  const centerSiaObservation = (
    observation: RemoteObservation
  ) => {
    setMarker({
      id: observation.product_id,
      label: observation.band,
      ra: observation.image_center_ra_deg,
      dec: observation.image_center_dec_deg,
    });

    changeMode("sky");

    goSky(
      observation.image_center_ra_deg,
      observation.image_center_dec_deg,
      REAL_CLOSE_UP_FOV_DEG
    );
  };

  /**
   * Selecciona un candidato del catálogo de demostración.
   */
  const pickCandidate = (obj: MovingObject) => {
    const first = trackPoints(obj)[0];

    if (!first) return;

    clearSiaSearch();

    const real = hasOwnImages(obj);

    setOutside(
      !real && frame
        ? skyToImage(first.ra, first.dec, frame) === null
        : false
    );

    setMarker(null);

    goSky(
      first.ra,
      first.dec,
      real ? REAL_CLOSE_UP_FOV_DEG : CLOSE_UP_FOV_DEG
    );

    setSelected(obj);
    setCardOpen(true);

    if (real) {
      setMode("sky");
    }

    clock.seek(0);
  };

  const message =
    loadError ??
    (!frame && !coordinateSearch ? "Cargando imágenes…" : null);

  const selectValue =
    selected?.id ?? (marker ? "custom" : "");

  /**
   * Marcadores visibles en el mapa.
   */
  const markers: Marker[] = [];

  if (marker) {
    markers.push(marker);
  }

  const moving = selected
    ? positionAt(selected, clock.t)
    : null;

  if (selected && moving) {
    markers.push({
      id: `${selected.id}-now`,
      label: selected.name ?? selected.id,
      ...moving,
    });
  }

  /**
   * Restablece la vista inicial del observatorio.
   */
  const resetViewer = () => {
    clearSiaSearch();

    clock.pause();
    clock.seek(0);

    setRevision((n) => n + 1);

    setMarker(null);
    setSelected(null);
    setOutside(false);

    goSky(
      ALL_SKY.raDeg,
      ALL_SKY.decDeg,
      ALL_SKY.fovDeg
    );
  };

  /**
   * Imágenes de demostración utilizadas en la animación.
   */
  const demoLayers = frames?.map((f, i) => (
    <EpochLayer
      key={f.epochId}
      imageUrl={f.imageUrl}
      filter={filter}
      inten={inten}
      gain={gain}
      opacity={layerOpacity(i, clock.t)}
      onError={setSceneError}
    />
  ));

  /**
   * Capas de imágenes propias del candidato o imágenes demo.
   */
  const patchLayers = realObject
    ? track.map((p, i) => (
        <EpochLayer
          key={`${realObject.id}-${p.index}`}
          imageUrl={p.imageUrl as string}
          filter={filter}
          inten={inten}
          gain={gain}
          opacity={layerOpacity(i, clock.t)}
          onError={setSceneError}
        />
      ))
    : demoLayers;

  /**
   * Región que se muestra sobre el mapa.
   *
   * Para búsquedas SIA representa el área consultada,
   * no una imagen FITS real.
   */
  const patch = searchCoordinates
    ? {
        ra: searchCoordinates.ra,
        dec: searchCoordinates.dec,
        fovDeg: (2 * SEARCH_RADIUS_ARCSEC) / 3600,
        label: "Búsqueda SIA · sin imagen FITS",
      }
    : realObject && track[0]
      ? {
          ra: track[0].ra,
          dec: track[0].dec,
          fovDeg: track[0].fovDeg ?? REAL_PATCH_FOV_DEG,
          label: realObject.name ?? realObject.id,
        }
      : {
          ra: frame?.ra ?? 209.4201,
          dec: frame?.dec ?? 53.9431,
          fovDeg: frame?.fovDeg ?? 3.5,
          label: TEST_LABEL,
        };

  return (
    <ViewerShell
      background={
        <>
          {skyOpened && !skyFailed && (
            <SkyStage
              active={skyMode}
              target={skyTarget}
              cssFilter={skyCssFilter(
                filter.id,
                inten,
                gain
              )}
              patch={patch}
              patchContent={
                skyMode && !coordinateSearch
                  ? patchLayers
                  : null
              }
              markers={markers}
              trail={track}
              t={clock.t}
              onFail={onSkyFail}
            />
          )}

          {skyMode && skyFailed && (
            <AladinBackground
              key={revision}
              position={{
                raDeg: skyTarget.raDeg,
                decDeg: skyTarget.decDeg,
              }}
              fovDeg={skyTarget.fovDeg}
              surveyUrl={ALLWISE_HIPS_URL}
              style={{
                marginTop: 88,
                height: "calc(100% - 88px)",
              }}
              title="Mosaico del cielo infrarrojo AllWISE"
            />
          )}

          {!skyMode && (
            <PanZoom key={revision}>
              {demoLayers}

              {frame && selected && !realObject && (
                <TrailLayer
                  frame={frame}
                  points={track}
                  t={clock.t}
                />
              )}

              {frame && (
                <MarkerLayer
                  frame={frame}
                  markers={realObject ? [] : markers}
                />
              )}
            </PanZoom>
          )}
        </>
      }
      controls={
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
          }}
        >
          {message && (
            <Typography sx={{ color: "#fff" }}>
              {message}
            </Typography>
          )}

          {/* Resultados de búsqueda científica */}
          {coordinateSearch && skyMode && (
            <Box
              component="section"
              aria-label="Resultados de observaciones SPHEREx"
              sx={{
                p: 2,
                borderRadius: 2,
                border:
                  "1px solid rgba(255,255,255,0.2)",
                backgroundColor:
                  "rgba(10,15,30,0.88)",
                color: "#fff",
              }}
            >
              <Typography
                sx={{
                  fontWeight: 700,
                  mb: 0.5,
                }}
              >
                Observaciones SPHEREx / IRSA SIA
              </Typography>

              <Typography
                variant="caption"
                sx={{
                  display: "block",
                  opacity: 0.8,
                  mb: 1,
                }}
              >
                RA: {searchCoordinates.ra.toFixed(4)}°
                {" · "}
                Dec: {searchCoordinates.dec.toFixed(4)}°
                {" · "}
                Radio: {SEARCH_RADIUS_ARCSEC}″
                {" · "}
                {SEARCH_BAND}
              </Typography>

              <Typography
                variant="caption"
                sx={{
                  display: "block",
                  opacity: 0.7,
                  mb: 1.5,
                }}
              >
                El fondo es AllWISE. Estos resultados
                son metadatos de SPHEREx; todavía no
                se ha cargado una imagen FITS en el mapa.
              </Typography>

              {/* Estado de carga */}
              {siaStatus === "loading" && (
                <Box
                  sx={{
                    display: "flex",
                    gap: 1.5,
                    alignItems: "center",
                  }}
                >
                  <CircularProgress
                    size={18}
                    color="inherit"
                  />

                  <Typography variant="body2">
                    Consultando IRSA…
                  </Typography>
                </Box>
              )}

              {/* Error de consulta */}
              {siaStatus === "error" && (
                <Alert severity="warning">
                  {siaError ??
                    "No se pudo completar la consulta a IRSA."}
                </Alert>
              )}

              {/* Observaciones encontradas */}
              {siaStatus === "success" && siaResult && (
                <>
                  <Typography
                    variant="body2"
                    sx={{ mb: 1 }}
                  >
                    {siaResult.count} observaciones
                    encontradas · {siaResult.collection}
                  </Typography>

                  {siaResult.observations.length === 0 && (
                    <Typography
                      variant="body2"
                      sx={{ opacity: 0.8 }}
                    >
                      No se encontraron productos para
                      esta banda y región. Prueba otras
                      coordenadas; el selector de bandas
                      se añadirá después.
                    </Typography>
                  )}

                  <Box
                    sx={{
                      display: "flex",
                      flexDirection: "column",
                      gap: 1,
                      maxHeight: 340,
                      overflowY: "auto",
                    }}
                  >
                    {siaResult.observations.map(
                      (observation, index) => (
                        <Box
                          key={`${observation.product_id}-${index}`}
                          sx={{
                            p: 1.5,
                            borderRadius: 1,
                            backgroundColor:
                              "rgba(255,255,255,0.06)",
                          }}
                        >
                          <Typography
                            variant="body2"
                            sx={{ fontWeight: 600 }}
                          >
                            {observation.band}
                          </Typography>

                          <Typography
                            variant="caption"
                            sx={{ display: "block" }}
                          >
                            Fecha inicial:{" "}
                            {observation.start_utc}
                          </Typography>

                          <Typography
                            variant="caption"
                            sx={{ display: "block" }}
                          >
                            RA:{" "}
                            {observation.image_center_ra_deg.toFixed(
                              5
                            )}
                            °
                            {" · "}
                            Dec:{" "}
                            {observation.image_center_dec_deg.toFixed(
                              5
                            )}
                            °
                          </Typography>

                          <Typography
                            variant="caption"
                            sx={{ display: "block" }}
                          >
                            Formato:{" "}
                            {observation.access_format}
                          </Typography>

                          <Box
                            sx={{
                              display: "flex",
                              flexWrap: "wrap",
                              gap: 1,
                              mt: 1,
                            }}
                          >
                            <Button
                              size="small"
                              variant="outlined"
                              color="inherit"
                              onClick={() =>
                                centerSiaObservation(
                                  observation
                                )
                              }
                            >
                              Centrar en Aladin
                            </Button>

                            <Button
                              component="a"
                              href={observation.access_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              size="small"
                              variant="text"
                              sx={{
                                color: "#c6afff",
                              }}
                            >
                              Producto en IRSA
                            </Button>
                          </Box>
                        </Box>
                      )
                    )}
                  </Box>
                </>
              )}
            </Box>
          )}

          {/* Aviso para imágenes de demostración */}
          {outside && !skyMode && (
            <Typography
              variant="body2"
              sx={{ color: "#fff" }}
            >
              Ese punto está fuera de esta imagen.
            </Typography>
          )}
          <CollapsiblePanel open={epochsOpen} onToggle={() => setEpochsOpen((o) => !o)}>
            <ModeToggle value={mode} onChange={changeMode} />
            {epochCount > 1 && shownEpochs.length > 1 && (
              <PlaybackBar
                epochs={shownEpochs}
                t={clock.t}
                playing={clock.playing}
                speed={clock.speed}
                onToggle={clock.toggle}
                onSeek={clock.seek}
                onSpeed={clock.setSpeed}
              />
            )}
          </CollapsiblePanel>
          <CollapsiblePanel open={filtersOpen} onToggle={() => setFiltersOpen((o) => !o)}>
            <ControlPanel
              filters={FILTERS}
              current={filterIndex}
              onSelect={setFilterIndex}
              intensityDisabled={filter.fn === null}
              inten={inten}
              gain={gain}
              onInten={setInten}
              onGain={setGain}
              onUpload={() =>
                setSceneError("En la vista previa se usan las épocas simuladas; no se pueden subir imágenes.")
              }
              onDemo={() => {}}
              onHelp={() => {
                setMenuSection(1);
                setMenuOpen(true);
              }}
              isDemo={false}
            />
          </CollapsiblePanel>
        </Box>
      }
      filterLabel={`${filter.name} · ${filter.band}`}
      sourceLabel={
        coordinateSearch && skyMode
          ? "AllWISE (referencia) · Metadatos SPHEREx/IRSA · sin imagen FITS"
          : realObject
            ? `Vista previa · SPHEREx / IRSA · ${realObject.positions.length} épocas reales`
            : "Vista previa · Imágenes simuladas (3 épocas)"
      }
      tagline={<PreviewCredit />}
      menuOpen={menuOpen}
      onOpenMenu={() => {
        setMenuSection(menuSection ?? 0);
        setMenuOpen(true);
      }}
      overlays={
        <>
          <SvgDefs />

          <TopRightTools
            onPickRegion={(
              ra,
              dec,
              fovDeg
            ) => {
              clearSiaSearch();

              setSelected(null);
              setMarker(null);
              setOutside(false);

              changeMode("sky");
              goSky(ra, dec, fovDeg);
            }}
            objects={objects}
            value={selectValue}
            onPickCandidate={(id) => {
              const obj = objects.find(
                (o) => o.id === id
              );

              if (obj) {
                pickCandidate(obj);
              }
            }}
            onSearch={search}
            onReset={resetViewer}
            onInfo={() => {
              setMenuSection(0);
              setMenuOpen(true);
            }}
            disabled={!frame}
          />

          {selected && cardOpen && (
            <PreviewCard
              object={selected}
              epochs={shownEpochs}
              onClose={() =>
                setCardOpen(false)
              }
            />
          )}

          <MenuDrawer
            open={menuOpen}
            onClose={() =>
              setMenuOpen(false)
            }
            section={menuSection}
            onSection={setMenuSection}
            filters={FILTERS}
            activeFilter={filterIndex}
            sourceLabel="Vista previa"
          />

          <Snackbar
            open={sceneError !== null}
            autoHideDuration={5000}
            onClose={(_, reason) => {
              if (reason !== "clickaway") {
                setSceneError(null);
              }
            }}
            anchorOrigin={{
              vertical: "top",
              horizontal: "center",
            }}
          >
            <Alert
              severity="error"
              variant="filled"
              onClose={() =>
                setSceneError(null)
              }
            >
              {sceneError}
            </Alert>
          </Snackbar>
        </>
      }
    />
  );
}
