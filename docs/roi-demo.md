# Demo ROI / FITS

Desde la raíz de `morley-roi`, con Python 3.12 y Node 22.18+ (las pruebas TS usan soporte nativo de tipos; se ejecutaron con Node 24):

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r apps/science-api/requirements.txt
PYTHONPATH=apps/science-api .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

En otra terminal:

```bash
cd apps/web
npm ci
npm run dev
```

Usar el comando predeterminado (Turbopack). El diagnóstico posterior con caché limpia comprobó Fast Refresh con Turbopack y reprodujo un fallo HMR con Webpack; véase `roi-integration-audit.md`. No ejecutar build y dev sobre la misma caché activa.

La URL de API predeterminada es `http://127.0.0.1:8000/api/v1`. Para otra dirección, definir `NEXT_PUBLIC_API_URL` en `apps/web/.env.local` antes de iniciar Next.js. El flujo ROI no depende del selector de mocks de la vista ÉTER.

## Demo desde el visor

1. Abrir `http://localhost:3000/preview` y elegir **Mosaico SPHEREx DR1**; alternativamente `/sky-test`.
2. Pulsar **Seleccionar región**. Se usa el centro actual, se acerca el mapa y aparece una región de 10′ × 10′ con marco máximo de 20′ × 20′. Para otro destino, editar RA/Dec y pulsar **Aplicar centro**.
3. Arrastrar el interior para mover la región o las esquinas para cambiar el tamaño. **Usar tamaño máximo** y **Restablecer 10′ × 10′** conservan su centro. También se puede **Dibujar / reemplazar**. El zoom no cambia sus coordenadas.
4. Revisar centro, cuatro esquinas y dimensiones; pulsar **Confirmar región**. Cualquier edición invalida la confirmación previa.
5. Elegir detector y **Consultar observaciones**. Son metadatos individuales SIA QR3. Se distingue ausencia de observaciones, falta de conexión al backend, errores HTTP e indisponibilidad IRSA.
6. Elegir un FITS remoto y confirmar la transferencia, o **Abrir FITS local**. Para la prueba real de esta sesión: `/Users/felixgarcia/Downloads/mosaic_cube.fits`, extensión `1: IMAGE`, índice de canal `62`.
7. Pulsar **Seleccionar centro del FITS**, ajustar si se desea y **Confirmar región** nuevamente.
8. **Extraer región** muestra PNG, unidades, cobertura, estadísticas y enlaces FITS/JSON. La región devuelta se verifica contra la enviada. **Eliminar** retira solo la selección.

Sin acceso al CDN de Aladin/HiPS no se puede navegar el cielo, pero el panel permite abrir el FITS y seleccionar su centro. La CLI siguiente es completamente local.

## Demo científica sin red

No copiar el FITS a Git. Desde la raíz, con el archivo real ya disponible:

```bash
.venv/bin/python -m science.pipeline \
  /Users/felixgarcia/Downloads/mosaic_cube.fits \
  /private/tmp/morley-m101-roi.fits \
  --hdu 1 --channel 62 --size 10
```

La CLI usa el centro WCS si no se dan `--ra` y `--dec`; escribe el recorte y un JSON con el mismo nombre base. Para otro FITS adaptar ruta, extensión y canal. El archivo de salida debe ser diferente del original. No descarga datos.

## Pruebas reproducibles

```bash
PYTHONPATH=apps/science-api MPLCONFIGDIR=/private/tmp/morley-mpl \
  .venv/bin/pytest apps/science-api/tests -q
node --test apps/web/tests/roi*.test.mjs
cd apps/web
npm run build
```

Para incluir la prueba opcional del FITS real:

```bash
ROI_TEST_FITS=/Users/felixgarcia/Downloads/mosaic_cube.fits \
PYTHONPATH=apps/science-api MPLCONFIGDIR=/private/tmp/morley-mpl \
  .venv/bin/pytest apps/science-api/tests/test_roi.py -q
```

Las pruebas de clientes remotos existentes usan servidores HTTP locales y necesitan permisos para sockets. Las pruebas ROI usan stubs para IRSA; no prueban disponibilidad actual ni descargan FITS remotos. La prueba real abre el archivo local indicado. Si falta `ROI_TEST_FITS`, se omite explícitamente.

## Archivos de implementación

- Frontend nuevo: `src/lib/roi.ts`, `src/components/roi/RoiSelection.tsx`, `src/components/roi/RoiWorkbench.tsx`, `src/services/roi-api.ts`, `tests/roi.test.mjs` dentro de `apps/web`.
- Frontend modificado: `SkyComparison.tsx`, `SpherexMosaic.tsx`, `src/types/aladin-lite.d.ts`.
- Backend nuevo: `app/core/science.py`, `app/services/roi.py`, `app/routers/roi.py`, `tests/test_roi.py` dentro de `apps/science-api`.
- Backend modificado: `app/main.py`, `app/schemas/sia.py`, `app/clients/sia.py`, `app/services/sia.py`.
- Motor: `science/pipeline/region.py`, `fits_roi.py`, `__main__.py`.
- Documentación: arquitectura, contrato, metodología y esta guía. `.gitignore` excluye caché/entorno y permite el nuevo módulo fuente bajo `src/lib`.

No se ejecutan commits, merges ni push. No se modifica la CNN ni se integra Gaia/ZOGY/BraAI.

## Verificación de la primera iteración (histórico)

El diagnóstico y las pruebas actualizados, incluida la ejecución en navegador y el build Turbopack, están en `roi-integration-audit.md`.

- Suite completa del backend, con el FITS real configurado: **265 passed, 1 skipped**, 69.06 s. La omisión corresponde a una prueba existente opcional, no se cuenta como ejecutada.
- Suite específica ROI repetida después de añadir los encabezados WCS a la inspección JSON: **18 passed**.
- Geometría TypeScript: **4 passed** con `node --test`.
- `npm run build -- --webpack`: compilación, TypeScript y generación de rutas correctos.
- `git diff --check`: sin errores.
- `npm run build` (Turbopack): no pasó en este entorno por `binding to a port / Operation not permitted`; se verificó con Webpack sin modificar el script existente.
- Astropy emitió advertencias sobre los cuatro ejes WCS del cubo real; se comprobó explícitamente la WCS 2D resultante y su igualdad con el original.
- No se ejecutó una prueba interactiva de navegador ni una consulta al IRSA público en vivo. Las pruebas de transporte usan servicios locales/stubs; la extracción real usa el FITS local.


## Regresión del selector en navegador

La comprobación automatizada nueva está en `apps/web/tests/roi-browser.mjs`. Requiere Chrome, ambos servidores activos y Playwright disponible **como herramienta de pruebas**, no como dependencia de producción. Se ejecutó con instalación temporal fuera del proyecto:

```bash
ROI_PLAYWRIGHT_MODULE=/private/tmp/morley-browser/node_modules/playwright/index.mjs \
ROI_TEST_FITS=/Users/felixgarcia/Downloads/mosaic_cube.fits \
node apps/web/tests/roi-browser.mjs
```

Esta regresión específica espera el cubo de M101 descrito en metodología y sus estadísticas conocidas. `ROI_WEB_URL` y `ROI_BROWSER_ARTIFACTS` permiten cambiar URL y carpeta de evidencias. Para un FITS distinto usar la CLI/prueba científica y adaptar las aserciones, no reinterpretar el resultado esperado. Las consultas SIA del navegador son controladas; el procesamiento del FITS es real. Para la auditoría actualizada, causas confirmadas y estado de las pruebas consultar `roi-integration-audit.md`.
