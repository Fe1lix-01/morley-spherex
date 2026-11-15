"""Availability checks must not train or fabricate ML results."""
import numpy as np
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ml_missing_configuration_is_explicit(monkeypatch):
    for name in ('ETER_ML_PYTHON', 'ETER_ML_WEIGHTS', 'ETER_ML_SAMPLE'):
        monkeypatch.delenv(name, raising=False)
    response = client.get('/api/v1/ml/demo')
    assert response.status_code == 503
    for name in ('ETER_ML_PYTHON', 'ETER_ML_WEIGHTS', 'ETER_ML_SAMPLE'):
        assert name in response.json()['detail']


def test_barnard_missing_and_malformed_artifacts(monkeypatch, tmp_path):
    monkeypatch.setenv('ETER_BARNARD_ARTIFACTS_DIR', str(tmp_path))
    for suffix in ('', '/image'):
        assert client.get('/api/v1/ml/barnard/preview' + suffix).status_code == 503
    np.savez(tmp_path / 'barnard_triplete_real_exploratorio.npz', valid_mask=np.ones(3))
    assert client.get('/api/v1/ml/barnard/preview').status_code == 503


def test_barnard_preview_remains_exploratory(monkeypatch, tmp_path):
    monkeypatch.setenv('ETER_BARNARD_ARTIFACTS_DIR', str(tmp_path))
    np.savez(tmp_path / 'barnard_triplete_real_exploratorio.npz', valid_mask=[[True, False], [True, True]])
    response = client.get('/api/v1/ml/barnard/preview')
    assert response.status_code == 200
    data = response.json()
    assert data['valid_pixels'] == 3
    assert data['cnn_inference_performed'] is False
    assert data['scientifically_validated'] is False
