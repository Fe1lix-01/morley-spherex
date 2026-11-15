# Reparación de integración del equipo

Rama `fix/full-team-e2e`, base `33601fe`. Sin cherry-pick, merge, commit ni push.

## Causas confirmadas

- **ROI desconectado:** comparado con `da35e66`, `SpherexMosaic` conservaba `roiView` pero había perdido el import, `setRoiView(aladin)` y el montaje de `RoiWorkbench`. Se restablecieron esas tres conexiones, conservando SIMBAD, selección espectral y controles del equipo. Acceso: `/preview` → **Mosaico SPHEREx DR1** → **Seleccionar región**. `PreviewPanel` no se reemplazó.
- **FastAPI inaccesible:** el PID 37813 era un recargador Uvicorn iniciado desde `apps/web`, con hijo 37815 terminado y socket 8000 CLOSED/reservado. No había listener HTTP. Se detuvo únicamente ese recargador y arrancó FastAPI desde el repositorio con ruta de importación explícita. No se atribuye la muerte del hijo a una excepción concreta porque no se dispone de su log original.
- **ML sin artefactos configurados:** los endpoints sí estaban registrados. Una vez recuperado FastAPI, respondieron 503 por falta de `ETER_ML_PYTHON`, `ETER_ML_WEIGHTS`, `ETER_ML_SAMPLE`, `ETER_BARNARD_ARTIFACTS_DIR`. No se encontraron pesos/tripletes procesados en el repositorio ni en la búsqueda de Downloads. El panel ahora muestra el detalle del backend. Barnard necesita `barnard_triplete_real_exploratorio.npz` con `valid_mask` 2D y `barnard_triplete_real_exploratorio.png`. Los PNG de `public/candidates/barnard` no son sustitutos de estos artefactos.
- **Recurso estático:** `/fenomenos/nebulosas.jpg` no existe; el archivo está en `/phenomena/nebulosas.jpg`. Se corrigió la referencia, sin mover archivos. Las tres épocas simuladas existen.
- **HiPS:** IRSA devolvió 200 durante esta auditoría; no se reprodujo una caída permanente. El proxy anterior hacía una descarga independiente sin caché de servidor por petición, con espera de 20 s y sin alternativa. Ahora agrupa peticiones simultáneas y mantiene caché limitada a 32 MiB/una hora; intenta IRSA y después un espejo del mismo AllWISE, con 6 s por intento. Los fallos no se almacenan. Se conserva el filtro de rutas, sin permitir URLs arbitrarias. `X-HiPS-Survey` y `X-HiPS-Upstream` identifican procedencia. El espejo China-VO publicado por CDS respondió 200; otros espejos comprobados devolvieron 404 o timeout.

- **Canal HiPS equivocado:** al seleccionar ordinal 62, la red pedía `Npix*_10.png`; ordinal 63 pedía `_9.png`. Aladin 3.8.2 no usa `data_cube_crval3_arr` y direcciona este cubo uniformemente en frecuencia. Se añadió un adaptador explícito al centro del bin de transporte; las etiquetas físicas siguen usando la tabla oficial. Se verificó por red que ordinales 62/63 descargan `_61.png`/`_62.png` con 200. La coordenada interna de transporte no se usa en ningún cálculo científico.
- **Descarga JSON tapada:** en el visor integrado Astro se superponía al pie del ROI. Se reservó espacio inferior y se agrupó el selector espectral con los controles del mosaico para que no tape los resultados FITS.

## Separación científica

AllWISE siempre se etiqueta como referencia. Un fallo de inicialización SPHEREx vuelve a AllWISE con aviso explícito. El fallo posterior de una tesela no se interpreta automáticamente como fallo de todo el survey.

SPHEREx publica 102 canales PNG y declara vacíos los ordinales 51 y 52. Esto corresponde al **HiPS DR1**, no invalida automáticamente el canal 52 del FITS local M101. Los cortes PNG se fijan explícitamente a 0–255, escala lineal, coherentes con los valores predeterminados del Aladin instalado. No se ha demostrado que los cortes fuesen la causa del blanco reportado. Los controles restaurados de brillo/contraste actúan sobre el renderizado de Aladin, nunca sobre el FITS ni sus estadísticas. El rango físico 0–40 declarado por el producto no se aplica como segundo recorte a sus PNG.

El pipeline FITS conserva su política SOURCE/OUTLIER/OVERFLOW y todos los canales. No se modificaron la CNN, los experimentos matemáticos 00–09, los endpoints de diagnósticos, Astro ni el frontend original de épocas. Diagnósticos multiepoca mantiene su región RA 295.4097841°, Dec −15.2231692°, distinta de M101 y Barnard.

