"""POST /predict, mirroring plumber.R's contract."""

from io import BytesIO
from pathlib import PurePath

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from PIL import Image, UnidentifiedImageError

import config

from . import bundles, predict, schemas

EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# Every landscape metric is computed in pixels and converted with one pixel
# taken as one ground metre, which is the resolution the model was trained at.
# Nothing here can verify that -- an image carries no scale -- so a caller who
# sends other imagery silently gets metrics off by the square of their scale
# factor. The web client guarantees it by resampling; direct callers, which
# /api/docs invites, have to do the same.
PIXEL_CONTRACT = """
Predicts the prevalence of one health outcome for the site in the uploaded
image, at the given coordinate.

**The image must be scaled so that one pixel covers one square metre of
ground.** The landscape metrics the model reads are computed in pixels and
converted at that rate; imagery at any other resolution produces silently
wrong areas, patch densities and patch sizes. Resample before uploading --
a 500 x 400 m site becomes a 500 x 400 px image.

The model was fitted on census tracts in five US metropolitan areas (New York,
Los Angeles, Miami, San Antonio, Seattle) covering 50-3000 ha. Requests outside
that envelope still return a prediction; `warnings` says why it is weaker.
"""

router = APIRouter()


def _open(upload: UploadFile | None, data: bytes) -> Image.Image:
    """Validate an upload the way plumber.R does, then decode it."""
    if upload is None or not data:
        raise HTTPException(400, "No image provided")

    name = upload.filename
    if not name or not name.strip():
        raise HTTPException(400, "Invalid image filename")

    if PurePath(name).suffix.lower().lstrip(".") not in EXTENSIONS:
        raise HTTPException(400, "Invalid image extension")

    # Content, not the filename, decides whether this is really an image.
    try:
        Image.open(BytesIO(data)).verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, "Invalid image") from None

    image = Image.open(BytesIO(data))
    if image.width * image.height > config.MAX_PIXELS:
        raise HTTPException(400, "Image is too large")

    return image


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "outcomes": bundles.available()}


@router.post(
    "/predict",
    response_model=schemas.Prediction,
    summary="Predict a health outcome for a site",
    description=PIXEL_CONTRACT,
)
async def predict_health(
    health_outcome: str = Query(...),
    longitude: float = Query(...),
    latitude: float = Query(...),
    image: UploadFile | None = File(
        None, description="One pixel must cover one square metre of ground."
    ),
) -> schemas.Prediction:
    outcome = health_outcome.strip().upper()
    bundle = bundles.get(outcome)
    if bundle is None:
        raise HTTPException(400, "Invalid health outcome")

    if not -180 <= longitude <= 180:
        raise HTTPException(400, "Invalid longitude")

    if not -90 <= latitude <= 90:
        raise HTTPException(400, "Invalid latitude")

    decoded = _open(image, await image.read() if image else b"")
    value, hectares, bounds, notes = predict.predict(
        bundle, decoded, longitude, latitude
    )

    return schemas.Prediction(
        health_outcome=outcome,
        prediction=value,
        longitude=longitude,
        latitude=latitude,
        input_area_ha=hectares,
        prediction_interval=bounds,
        interval_confidence=predict.CONFIDENCE,
        warnings=notes,
    )
