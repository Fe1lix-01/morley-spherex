# ÉTER / MORLEY Frontier — Science Workspace

**NASA Space Apps Challenge 2026 — Planet X and SPHEREx**  
**Document:** `science/richi/Documentation/README.md`  
**Status:** Active scientific prototype; incremental migration into `morley-spherex`  
**Updated:** 2026-11-14

## 1. Mission

ÉTER provides a consistent interface for exploring the infrared sky, while **MORLEY Frontier** investigates possible temporal changes using documented astronomical measurements and uncertainty estimates.

Our science workflow connects:

1. **AllWISE** — contextual sky background.
2. **SPHEREx DR1 All-Sky HiPS Cube** — sky exploration and wavelength/channel selection.
3. **SPHEREx Level-2 Spectral Images** — individual observations with timestamps for temporal analysis.
4. **Gaia DR3** — external astrometric reference and predicted positions.
5. **MORLEY** — spectral/spatial eligibility checks, WCS registration, instrumental ePSF fitting, potential ZOGY subtraction, and hypothesis comparison.

**Critical distinction:** the 102 SPHEREx cube channels represent **wavelengths, not observation dates**. The cube is an exploration/reference data product; dated Level-2 images are required for independent-epoch temporal measurements. An all-sky image layer must never be presented as a temporal measurement.

## 2. Mandatory scientific-integrity policy

All science outputs, API responses, and visualizations **must comply** with the ten project rules in:

**[SCIENTIFIC_INTEGRITY_POLICY.md](./SCIENTIFIC_INTEGRITY_POLICY.md)**

In particular:

- Preserve the selected RA/Dec, reference frame, field of view, projection, and orientation where technically compatible when switching sources.
- Keep **time and wavelength controls separate**.
- Use AllWISE as a contextual background; identify SPHEREx and Gaia layers explicitly.
- Never stretch or visually enhance an image in ways that impersonate actual astronomical changes. Display processing must be disclosed.
- Clearly distinguish `observed`, `catalog_prediction`, `simulation`, and `visualization`.
- If data are missing or ineligible, return an explicit unavailable/blocked state, not substituted or invented observations.
- Use an AIT all-sky projection and suitable SIN/TAN local projections as specified by the policy.

## 3. Repository layout

The current repository keeps scripts, outputs, and documentation **inside `science/richi/`**, as sibling folders:

```text
morley-spherex/
├── apps/                          # Backend and frontend (maintained by other teams)
├── data/
├── docs/
└── science/
    ├── pipeline/                 # Shared reusable science modules, when extracted
    └── richi/
        ├── 01_traceback_spherex.py
        ├── [migrated_science_scripts].py
        ├── Documentation/
        │   ├── README.md
        │   └── SCIENTIFIC_INTEGRITY_POLICY.md
        ├── outputs/
        │   ├── catalogs/         # Inventory, candidate pairs and JSON manifests
        │   ├── data/             # FITS caches and cutouts; do not commit large raw files
        │   ├── epsf/             # Instrumental PSF diagnostics and fitted astrometry
        │   ├── figures/          # WCS images and other scientific plots
        │   └── validations/      # H0-H3 injection evidence, CSV/JSON, confusion matrices
        └── targets/             # Target definitions and coordinates
```

The `[migrated_science_scripts].py` line describes files to be migrated, not a literal filename. Do **not** assume a script is executable until its input/output paths are updated and it is retested in this new repository.

### Path convention

For Python files directly in `science/richi/`, resolve paths relative to the script, not to the current terminal directory:

```python
from pathlib import Path

RICHI_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = RICHI_DIR / "outputs"
CATALOGS_DIR = OUTPUTS_DIR / "catalogs"
DATA_DIR = OUTPUTS_DIR / "data"
VALIDATIONS_DIR = OUTPUTS_DIR / "validations"
```

Create output folders as needed. Resolve file references in catalogs against an explicitly documented base directory; never silently rely on legacy absolute paths.

## 4. End-to-end scientific pipeline

```text
User selects sky region (RA, Dec, field of view)
        |
        v
AllWISE context + SPHEREx DR1 HiPS spectral browsing
        |
        v
Traceback: Level-2 observation search by celestial coordinates
        |
        v
Independent epochs + spectral / spatial / quality eligibility
        |
        +--> Ineligible or unavailable => explanatory status + provenance
        |
        v
WCS alignment + masks + variance + background / flux calibration
        |
        +-------------------------------+
        |                               |
        v                               v
Instrumental ePSF fitting       ZOGY image subtraction
(centroids, flux, errors)        (only after full eligibility checks)
        |                               |
        +---------------+---------------+
                        |
                        v
MORLEY Model Comparator (H0 / H1 / H2 / H3)
                        |
                        v
Gaia comparison + uncertainty / limitations / evidence
                        |
                        v
Provenance-aware JSON => Backend API => ÉTER frontend
```

