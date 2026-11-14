# Scientific Data and Reproducibility

## Three different resources

1. Local SIMP D1–D6 FITS files used by the catalog and local previews.
2. The `M101_irsa.fits` demonstration cube used to generate the channel 63 figure.
3. A JSON snapshot of SIA remote products spatially associated with M101.

Do not treat these as the same product or as evidence of motion.

## Local SIMP FITS files

Expected location: `resources/objects/images/fits/`.

This local directory must exist to build the catalog, even when remote data are available. It may be empty. To display SIMP, place its six real files there; do not create empty FITS files to simulate real images.

The `.gitignore` excludes new FITS files, but files already tracked may remain in Git. Check their tracking status before copying or attempting to remove them from history.

## Download the M101 cube

From the repository root:

```powershell
New-Item -ItemType Directory -Path .\data\m101 -Force
Invoke-WebRequest -Uri "https://irsa.ipac.caltech.edu/data/demos/notebooks/spherex/M101_irsa.fits" -OutFile .\data\m101\M101_irsa.fits
$env:M101_FITS_PATH = (Resolve-Path -LiteralPath ".\data\m101\M101_irsa.fits").Path
Test-Path -LiteralPath $env:M101_FITS_PATH
```

The download writes to the target file. If a valid copy is already present, there is no need to download it again. Do not commit the cube or a personal `.env` file.

After starting the backend, open [the M101 figure](http://127.0.0.1:8000/api/v1/science/m101/channel-63/preview). It generates three panels: image, NHITS coverage, and quality mask. It does not merely serve a pre-existing PNG from `outputs`.

The service checks for the IMAGE, NHITS, FLAGS, and SPECTRAL_CHANNELS extensions, compatible dimensions, channel structure, and available wavelength information. See the code and tests for the full validation rules. A missing resource or rejected processing request returns this endpoint's controlled HTTP 503 response.

## FLAGS policy for this mosaic

The existing scientific documentation records comparison with the cube header and [IRSA's official Mosaic Tool help](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/mosaic.html).

For this visualization, bit positions 1 and 19 are excluded; the inspected header identifies them as MP_OVERFLOW and MP_OUTLIER. MP_SOURCE (21) is retained. IMAGE values must be finite and NHITS must be positive. This is an exploratory project display policy, not a universal photometry recommendation.

Do not automatically apply every pipeline `bad_flag_bits` value or transfer this mask to other products. Individual remote cutout previews do not apply the mosaic mask. Any scientific change requires checking the relevant product and review by the team.

## Generate the remote snapshot

With backend dependencies installed, run from the repository root:

```powershell
.\.venv\Scripts\python.exe .\science\targets\consultar_metadatos_m101.py
```

This operation makes a real IRSA query. It reuses the backend SIA service and saves `data/m101/observations.json` using a temporary file followed by replacement. It can replace an earlier snapshot; preserve the version used if exact reproduction of a historical query is needed.

The implemented query requests QR2, SPHEREx-D4, a 30-arcsecond radius, and a limit of 2 at RA 210.8022671 / Dec 54.34895. It records the query time, position provenance, collection, products, dates, and URLs.

The documented association is **spatial intersection**: the image coverage intersects the queried circle. This alone does not prove detection of the object or that those exposures were used to build the demonstration cube.

If the snapshot is absent, no remote observations are added. If it is present but invalid, the catalog returns a controlled error. Do not insert M101 manually to hide a missing snapshot.

## Data and tests

Synthetic FITS files in tests validate structure, masks, and PNG generation reproducibly; they are not real observations. Some local integration tests may depend on SIMP FITS files. M101's synthetic FITS tests run without downloading the real cube or setting `M101_FITS_PATH`.

Ignored resources are not automatically included when cloning the repository. Prepare them using the locations and instructions above.