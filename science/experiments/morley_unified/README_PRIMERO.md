# MORLEY — Pipeline científico consolidado (00B → 00C → 00D → 06)

**Versión:** 2026-11-15 — consolidación independiente, sin backend/frontend/CNN.

## IMPORTANTE: NO BORRAR LOS DATOS PREVIOS TODAVÍA

Los archivos **FITS** y los catálogos **CSV/JSON** ya obtenidos se encuentran en tus carpetas locales. **No están en este ZIP.** Antes de borrar la carpeta antigua, verifica que hayas copiado `outputs/data/` y respaldado `outputs/catalogs/` (y que tengan el mismo número de archivos y tamaños). Puedes reutilizarlos con `MIGRAR_DATOS_ANTERIORES.ps1`. Al generar inventarios nuevos puede variar la selección.

## Qué incluye

| Archivo | Función | Origen en esta entrega |
|---|---|---|
| `00b_discover_sia_candidates.py` | Consulta **SIA2** oficial por posición para DR1 y QR3, guarda VOTables en caché | **Reconstruido**: código original no disponible en los archivos adjuntos |
| `00c_catalogo_sia.py` | Convierte la caché SIA a `spherex_sia_inventory.csv` con los campos que espera 00D | **Reconstruido**: código original no disponible |
| `morley_sia.py` | Parser y validador de URLs Level-2 para 00B/00C | **Nuevo**, apoyo a reconstrucción |
| `00_select_fits_candidates.py` | `inspect_fits()` requerido por 00D | **Adaptación** de la función original; no incluye el antiguo selector TAP/samples |
| `00d_validate_multiepoch.py` | Recupera y verifica cutouts, genera **pares únicos entre todos los releases**, no solo DR1-vs-QR3 | **Basado en el corregido que ya compartimos** |
| `06_science_routes.py` | Fotometría de apertura diagnóstica y rutas espectral/temporal | **Original proporcionado por el usuario** |
| `INSTALAR_WINDOWS.ps1`, `EJECUTAR_TODO.ps1`, `MIGRAR_DATOS_ANTERIORES.ps1` | Preparación, ejecución automática, recuperación de datos | Nuevos |
| `INSTALAR_MAC.sh`, `EJECUTAR_TODO_MAC.sh` | Instalación y ejecución en Mac | Nuevos |
| `tests/test_pairs.py` | Pruebas sintéticas de comparación de parejas | Nuevas |

Se conservan los formatos principales esperados por 00D y 06, pero 00B/00C **no son copias exactas** de las versiones anteriores. No se garantiza recuperar exactamente las 37 observaciones originales en una consulta nueva. La disponibilidad de IRSA puede cambiar.

## Instalación — Windows / PowerShell

1. Extrae el ZIP una sola vez, sin carpetas duplicadas (directorio `MORLEY_PIPELINE_UNIFICADO`).
2. Abre PowerShell en esa carpeta.
3. Ejecuta:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

También puedes ejecutar `powershell -ExecutionPolicy Bypass -File .\INSTALAR_WINDOWS.ps1` si tu equipo bloquea scripts PowerShell.

## Ejecución limpia, paso por paso

```powershell
.\.venv\Scripts\python.exe .\00b_discover_sia_candidates.py
.\.venv\Scripts\python.exe .\00c_catalogo_sia.py
.\.venv\Scripts\python.exe .\00d_validate_multiepoch.py --detector D6 --per-epoch 3 --min-days 14 --threshold 0.25
.\.venv\Scripts\python.exe .\06_science_routes.py --input .\outputs\catalogs\candidate_pairs_multiepoch_05.json --min-days 14
```

O bien, con el entorno instalado:

```powershell
powershell -ExecutionPolicy Bypass -File .\EJECUTAR_TODO.ps1
```

Esto hace consultas de red reales (00B) y puede descargar FITS reales (00D). No inventa observaciones ni resultados. Si la red falla, no se reemplaza la caché buena con una respuesta inválida.

