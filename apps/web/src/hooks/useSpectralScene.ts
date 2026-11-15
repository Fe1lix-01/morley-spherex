"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { DEMO_IMAGE_URL, H, W } from "@/lib/viewer/constants";
import { createLayers, generateScene } from "@/lib/viewer/engine/generateScene";
import { loadImageIntoLayers, loadUrlIntoLayers } from "@/lib/viewer/engine/imageLayers";
import { renderLayers } from "@/lib/viewer/engine/render";
import type { FilterDef, Layers } from "@/lib/viewer/types";

/** De dónde vienen los datos de la imagen que se está mostrando. */
export type Source = "demo" | "upload";

/**
 * Maneja la escena del visor: crea las capas de luz, carga la escena demo o una imagen
 * subida y la dibuja en un canvas con el filtro y los controles actuales.
 *
 * Devuelve la referencia del canvas (para pasársela a <ViewerCanvas />), la fuente actual,
 * el mensaje de error y las acciones para subir una imagen o volver a la escena demo.
 */
export function useSpectralScene(filter: FilterDef, inten: number, gain: number, frameUrl?: string) {
  const [source, setSource] = useState<Source>("demo");
  const [sceneVersion, setSceneVersion] = useState(0); // sube cada vez que cambian los datos
  const [error, setError] = useState<string | null>(null);

  // Datos y lienzo: viven en refs porque no deben provocar un render al cambiar.
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const layersRef = useRef<Layers | null>(null);
  const imageRef = useRef<ImageData | null>(null);

  // Dibuja la imagen con los valores actuales.
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const layers = layersRef.current;
    if (!canvas || !layers) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (!imageRef.current) imageRef.current = ctx.createImageData(W, H);
    renderLayers(ctx, imageRef.current, layers, filter, inten, gain);
  }, [filter, inten, gain]);

  // Carga la escena demo: usa /public/escena-demo.jpg si existe; si no, genera una simulada.
  // Solo carga los datos; los setters se ejecutan después en un callback de la promesa.
  const loadDemo = useCallback(async (
    layers: Layers,
    isCancelled: () => boolean = () => false
  ): Promise<boolean> => {
    try {
      await loadUrlIntoLayers(DEMO_IMAGE_URL, layers);
    } catch {
      if (isCancelled()) return false;
      generateScene(layers);
    }
    return !isCancelled();
  }, []);

  // Al montar: crea las capas y carga la imagen indicada o, si no hay, la escena demo.
  useEffect(() => {
    let cancelled = false;
    const layers = createLayers();
    layersRef.current = layers;
    if (frameUrl) {
      loadUrlIntoLayers(frameUrl, layers)
        .then(() => {
          if (cancelled) return;
          setSource("upload");
          setSceneVersion((v) => v + 1);
        })
        .catch(() => {
          if (!cancelled) setError("No se pudo cargar la imagen de la época.");
        });
    } else {
      void loadDemo(layers, () => cancelled).then((loaded) => {
        if (!loaded || cancelled) return;
        setSource("demo");
        setError(null);
        setSceneVersion((v) => v + 1);
      });
    }
    return () => {
      cancelled = true;
    };
  }, [loadDemo, frameUrl]);

  // Cada vez que cambia filtro, sliders o datos: vuelve a dibujar (máx. una vez por frame).
  useEffect(() => {
    const id = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(id);
  }, [draw, sceneVersion]);

  // Sube una imagen elegida por la persona. Si falla, deja un mensaje en `error`.
  const upload = async (file: File) => {
    if (!layersRef.current) return;
    try {
      await loadImageIntoLayers(file, layersRef.current);
      setSource("upload");
      setSceneVersion((v) => v + 1);
    } catch (err) {
      console.error(err);
      setError("No se pudo cargar la imagen. Prueba con otro archivo.");
    }
  };

  // Vuelve a la escena demo.
  const reloadDemo = () => {
    const layers = layersRef.current;
    if (!layers) return;
    void loadDemo(layers).then((loaded) => {
      if (!loaded || layersRef.current !== layers) return;
      setSource("demo");
      setError(null);
      setSceneVersion((v) => v + 1);
    });
  };

  const clearError = () => setError(null);

  return { canvasRef, source, error, clearError, upload, reloadDemo };
}