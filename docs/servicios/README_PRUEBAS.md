# Tests and K1/K2 Audits

## Backend

From `apps/science-api`:

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests -v
```

Latest result reported by Kevin: **248 tests passed**. The suite was not rerun while preparing these README files. Recheck results after code, dependency, or environment changes.

To check the HTTP clients:

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/test_irsa.py tests/test_sia.py tests/test_irsa_cutouts.py -v
```

## Frontend and proxy

From `apps/web`, with dependencies installed:

```powershell
node --test tests/science-proxy.test.mjs
npx eslint src/app/api/science/m101/route.ts tests/science-proxy.test.mjs
npx next typegen
npx tsc --noEmit
```

Historical proxy checks covered missing configuration, valid PNG, backend error, unexpected format, empty body, refused connection, and timeout. They were not rerun while preparing these docs.

## K1 and K2

K1 reviewed the catalog, TAP, SIA, remote snapshot, previews, layers, and contracts. It fixed specific inconsistencies and documented proposals that were not implemented. K2 added HTTP tests for timeouts, errors, retries, response content, and connection closure; production clients did not need changes for K2.

K2 uses controlled local servers and ports; NASA outages are not required. A valid empty result is distinguished from an empty body or unexpected format.

Limitations that should accompany the delivery:

- Read timeouts were reproduced; not every timeout type was tested.
- No total deadline was established across all attempts.
- Connection-refusal tests do not count connection attempts and release the port first, leaving a window in which another process could occupy it.
- On Windows, local connection refusal took more than two seconds; these tests use a 10-second connect timeout.
- Connection closure was checked in the documented scenarios, not every failure combination.
- Broad exception handling in PNG rendering, generic typing, and some cross-model rules remain proposals or limitations recorded in K1.

See the copies in `referencias/` for detailed findings and evidence. Do not describe every proposal as an implemented fix.

## Minimum manual checks

- Swagger lists Objects, IRSA, SIA, Frames, and Science.
- The catalog groups the six SIMP files as one object and displays all six PNGs.
- M101 appears only when observations are registered; details distinguish local and remote records.
- Each remote product uses its complete `product_id` and retrieves its cutout when the network is available.
- The M101 figure is generated from the configured cube; missing configuration returns 503.
- A search with no results returns HTTP 200 and an empty list.
- The proxy distinguishes errors, timeout, empty content, and unexpected format without returning internal traces.
- Remote data are not misrepresented as confirmed inputs to the cube or as proof of motion.