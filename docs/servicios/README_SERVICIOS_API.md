# Arquitectura y contratos de API

## Responsabilidades

- `app/routers`: parámetros HTTP, modelos de respuesta y traducción de excepciones.
- `app/services`: agrupación, transformación, validación y generación de resultados.
- `app/clients`: solicitudes a IRSA, timeouts, clasificación de errores y descarga.
- `app/schemas`: contratos Pydantic y coherencia de datos.
- `app/core/paths.py`: resolución de rutas respecto de la estructura del proyecto.

Los cinco servicios auditados en K1 no importan directamente FastAPI/Starlette ni construyen respuestas HTTP. Mantener esa separación.

## Rutas principales

| Método y ruta | Entrada principal | Respuesta |
|---|---|---|
| `GET /api/v1/objects` | `q` opcional | JSON con total y resúmenes |
| `GET /api/v1/objects/{object_id}` | ID del catálogo | Detalle con observaciones locales/remotas |
| `GET /api/v1/irsa/observations` | `ra`, `dec`, `band`, `limit` | Metadatos TAP normalizados |
| `GET /api/v1/sia/observations` | `ra`, `dec`, `collection`, `radius_arcsec`, `band`, `limit` | Metadatos SIA normalizados |
| `GET /api/v1/objects/{object_id}/remote-preview` | `product_id` obligatorio | `image/png` de un recorte remoto |
| `GET /api/v1/science/m101/channel-63/preview` | FITS configurado en servidor | `image/png` con tres paneles |
| `GET /api/v1/frames` | Consultar Swagger | Metadatos de frames locales |
| `GET /api/v1/frames/{frame_id}/image` | Frame local registrado | PNG local |

Health y Observations son módulos existentes que deben conservarse. Registrar los routers nuevos una sola vez en `app/main.py`; `frames` y `science_preview` son funcionalidades diferentes y se conservan ambas.

## Catálogo de objetos

`services/objects.py` reutiliza `list_observations()` sin volver a leer FITS. Reconoce la convención de archivos `nombre_D1_...fits`, hasta D6, mediante una expresión regular que conserva espacios del nombre.

Agrupa usando `casefold()`, selecciona un nombre de forma determinista y genera UUID5. Los IDs de variantes locales presentes permiten consultar el mismo grupo. No existe un registro histórico para garantizar IDs de variantes eliminadas.

La búsqueda `q` es parcial e insensible a mayúsculas. Sin coincidencias devuelve HTTP 200 con total cero. Un ID inexistente devuelve 404.

`observation_count` suma registros locales y remotos; los subtotales y listas se validan. No se deduplican científicamente dos registros de fuentes diferentes sin conocer su procedencia.

M101 solo se incorpora si existen observaciones locales reconocidas o registros remotos presentes y válidos. No insertar un objeto ficticio para hacer aparecer una figura. `science_preview` indica una operación soportada; no garantiza que el cubo esté disponible.

## TAP y SIA

RA en grados ICRS: `0 <= ra < 360`. Dec: `-90 <= dec <= 90`. Bandas SPHEREx-D1 a D6. Límite de respuesta de 1 a 100.

SIA admite `spherex_qr2` y `spherex_qr3`, con QR3 predeterminado. Radio en segundos de arco, mayor que cero y hasta 300 por la validación actual del proyecto. Ese máximo no se presenta como límite oficial del proveedor. El cliente convierte el radio a grados para `POS=CIRCLE`.

El límite SIA se aplica después de consultar, filtrar y ordenar los resultados. `count` es lo devuelto, no el total disponible en NASA. Conservar `product_id` completo: el identificador de exposición por sí solo puede no distinguir detectores.

Ejemplo para Swagger o navegador, con consulta externa real:

```text
/api/v1/sia/observations?collection=spherex_qr2&ra=210.8022671&dec=54.34895&radius_arcsec=30&band=SPHEREx-D4&limit=2
```

Los clientes se ejecutan al invocar sus métodos, no al importar sus módulos. Los scripts de prácticas no sustituyen el servicio.

## Recortes remotos

La previsualización busca el producto dentro del objeto registrado. El consumidor proporciona un `product_id`, no una URL arbitraria de descarga.

El cliente restringe origen, ruta SPHEREx, extensión FITS y ausencia de query/fragmento en la URL original. No sigue redirecciones. Descarga un recorte de 0,025 grados en streaming, con límite de 8 MiB. El servicio exige IMAGE 2D, WCS celestial y la posición consultada dentro del recorte; reutiliza el contraste PNG existente.

El navegador no muestra FITS directamente mediante `<img>`. Ampliar el PNG en pantalla no añade resolución científica.

## Errores y límites HTTP

- Parámetros inválidos: normalmente HTTP 422 por FastAPI/Pydantic.
- Objeto/producto inexistente: 404.
- Respuesta externa inválida: 502.
- Catálogo, configuración científica o servicio no disponible: 503.
- Timeout externo: 504.

Una URL malformada dentro del JSON invalida el registro y produce 503 antes de descargar. Una URL sintácticamente válida pero no permitida por el cliente produce 502.

TAP/SIA permiten tres intentos para la política definida, con esperas limitadas; 400/401/403/404/422 de SIA se comprobaron sin reintento. El cliente de recortes no repite respuestas HTTP fallidas; configura dos reintentos de conexión en su transporte. No equiparar estas políticas.

Timeouts predeterminados: conexión 10 s, lectura 60 s, escritura 10 s y pool 10 s. No son un plazo total de la operación. El proxy Next.js de M101 usa un plazo de 10 s que incluye lectura del cuerpo; ese límite puede vencer antes de que termine un procesamiento lento del backend.

Las respuestas públicas usan mensajes genéricos. Puede haber trazas en los logs internos para diagnóstico; no entregarlas al consumidor como cuerpo HTTP.
