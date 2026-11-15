# MVP conectado: objetivos, FITS y trabajos científicos

Implementación en `fix/full-team-e2e`, conservando ambos visores y sus componentes. No se hizo merge, commit ni push. Los cambios de la reparación anterior permanecen intactos.

## Flujo de uso

1. En ÉTER, elegir un candidato. **Iniciar ROI del objetivo** abre el mosaico conservando identidad y coordenadas. En SPHEREx, **Elegir candidato** usa la misma lista. Cambiar de visor mantiene los componentes montados, el objetivo, el archivo y el resultado.
2. **Seleccionar región** crea 10′ × 10′; permite mover, redimensionar hasta 20′ y confirmar. Las coordenadas manuales y las selecciones SIMBAD también se comparten. **Seleccionar centro del FITS** cambia explícitamente el objetivo a «Centro del FITS seleccionado», evitando atribuir M101 al objeto anterior.
3. **Consultar observaciones** usa el endpoint SIA existente con la región confirmada. La descarga remota exige confirmación, admite únicamente IRSA y conserva el límite 128 MiB.
4. Sin Internet: **Actualizar catálogo FITS local**, **Buscar FITS locales del objetivo**, elegir un producto y **Usar FITS registrado**. También funciona **Abrir FITS local**. La cobertura parcial está indicada; un archivo que no contiene el centro no se usa para la extracción del flujo nuevo.
5. **Extraer región** envía un trabajo controlado. Se reutiliza `science/pipeline/`, con sus máscaras y WCS, preservando todos los canales. Se muestran las tres imágenes científicas y las estadísticas.
6. **Analizar FITS y comprobar épocas** calcula la tabla por canal y consulta los FITS temporales que realmente cubren esa región. **Comprobar diagnósticos multiepoca** permite hacerlo también antes de extraer. Los resultados se descargan como JSON, además del FITS y JSON del recorte.

## Matriz funcional

`PASS` significa conexión y comprobación correctas; no certifica precisión astrofísica. `PARTIAL` identifica un resultado limitado. `BLOCKED` identifica datos o requisitos ausentes. Ninguno se transforma en una detección por cambiar el estado de un trabajo a SUCCEEDED.

