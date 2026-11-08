"""Download the model bundles into api/models/ so the installer can ship them.

Run from api/ with HF_TOKEN set: `uv run python desktop/fetch_models.py`.
"""

import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR / "src"))

import config  # noqa: E402
from service import model_download  # noqa: E402


def main() -> None:
    model_download.download_missing(
        API_DIR / "models",
        config.settings.hf_owner,
        config.settings.hf_repo,
        os.environ.get("HF_TOKEN"),
    )


if __name__ == "__main__":
    main()
