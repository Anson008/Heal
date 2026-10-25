"""Runtime configuration, replacing the R service's .Renviron."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The envelope the paper states the model is valid within. Inputs outside it
# still get a prediction; the response says so.
MIN_AREA_HECTARES = 50.0
MAX_AREA_HECTARES = 3000.0
MIN_GREENSPACE_PERCENT = 5.0
MAX_GREENSPACE_PERCENT = 75.0

# Well above the paper's 3000 ha ceiling, and a guard against decompression
# bombs reaching the classifier.
MAX_PIXELS = 64_000_000


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8000
    allowed_origins: str = "http://localhost:5173"
    models_dir: Path = Path(__file__).resolve().parent.parent / "models"
    download_models: bool = False
    hf_owner: str = "CarterOJ"
    hf_repo: str = "heal_models"
    hf_token: str | None = None

    @property
    def origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
