# Contrato del MVP ROI

Base: `http://127.0.0.1:8000/api/v1`. Se conservan los endpoints previos.

## Región

```json
{
  "center": {"ra": 210.8022671, "dec": 54.34895},
  "corners": ["cuatro objetos {ra, dec}, en orden perimetral"],
  "width_arcmin": 10,
  "height_arcmin": 10
}
```

El ejemplo ilustra la estructura: generar las cuatro coordenadas reales con el visor o `centered_region`; no usar la cadena de ejemplo como petición. ICRS, grados; RA en [0,360), Dec en [-90,90]. Valores finitos. Se valida convexidad, centro interior y concordancia entre dimensiones declaradas y las separaciones de las esquinas. Máximo configurable de 20′ por lado. La anchura/altura son el máximo de sus dos lados opuestos.

## Operaciones reutilizadas

- `GET /sia/observations?ra=…&dec=…&band=SPHEREx-D2&roi=<JSON codificado>&limit=20`: metadatos reales de observaciones individuales. `roi` reemplaza la geometría circular, no las restricciones del detector/colección. `ra` y `dec` siguen siendo obligatorios por compatibilidad; deben coincidir con el centro de la ROI (tolerancia 1e-8 grados), o se devuelve 422 antes de consultar IRSA. No garantiza cobertura completa del rectángulo. Se conserva la respuesta `SiaResponse`, con `access_url`, formato, ID, colección, detector y tiempos.
- `GET /observations`: nombres de FITS del catálogo local existente. Usar `filename` para importar uno.
- Se reutilizan internamente el transporte limitado de `clients/irsa_cutouts.py` y el renderizador PNG de `services/frame_images.py`.

## Operaciones nuevas (prefijo `/science/roi`)

| Método / ruta | Entrada | Resultado |
| --- | --- | --- |
| `GET /config` | — | `max_arcmin`, `default_arcmin`, `max_fits_bytes` |
| `POST /files` | Cuerpo binario FITS, Content-Type `application/fits` | `asset_id`, bytes, tipo, extensiones con dimensiones, unidades, WCS compatible, centro, canales y metadatos |
| `POST /files/import` | `{filename}` del catálogo local **o** `{url, confirm_download: true}` | Mismo resultado de inspección; caché de contenido y URL |
| `POST /products` | `{asset_id, region, hdu_index: 0, channel: 0}` | Producto, estadísticas, máscaras, procedencia, metadatos espectrales, extensiones preservadas/omitidas y aviso de cobertura parcial |
| `GET /products/{id}/fits` | — | FITS reutilizable con WCS, planos científicos/calidad y máscaras |
| `GET /products/{id}/json` | — | Metadatos persistentes del procesamiento |
| `GET /products/{id}/png` | — | Vista por percentiles 1–99, filas invertidas para origen inferior, inválidos negros |

HDU y canal usan índices **desde cero**. Los canales son planos espectrales; nunca se convierten automáticamente en épocas. `product_kind` distingue `spectral_cube` e `image_2d`; el tipo 2D por sí solo no prueba que sea una exposición individual.

Errores: 409 falta confirmación remota; 413 carga local excesiva; 422 coordenadas/geometría/FITS/URL/canal incompatibles o caché sin espacio; 404 recurso ausente; 502 respuesta IRSA inválida o descarga demasiado grande; 503 servicio remoto no disponible; 504 timeout. Los errores de validación FastAPI pueden devolver `detail` como lista.

Los productos devuelven `roi_pixels`, `finite_pixels`, `valid_pixels`, `masked_percent`, `median`, `std` y `mad`; sin píxeles válidos las estadísticas de valores son `null`, nunca NaN en JSON.