| Funcionalidad | Frontend que la invoca | Endpoint utilizado | Datos de entrada | Procesamiento ejecutado | Resultado obtenido | Estado |
|---|---|---|---|---|---|---|
| Selección de los cinco objetivos | TopRightTools / selector de SpherexMosaic / TargetProvider | GET `/science/workflow/targets` | Catálogo astrométrico versionado | Propagación angular ICRS de J2000 a J2026 | Misma identidad y coordenadas en ambos visores | PASS |
| Coordenadas, cambio de visor e inicio ROI | PreviewPanel / ViewerSwitch / RoiWorkbench | Estado compartido; después endpoints ROI | Objetivo o RA/Dec manuales | Centrado Aladin; región esférica; conservación del resultado | Verificado en Chrome para los cinco objetivos | PASS |
| Búsqueda remota | RoiWorkbench / búsqueda ÉTER | GET `/sia/observations` | Coordenadas, detector, colección y/o polígono | Consulta real SIA; sin inferir píxeles a partir de metadatos | HTTP 200 para cinco consultas; cuatro con productos, WISE sin productos en D2/QR3 | PASS para conexión; PARTIAL para disponibilidad científica |
| Indexación local | RoiWorkbench | POST `/science/workflow/jobs`, kind=index | Rutas locales permitidas por configuración | WCS, huella, fecha, detector, procedencia y SHA256; límite 256 archivos y 128 MiB/archivo | M101 original, recortes y doce Level-2 indexados | PASS |
| Selección offline | RoiWorkbench | POST `/science/workflow/catalog/search`; job kind=import_local | ROI; target_id cuando está verificado | Cobertura WCS y posición del objetivo a fecha de observación cuando existe; integridad del archivo | M101 seleccionable; ninguno de los cinco recibe FITS de otra región | PASS |
| Abrir FITS local | RoiWorkbench | POST `/science/roi/files` | FITS local acotado | Registro por hash e inspección de extensiones | M101 registrado, IMAGE/NHITS/FLAGS inspeccionables y 102 canales | PASS |
| Extracción y máscaras | RoiWorkbench | job kind=extract; GET `/science/workflow/jobs/{id}` | asset_id, HDU, canal, ROI | Verificación del centro; motor WCS existente; política de calidad del producto | M101 `(102,67,67)`, canal 1: 3750/4489; canal 52: 4224/4489 | PASS |
| Análisis espectral / suma regional | ScienceResults | job kind=analysis | product_id | Mediana, media y suma por máscara; área sólida WCS para MJy/sr→mJy | 102 filas con metadatos espectrales y hash del FITS | PASS como resumen regional |
| Fotometría de fuente calibrada | ScienceResults | Mismo trabajo; limitaciones explícitas | ROI y máscaras | No se inventan PSF, corrección de apertura ni fondo | La suma regional no se presenta como flujo total de una fuente | BLOCKED para fotometría calibrada |
| Diagnóstico de las doce observaciones | RoiWorkbench / ScienceResults | job kind=temporal/analysis | Centro de la región cubierta y FITS Level-2 reales | Funciones `measure_single_cutout` y `decide_pair` de `06_science_routes.py`; apertura 3 px, anillo 5–8 px | Diagnósticos individuales y evaluación de pares; sin sustracción ni declaración de variabilidad | PARTIAL |
| Multiepoca M101 y cinco objetivos | Mismos controles | Mismo trabajo | Selección espacial | Exclusión de cubos espectrales y recortes derivados como épocas independientes | Sin épocas locales compatibles; motivo explícito | BLOCKED |
| Panel Barnard | BarnardPanel | GET `/ml/barnard/preview` | ETER_BARNARD_ARTIFACTS_DIR | Validación de NPZ y máscara, sin inferencia automática | 503 con nombres de los dos artefactos faltantes | BLOCKED por datos |
| Demo CNN | BarnardPanel | job kind=demo → función existente de Marvin | ETER_ML_PYTHON, ETER_ML_WEIGHTS, ETER_ML_SAMPLE | Solo comando infer, nunca demo/train del script | Estado de servicio ausente; identificación sintética conservada | BLOCKED por artefactos |
| Inferencia sobre ciencia | ScienceResults | GET `/science/workflow/ml/compatibility`; job kind=inference | Triplete registrado asociado al product_id | Validación `(3,63,63)`, finitud, procedencia, épocas/banda/PSF; proceso infer acotado | Contrato conectado; no existe un triplete real compatible ni pesos configurados en esta instalación | BLOCKED por artefactos/preparación |
| Descargas | RoiWorkbench / ScienceResults | GET `/science/roi/products/{id}/{fits,json}`; GET `/science/workflow/jobs/{id}/result` | Identificadores del producto/trabajo | Entrega de productos persistidos | FITS, metadatos y análisis descargados en Chrome | PASS |
| Diagnósticos anteriores de solo lectura | API existente | GET `/science/diagnostics/{summary,observations,pairs}` | Reporte offline anterior | Lectura del reporte propio de RA 295.4097841°, Dec −15.2231692° | Contrato preservado; no reutilizado como resultado de M101/Barnard | PASS |
| Astro, canales y épocas simuladas | Componentes existentes | Sus servicios previos; HiPS | Pregunta / canal / controles | Respuesta Astro; direccionamiento HiPS; animación explícitamente simulada | Regresión visual y HTTP, canales 62/63 y controles | PASS |

## Cinco objetivos: identidad y evidencia individual

Fuente única: `resources/science/targets.json`, servida por la API. La lista visual existente se reutiliza: se añade Epsilon Indi B, sin duplicar los otros candidatos ni reemplazar sus imágenes. Las coordenadas científicas usan la ficha verificada, no las posiciones de las PNG de demostración.