**ZOGY is an optimal image-subtraction methodology, not a generic noise-removal filter.** A WCS match or a similar central wavelength alone is insufficient to run a valid scientific subtraction. Confirm independent observation times, pixel footprints, matched spectral response (including CWAVE/CBAND when available), relevant masks and variance, calibrated photometric units, background treatment, PSF handling, and registration. Report covariance or other uncertainty limitations.

## 5. Traceback — first migration target

**Proposed script:** `science/richi/01_traceback_spherex.py`  
**Input:** target RA/Dec and optional query configuration.  
**Purpose:** connect an all-sky selection to a SPHEREx HiPS spectral tile and to candidate timestamped Level-2 observations.  
**Expected output:** a catalog/JSON manifest under `science/richi/outputs/catalogs/`.

From the root of `morley-spherex`, after copying the script and installing its dependencies:

```powershell
python -m pip install requests hpgeom astroquery astropy
python .\science\richi\01_traceback_spherex.py --solo-cubo
python .\science\richi\01_traceback_spherex.py --ra 295.4097841 --dec -15.2231692
```

These commands describe the planned workflow; **execution in the new repository is not yet verified here**. The script discovers *candidate observations* and must not claim to reconstruct the exact per-pixel history of a combined all-sky cube. If IRSA is unavailable, record a service error explicitly.

Official HiPS resource: <https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube/>

## 6. Experimental evidence from the previous workspace

Results below were generated in the **previous** science directory and must be copied together with their metadata and retested after migration. They are not new results produced by this README.

### 6.1 Real SPHEREx source modeling

Two dated SPHEREx cutouts from a common sky region were compared:

- 2025 observation: `2025W38_1A_0596_4` (2025-09-17).
- 2026 observation: `2026W38_1A_0297_1` (2026-09-15).
- Time separation: approximately **363.15 days**.
- Approximate wavelength mismatch measure: **0.3469** (exploratory; **not** proof of matched spectral response).

The instrumental ePSF reduced weighted-fit residuals compared with a circular Gaussian:

| Measurement | Gaussian reduced χ² | ePSF reduced χ² |
|---|---:|---:|
| Source A, 2025 | 4.082 | 1.594 |
| Source A, 2026 | 3.639 | 1.355 |
| Source B, 2025 | 2.334 | 2.037 |
| Source B, 2026 | 2.552 | 1.108 |

Source A's apparent displacement changed from approximately **0.312″** (Gaussian) to **0.038″** (ePSF). This demonstrates **model dependence**, **not a confirmed physical-motion detection**. Formal centroid errors omit some WCS, instrument, blending, and parallax systematics.

### 6.2 Controlled model-comparator validation

**Script:** `validar_movimiento_inyectado_morley.py`  
**Conditions:** synthetic point sources and independent noise drawn using real SPHEREx ePSF, WCS, variance, flag masks, and background levels. Peak reference SNR = 20; 10 repeats per hypothesis; seed = 2026.

| Injected truth | Predicted H0 | Predicted H1 | Predicted H2 | Predicted H3 |
|---|---:|---:|---:|---:|
| H0: unchanged | 9 | 1 | 0 | 0 |
| H1: brightness change | 0 | 10 | 0 | 0 |
| H2: motion | 0 | 0 | 10 | 0 |
| H3: motion and brightness change | 0 | 0 | 0 | 10 |

**Result: 39/40 = 97.5% classification accuracy in this specific controlled simulation.** The injected motion was +8.0″ east, +6.7″ north (~10.435″ total). One unchanged case was classified as variable. Neither the 97.5% figure nor the recovered subarcsecond errors are a measured real-sky detection rate. This test **did not execute ZOGY**.

### 6.3 Still pending

- Validated independent-epoch ZOGY run on spectrally compatible real observations.
- Reliable multi-star WCS/systematics calibration and observer-aware Gaia comparison.
- Full uncertainty quantification and real-sky sensitivity/false-positive measurements.
- Production Science → Backend → Frontend integration.

## 7. Machine-readable results for backend

