"""FastAPI application for the HEAL Tool prediction service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

import config

from . import bundles, model_download, routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    if config.settings.download_models:
        model_download.download_missing(
            config.settings.models_dir,
            config.settings.hf_owner,
            config.settings.hf_repo,
            config.settings.hf_token,
        )

    loaded = bundles.load(config.settings.models_dir)
    print(f"loaded {len(loaded)} bundles: {', '.join(loaded)}", flush=True)
    yield


# root_path: the proxy strips /api/ before forwarding, so the docs page has to
# be told the public prefix or its openapi.json and "Try it out" calls miss.
app = FastAPI(
    title="HEAL Tool prediction API",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/api",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.settings.origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(routes.router)


# The web client reads `errorBody.error`; FastAPI would otherwise say `detail`.
@app.exception_handler(HTTPException)
async def http_error(request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc: RequestValidationError) -> JSONResponse:
    location = exc.errors()[0]["loc"]
    field = ".".join(str(part) for part in location[1:]) or "request"

    return JSONResponse(status_code=400, content={"error": f"Invalid {field}"})
