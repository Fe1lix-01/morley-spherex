from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.schemas.common import Band


SiaCollection = Literal[
    "spherex_dr1",
    "spherex_dr1_deep",
    "spherex_qr3",
    "spherex_qr3_deep",
]



class SiaQuery(BaseModel):
    """Parámetros de la consulta espacial a IRSA SIA."""

    model_config = ConfigDict(allow_inf_nan=False)

    collection: SiaCollection = Field(
    default="spherex_qr3",
    description="Colección de imágenes espectrales SPHEREx",
)

    ra: float = Field(
        ge=0,
        lt=360,
        description="Ascensión recta ICRS en grados",
    )
    dec: float = Field(
        ge=-90,
        le=90,
        description="Declinación ICRS en grados",
    )
    radius_arcsec: float = Field(
        default=30,
        gt=0,
        le=300,
        description="Radio de búsqueda en segundos de arco",
    )
    # Utiliza el tipo compartido de bandas espectrales.
    band: Band = "SPHEREx-D2"

    limit: int = Field(default=10, ge=1, le=100)


class SiaObservation(BaseModel):
    """Metadatos de una imagen encontrada mediante SIA."""

    model_config = ConfigDict(allow_inf_nan=False)

    observation_id: str = Field(min_length=1)

    product_id: str = Field(
        min_length=1,
        description="Identificador completo obs_publisher_did de IRSA",
    )

    collection: SiaCollection
    band: Band

    image_center_ra_deg: float = Field(ge=0, lt=360)
    image_center_dec_deg: float = Field(ge=-90, le=90)

    start_mjd: float
    end_mjd: float
    start_utc: str

    access_url: HttpUrl
    access_format: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_time_interval(self):
        if self.end_mjd < self.start_mjd:
            raise ValueError("La fecha final precede a la inicial")
        return self


class SiaResponse(BaseModel):
    """Respuesta normalizada de nuestra consulta SIA."""

    source: Literal["IRSA SIA"] = "IRSA SIA"
    collection: SiaCollection = "spherex_qr3"
    query: SiaQuery
    count: int = Field(ge=0)
    observations: list[SiaObservation]

    @model_validator(mode="after")
    def validate_count(self):
        if self.count != len(self.observations):
            raise ValueError(
                "El conteo debe coincidir con las observaciones devueltas"
            )

        if self.count > self.query.limit:
            raise ValueError("La respuesta supera el límite solicitado")

        return self