| Objetivo | Identidad verificada | RA J2026 (°) | Dec J2026 (°) | Selección ÉTER/SPHEREx y ROI | FITS offline | Consulta IRSA D2/QR3, radio 100″, límite 3 |
|---|---|---:|---:|---|---|---|
| Barnard's Star | NAME Barnard's star | 269.446267880 | +4.768204412 | PASS | BLOCKED: fuera de las huellas disponibles | 200, 3 productos |
| Epsilon Indi B | * eps Ind B, sistema Ba/Bb; **no A** | 331.096668779 | −56.800649174 | PASS | BLOCKED: fuera de las huellas disponibles | 200, 3 productos |
| WISE 0855-0714 | WISEA J085510.74-071442.5 | 133.759765271 | −7.242182183 | PASS | BLOCKED: fuera de las huellas disponibles | 200, 0 productos |
| RW Aurigae | V* RW Aur, sistema de catálogo | 76.956586575 | +30.401291346 | PASS | BLOCKED: fuera de las huellas disponibles | 200, 3 productos |
| R Draconis | V* R Dra | 248.167233072 | +66.755023826 | PASS | BLOCKED: fuera de las huellas disponibles | 200, 3 productos |

La ausencia en esa búsqueda de WISE no demuestra ausencia en otras bandas/colecciones. La presencia de metadatos SIA tampoco certifica una detección del objeto ni calidad del FITS. No se descargaron estos productos remotos.

Se verificaron coordenadas ICRS a época J2000 y movimientos propios μRA·cosDec/μDec en mas/año: Barnard −801.551/+10362.394; Epsilon Indi B +3981.977/−2466.832; WISE −8123.7/+673.2; RW Aur +7.23/−20.33; R Dra −20.643/+6.149. Astropy propaga movimiento angular para el apuntado; no se aplican paralaje, velocidad radial, aceleración perspectiva ni órbita binaria. No es una solución astrométrica de precisión para fotometría. Los mensajes ERFA sobre distancia implícita permanecen visibles. Las coordenadas manuales no reciben una época inventada.

Referencias primarias consultadas el 2026-11-15: [Barnard](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=Barnard%20Star&output.format=ASCII), [Epsilon Indi B](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=eps%20Ind%20B&output.format=ASCII), [WISE 0855](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=WISE%20J085510.83-071442.5&output.format=ASCII), [RW Aur](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=RW%20Aur&output.format=ASCII), [R Dra](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=R%20Dra&output.format=ASCII). El servidor principal devolvió 404 a las consultas ensayadas; se verificó el espejo Harvard.

## Límites científicos y operativos

- Índice local en `data/science-mvp/catalog.json`; trabajos en `data/science-mvp/jobs/`, ambos ignorados por Git. Los FITS siguen excluidos. Se incluyen la caché ROI, el directorio FITS previo y `morley_unified/outputs/data/candidates_05`; se pueden ampliar con `MORLEY_FITS_ROOTS`, o usar `M101_FITS_PATH`. Los endpoints no aceptan rutas arbitrarias.
- El índice conserva WCS/huella, fechas y procedencia. Se distingue el cubo coadicionado de una exposición individual y de un recorte derivado. Un hueco en FLAGS/calidad no se considera detección: la cobertura geométrica y la calidad científica se evalúan por separado.
- Un trabajador, máximo cuatro trabajos admitidos, subproceso aislado, 120 s de ejecución por trabajo, captura de fallos, máximo 300 trabajos persistidos. Los procesos que exceden el plazo y sus descendientes se terminan. Después de un reinicio, un trabajo que quedó RUNNING se informa como interrumpido. El límite aplica por instancia FastAPI; usar una instancia para este MVP local.
- La extracción síncrona anterior permanece por compatibilidad; la UI usa trabajos para indexar, importar archivos registrados, extraer, analizar y ejecutar ML. Ningún entrenamiento se inicia al arrancar.
- Estados operativos QUEUED/RUNNING/SUCCEEDED/FAILED separados de PASS/PARTIAL/BLOCKED científicos. Un trabajo puede terminar correctamente y reportar ciencia BLOCKED por falta de épocas.
- Análisis regional: ciencia original y VALID_MASK; suma mJy solo con BUNIT MJy/sr y área sólida WCS aproximada. No se suman píxeles descartados ni se aplica brillo/contraste. Las máscaras cambian entre bandas: no es un espectro de apertura uniforme ni una SED de fuente calibrada.
- Los diagnósticos temporales usan los archivos locales y el centro solicitado; no ejecutan los CLI de los experimentos sobre rutas globales ni muestran el reporte fijo como nuevo cálculo. Las estimaciones espectrales aproximadas previas se usan únicamente a menos de 1″ del objetivo offline que las originó; fuera de allí quedan sin determinar. Pares sin fechas distintas, banda aproximada o unidades compatibles no se presentan como comparaciones validadas. Se exige calibración CWAVE/CBAND, registro y PSF antes de variabilidad/sustracción.

