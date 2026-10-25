from pathlib import Path

import pytest

from service import model_download


def test_download_requires_a_token(tmp_path: Path):
    with pytest.raises(RuntimeError, match="HF_TOKEN"):
        model_download.download_missing(tmp_path, "owner", "repo", None)


def test_download_replaces_existing_files(tmp_path: Path, monkeypatch):
    existing = tmp_path / "MHLTH" / "meta.json"
    existing.parent.mkdir()
    existing.write_text("existing")
    stale = tmp_path / "stale.txt"
    stale.write_text("stale")
    calls = []

    monkeypatch.setattr(
        model_download,
        "_download",
        lambda url, destination, token: calls.append((url, destination, token)),
    )

    model_download.download_missing(tmp_path, "owner", "repo", "token")

    assert not existing.exists()
    assert not stale.exists()
    assert len(calls) == len(model_download.MODEL_METRICS) * len(
        model_download.MODEL_FILES
    )