### Reutilizar datos antiguos (recomendado antes de borrar nada)

Ejecuta desde la **carpeta nueva**:

```powershell
powershell -ExecutionPolicy Bypass -File .\MIGRAR_DATOS_ANTERIORES.ps1 -Origen "C:\Users\Foucault_cmandelbrot\Downloads\MORLEY_LISTO_PARA_EJECUTAR\MORLEY_LISTO_PARA_EJECUTAR"
```

El script copia exclusivamente los archivos dentro de `outputs/`. No mueve ni borra la carpeta anterior. Después puedes probar sin volver a descargar (también puedes usar `powershell -ExecutionPolicy Bypass -File .\EJECUTAR_TODO.ps1 -Offline`):

```powershell
.\.venv\Scripts\python.exe .\00d_validate_multiepoch.py --detector D6 --per-epoch 3 --min-days 14 --threshold 0.25 --offline
.\.venv\Scripts\python.exe .\06_science_routes.py --min-days 14
```

**Atención:** en modo `--offline`, 00D toma las observaciones del inventario CSV previamente copiado. Por eso el inventario y los FITS deben venir del mismo conjunto de datos.

## Instalación y ejecución — macOS

```bash
cd MORLEY_PIPELINE_UNIFICADO
bash INSTALAR_MAC.sh
bash EJECUTAR_TODO_MAC.sh
```

Para copiar datos existentes de Windows a Mac, mueve los archivos bajo `outputs/` manteniendo las rutas relativas del proyecto. No copies `.venv` entre sistemas operativos.

## Productos esperados

```text
outputs/
├── catalogs/
│   ├── sia_cache/
│   │   ├── spherex_dr1.xml               # 00B: respuesta cruda de IRSA
│   │   └── spherex_qr3.xml               # 00B
│   ├── sia_discovery_00b.json            # 00B: proveniencia/errores
│   ├── spherex_sia_inventory.csv         # 00C: entrada de 00D
│   ├── candidatos_d6_sia.csv            # 00C: resumen D6
│   ├── spherex_sia_report.json           # 00C
│   └── candidate_pairs_multiepoch_05.json  # 00D: entrada de 06
├── data/
│   └── candidates_05/*.fits              # 00D: recortes verificados
└── validations/
    └── morley_science_routes.json        # 06
```

## Controles y limitaciones científicas

- El objetivo usado por defecto es RA **295.4097841°**, Dec **−15.2231692°**, detector **D6**.
- 00D selecciona un subconjunto de las observaciones de DR1/QR3 y compara todos los **pares únicos verificados del mismo detector**, incluso DR1–DR1 y QR3–QR3.
- Ejecutamos `--min-days 14` para la prueba con las observaciones de abril/mayo, **no** como umbral físico universal de movimiento.
- El `relative_mismatch` usa `abs(lambda_a-lambda_b) / mean(bandwidth_a, bandwidth_b)`. Es **aproximado** y **no** valida por sí solo compatibilidad fotométrica.
- **WARN SIP/WCS:** los encabezados FITS pueden generar un aviso de distorsión inconsistente. No lo suprimas ni modifiques sin revisar la astrometría.
- `00D` verifica un parche 7×7 de imagen/varianza pero no impone `FLAGS==0` allí; el diagnóstico de apertura de `06` sí exige `FLAGS==0`. Por ello una observación puede pasar 00D y quedar bloqueada en 06.
- `06` no calcula ePSF ajustada, CWAVE/CBAND científico, ZOGY real, movimiento, variabilidad, clasificación ni detección física.
- `TEMPORAL_CALIBRATION_CANDIDATE` significa **candidato a calibración**, no *listo para ZOGY*.

## Próximo paso de desarrollo

MORLEY 07: verificar espectro con **CWAVE/CBAND**, resolver WCS/SIP, registro astrométrico y ePSF, manejar covarianzas y control de calidad. MORLEY 08: diferencias ZOGY y contrastes H0–H3. Ninguno se incluye como implementación real en este paquete.

Documentación de archivo: https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/
