# API Architecture and Contracts

## Responsibilities

- `app/routers`: HTTP parameters, response models, and exception-to-response translation.
- `app/services`: grouping, transformation, validation, and result generation.
- `app/clients`: IRSA requests, timeouts, error classification, and downloads.
- `app/schemas`: Pydantic contracts and data consistency rules.
- `app/core/paths.py`: path resolution relative to the project structure.

The five services audited in K1 do not directly import FastAPI/Starlette or construct HTTP responses. Preserve that separation.

## Main routes

| Method and route | Main input | Response |
|---|---|---|
| `GET /api/v1/objects` | Optional `q` | JSON with total and summaries |
| `GET /api/v1/objects/{object_id}` | Catalog ID | Detail with local and remote observations |
| `GET /api/v1/irsa/observations` | `ra`, `dec`, `band`, `limit` | Normalized TAP metadata |
| `GET /api/v1/sia/observations` | `ra`, `dec`, `collection`, `radius_arcsec`, `band`, `limit` | Normalized SIA metadata |
| `GET /api/v1/objects/{object_id}/remote-preview` | Required `product_id` | `image/png` remote cutout |
| `GET /api/v1/science/m101/channel-63/preview` | Server-configured FITS | Three-panel `image/png` |
| `GET /api/v1/frames` | See Swagger | Local frame metadata |
| `GET /api/v1/frames/{frame_id}/image` | Registered local frame | Local PNG |

Health and Observations are existing modules and must be preserved. Register each router only once in `app/main.py`. `frames` and `science_preview` are separate features; retain both.

## Object catalog

`services/objects.py` reuses `list_observations()` without reading FITS files again. It recognizes filenames following `name_D1_...fits`, through D6, using a regular expression that preserves spaces in names.

Objects are grouped with `casefold()`, a deterministic name is selected, and UUID5 is generated. IDs for local variants currently present can resolve to the same group. There is no historical registry to guarantee IDs for variants that have been removed.

Search `q` is partial and case-insensitive. No matches return HTTP 200 with a total of zero. An unknown ID returns 404.

`observation_count` sums local and remote records; subtotals and lists are validated. Records from separate sources are not scientifically deduplicated without provenance linking them.

M101 is included only when recognized local observations or a present, valid remote snapshot exists. Do not insert a fictitious object to make a figure appear. `science_preview` indicates a supported operation; it does not guarantee that the cube is currently available.

## TAP and SIA

RA is in ICRS degrees: `0 <= ra < 360`. Dec: `-90 <= dec <= 90`. SPHEREx bands are D1 through D6. The response limit is 1 to 100.

SIA accepts `spherex_qr2` and `spherex_qr3`, with QR3 as the default. Radius is in arcseconds, greater than zero and up to 300 under the project's current validation. This maximum is not presented as an official provider limit. The client converts the radius to degrees for `POS=CIRCLE`.

The SIA limit is applied after querying, filtering, and sorting results. `count` is the number returned, not the total available at NASA. Preserve the full `product_id`: an exposure ID alone may not distinguish detectors.

Example for Swagger or a browser; this makes a real external query:

```text
/api/v1/sia/observations?collection=spherex_qr2&ra=210.8022671&dec=54.34895&radius_arcsec=30&band=SPHEREx-D4&limit=2
```

Clients execute when their methods are called, not when modules are imported. Practice scripts do not replace the service.

## Remote cutouts

The preview looks up the product in the registered object. The consumer provides a `product_id`, not an arbitrary download URL.

The client restricts the origin, SPHEREx path, FITS extension, and absence of a query or fragment in the original URL. It does not follow redirects. It streams a 0.025-degree cutout with an 8 MiB size limit. The service requires a 2D IMAGE extension, celestial WCS, and the queried position within the image; it reuses the existing PNG contrast rendering.

The browser cannot display FITS directly with `<img>`. Enlarging a PNG on screen does not add scientific resolution.

## HTTP errors and limits

- Invalid parameters: normally HTTP 422 from FastAPI/Pydantic.
- Unknown object/product: 404.
- Invalid external response: 502.
- Catalog, scientific configuration, or service unavailable: 503.
- External timeout: 504.

A malformed URL in the JSON invalidates the snapshot and returns 503 before downloading. A syntactically valid but disallowed URL returns 502 from the client.

TAP/SIA allow three attempts under the defined policy, with bounded waits; SIA 400/401/403/404/422 responses were verified not to retry. The cutout client does not retry failed HTTP responses; its transport configures two connection retries. These policies are different and should not be conflated.

Default timeouts: connect 10 s, read 60 s, write 10 s, and pool 10 s. These are not a total-operation deadline. The M101 Next.js proxy has a 10-second timeout that includes reading the response body; it can expire before slow backend processing finishes.

Public responses use generic messages. Internal logs may contain diagnostic traces; do not return those traces in HTTP response bodies.