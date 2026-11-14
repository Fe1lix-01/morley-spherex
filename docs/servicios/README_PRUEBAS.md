# Pruebas y auditorías K1/K2

## Backend

Desde `apps/science-api`:

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests -v
```

Último resultado reportado por Kevin: **248 pruebas aprobadas**. No se ejecutó de nuevo durante la preparación de estos README. Los resultados deben comprobarse de nuevo cuando cambien el código, las dependencias o el entorno.

Para revisar los clientes HTTP:

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/test_irsa.py tests/test_sia.py tests/test_irsa_cutouts.py -v
```

## Frontend y proxy

Desde `labs/frontend/aladin-test`, con dependencias instaladas:

```powershell
node --test tests/science-proxy.test.mjs
npx eslint src/app/api/science/m101/route.ts tests/science-proxy.test.mjs
npx next typegen
npx tsc --noEmit
```

La comprobación histórica del proxy incluyó ausencia de configuración, PNG correcto, error del backend, formato inesperado, cuerpo vacío, conexión rechazada y timeout. No se volvió a ejecutar al redactar esta entrega.

## K1 y K2

K1 revisó catálogo, TAP, SIA, registro remoto, previsualizaciones, capas y contratos. Corrigió incoherencias concretas y documentó propuestas sin implementar. K2 añadió pruebas HTTP de timeouts, errores, reintentos, contenidos y cierre; no requirió modificar clientes de producción.

K2 utiliza servidores locales y puertos controlados; no requiere fallos reales de NASA. Un resultado vacío válido se diferencia de un cuerpo vacío o formato inesperado.

Límites que deben acompañar la entrega:

- Se reprodujeron timeouts de lectura, no todos los tipos de timeout.
- No se estableció un plazo total para todos los intentos.
- Las pruebas de conexión rechazada no cuentan intentos de conexión y liberan previamente el puerto: existe una ventana para que otro proceso lo ocupe.
- En Windows el rechazo local medido superó dos segundos; esas pruebas usan 10 s de conexión.
- El cierre de conexiones se verificó en los escenarios documentados, no en todas las combinaciones de fallo.
- La captura amplia de errores de PNG, tipado genérico y algunas reglas entre modelos siguen registrados como propuestas o límites en K1.

Consultar las copias originales en `referencias/` para el detalle de hallazgos y evidencia. No presentar todas las propuestas como correcciones implementadas.

## Comprobación manual mínima

- Swagger muestra Objects, IRSA, SIA, Frames y Science.
- Catálogo agrupa los seis archivos de SIMP como un objeto y permite sus seis PNG.
- M101 aparece solo si hay observaciones registradas y el detalle separa local/remoto.
- Cada producto remoto usa su product_id completo y obtiene su recorte, con red disponible.
- La figura de M101 se genera desde el cubo configurado; la ausencia de configuración produce 503.
- Sin resultados de búsqueda, Objects devuelve HTTP 200 y lista vacía.
- El proxy distingue error, timeout, contenido vacío y formato inesperado sin entregar trazas internas.
- Los datos remotos no se confunden con insumos comprobados del cubo ni con movimiento demostrado.