## Contrato CNN y activación futura sin entrenamiento

El código de Marvin `eter_cnn_mvp.py` no se modificó. `infer` acepta NPZ con `science`, `reference`, `difference` de 63×63, o `stamp` de forma `(3,63,63)`, todos finitos. Orden: ciencia, referencia, diferencia. El script convierte a float32 y normaliza cada plano con mediana/MAD, limita extremos y normaliza la norma. Esa normalización afecta solo a la entrada ML, nunca a los valores del FITS descargado.

Pesos: checkpoint PyTorch con `state_dict` compatible con MiniBraai y `source`; se carga con `weights_only=True`. Se necesitan `ETER_ML_PYTHON`, `ETER_ML_WEIGHTS`; la demo añade `ETER_ML_SAMPLE`. Barnard necesita `barnard_triplete_real_exploratorio.npz` y `.png` bajo `ETER_BARNARD_ARTIFACTS_DIR`. Las imágenes de `public/candidates/barnard` no sustituyen esos artefactos.

Para inferencia real ya preparada, `MORLEY_ML_TRIPLETS` puede apuntar a un manifiesto JSON **administrado en el servidor**:

```json
[{
  "id": "triplete-verificado",
  "path": "/ruta/local/triplete.npz",
  "product_ids": ["identificador-real-del-producto-ROI"],
  "wcs_aligned": true,
  "psf_matched": true,
  "band_compatible": true,
  "quality_applied": true,
  "real_epochs": true
}]
```

Esos indicadores son una declaración de procedencia del responsable de preparar el triplete, no una validación automática de PSF/registro por Morley. Se comprueba formato, tamaño comprimido/expandido ≤8 MiB, finitud y asociación al producto. No hay carga pública de manifiestos ni relleno automático de píxeles inválidos. Solo se habilita inferencia cuando hay entrada compatible y archivos del modelo disponibles; un checkpoint o entorno incorrecto falla explícitamente. El score sigue siendo experimental, no probabilidad de realidad astrofísica. No se implementaron BraAI/ZOGY ni entrenamiento.

## Pruebas y artefactos

Ejecución final del 2026-11-15:

