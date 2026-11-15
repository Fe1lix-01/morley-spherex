# Integración ROI / FITS — auditoría y MVP

Auditoría realizada sobre `feat/roi-fits`. Este documento, el contrato y la metodología estaban vacíos antes del MVP.

## Código existente

- `SkyComparison.tsx`: instancia `A.aladin` en `#eter-sky-viewer`, conservada en un ref; ruta `/sky-test`.
- `SpherexMosaic.tsx`: instancia independiente en `#eter-mosaic-viewer`; accesible desde `/preview`, selector de visor SPHEREx. AllWISE y SPHEREx HiPS son servicios reales. Un cambio de canal HiPS no representa un cambio de época.
- `SkyStage.tsx`: instancia directa en un contenedor de la vista previa, cargada dinámicamente. Usa `world2pix` para situar imágenes de prueba, marcadores y la capa SIMBAD. No se sustituye.
- `AladinBackground.tsx`: iframe con documento generado por `lib/aladin`; no comparte instancia con los anteriores.
- `PreviewPanel.tsx`: flujo mixto de catálogo remoto y épocas simuladas. `data/services/index.ts` usa mocks por defecto salvo `NEXT_PUBLIC_USE_MOCK=false`. El MVP ROI no usa ese servicio ni sus imágenes simuladas.
- `/api/v1/sia/observations`: búsqueda real en IRSA, normalización de tiempos y productos QR2/QR3; originalmente solo círculo de hasta 300 arcsec. Se añade el parámetro opcional `roi`, sin cambiar el comportamiento circular previo.
- `/api/v1/irsa/observations`: consulta TAP por posición/detector y enlaces de recortes fijos de 0.025°. No sirve para extraer una ROI de 20′.
- `/api/v1/observations`: catálogo local por nombres que incluyen `_D1_`…`_D6_`. Se reutiliza para importar por nombre; cargar un archivo desde el navegador permite también cubos sin esa convención.
- `/api/v1/frames`: metadatos y PNG locales, con restricciones de imagen primaria 2D y nombre de detector.
- `/api/v1/objects/{id}/remote-preview`: PNG de recortes IRSA de productos previamente registrados.
- `/api/v1/science/m101/channel-63/preview`: figura específica de M101, no un recorte arbitrario.
- `clients/irsa_cutouts.py`: descarga acotada, sin redirecciones; se reutiliza su transporte para importar un producto confirmado. No se modifica su API existente de recortes fijos.

## Integración implementada

1. `lib/roi.ts` calcula coordenadas y dimensiones esféricas; no realiza HTTP.
2. `RoiSelection` convierte las cuatro esquinas y el centro mediante `pix2world(..., "ICRS")`, y vuelve a proyectar la selección con `world2pix` cuando se mueve el mapa. Usa la instancia ya existente. La versión instalada 3.8.2 tiene un problema en el argumento opcional de `world2pix`; se usa su forma de dos argumentos, como el resto del proyecto.
3. `RoiWorkbench` coordina la interfaz y `services/roi-api.ts` concentra HTTP. Se monta en el mosaico y en `/sky-test`. El panel se oculta durante el dibujo para liberar espacio en móvil.
4. La búsqueda SIA acepta el polígono validado y conserva sus metadatos originales. Caché de consultas ROI en disco con TTL de una hora. No inicia descargas.
5. El nuevo router ROI recibe FITS locales o importa un producto IRSA confirmado; inspecciona HDUs y llama a `science/pipeline`. Los productos se identifican por hash de fuente y parámetros.
6. `science/pipeline` funciona también sin FastAPI mediante `python -m science.pipeline`.

## Operación y límites

- Caché predeterminada `data/roi-cache`, excluida de Git; configurable con `ROI_CACHE_DIR`.
- `ROI_MAX_ARCMIN=20`, `ROI_MAX_FITS_BYTES=134217728` (128 MiB), `ROI_CACHE_MAX_BYTES=1073741824` (1 GiB). Deben configurarse al iniciar el backend. El frontend lee `/science/roi/config`.
- Solo HTTPS en `irsa.ipac.caltech.edu`, rutas SPHEREx permitidas, sin query, redirecciones ni traversal. FITS sin compresión de archivo (`.fits`); no se aceptan `.fits.gz` en la API.
- Todas las importaciones remotas requieren confirmación; incluso tamaño desconocido. El transporte se corta al superar el límite, aunque el servidor no declare Content-Length.
- Se serializan las escrituras/procesamientos dentro de un proceso. Usar un worker para el MVP. No hay cola distribuida, autenticación, expiración automática de productos ni mantenimiento de caché; detener el backend antes de retirar productos manualmente.
- Los límites acotan un prototipo local, no sustituyen cuotas/autenticación de un servicio público. La reserva de espacio para procesar es conservadora y puede rechazar trabajo antes de llenar el disco.
- Los archivos de prueba y productos reales no se incorporan a Git. CNN, Gaia y ZOGY no se modifican.

Referencia de las conversiones del visor: [API oficial Aladin](https://cds-astro.github.io/aladin-lite/Aladin.html).
