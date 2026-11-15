"""Contract tests for read-only Morley science diagnostics API."""

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.diagnostics import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)
PREFIX = "/api/v1/science/diagnostics"


def report_fixture():
    return {
        "schema_version": "morley.science_routes.v1",
        "generated_at_utc": "2026-11-15T07:18:16+00:00",
        "target": {"ra_deg": 295.4097841, "dec_deg": -15.2231692, "frame": "ICRS"},
        "scientific_integrity": {
            "cwave_cband_verified": False,
            "real_zogy_executed": False,
            "motion_detected": False,
            "temporal_variability_claimed": False,
        },
        "summary": {"observations": 1, "pairs": 1, "routes": {"TEMPORAL_CALIBRATION_CANDIDATE": 1}},
        "single_observation_diagnostics": [{
            "obs_id": "obs01", "status": "SINGLE_IMAGE_APERTURE_DIAGNOSTIC",
            "formal_snr_diagnostic": float("nan"),
            "file": "/private/path/example.fits", "file_sha256": "secret",
            "limitations": ["Not science-grade photometry"],
        }],
        "pair_routes": [{
            "pair_id": "C001", "earlier_obs_id": "obs01", "later_obs_id": "obs02",
            "route": "TEMPORAL_CALIBRATION_CANDIDATE", "separation_days": 154.5315,
            "cwave_cband_verified": False, "real_zogy_executed": False,
            "reasons": ["Exact spectral calibration required"],
            "file": "/private/path/example.fits",
        }],
    }


def test_missing_report_is_explicit(monkeypatch, tmp_path):
    monkeypatch.setenv("MORLEY_SCIENCE_REPORT_PATH", str(tmp_path / "absent.json"))
    response = client.get(PREFIX + "/summary")
    assert response.status_code == 503
    assert "no está disponible" in response.json()["detail"]


def test_readonly_metadata_filters_and_safe_serialization(monkeypatch, tmp_path):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report_fixture()), encoding="utf-8")
    monkeypatch.setenv("MORLEY_SCIENCE_REPORT_PATH", str(path))

    summary = client.get(PREFIX + "/summary")
    assert summary.status_code == 200
    assert summary.json()["target"]["ra_deg"] == 295.4097841
    assert summary.json()["scientific_integrity"]["real_zogy_executed"] is False

    obs = client.get(PREFIX + "/observations")
    assert obs.status_code == 200
    assert obs.json()["total"] == 1
    assert obs.json()["items"][0]["formal_snr_diagnostic"] is None
    assert "file" not in obs.text and "secret" not in obs.text

    pairs = client.get(PREFIX + "/pairs", params={"route": "TEMPORAL_CALIBRATION_CANDIDATE"})
    assert pairs.status_code == 200
    assert pairs.json()["total"] == 1
    assert pairs.json()["items"][0]["pair_id"] == "C001"
    assert "/private/" not in pairs.text
    assert pairs.json()["scientific_integrity"]["cwave_cband_verified"] is False

    empty = client.get(PREFIX + "/pairs", params={"route": "TEMPORAL_REVIEW"})
    assert empty.status_code == 200 and empty.json()["total"] == 0

    assert client.get(PREFIX + "/pairs", params={"limit": 1000}).status_code == 422
    assert client.get(PREFIX + "/pairs", params={"route": "FAKE"}).status_code == 422


def test_invalid_schema_rejected(monkeypatch, tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text('{"schema_version":"unknown"}', encoding="utf-8")
    monkeypatch.setenv("MORLEY_SCIENCE_REPORT_PATH", str(path))
    assert client.get(PREFIX + "/summary").status_code == 503
