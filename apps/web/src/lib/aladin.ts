import type { CSSProperties } from "react";
import type { FilterId } from "@/lib/viewer/types";

/* ------------------------------------------------------------------ */
/* Tipos                                                               */
/* ------------------------------------------------------------------ */

/** Coordenadas ecuatoriales ICRS, siempre en grados decimales. */
export interface SkyPosition {
  raDeg: number;
  decDeg: number;
}

export interface AladinBackgroundProps {
  position?: SkyPosition;
  /** Campo de visión horizontal en grados. Menor valor = más acercamiento. */
  fovDeg?: number;
  /** URL raíz de un HiPS, NO de un FITS, PNG ni del explorador de IRSA. */
  surveyUrl?: string;
  className?: string;
  style?: CSSProperties;
  title?: string;
}

export interface SkyDocumentOptions {
  raDeg: number;
  decDeg: number;
  fovDeg: number;
  surveyUrl: string;
}

/* ------------------------------------------------------------------ */
/* Documento de Aladin Lite                                            */
/* ------------------------------------------------------------------ */

// Fondo de contexto real de WISE. No son observaciones SPHEREx.
export const ALLWISE_HIPS_URL = "/api/sky-hips/";

// Versión fija: actualizar deliberadamente después de comprobar el visor.
export const ALADIN_SCRIPT_URL = "https://cdn.jsdelivr.net/npm/aladin-lite@3.8.1/dist/aladin.js";

export function validateSkyOptions(options: SkyDocumentOptions): string | null {
  if (!Number.isFinite(options.raDeg) || options.raDeg < 0 || options.raDeg >= 360)
    return "La ascensión recta debe estar entre 0 (incluido) y 360 grados.";
  if (!Number.isFinite(options.decDeg) || Math.abs(options.decDeg) > 90)
    return "La declinación debe estar entre −90 y 90 grados.";
  if (!Number.isFinite(options.fovDeg) || options.fovDeg < 0.001 || options.fovDeg > 360)
    return "El campo de visión debe estar entre 0.001 y 360 grados.";
  try {
    // Se admiten también rutas del mismo sitio, p. ej. /hips/m101/.
    const url = new URL(options.surveyUrl, "https://local.invalid");
    if (!options.surveyUrl.trim() || !["https:", "http:"].includes(url.protocol))
      return "La capa debe ser una URL HTTP(S) o una ruta a un conjunto HiPS.";
    if (url.username || url.password || url.search || url.hash)
      return "Usa una URL raíz HiPS sin credenciales, parámetros ni fragmentos.";
  } catch {
    return "La URL de la capa HiPS no es válida.";
  }
  return null;
}

/** Escapa datos antes de incluirlos en un script de un documento HTML. */
function scriptJSON(value: unknown): string {
  return JSON.stringify(value)
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/&/g, "\\u0026")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
}

