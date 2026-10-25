"""Response shape."""

from pydantic import BaseModel


class Prediction(BaseModel):
    """The R service's four fields, plus context an older client ignores."""

    health_outcome: str
    prediction: float
    longitude: float
    latitude: float

    input_area_ha: float
    prediction_interval: list[float] | None
    interval_confidence: float
    warnings: list[str]