- Python (backend, pipeline y experimentos): **293 passed, 1 skipped**, 92 advertencias de bibliotecas conservadas. Registro: `/private/tmp/mvp-python-final.log`.
- Frontend Node: **22 passed**, ningún fallo. Registro: `/private/tmp/mvp-frontend-final.log`.
- TypeScript `tsc --noEmit` y ESLint de los componentes/servicios del flujo modificados: **PASS**.
- `npm run build`: **PASS**, incluidas `/preview`, `/sky-test`, `/catalog` y las rutas API. Registro: `/private/tmp/mvp-build-final.log`. Se detuvo únicamente Next de este worktree, se conservó su caché dev fuera del repositorio y se restauró después del build; desarrollo vuelve a usar Turbopack.
- Chrome automatizado: **PASS** para los cinco objetivos en ambos visores, coordenadas, inicio ROI, ausencia de asociaciones locales falsas, selección offline M101, carga, extracción, 102 filas de análisis y descarga JSON. Artefactos: `/private/tmp/mvp-browser/`.
- Regresión ROI: **PASS** para geometría esférica, RA wrap, Dec 85°, redimensionado, sincronización SIA, tres imágenes, descarga FITS/JSON y estadísticas invariantes al estiramiento visual. Artefactos: `/private/tmp/mvp-roi-regression/`.
- Regresión equipo: **PASS** para Astro, errores explícitos Barnard/demo, imágenes y canales 62/63 (frames HiPS 61/62). Sin errores JavaScript registrados. Artefactos: `/private/tmp/mvp-team-regression/`.
- Trabajo temporal real vía HTTP: **SUCCEEDED**, resultado científico **PARTIAL**, doce observaciones y 66 pares; 30 rechazados por unidades ausentes/incompatibles, 20 solo análisis espectral, 7 candidatos a calibración temporal, 6 revisión espectral y 3 revisión temporal. Ninguno certifica variabilidad ni ejecuta ZOGY. El endpoint de salud permaneció accesible durante el sondeo. Resultado: `/private/tmp/mvp-temporal-http.json`.

### Verificación independiente del FITS descargado

El archivo descargado por Chrome `M101-10arcmin-cube.fits` se abrió nuevamente con Astropy y se comparó con `mosaic_cube.fits`, sin reutilizar la función de extracción. Sus 102 planos SCIENCE son exactamente iguales, incluidos NaN, al segmento NumPy `[:,67:134,67:134]`; FLAGS y NHITS también son idénticos. La máscara calculada independientemente con finitud, NHITS positivo, rechazo de bits distintos de SOURCE y pertenencia al ROI coincide con VALID_MASK en las 102 bandas.

Resultado: `(102,67,67)`, canal 1 **3750/4489**, canal 52 **4224/4489**, **4488** finitos en canal 52; mediana coincidente con JSON. WCS en esquinas y centro coincide con el original (diferencia numérica máxima comprobada: **0°**); centro `(210.8022671°,54.34895°)`. SHA256 del FITS descargado: `9ee96d330c367c8357b8d1a58130d27db16bc8ac0b253edf06aa6e75e89888fe`. Evidencia: `/private/tmp/mvp-roi-regression/independent-verification.json`.

Las consultas reales SIA se conservan en `/private/tmp/mvp-live-search.json`. No se confunden con pruebas de descarga/procesamiento de esos productos remotos. Los artefactos `/private/tmp/` son locales y temporales; no se añadieron FITS al repositorio.

## Archivos de esta conexión del MVP

- Backend: `app/main.py`, nuevo router `app/routers/science_workflow.py` y servicios `science_targets.py`, `local_fits.py`, `science_jobs.py`, `science_worker.py`, `science_analysis.py`, `ml_inputs.py` bajo `apps/science-api/`; configuración `.env.example` y pruebas `tests/test_science_workflow.py`.
- Catálogo verificado: `resources/science/targets.json`; exclusión de resultados locales en `.gitignore`.
- Frontend bajo `apps/web/src/`: `components/viewer/{TargetContext,ViewerSwitch,SpherexMosaic,BarnardPanel}.tsx`, `components/preview/PreviewPanel.tsx`, `components/roi/{RoiWorkbench,ScienceResults}.tsx`, `hooks/useSimbadLayer.ts`, `services/{workflow-api,science-api}.ts`.
- Pipeline: `science/pipeline/fits_roi.py` evita copiar máscaras derivadas antiguas al recortar nuevamente un producto; vuelve a calcularlas.
- Pruebas frontend: `apps/web/tests/{workflow-api.test,mvp-browser,roi-browser}.mjs`. Esta documentación complementa `docs/full-team-e2e.md`, que describe las reparaciones anteriores conservadas. No se modificó la CNN de Marvin.