/** Documento privado: el iframe aísla CSS, listeners y el contexto WebGL. */
export function createAladinDocument(options: SkyDocumentOptions): string {
  const validationError = validateSkyOptions(options);
  if (validationError) throw new Error(validationError);
  return `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    html, body, #sky { width:100%; height:100%; margin:0; overflow:hidden; background:#070a13; }
    #status { position:absolute; inset:0; z-index:10000; display:grid; place-content:center;
      padding:24px; color:#e5e9f2; background:#070a13; font:15px/1.6 system-ui,sans-serif; text-align:center; }
    #status[hidden] { display:none; }
    #status p { max-width:560px; margin:0 auto; }
  </style>
</head>
<body>
  <div id="sky"></div>
  <div id="status" role="status" aria-live="polite"><p>Cargando el visor del cielo…</p></div>
  <script>
    (() => {
      "use strict";
      const config = ${scriptJSON(options)};
      const status = document.getElementById("status");
      const controller = new AbortController();
      let stopped = false;
      let timer;
      function fail(message) {
        if (stopped) return;
        stopped = true;
        clearTimeout(timer);
        controller.abort();
        status.hidden = false;
        status.setAttribute("role", "alert");
        status.firstElementChild.textContent = message;
      }
      timer = setTimeout(() => fail(
        "La carga tardó demasiado. Comprueba tu conexión y el acceso a jsDelivr e IRSA; después pulsa Reiniciar visor."
      ), 45000);
      addEventListener("pagehide", () => {
        stopped = true;
        clearTimeout(timer);
        controller.abort();
      }, { once:true });
      async function start() {
        let A;
        try {
          A = (await import(${scriptJSON(ALADIN_SCRIPT_URL)})).default;
        } catch {
          fail("No se pudo descargar Aladin Lite desde jsDelivr. Comprueba la conexión y pulsa Reiniciar visor.");
          return;
        }
        try {
          await A.init;
          if (stopped) return;
          const root = new URL(config.surveyUrl, document.baseURI);
          root.pathname = root.pathname.replace(/\\/?$/, "/");
          // Detecta errores de URL/CORS antes de dejar un mapa vacío.
          const response = await fetch(new URL("properties", root), { signal:controller.signal });
          if (!response.ok) {
            let message = "El servidor HiPS respondió HTTP " + response.status + ".";
            if (root.origin === location.origin) {
              const detail = await response.json().catch(() => null);
              if (typeof detail?.error === "string") message += " " + detail.error;
            }
            throw new Error(message);
          }
          const properties = await response.text();
          if (!/^hips_order\\s*=/m.test(properties))
            throw new Error("La URL no contiene un archivo properties de un HiPS de imágenes.");
          if (stopped) return;
          const survey = A.HiPS(root.href, {
            successCallback: () => {
              if (stopped) return;
              clearTimeout(timer);
              status.hidden = true;
            },
            errorCallback: () => fail("No se pudo cargar la capa HiPS. Comprueba la URL, CORS y la conexión.")
          });
          A.aladin("#sky", {
            survey,
            target: config.raDeg + " " + config.decDeg,
            fov: config.fovDeg,
            projection: "AIT",
            cooFrame: "ICRSd",
            mode: "dark",
            // Evita una petición opcional de estadísticas al servidor de CDS.
            log: false,
            showLayersControl: false,
            showGotoControl: false,
            showShareControl: false,
            showFullscreenControl: false,
            showZoomControl: true,
            showReticle: true,
            showCooGridControl: true
          });
          // Las teselas continúan cargándose progresivamente al navegar.
        } catch (error) {
          const detail = error instanceof Error ? error.message : String(error);
          fail("No se pudo iniciar el mapa. Revisa WebGL2, la URL HiPS y CORS. " + detail);
        }
      }
      start();
    })();
  </script>
</body>
</html>`;
}

/* ------------------------------------------------------------------ */
/* Filtros de color del mosaico                                        */
/* ------------------------------------------------------------------ */

/**
 * Aproximación de color de cada filtro del visor para el mosaico de Aladin.
 *
 * Los filtros reales trabajan píxel por píxel sobre las imágenes de la prueba. El mosaico lo
 * dibuja Aladin con WebGL, así que aquí solo se imita el tono con filtros CSS. Es una
 * ayuda visual, no una banda real.
 */
type Recipe = { gray: number; sepia: number; hue: number; sat: number; contrast: number };

const RECIPES: Record<FilterId, Recipe> = {
  visible: { gray: 0, sepia: 0, hue: 0, sat: 1, contrast: 1 },
  nir: { gray: 1, sepia: 1, hue: -12, sat: 2.2, contrast: 1.05 }, // naranja cálido
  mir: { gray: 0.3, sepia: 0.7, hue: -45, sat: 2, contrast: 1.05 }, // rojizo
  ice: { gray: 1, sepia: 1, hue: 150, sat: 3, contrast: 1.05 }, // cian
  thermal: { gray: 1, sepia: 1, hue: -35, sat: 4, contrast: 1.2 }, // rojo-naranja intenso
  comp: { gray: 0, sepia: 0, hue: 0, sat: 2.2, contrast: 1.1 }, // colores realzados
};

/**
 * @param inten "Aplicación del filtro" (0 a 100): cuánto se acerca al tono del filtro.
 * @param gain "Intensidad de luz" (10 a 300): brillo general.
 */
export function skyCssFilter(id: FilterId, inten: number, gain: number): string {
  const r = RECIPES[id];
  const k = Math.min(Math.max(inten, 0), 100) / 100;
  const mix = (neutral: number, target: number) => neutral + (target - neutral) * k;

  const parts: string[] = [];
  if (r.gray) parts.push(`grayscale(${mix(0, r.gray).toFixed(2)})`);
  if (r.sepia) parts.push(`sepia(${mix(0, r.sepia).toFixed(2)})`);
  if (r.hue) parts.push(`hue-rotate(${mix(0, r.hue).toFixed(0)}deg)`);
  if (r.sat !== 1) parts.push(`saturate(${mix(1, r.sat).toFixed(2)})`);
  if (r.contrast !== 1) parts.push(`contrast(${mix(1, r.contrast).toFixed(2)})`);
  parts.push(`brightness(${(gain / 100).toFixed(2)})`);
  return parts.join(" ");
}