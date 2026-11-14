# Datos científicos y reproducibilidad

## Tres recursos diferentes

1. FITS locales SIMP D1–D6, utilizados por el catálogo y las previsualizaciones locales.
2. Cubo demostrativo `M101_irsa.fits`, utilizado para generar la figura del canal 63.
3. Registro JSON de productos remotos SIA asociados espacialmente a M101.

No tratar estos tres recursos como si fueran el mismo producto o una prueba de movimiento.

## FITS locales SIMP

Ubicación esperada: `resources/objects/images/fits/`.

El directorio local debe existir para construir el catálogo, incluso si hay datos remotos. Puede estar vacío. Para mostrar SIMP se necesitan sus seis archivos reales en esa ubicación; no crear FITS vacíos para simular imágenes reales.

El `.gitignore` excluye nuevos FITS, pero archivos ya versionados pueden seguir incluidos en Git. Comprobar la situación de los archivos antes de duplicarlos o intentar quitarlos del historial.

## Descargar el cubo de M101

Desde la raíz del proyecto:

```powershell
New-Item -ItemType Directory -Path .\data\m101 -Force
Invoke-WebRequest -Uri "https://irsa.ipac.caltech.edu/data/demos/notebooks/spherex/M101_irsa.fits" -OutFile .\data\m101\M101_irsa.fits
$env:M101_FITS_PATH = (Resolve-Path -LiteralPath ".\data\m101\M101_irsa.fits").Path
Test-Path -LiteralPath $env:M101_FITS_PATH
```

La descarga escribe el archivo de destino: si ya existe una copia válida, no hace falta repetirla. No subir el cubo ni un `.env` personal a Git.

Después de iniciar el backend, abrir [la figura de M101](http://127.0.0.1:8000/api/v1/science/m101/channel-63/preview). Genera tres paneles: imagen, cobertura NHITS y máscara de calidad. No se limita a servir un PNG preexistente de outputs.

El servicio comprueba extensiones IMAGE, NHITS, FLAGS y SPECTRAL_CHANNELS, dimensiones compatibles, estructura de canales y longitud de onda disponible. Consultar el código y las pruebas para las validaciones completas. Un recurso ausente o un procesamiento rechazado produce el 503 controlado de este endpoint.

## Política FLAGS específica del mosaico

La documentación científica existente registra la comparación con el encabezado del cubo y [la ayuda oficial del Mosaic Tool de IRSA](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/mosaic.html).

Para esta visualización se excluyen los bits de posición 1 y 19, registrados como MP_OVERFLOW y MP_OUTLIER. Se conserva MP_SOURCE (21), se exigen valores IMAGE finitos y NHITS positivo. La decisión es una política exploratoria del proyecto, no una recomendación universal de fotometría.

No aplicar automáticamente todos los `bad_flag_bits` del pipeline ni trasladar esta máscara a otros productos. Las previsualizaciones individuales de los recortes remotos no aplican la máscara del mosaico. Un cambio científico requiere contraste con el producto y revisión del equipo.

## Generar el registro remoto

Con las dependencias del backend instaladas, desde la raíz:

```powershell
.\.venv\Scripts\python.exe .science\targets\consultar_metadatos_m101.py
```

Esta operación sí consulta IRSA. Reutiliza SIA del backend y guarda `data/m101/observations.json` con escritura temporal y reemplazo final. Puede reemplazar una instantánea previa; conservar la versión utilizada si se necesita reproducir exactamente la consulta histórica.

La consulta implementada solicita QR2, SPHEREx-D4, radio 30 segundos de arco y límite 2, en RA 210.8022671 / Dec 54.34895. Registra fecha de consulta, procedencia de la posición, colección, productos, fechas y URLs.

La relación documentada es **intersección espacial**: la cobertura intersecta el círculo consultado. No prueba por sí sola una detección del objeto ni que esas exposiciones construyeran el cubo demostrativo.

Si el registro no existe, no se añaden observaciones remotas. Si existe pero es inválido, el catálogo devuelve un error controlado. No insertar M101 manualmente para ocultar la ausencia del registro.

## Datos y pruebas

Los FITS sintéticos de las pruebas sirven para validar estructura, máscaras y PNG de manera repetible; no representan observaciones reales. Algunas pruebas de integración local pueden depender de los FITS de SIMP. La generación sintética de M101 se prueba sin descargar el cubo real ni requerir M101_FITS_PATH.

Los recursos ignorados no se incluyen automáticamente al clonar el repositorio. Prepararlos según las ubicaciones y las instrucciones anteriores.