Referencias: [registro CDS de AllWISE y espejos](https://alasky.cds.unistra.fr/MocServer/query?ID=CDS%2FP%2FallWISE%2Fcolor&fmt=html&get=record), [propiedades oficiales SPHEREx HiPS](https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube/properties), [controles de renderizado Aladin](https://aladin.cds.unistra.fr/AladinLite/doc/API/).

## Arranque reproducible

Desde la raíz del repositorio:

```sh
.venv/bin/python -m uvicorn app.main:app --app-dir apps/science-api --host 127.0.0.1 --port 8000
```

En otra terminal, desde `apps/web`: `npm run dev`. No lanzar `uvicorn app.main:app` desde `apps/web`. Las variables opcionales están documentadas en `apps/science-api/.env.example`; se deben exportar o cargar explícitamente con `--env-file`. Crear un archivo `.env` por sí solo no configura estos endpoints. No se ejecuta entrenamiento al arrancar.

## Verificación

Resultados y artefactos de esta ejecución se completan al finalizar las pruebas. ML real queda no disponible mientras no se proporcionen sus artefactos; no se simulan predicciones para aprobar el flujo.

### Resultados ejecutados

- `tsc --noEmit`: correcto. ESLint de los archivos modificados: sin errores ni advertencias.
- `npm run build`: correcto con Turbopack; cachés de build y desarrollo separadas. Servidor de desarrollo restaurado en 3000, FastAPI en 8000.
- Python: suite existente **274 passed, 1 skipped**; nuevas pruebas de disponibilidad ML **3 passed**. ROI usa `ROI_TEST_FITS=/Users/felixgarcia/Downloads/mosaic_cube.fits`. Las 52 advertencias Astropy describen cuatro ejes WCS en el cubo de tres dimensiones; no se ocultaron.
- Frontend: **20 passed**, incluyendo fallo/alternativa/caché/deduplicación de HiPS y direccionamiento de los 102 planos.
- Chrome aislado, sin extensiones/traducción: flujo ROI completo desde `/preview`, dibujo, arrastre, redimensión, máximo 20′, centro FITS, canal índice 51, tres imágenes y descargas FITS/JSON. Consulta SIA simulada únicamente para comprobar el contrato geométrico; FITS y backend reales.
- El FITS **descargado por el navegador** contiene `(102,67,67)`, SCIENCE/FLAGS/NHITS exactamente iguales a las rebanadas del original, WCS celeste idéntica (máxima diferencia 0°), checksums válidos y PROVENANCE igual al JSON descargado. Canal índice 51: 4489 totales, 4488 finitos, 4224 válidos, FLAGS=0 828, SOURCE 3486, OUTLIER 264, OVERFLOW 0. SHA256 del FITS: `9ee96d330c367c8357b8d1a58130d27db16bc8ac0b253edf06aa6e75e89888fe`.
- HTTP 200: `/`, `/preview`, `/sky-test`, `/catalog`, nebulosas, las tres épocas PNG y Allsky del proxy. Diagnósticos devuelve la región correcta y conserva explícitamente sus limitaciones científicas. ML responde 503 en vez de quedar esperando por un backend muerto.
- Astro responde preguntas y Barnard muestra los nombres de configuración ausentes. La CNN no se ejecutó por falta de artefactos, ni se inventó su salida.

Artefactos de esta sesión: `/private/tmp/full-team-integrated-roi/` (FITS, JSON, validación independiente y captura ROI), `/private/tmp/full-team-browser/` (Astro, Barnard, mosaico, traza de teselas, HTTP). Logs: `/private/tmp/full-team-{python,frontend,build}.log`.

### Archivos modificados

- Montaje y disposición: `SpherexMosaic.tsx`, `RoiWorkbench.tsx`.
- Visualización/HiPS: `src/lib/spherex-hips.ts`, `src/types/aladin-lite.d.ts`, `src/app/api/sky-hips/[...path]/route.ts`.
- Disponibilidad ML: `app/routers/ml.py`, `src/services/science-api.ts`, `BarnardPanel.tsx`, `apps/science-api/.env.example`.
- Recurso: `src/data/phenomena.ts`.
- Regresiones: `test_ml_availability.py`, `hips-proxy.test.mjs`, `roi-browser.mjs`, `team-browser.mjs`.
- Documentación: este informe. Los `.DS_Store` aparecidos durante la sesión se dejaron intactos y no forman parte de la reparación.

### Blanco durante la carga: alcance de la evidencia

Una captura temprana mostró el cielo blanco al cambiar de canal. Una inspección controlada, manteniendo cortes `[0,255]`, brillo −0.02 y contraste +0.02, mostró correctamente el plano 63 después de completar las teselas. La prueba visual final espera las 12 teselas Norder0 de cada plano y ambas capturas son correctas. La tesela original examinada es PNG con paleta y valores RGB no saturados (mediana 0, percentil 99 = 35), por lo que no corresponde modificar el FITS ni atribuir el blanco a valores científicos saturados. No se ha aislado la causa interna del blanco transitorio del renderizador; no se afirma haber corregido un defecto de Aladin. Queda registrado para seguimiento si vuelve a persistir con la carga completa.
