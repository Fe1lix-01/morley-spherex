# Auditoría de integración y diagnóstico de desarrollo — 2026-11-15

## Base de comparación recuperada

No se usa `dev_felix` como única referencia. El reflog conserva:

- `5f49ab6`: estado con el trabajo científico/API de Marvin, anterior a la última integración de Richi.
- `93c7bcb`: merge con padres `5f49ab6` y `13b8bc4`; integra los paneles de Richi con el estado científico previo. La historia también contiene las integraciones del frontend de Alex.
- `9c51535`: corrección posterior de sintaxis/estructura de PreviewPanel y lockfile, hecha antes de esta implementación ROI. Es HEAD al inicio de ambas sesiones ROI.

El estado inicial de esta segunda sesión contiene los cambios ROI sin commit de la sesión anterior. Se revisaron `git status`, `git diff --stat`, log, reflog y diffs contra HEAD. No se ha cambiado de rama, restaurado archivos de compañeros ni realizado commits/merges/push. La atribución de cambios locales se basa en los diffs y el historial de trabajo de estas sesiones, no en atribuir autoría Git a archivos sin commit.

## Separación del trabajo

Código integrado que se conserva: `SkyStage`, `PreviewPanel`, `AladinBackground`, selector de visores, catálogo, hooks, estilos globales, layout y endpoints anteriores. No se alteran en esta sesión.

La integración ROI anterior añadió montaje de `RoiWorkbench` en `SkyComparison` y `SpherexMosaic`, tipos Aladin, router/servicios científicos, polígono opcional SIA y pipeline. Los documentos científicos estaban vacíos y se completaron en aquella sesión. La auditoría inicial detallada está en `architecture.md`.

Cambios nuevos de esta sesión:

- `src/lib/roi.ts`: movimiento mediante rotación esférica, redimensionado en plano tangente acotado, zoom separado del estado científico.
- `RoiSelection.tsx`: marco máximo, movimiento del interior, cuatro tiradores, cancelación de gesto, dibujo libre conservado.
- `RoiWorkbench.tsx`: selección guiada, destino explícito, campos sincronizados con ROI, confirmación, botones máximo/restablecer, estado de conexión y contraste local de campos.
- `services/roi-api.ts`: errores de conexión/HTTP/IRSA/descarga diferenciados, comprobación del eco de región y copia de parámetros al enviar.
- `SkyComparison.tsx`, `SpherexMosaic.tsx`: cambio mínimo adicional de integración: publicar la instancia Aladin al hijo mediante estado en lugar de leer un ref durante render. Corrige dos errores ESLint introducidos por nuestra integración previa; no sustituye ni reinicializa el visor al editar ROI.
- `types/aladin-lite.d.ts`: método `getSize` para adaptar el margen de zoom a la proporción del visor.
- `app/schemas/sia.py`: rechazar RA/Dec de consulta diferentes del centro del polígono. La validación solo afecta al parámetro ROI nuevo; el círculo existente conserva su comportamiento.
- Pruebas: geometría/HTTP del frontend, contrato FastAPI y regresión de navegador con FITS real.
- `apps/web/AGENTS.md`: bloque agregado automáticamente por Next al arrancar con `experimental.agentFeedback` ya habilitado; no fue una refactorización manual.

No se modifican CNN, Gaia, ZOGY, rutas ni métodos anteriores de Marvin. El pipeline FITS previo se conserva y se verifica nuevamente con datos reales.

## Diagnóstico: evidencia y límites

### Procesos y backend

Al inicio había un único servidor Next.js: `next dev --webpack`, puerto 3000, cwd de este worktree. No había listener en 8000. Una petición a `/api/v1/science/roi/config` produjo conexión rechazada. Esto confirma un backend local detenido en ese momento, no un fallo IRSA.

Se inició FastAPI en 127.0.0.1:8000. `/config` respondió 200 y `Access-Control-Allow-Origin: http://localhost:3000`. Se inspeccionó OpenAPI y se reinició después de actualizar la validación. No se cambiaron CORS ni URL predeterminada porque ya coincidían con las rutas/puertos de la aplicación.

### Cachés y bundlers

Se detuvo únicamente el Next identificado. La carpeta `.next` original se movió, sin eliminarla, a `/private/tmp/morley-roi-diagnostic/original-next`; se conservaron los logs. Se probaron secuencialmente Turbopack y Webpack, siempre un servidor en 3000, cachés separadas, y contextos Chrome nuevos sin extensiones ni traducción. No se tocaron `node_modules`, lockfiles, layout ni dependencias del proyecto. Playwright se instaló únicamente en `/private/tmp/morley-browser` para las pruebas.

| Prueba controlada | Turbopack | Webpack |
| --- | --- | --- |
| `/preview`, `/sky-test`, `/catalog` | HTTP 200, sin errores JS | HTTP 200, sin errores JS en carga inicial |
| Hidratación en contexto limpio | Sin advertencias | Sin advertencias |
| Edición temporal de texto de RoiWorkbench | Texto actualizado, 0 navegaciones, campo RA conserva 123.45 | Texto actualizado mediante 2 recargas, RA pierde el valor |
| Error HMR | No apareció | `self.webpackHotUpdate_N_E is not a function`, reproducido |

