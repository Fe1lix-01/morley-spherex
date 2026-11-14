# Running the Backend and Frontend

The following PowerShell commands start from the repository root, which contains `apps`, `resources`, and `data`. Keep two terminals open.

## Dependencies

The backend was checked locally with Python 3.14. The frontend requires Node.js and npm compatible with the versions in the project manifests.

Use the project manifests to install dependencies:

- Backend: `apps/science-api/requirements.txt`.
- Frontend: `apps/web/package.json` and `package-lock.json`.

HTTPX is used by the production clients. HTTPX2 is included for Starlette's TestClient, according to the project's recorded verification. Do not substitute one for the other without checking compatibility.

## Terminal 1 — Backend

From the repository root:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\apps\science-api\requirements.txt
```

Prepare the FITS cube and catalog directory as described in [Scientific data](README_DATOS_CIENTIFICOS.md). For the M101 figure:

```powershell
$env:M101_FITS_PATH = (Resolve-Path -LiteralPath ".\data\m101\M101_irsa.fits").Path
Test-Path -LiteralPath $env:M101_FITS_PATH
cd .\apps\science-api
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`M101_FITS_PATH` applies to the current PowerShell session. The API can start without it, but the scientific preview will return HTTP 503. The root path `/` does not have to exist; HTTP 404 there does not mean the server is down.

- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

## Terminal 2 — Frontend

From the repository root:

```powershell
cd .\apps\web
npm ci
$env:SCIENCE_API_URL = "http://127.0.0.1:8000"
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000/api/v1"
npm run dev
```

Open [http://localhost:3000/catalog](http://localhost:3000/catalog). If Next.js chooses another port, check its terminal output and the backend's CORS origins.

`SCIENCE_API_URL` is used on the Next.js server for the M101 proxy. `NEXT_PUBLIC_API_URL` is used by the browser for other API requests. Restart the frontend after changing either variable. The API's `q` filter does not imply that the current catalog UI has a search box.

## Services on separate machines

Set `SCIENCE_API_URL` to an address reachable from the Next.js server. Set `NEXT_PUBLIC_API_URL` to an address reachable from the user's browser, and configure the backend's CORS origins as needed.

This delivery was verified locally. Deployment to remote servers was not verified.