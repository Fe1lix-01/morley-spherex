# Morley Science API

FastAPI backend for Morley / ETER, an interactive
observatory built around SPHEREx data.

## Responsibilities

- Astronomical object and observation endpoints
- FITS metadata extraction and WCS validation
- FITS-to-PNG rendering
- IRSA TAP and SIA integrations
- Scientific preview endpoints

## Requirements

- Python 3.13
- Dependencies in requirements.txt

## Setup

Run these commands from apps/science-api:

    py -3.13 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt

## Run

    python -m uvicorn app.main:app --reload

Interactive documentation:

http://127.0.0.1:8000/docs

## Tests

    python -m pytest -q -rs
    python -m pip check

Last verified local result:
136 passed, 2 skipped.

## Configuration

See .env.example for configurable options.

MORLEY_FITS_DIR can be used to specify a local
FITS directory when supported by the running
configuration.

## Scientific data

Unit tests use synthetic FITS fixtures.
These are not real SPHEREx observations.

Real astronomical products must retain their
source and processing provenance.
