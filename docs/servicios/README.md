# Kevin's Work — Sphere-X / ÉTER

This documentation describes the work on Sphere-X / ÉTER services, scientific visualization, and tests. It does not replace the project README, license, or attribution notices.

## Using these documents

1. [Local setup](README_EJECUCION.md)
2. [API architecture and services](README_SERVICIOS_API.md)
3. [Scientific data and reproducibility](README_DATOS_CIENTIFICOS.md)
4. [Tests and K1/K2 audits](README_PRUEBAS.md)

Read these documents together. Commands assume the repository's current layout and identify the directory from which they should run.

## Included work

- Object catalog: observation grouping, stable identifiers for currently available data, partial search, and detail views.
- IRSA/TAP client using HTTPX, with Pydantic-normalized responses.
- SIA client for SPHEREx QR2 and QR3, VOTable transformation, and error handling.
- Local snapshot of remote M101 metadata obtained through SIA.
- Controlled download of registered FITS cutouts and conversion to PNG.
- Generation of the M101 channel 63 scientific figure from its FITS cube.
- Frontend catalog integration for local and remote observations and the scientific preview, plus the Next.js proxy.
- K1 audit and expanded K2 HTTP tests.

This work reuses components from Marvin, Santi's scientific scripts, and Felix's SIA flow. This documentation does not claim those original components as Kevin's work alone.

## What this delivery does not imply

- It does not add a database, advanced cache, or multiple providers.
- It does not implement a complete temporal comparison or prove astronomical motion.
- It does not establish that the queried remote products were used to build the M101 demonstration cube.
- These README files do not include credentials, personal environments, or scientific data files.

## Verification status

Working branch reported by Kevin: `dev_kevin`.

- Backend: 248 tests passed.
- Frontend proxy: seven tests passed.
- Next.js route types generated successfully.
- TypeScript check completed without errors.
- Catalog, SIMP observations, and M101 visualizations were checked locally.

The reference documents retain historical findings and verification details for K1, K2, and the scientific integration. Proposals that remain under review must not be described as implemented fixes.