# K2 — Robustez de conexiones HTTP

## Alcance

Clientes HTTP del backend asignado:
- app/clients/irsa.py
- app/clients/sia.py
- app/clients/irsa_cutouts.py

### K2-01 — Timeouts explícitos

- Revisión: los tres clientes configuran tiempos de conexión,
  lectura, escritura y espera del pool.
- Valores predeterminados: conexión 10 s, lectura 60 s,
  escritura 10 s y pool 10 s.
- Verificación: tres pruebas con servidores HTTP locales provocan
  un timeout de lectura.
- Resultado: TAP y recortes generan IrsaTimeoutError;
  el endpoint SIA responde HTTP 504.
- Limitaciones: las pruebas ejecutadas no reproducen los timeouts
  de conexión, escritura o pool. Tampoco comprueban un plazo total
  para la operación completa con sus reintentos.
- Corrección de código: ninguna.

### K2-02 — Reintentos de SIA

- Archivo: app/clients/sia.py.
- Verificación: solicitudes reales contra un servidor HTTP local.
- Resultados:
  - HTTP 400, 401, 403, 404 y 422: una sola solicitud.
  - HTTP 429, 502, 503 y 504 persistentes: tres intentos.
  - HTTP 503 seguido de 200: termina después del segundo intento.
- Resultado de las pruebas: 10 casos aprobados.
- Corrección del cliente: ninguna; se amplió la cobertura.
- Alcance: estos resultados corresponden a SIA, no al cliente de recortes.

### K2-03 — Reintentos de TAP

- Archivo: app/clients/irsa.py.
- Verificación: servidor HTTP local controlado.
- Resultados:
  - HTTP 400 y 404: una sola solicitud.
  - HTTP 429, 502, 503 y 504 persistentes: tres intentos.
  - HTTP 503 seguido de 200: termina al segundo intento.
- Resultado: siete casos aprobados.
- Corrección del cliente: ninguna.

### K2-04 — Respuestas HTTP fallidas en recortes

- Archivo: app/clients/irsa_cutouts.py.
- Verificación: servidor HTTP local con contador de solicitudes.
- Resultado: HTTP 400, 401, 403, 404, 429, 500, 502, 503 y 504
  producen IrsaResponseError después de una sola solicitud.
- Pruebas: nueve casos aprobados.
- Alcance: no comprueba el número de intentos de conexión.
- Corrección del cliente: ninguna.

### K2-05 — Conexión rechazada al descargar recortes

- Archivo: app/clients/irsa_cutouts.py.
- Verificación: conexión real a un puerto local sin servidor.
- Resultado: el cliente convierte el rechazo en IrsaUnavailableError.
- Prueba: test_recorte_controla_conexion_rechazada aprobó.
- Configuración de prueba: timeout de conexión de 10 segundos,
  igual al valor predeterminado del cliente.
- Observación: en Windows, un límite de dos segundos vencía antes
  de recibir el rechazo de conexión.
- Limitaciones: esta prueba no cuenta los intentos de conexión.
  Existe una pequeña posibilidad de que otro proceso ocupe el
  puerto después de liberarlo.
- Verificación conjunta: las 24 pruebas de tests/test_irsa_cutouts.py aprobaron.
- Corrección del cliente: ninguna.

### K2-06 — Cierre de conexiones del cliente de recortes

- Verificación: servidor HTTP/1.1 que permite conexiones persistentes.
- Resultado: el servidor detectó el fin de la conexión después de
  éxito, error HTTP, respuesta vacía y exceso de tamaño.
- Pruebas: cuatro casos aprobados.
- Alcance: cliente de recortes; no demuestra todavía el cierre en TAP o SIA.
- Corrección del cliente: ninguna.

### K2-07 — Cierre de conexiones TAP

- Verificación: servidor HTTP/1.1 con conexiones persistentes.
- Resultado: se detectó el cierre después de HTTP 200 y HTTP 400.
- Pruebas: dos casos aprobados.
- Corrección del cliente: ninguna.

### K2-08 — Cierre de conexiones SIA

- Verificación: servidor HTTP/1.1 con conexiones persistentes.
- Resultado: se detectó el cierre después de una respuesta correcta
  y después de un error HTTP 400 externo.
- Respuestas del backend: HTTP 200 y HTTP 502, respectivamente.
- Pruebas: dos casos aprobados.
- Corrección del cliente: ninguna.
- Alcance: no comprueba por sí sola el cierre durante todos los
  escenarios de timeout, reintentos o errores de procesamiento.
  - Verificación conjunta: 104 casos aprobados entre test_irsa.py,
  test_sia.py y test_irsa_cutouts.py.

  ### K2-09 — Contenido externo de TAP

- Verificación: endpoint completo contra un servidor HTTP local.
- Resultados:
  - CSV con cabecera válida y sin filas: HTTP 200, count 0 y lista vacía.
  - Cuerpo vacío: HTTP 502.
  - HTML inesperado: HTTP 502.
- Cada escenario realizó una sola solicitud externa.
- Los errores devuelven un mensaje genérico, sin el contenido
  externo de prueba ni una traza.
- Pruebas: tres casos aprobados.
- Corrección del cliente o servicio: ninguna.

### K2-10 — Contenido externo de SIA

- Verificación: endpoint completo contra un servidor HTTP local.
- Resultados:
  - VOTable válido sin filas: HTTP 200, count 0 y lista vacía.
  - Cuerpo vacío: HTTP 502.
  - JSON inesperado: HTTP 502.
- Cada escenario realizó una sola solicitud externa.
- Los errores devuelven el mensaje genérico esperado, sin el
  contenido externo de prueba ni una traza.
- Pruebas: tres casos aprobados.
- Corrección del cliente o servicio: ninguna.

### K2-11 — Error de conexión desde el endpoint TAP

- Verificación: conexión real a un puerto local sin servidor.
- Resultado: HTTP 503 con el mensaje público esperado.
- La respuesta no incluye la URL interna utilizada en la prueba
  ni una traza.
- Prueba: test_tap_endpoint_controla_conexion_rechazada aprobó.
- Limitación: el puerto se libera antes de conectar; otro proceso
  podría ocuparlo durante ese intervalo.
- Corrección del cliente o router: ninguna.

### K2-12 — Error de conexión desde el endpoint SIA

- Verificación: conexión real a un puerto local sin servidor.
- Resultado: HTTP 503 con el mensaje público esperado.
- La respuesta no incluye la URL interna utilizada en la prueba
  ni una traza.
- Prueba: test_sia_endpoint_controla_conexion_rechazada aprobó.
- Limitación: el puerto se libera antes de conectar; otro proceso
  podría ocuparlo durante ese intervalo.
- Corrección del cliente o router: ninguna.

## Verificación conjunta

- Suite completa del backend: 248 pruebas aprobadas.
- Las nuevas pruebas HTTP utilizan servidores y puertos locales.
- No fue necesario modificar los clientes durante K2.

## Límites de la verificación

- Los timeouts de red no establecen un plazo total para todos
  los intentos y esperas.
- Se reprodujeron timeouts de lectura, no todos los tipos de timeout.
- Las pruebas de conexión rechazada no cuentan los intentos.
- El cierre de conexiones se comprobó en los escenarios documentados;
  no en todas las combinaciones posibles de fallos.
- No se verificaron en esta ejecución fallos reales del servicio NASA.