Every scientific response should include traceable source metadata and an explicit **evidence kind** and **status**. Example *schema sketch only* (not a real measurement or a deployed API):

```json
{
  "schema_version": "morley.science.v1",
  "target": { "ra_deg": null, "dec_deg": null, "frame": "ICRS" },
  "data_source": "spherex_level2",
  "evidence_kind": "simulation",
  "status": "requires_validation",
  "observations": [],
  "wavelength_um": null,
  "provenance": { "collection": null, "observation_ids": [], "access_urls": [] },
  "methods": { "wcs": true, "epsf": true, "zogy_executed": false },
  "result": { "hypothesis": null, "delta_bic": null, "motion_arcsec": null },
  "limitations": ["Controlled example only; no validated astrophysical detection"]
}
```

Required semantics:

- `evidence_kind`: `observed` | `catalog_prediction` | `simulation` | `visualization`.
- `status`: e.g. `ready`, `insufficient_data`, `incompatible_wavelength`, `unavailable`, `requires_validation`.
- Missing observations must not be replaced silently by simulated or unrelated observations.
- Time slider (independent observation epochs) and wavelength/channel slider (spectral axis) must be separate.
- The backend may display catalog positions, but they must be labeled as **catalog predictions** rather than observed trajectories.

**Suggested API operations (not implemented yet):** metadata, target discovery, epoch discovery, analysis start, and results retrieval. Backend should consume JSON manifests instead of scraping terminal logs.

## 8. Migration checklist

Update this section one script at a time. The list tracks work to be verified; unchecked tasks are not claimed complete.

- [ ] Copy both documentation files into `science/richi/Documentation/` and ensure their relative link works.
- [ ] Migrate and test `01_traceback_spherex.py` (HiPS + Level-2 discovery).
- [ ] Migrate candidate pair and spectral compatibility selection.
- [ ] Migrate WCS registration and quality-mask diagnostics.
- [ ] Migrate Gaussian vs. ePSF measurements, including diagnostic figures.
- [ ] Migrate Gaia cross-checks and quantify systematics.
- [ ] Migrate H0–H3 controlled validation; reproduce 39/40 with its recorded seed and inputs.
- [ ] Integrate ZOGY only after selecting eligible independent-epoch observations.
- [ ] Verify Science JSON and Backend/Frontend display against all ten integrity rules.

For every migrated script record: **script name, version/commit, purpose, input IDs and provenance, dependencies, command, generated files, science limitations, and reproducibility check**.

## 9. Operational notes

- Avoid committing FITS caches, credentials, virtual environments, or large generated artifacts to Git; maintain a `.gitignore` suited to `science/richi/outputs/data/`.
- Keep small provenance manifests and documentation under version control.
- Do not copy old repository history indiscriminately; preserve authorship, applicable license notices, and event participation requirements.
- IRSA availability can fluctuate; where useful, demonstrate with previously verified local files while indicating when results are cached.
- Reproducibility depends on recording observation IDs, effective wavelength, processing and calibration versions, software versions, configuration, and random seeds.

## 10. References

- [IRSA — SPHEREx All-Sky Cube](https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube/)
- [IRSA — SPHEREx tutorials](https://caltech-ipac.github.io/irsa-tutorials/)
- [IRSA — SPHEREx archive documentation](https://caltech-ipac.github.io/spherex-archive-documentation/)
- [ESA — Gaia Archive](https://gea.esac.esa.int/archive/)
- [Zackay, Ofek & Gal-Yam — Proper Image Subtraction](https://arxiv.org/abs/1601.02655)

---

*Living document. Update after each script migration and each independently verified result; never relabel simulated evidence as a real astronomical discovery.*


## Practice 03 — Temporal Epoch Pair Preselection

**Script:** `03_select_epoch_pairs.py`

**Input:** Cached SPHEREx Level 2 discovery manifest from Practice 02.

**Method:**
- Separates observations by year.
- Identifies distinct observing campaigns.
- Compares observation dates.
- Creates a shortlist of epoch pairs.
- Preserves original observation identifiers and archive URLs.

**Expected result for the test region:**
- 57 Level 2 observations.
- 20 observations from 2025.
- 37 observations from 2026.
- 740 temporal pair combinations.
- 16 candidates selected for subsequent inspection.

**Scientific status:** `METADATA_ONLY`

The candidate pairs are not spectrally validated. Matching
detector identifiers and observation dates are insufficient
to authorize ZOGY.

**Next:** Validate FITS cutouts, spectral compatibility,
WCS, variance, masks, and instrumental ePSF.
