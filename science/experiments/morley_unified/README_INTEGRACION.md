# MORLEY — integración conservadora del pipeline de investigación

Esta carpeta contiene **los scripts originales** extraídos de `MORLEY_PIPELINE_UNIFICADO.zip`,
ubicados aquí para convivir con el repositorio `morley-spherex` sin sobrescribir
`science/pipeline/`, `apps/science-api/` ni los componentes web. Los scripts conservan
su comportamiento y sus rutas relativas a `outputs/`.

## Contenido

- 00B–00D: descubrimiento SIA, catálogos, selección y prechequeo de pares temporales.
- 06: diagnósticos de fotometría individual y rutas.
- 07–07P: auditorías de calidad, WCS/SIP, dispersión espectral, ePSF, astrometría,
  fotometría y residuos en datos observacionales (diagnósticos, no detección confirmada).
- 08–09: pruebas de ZOGY e hipótesis H0–H3 **sobre datos sintéticos solamente**.

El objetivo por defecto de los scripts es RA=295.4097841°, Dec=-15.2231692°,
detector D6. **No corresponde a M101 ni a la estrella de Barnard.**

## Instalación en Mac

Desde la raíz del repositorio `morley-roi`, con su `.venv` activado:

```bash
python -m pip install -r science/experiments/morley_unified/requirements.txt
python -m unittest discover -s science/experiments/morley_unified/tests -v
```

Si dispones del ZIP original con los recortes FITS, importa solo `outputs/`:

```bash
python science/experiments/morley_unified/import_outputs.py "$HOME/Downloads/MORLEY_PIPELINE_UNIFICADO.zip"
```

Este comando **no** importa el entorno Windows `.venv` y **no sobreescribe** resultados previos.
En Git se ignora todo `outputs/` porque contiene datos, cachés y productos que pueden ser grandes.

## Validación offline inicial

```bash
cd science/experiments/morley_unified
python -m unittest discover -s tests -v
python 06_science_routes.py --input outputs/catalogs/candidate_pairs_multiepoch_05.json --min-days 14
```

El segundo comando genera/actualiza `outputs/validations/morley_science_routes.json`:
respáldalo primero si necesitas conservar la salida exacta anterior.

**No ejecutes `EJECUTAR_TODO_MAC.sh` al principio**: inicia consultas SIA reales y
puede generar un nuevo inventario/catálogo, cambiando pares e invalidando la
comparabilidad con los productos previos. Tampoco ejecutes 00D antes de
verificar y respaldar sus entradas/salidas.

## Compatibilidad científica

- Los scripts experimentales no son endpoints FastAPI. Se requiere un adaptador explícito
  para exponer resúmenes por API sin ejecutar análisis pesados por cada petición.
- Las políticas de FLAGS son **dependientes del producto y de cada diagnóstico**;
  no reemplazar automáticamente la máscara preliminar del ROI.
- Revisar por separado WCS, valores y procedencia DR1/QR3 y calibraciones
  antes de inferir variabilidad física.
- Los diagnósticos del archivo original marcan `real_zogy_authorized: false`
  y/o `real_zogy_executed: false`; el clasificador H0–H3 es sintético.
- El README original (`README_PRIMERO.md`) describe una entrega más reducida
  y afirma que el ZIP no trae FITS; en el ZIP suministrado **sí** hay FITS, catálogos
  y diagnósticos. Este paquete de integración, en cambio, contiene **solo código**.
