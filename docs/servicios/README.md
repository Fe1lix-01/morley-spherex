# Entrega del trabajo de Kevin — Sphere-X / ÉTER

Documentación del trabajo realizado en los servicios, la visualización científica y las pruebas de Sphere-X / ÉTER. No sustituye el README general, la licencia ni las atribuciones del proyecto.

## Cómo usar estos documentos

1. [Ejecución local]
(README_EJECUCION.md).
2. [Arquitectura, servicios y API](README_SERVICIOS_API.md).
3. [Datos científicos y reproducibilidad](README_DATOS_CIENTIFICOS.md).
4. [Pruebas y auditorías K1/K2](README_PRUEBAS.md).

Estos documentos se consultan juntos. Los comandos parten de la estructura actual del proyecto y especifican el directorio desde el que deben ejecutarse.

## Trabajo incluido

- Catálogo de objetos: agrupación de observaciones, identificación estable para los datos presentes, búsqueda parcial y detalle.
- Cliente IRSA/TAP con HTTPX y respuestas normalizadas mediante Pydantic.
- Cliente SIA para SPHEREx QR2 y QR3, transformación de VOTable y gestión de errores.
- Registro local de metadatos remotos de M101 obtenido mediante SIA.
- Descarga controlada de recortes FITS registrados y conversión a PNG.
- Generación de la figura científica del canal 63 de M101 desde el cubo FITS.
- Adaptaciones del catálogo frontend para observaciones locales, remotas y vista científica; proxy de Next.js.
- Auditoría K1 y ampliación de pruebas HTTP K2.

El trabajo reutiliza componentes de Marvin, scripts científicos de Santi y el flujo SIA de Félix. La documentación no atribuye esos componentes originales exclusivamente a Kevin.

## Qué NO implica esta entrega

- No introduce una base de datos, caché avanzada o múltiples proveedores.
- No implementa una comparación temporal completa ni prueba movimiento astronómico.
- No garantiza que los productos remotos consultados sean los insumos usados para construir el cubo demostrativo de M101.
- No incluye credenciales, entornos personales o datos científicos en estos README.

## Estado de verificación

Rama de trabajo: dev_kevin.

- Backend: 248 pruebas aprobadas.
- Proxy del frontend: siete pruebas aprobadas.
- Tipos de rutas generados correctamente.
- Comprobación TypeScript sin errores.
- Catálogo, observaciones SIMP y visualizaciones M101 comprobados localmente.

Los documentos de referencias conservan los hallazgos y comprobaciones
históricas de K1, K2 y la integración científica. Las propuestas pendientes
de revisión no deben interpretarse como correcciones implementadas.
