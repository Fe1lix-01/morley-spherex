# Ejecutar backend y frontend

Los comandos siguientes son para PowerShell y parten de la raíz del repositorio que contenga `apps`, `labs`, `resources` y `data`. Mantener dos terminales abiertas.

## Dependencias

El backend se comprobó localmente con Python 3.14. Para el frontend se
requieren Node.js y npm compatibles con las versiones del proyecto.

Utilizar los manifiestos del proyecto para instalar las dependencias:

- Backend: `apps/science-api/requirements.txt`.
- Frontend: `labs/frontend/aladin-test/package.json` y `package-lock.json`.
- Núcleo científico completo: `pyproject.toml`; no es necesario instalarlo para iniciar exclusivamente esta API.

HTTPX se usa en los clientes de producción. HTTPX2 está incluido para el TestClient de Starlette, según la verificación registrada del proyecto. No sustituir uno por otro sin comprobar versiones.

## Terminal 1 — backend

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\apps\science-api\requirements.txt
```

Preparar el FITS y el directorio del catálogo según [Datos científicos](README_DATOS_CIENTIFICOS.md). Para la figura M101:

```powershell
$env:M101_FITS_PATH = (Resolve-Path -LiteralPath ".\data\m101\M101_irsa.fits").Path
Test-Path -LiteralPath $env:M101_FITS_PATH
cd .\apps\science-api
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`M101_FITS_PATH` pertenece a esta sesión. Se puede iniciar la API sin esa variable, pero la vista científica responderá HTTP 503. La raíz `/` no tiene por qué existir: un HTTP 404 allí no significa que el servidor esté detenido.

- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
- Health: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health).

## Terminal 2 — frontend

Desde la raíz:

```powershell
cd .\labs\frontend\aladin-test
npm ci
$env:SCIENCE_API_URL = "http://127.0.0.1:8000"
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000/api/v1"
npm run dev
```

Abrir [http://localhost:3000/catalog](http://localhost:3000/catalog). Si Next utiliza otro puerto, revisar la salida y los orígenes CORS del backend.

`SCIENCE_API_URL` se utiliza en el servidor Next.js para el proxy de M101. `NEXT_PUBLIC_API_URL` se utiliza desde el navegador para las demás consultas. Reiniciar el frontend después de cambiar estas variables. La existencia del filtro `q` en la API no implica una caja de búsqueda en el catálogo actual.

## Servicios en equipos diferentes

Configurar SCIENCE_API_URL con una dirección del backend accesible
desde el servidor Next.js.

Configurar NEXT_PUBLIC_API_URL con una dirección accesible desde el
navegador. Ajustar los orígenes CORS del backend según corresponda.

La ejecución verificada para esta entrega es local. No se comprobó
un despliegue en servidores remotos.