"""Download missing Python model bundles from Hugging Face."""

import os
import shutil
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODEL_FILES = ("rf.joblib", "krige.npz", "meta.json")
MODEL_METRICS = ("CHD", "COPD", "DIABETES", "LPA", "MHLTH", "STROKE")


def download_missing(
    directory: Path, owner: str, repository: str, token: str | None
) -> None:
    """Replace the model directory with fresh bundles from Hugging Face."""
    if not token:
        raise RuntimeError("DOWNLOAD_MODELS is enabled but HF_TOKEN is not set")

    shutil.rmtree(directory, ignore_errors=True)
    directory.mkdir(parents=True, exist_ok=True)
    base_url = f"https://huggingface.co/datasets/{owner}/{repository}/resolve/main"

    for metric in MODEL_METRICS:
        for filename in MODEL_FILES:
            destination = directory / metric / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            url = f"{base_url}/{metric}/{filename}?download=true"
            _download(url, destination, token)


def _download(url: str, destination: Path, token: str) -> None:
    request = Request(url, headers={"Authorization": f"Bearer {token}"})
    temporary_path: Path | None = None

    try:
        with urlopen(request) as response:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(response.read())
    except (HTTPError, URLError, OSError) as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise RuntimeError(f"Could not download {url}: {error}") from error

    os.replace(temporary_path, destination)
    print(f"downloaded {destination}", flush=True)
