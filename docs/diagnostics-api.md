# Morley — API de diagnósticos multiepoca (solo lectura)

Este módulo expone un **reporte JSON ya calculado** mediante FastAPI. No descarga
FITS, no ejecuta ZOGY, no entrena CNN y no infiere movimiento ni variabilidad.

## Instalación

1. Copiar `apps/science-api/app/routers/diagnostics.py` y
   `apps/science-api/tests/test_diagnostics.py` a las rutas indicadas.
2. En `apps/science-api/app/main.py`, **sin reemplazar las rutas actuales**, agregar:

   ```python
   from app.routers import diagnostics
   ```

   Después de crear `app = FastAPI(...)`, junto a los otros `include_router`:

   ```python
   app.include_router(diagnostics.router)
   ```

3. Desde la raíz del repositorio (con el venv existente):

   ```bash
   PYTHONPATH=apps/science-api python -m pytest apps/science-api/tests/test_diagnostics.py -v
   ```

4. El reporte usado por defecto es
   `science/experiments/morley_unified/outputs/validations/morley_science_routes_recheck.json`.
   Si se encuentra en otra ruta del mismo servidor:

   ```bash
   export MORLEY_SCIENCE_REPORT_PATH="/ruta/absoluta/al/reporte.json"
   ```

   El reporte no se incluye en Git y debe existir en cada máquina o despliegue.

5. Levantar FastAPI como habitualmente y comprobar:

   ```bash
   curl -sS http://127.0.0.1:8000/api/v1/science/diagnostics/summary
   curl -sS 'http://127.0.0.1:8000/api/v1/science/diagnostics/pairs?route=TEMPORAL_CALIBRATION_CANDIDATE'
   curl -sS http://127.0.0.1:8000/api/v1/science/diagnostics/observations
   ```

## Contrato

Los tres endpoints devuelven `schema_version`, `generated_at_utc`,
`target`, `scientific_integrity`, `source_kind`. `summary` devuelve además
`summary`; `observations` y `pairs` devuelven `total`, `offset`, `limit`, `items`.
Los listados admiten paginación; `pairs` filtro `route`, y `observations` filtro
`status`. Límites: 100 elementos por respuesta y 10 MiB por reporte.

La lectura está acotada a la ruta configurada en el **servidor**, no se admite
una ruta de archivo recibida del cliente. Se omiten direcciones locales,
URLs internas y hashes del contenido publicado.

**Advertencia:** estos resultados proceden del objetivo predeterminado
RA=295.4097841°, Dec=-15.2231692° (ICRS), no de una ROI nueva de Aladin.
El frontend debe validar el `target` o mostrar explícitamente el contexto.
`TEMPORAL_CALIBRATION_CANDIDATE` **no significa** movimiento detectado.

## Prueba con los FITS reales

Para que el reporte exista, ejecutar fuera de la API:

```bash
cd science/experiments/morley_unified
python 06_science_routes.py \
  --input outputs/catalogs/candidate_pairs_multiepoch_05.json \
  --output outputs/validations/morley_science_routes_recheck.json \
  --min-days 14
```

No integrar la rama de Marvin hasta resolver sus merges y pasar la batería
completa de pruebas de ambas ramas.