La edición temporal se restauró y no cambió la funcionalidad. El caso Webpack exporta únicamente un componente React; el mensaje genérico de Fast Refresh no basta para demostrar que el archivo exporte valores externos al árbol React. El fallo persiste en caché limpia, así que **no se ha confirmado mezcla de recursos como causa**. El bundle Aladin instalado no contiene `webpackHotUpdate`; eso tampoco constituye una prueba exhaustiva sobre el origen interno del fallo.

Se regresa al comando predeterminado `npm run dev` (Turbopack). No se cambian permanentemente scripts ni bundler. Tras cambiar de bundler, abrir una pestaña nueva o recargar completamente las pestañas antiguas para no conservar un runtime de la sesión anterior. Producción y desarrollo se verifican sin procesos compartiendo `.next`.

### Hidratación y traducción

El log original confirma divergencia entre `lang=en` esperado por React y `lang=es`/`translated-ltr` presentes en DOM. El layout fuente declara `lang=en`; la aplicación no añade `translated-ltr`. El documento español de `AladinBackground` pertenece a un iframe separado, no al html raíz.

En Chrome nuevo, ambas variantes de bundler conservaron `lang=en` y no emitieron errores de hidratación. Una prueba adicional mutó deliberadamente `lang` y la clase antes de hidratar, exclusivamente dentro del navegador de prueba: produjo una advertencia de hidratación. Esto reproduce el mecanismo de mutación externa, **no identifica de forma definitiva el traductor/extensión del navegador original**. La comparación manual en la ventana privada del usuario no se ha recibido durante la implementación.

No se usa `suppressHydrationWarning` ni se cambia `layout.tsx`. Los iconos Apple opcionales quedan fuera de prioridad; tampoco se atribuyen automáticamente todos los 404 a iconos sin verificar su URL.

### Discrepancia de coordenadas

Antes, RA/Dec se inicializaban con M101 mientras Aladin arrancaba en 0°,0°. Dibujar convertía correctamente el lugar del visor mediante `pix2world`, pero no actualizaba los campos. Por eso podían verse coordenadas de destino de M101 junto a una ROI en otra parte del cielo. Era una ambigüedad de estado/presentación, no evidencia de una conversión lineal de píxeles incorrecta.

Ahora no hay destino de M101 precargado independiente del visor. Activar selección usa el centro actual o un destino editado explícitamente; cada edición de ROI actualiza campos y lectura de esquinas. Modificar manualmente el destino invalida la confirmación hasta aplicarlo. Las consultas y productos usan una copia de la ROI confirmada, verifican el eco del servidor y el backend rechaza el centro contradictorio.

## Conflictos de integración posibles

- Cambios simultáneos en inicialización Aladin o en sus tipos pueden afectar el montaje ROI; se conservan los refs y el ciclo de vida original y solo se publica el estado para el hijo.
- La extensión opcional del modelo SIA debe conservarse al integrar futuras validaciones de Marvin. No duplicar la operación de búsqueda.
- Los documentos estaban vacíos en la base; futuras contribuciones deben combinar contenido, no sustituirlo.
- La caché y los productos locales no se suben a Git. Los respaldos de diagnóstico están fuera del repositorio.
- El bloque AGENTS autogenerado depende de una opción preexistente de Next; no implica que se haya cambiado la configuración del equipo.

## Verificaciones ejecutadas

- Backend: 266 aprobadas, 1 omitida; incluye FITS real local y rechazo de centro contradictorio antes de consultar IRSA.
- Geometría y cliente HTTP: 11 aprobadas; polos, RA 0/360°, movimiento, límite de redimensionado, zoom inmutable, igualdad de región enviada/devuelta y clasificación de errores.
- TypeScript: sin errores.
- `npm run build`: correcto con Turbopack, caché independiente y desarrollo detenido; rutas estáticas y dinámicas generadas.
- ESLint: cero errores; permanece una advertencia preexistente de `<img>` en `catalog/page.tsx`, que no se modifica.
- Chrome/Aladin real: activación desde cielo completo, movimiento a Dec 85° con cruce de RA, cambio de tamaño acotado, máximo/restablecimiento, sustitución por dibujo libre, zoom, confirmación, consulta de metadatos controlada, carga y extracción real del cubo M101, borrado y selector dentro de `/preview`. `/catalog` también comprobado.
- La búsqueda SIA en la regresión de navegador usa una respuesta controlada; no se declara una consulta IRSA en vivo. Aladin sí cargó HiPS y `/api/sky-hips/properties` y tiles respondieron 200 durante el diagnóstico.
- El FITS real se transfirió al FastAPI local y se extrajo IMAGE, índice de canal 62: 742 píxeles válidos de 4489, con región devuelta idéntica a la confirmada.
- Hidratación: carga limpia sin advertencias; mutación deliberada de atributos reproduce una advertencia.

Referencias para interpretar los mensajes, sin sustituir la reproducción local: [Fast Refresh](https://nextjs.org/docs/architecture/fast-refresh), [CLI y selección de bundler](https://nextjs.org/docs/app/api-reference/cli/next).


Estado al terminar: un Next.js predeterminado (Turbopack) en 3000 y FastAPI en 8000. La regresión de navegador persistida en el repositorio se ejecutó correctamente después de reiniciar los servicios. Los respaldos de caché de producción y desarrollo están separados; no se hizo un build mientras el servidor de desarrollo usaba esa carpeta.
