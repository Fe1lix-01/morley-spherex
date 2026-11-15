# Metodología del MVP ROI

## Geometría y extracción

La selección es un cuadrilátero convexo pequeño definido por cuatro esquinas ICRS. Sus lados se interpretan como segmentos de círculo máximo. Las distancias se calculan sobre la esfera, por lo que un cruce RA 359.99° → 0.01° no se interpreta como casi una vuelta completa. Una selección programática usa un cuadrado gnomónico centrado de aproximadamente 10′ × 10′, válido también cerca de los polos.

El rectángulo de pantalla se convierte con la proyección real de Aladin. Fuera de la proyección o por encima del máximo se rechaza. Entre esquinas se aproxima el borde de pantalla por geodésicas; para regiones pequeñas es una aproximación explícita, no una huella arbitraria exacta del viewport.

El motor transforma 65 muestras por borde al WCS del FITS y obtiene una caja de píxeles, limitada al archivo. Extrae los píxeles originales, **sin reproyección ni interpolación**. `Cutout2D` actualiza CRPIX y SIP. `ROI_MASK` marca los centros de píxel dentro del cuadrilátero; la caja puede contener otros píxeles que se conservan, pero no entran en estadísticas. No hay ponderación fraccionaria de píxeles de borde.

Admite imágenes 2D y cubos `(canal,y,x)` con ejes celestes primero en la WCS FITS. Rechaza geometrías no separables y tablas de distorsión espacial no soportadas. Conserva WCS celeste 2D y metadatos no espaciales; las tablas `SPECTRAL_CHANNELS` y `WCS-WAVE` se conservan como procedencia. El JSON identifica el plano seleccionado y la fila espectral o coordenada espectral cuando se puede interpretar.

Las extensiones de dimensiones compatibles se recortan con los mismos índices. Si tienen WCS, se comprueba alineación en tres puntos. Planos conocidos FLAGS, MASK, NHITS, VARIANCE y WAVELENGTH sin WCS propio se interpretan como asociados a la rejilla científica si comparten dimensiones; es una suposición registrada de este MVP. Las extensiones incompatibles se enumeran como omitidas, no se remuestrean. La comprobación en tres puntos no certifica igualdad de distorsiones de orden alto en toda la imagen.

## Máscaras y estadísticas

Un píxel válido debe estar dentro de ROI, tener ciencia finita y cumplir, cuando existan los planos compatibles:

- `FLAGS == 0` y `MASK == 0`.
- `NHITS > 0`, finito.
- `VARIANCE >= 0`, finita.

La política de flags es deliberadamente conservadora: no interpreta todavía los bits específicos de cada versión SPHEREx. `VALID_MASK` hace reproducible la selección, y se preservan los valores originales de calidad.

`finite_pixels` cuenta ciencia finita dentro de ROI antes de máscaras de calidad. `valid_pixels` cuenta después. `masked_percent = 100 × (1 - valid_pixels / roi_pixels)`. Mediana, desviación estándar poblacional (`ddof=0`) y MAD sin normalizar se calculan sobre los válidos, sin pesos. No se estima incertidumbre fotométrica ni significancia de detección. Las unidades se copian de `BUNIT`; no hay conversión de flujo.

La vista PNG es un recurso visual de percentiles, no un producto fotométrico calibrado. Los valores científicos están en el FITS. Una región sin datos válidos se entrega con máscara vacía, PNG negro y estadísticas nulas.

## Validación real realizada

Archivo local `mosaic_cube.fits` (47 MiB aproximadamente), centro ICRS 210.8022671°, 54.34895°, imagen 102 × 201 × 201. Selección 10′ × 10′, HDU IMAGE (índice 1), plano de índice 62 (canal ordinal 63): longitud de onda ≈3.293 µm, detector 4/subcanal 12 según la tabla del archivo.

4489 píxeles ROI, 4489 finitos, 742 válidos; 83.470706% enmascarados. Mediana 0.1190719567 MJy/sr, desviación 0.0935269936 MJy/sr, MAD 0.0393324718 MJy/sr. Se compararon todos los píxeles recortados de IMAGE, FLAGS y NHITS con el original: igualdad exacta. Comparación de WCS de todos los centros de píxel: diferencia máxima 0″ en esa ejecución. No se deduce validez astrofísica a partir de esta igualdad computacional.

Astropy advierte que este cubo tiene cuatro ejes WCS para tres dimensiones de imagen: el cuarto describe ancho espectral y comparte el eje de canal. Se usa la sub-WCS celestial separable, se conservan las tablas originales y se elimina ese eje del plano 2D de salida.

## Trabajo posterior

- Gaia: consulta y caché de catálogo, épocas y movimiento propio, transformación al mismo marco, asociación con incertidumbres y máscaras de estrellas.
- Comparación temporal: seleccionar exposiciones individuales por tiempo y banda comparable; validar calibración/unidades, alinear WCS, modelar PSF, propagar varianza y máscaras. Los 102 canales no son 102 fechas.
- BraAI: acordar contrato de entradas/salidas, normalización, procedencia, versiones del modelo y validación con positivos/negativos reales. No se modifica la CNN de Marvin.
- ZOGY queda fuera del MVP; faltan los requisitos de PSF, ruido y registro para una sustracción científicamente defendible.

Referencia: [Astropy Cutout2D y límites de distorsión](https://docs.astropy.org/en/stable/api/astropy.nddata.Cutout2D.html).
