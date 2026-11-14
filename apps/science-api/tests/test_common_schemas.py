import pytest
from pydantic import TypeAdapter, ValidationError

# Tipos compartidos que queremos validar.
from app.schemas.common import Band, Detector

# Modelos que utilizan los tipos compartidos.
from app.schemas.observations import Observations
from app.schemas.frames import FrameMetadata
from app.schemas.objects import AstronomicalObjectSummary


# Comprueba que los seis detectores permitidos sean válidos.
@pytest.mark.parametrize(
    "detector",
    ["D1", "D2", "D3", "D4", "D5", "D6"],
)
def test_detector_admite_valores_validos(detector):
    adapter = TypeAdapter(Detector)

    assert adapter.validate_python(detector) == detector


# Comprueba que no se acepten detectores inexistentes.
def test_detector_rechaza_valor_invalido():
    adapter = TypeAdapter(Detector)

    with pytest.raises(ValidationError):
        adapter.validate_python("D7")


# Comprueba que las seis bandas espectrales sean válidas.
@pytest.mark.parametrize(
    "band",
    [
        "SPHEREx-D1",
        "SPHEREx-D2",
        "SPHEREx-D3",
        "SPHEREx-D4",
        "SPHEREx-D5",
        "SPHEREx-D6",
    ],
)
def test_band_admite_valores_validos(band):
    adapter = TypeAdapter(Band)

    assert adapter.validate_python(band) == band


# Comprueba que no se acepten bandas inexistentes.
def test_band_rechaza_valor_invalido():
    adapter = TypeAdapter(Band)

    with pytest.raises(ValidationError):
        adapter.validate_python("SPHEREx-D7")


# Comprueba que el modelo de observaciones utilice Detector.
def test_observation_rechaza_detector_invalido():
    with pytest.raises(ValidationError):
        Observations(
            id="observation-1",
            detector="D7",
            filename="M101_D7_test.fits",
            format="FITS",
        )


# Comprueba que el resumen del objeto rechace detectores inválidos.
def test_object_summary_rechaza_detector_invalido():
    with pytest.raises(ValidationError):
        AstronomicalObjectSummary(
            id="object-1",
            name="M101",
            observation_count=1,
            local_observation_count=1,
            remote_observation_count=0,
            detectors=["D1", "D7"],
        )

# Comprueba que el modelo de frames rechace detectores inválidos.
def test_frame_metadata_rechaza_detector_invalido():
    with pytest.raises(ValidationError):
        FrameMetadata(
            id="frame-1",
            detector="D7",
            filename="M101_D7_test.fits",
            format="FITS",
            width=100,
            height=100,
            center_ra_deg=10.0,
            center_dec_deg=20.0,
            pixel_scale_x_arcsec=1.0,
            pixel_scale_y_arcsec=1.0,
            fov_x_deg=1.0,
            fov_y_deg=1.0,
            coordinate_system="ICRS",
            projection="TAN",
        )
