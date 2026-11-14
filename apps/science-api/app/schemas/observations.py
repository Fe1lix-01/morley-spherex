from typing import Literal

from pydantic import BaseModel

from app.schemas.common import Detector


class Observations(BaseModel):
    """Define la estructura de una observación individual."""

    id: str
    detector: Detector
    filename: str
    format: Literal["FITS"]


class ObservationsResponse(BaseModel):
    """Define la respuesta completa del endpoint."""

    total: int
    observations: list[Observations]
