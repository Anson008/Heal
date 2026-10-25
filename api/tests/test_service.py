import pytest

QUERY = {"health_outcome": "MHLTH", "longitude": -84.29, "latitude": 34.07}


def post(client, png, **overrides):
    params = {**QUERY, **overrides}
    return client.post("/predict", params=params, files={"image": ("site.png", png, "image/png")})


def test_returns_the_r_services_four_fields(client, png):
    body = post(client, png).json()

    assert set(body) >= {"health_outcome", "prediction", "longitude", "latitude"}
    assert body["health_outcome"] == "MHLTH"
    assert isinstance(body["prediction"], float)
    assert body["longitude"] == -84.29 and body["latitude"] == 34.07


def test_adds_area_and_warnings(client, png):
    body = post(client, png).json()

    assert body["input_area_ha"] == 1.0
    assert any("50-3000 ha" in note for note in body["warnings"])


def _spatial_bundle():
    """A bundle whose kriging sits on one tract, with a 10 km fitted range."""
    from types import SimpleNamespace

    from service import predict

    return SimpleNamespace(
        feature_ranges={},
        kriging=SimpleNamespace(
            coords=[[40.0, -74.0]],
            range=10.0 / predict.KM_PER_DEGREE,
        ),
    )


def test_no_coverage_warning_inside_the_training_footprint():
    from service import predict

    assert predict.coverage(_spatial_bundle(), 40.0, -74.0) is None


def test_warns_when_the_nearest_training_tract_is_far_away():
    from service import predict

    note = predict.coverage(_spatial_bundle(), 41.737, -111.8338)

    assert note is not None
    assert "km away" in note and "extrapolated trend" in note


def test_longitude_distance_is_scaled_by_latitude():
    """A degree of longitude is shorter near the poles, and must measure so."""
    from service import predict

    bundle = _spatial_bundle()
    equatorial = predict.nearest_training_tract(bundle, 0.0, 1.0)
    polar = predict.nearest_training_tract(bundle, 60.0, 1.0)

    assert polar < equatorial


def test_patch_structure_warnings_collapse_to_one_note():
    """Three granularity features out of range must not read as three problems."""
    from types import SimpleNamespace

    from service import predict

    bundle = SimpleNamespace(
        feature_ranges=dict.fromkeys(predict.GRANULARITY, [0.0, 1.0]),
        kriging=SimpleNamespace(coords=[[40.0, -74.0]], range=1.0),
    )
    metrics = {"PLAND": 40.0, **dict.fromkeys(predict.GRANULARITY, 99.0)}

    notes = predict.warnings(bundle, metrics, hectares=100.0, latitude=40.0, longitude=-74.0)

    assert len(notes) == 1
    assert all(feature in notes[0] for feature in predict.GRANULARITY)


def test_normalised_features_are_not_warned_on():
    """CA restates the area check; COHESION and AI said nothing on their own."""
    from types import SimpleNamespace

    from service import predict

    bundle = SimpleNamespace(
        feature_ranges={name: [0.0, 1.0] for name in ("CA", "COHESION", "AI")},
        kriging=SimpleNamespace(coords=[[40.0, -74.0]], range=1.0),
    )
    metrics = {"PLAND": 40.0, "CA": 1e6, "COHESION": 1e6, "AI": 1e6}

    notes = predict.warnings(bundle, metrics, hectares=100.0, latitude=40.0, longitude=-74.0)

    assert notes == []


def test_reports_a_prediction_interval(client, png):
    body = post(client, png).json()
    low, high = body["prediction_interval"]

    assert body["interval_confidence"] == 0.95
    assert low <= body["prediction"] <= high
    assert low >= 0.0
    assert high - low == pytest.approx(2 * 1.959963984540054 * 0.8)


def test_interval_prefers_the_served_error():
    """A bundle recording both errors must use the one the service runs in."""
    from types import SimpleNamespace

    from service import predict

    bundle = SimpleNamespace(scores={"test_rmse": 0.8, "test_rmse_served": 3.0})
    low, high = predict.interval(bundle, 10.0)

    assert high - low == pytest.approx(2 * 1.959963984540054 * 3.0)


def test_outcome_is_upper_cased(client, png):
    assert post(client, png, health_outcome="mhlth").status_code == 200


def test_errors_use_the_error_key_and_400(client, png):
    response = post(client, png, health_outcome="BOGUS")

    assert response.status_code == 400
    assert response.json() == {"error": "Invalid health outcome"}


def test_coordinate_bounds(client, png):
    assert post(client, png, longitude=200).json()["error"] == "Invalid longitude"
    assert post(client, png, latitude=100).json()["error"] == "Invalid latitude"


def test_unparseable_coordinate_is_a_400_not_a_422(client, png):
    response = post(client, png, longitude="north")

    assert response.status_code == 400
    assert response.json() == {"error": "Invalid longitude"}


def test_missing_image(client):
    response = client.post("/predict", params=QUERY)

    assert response.status_code == 400
    assert response.json() == {"error": "No image provided"}


def test_rejects_extension_then_content(client, png):
    bad_name = client.post(
        "/predict", params=QUERY, files={"image": ("site.txt", png, "text/plain")}
    )
    assert bad_name.json() == {"error": "Invalid image extension"}

    not_an_image = client.post(
        "/predict", params=QUERY, files={"image": ("site.png", b"nope", "image/png")}
    )
    assert not_an_image.json() == {"error": "Invalid image"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "outcomes": ["MHLTH"]}
