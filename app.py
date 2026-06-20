import asyncio
import json
import os
import importlib
import shutil
import traceback
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import Request, status, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from helpers.config_loader import set_config_path

set_config_path(os.environ["CONFIG_PATH"])

from core import config, SonolusFastAPI, SonolusMiddleware

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from helpers.api import SbugaAPI

from helpers.level_builder import fetch_music_data

debug = config["server"]["debug"]


@asynccontextmanager
async def lifespan(app: SonolusFastAPI):
    folder = "sonolus"
    if len(os.listdir(folder)) == 0:
        print("[WARN] No routes loaded.")
    else:
        load_routes(folder, cleanup=debug)
        print("Routes loaded!")

    app.api = SbugaAPI(app.api_config["url"])

    asyncio.create_task(fetch_music_data(app.api))

    yield


if debug:
    app = SonolusFastAPI(
        debug=debug, base_url=config["server"]["base-url"], lifespan=lifespan
    )
else:
    app = SonolusFastAPI(
        debug=debug,
        base_url=config["server"]["base-url"],
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )


@app.middleware("http")
async def no_unhandled_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        traceback.print_exc()
        return Response(
            content="Unhandled error. Report to discord.gg/Cdjs8c3SRy",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


if debug:

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        print("Validation Error:")
        print(json.dumps(exc.errors(), indent=2))

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SonolusMiddleware)
if not debug:
    domain = urlparse(config["server"]["base-url"]).netloc
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[domain])


@app.middleware("http")
async def force_https_redirect(request, call_next):
    response = await call_next(request)

    if config["server"]["force-https"] and not debug:
        if response.headers.get("Location"):
            response.headers["Location"] = response.headers.get("Location").replace(
                "http://", "https://", 1
            )

    return response


def load_routes(folder, cleanup: bool = True):
    global app

    routes = []

    def traverse_directory(directory):
        for root, dirs, files in os.walk(directory, topdown=False):
            for file in files:
                if (
                    not "__pycache__" in root
                    and file.endswith(".py")
                    and not file.startswith("_")
                ):
                    route_name: str = (
                        os.path.join(root, file)
                        .removesuffix(".py")
                        .replace("\\", "/")
                        .replace("/", ".")
                    )

                    if "{" in route_name and "}" in route_name:
                        routes.append((route_name, False))
                    else:
                        routes.append((route_name, True))

    traverse_directory(folder)

    routes.sort(key=lambda x: (not x[1], x[0]))

    for route_name, is_static in routes:
        try:
            route = importlib.import_module(route_name)
        except NotImplementedError:
            continue

        route_version = route_name.split(".")[0]
        route_name_parts = route_name.split(".")

        if route_name.endswith(".index"):
            del route_name_parts[-1]

        route_name = ".".join(route_name_parts)
        app.include_router(
            route.router,
            prefix="/" + route_name.replace(".", "/"),
            tags=(
                route.router.tags + [route_version]
                if isinstance(route.router.tags, list)
                else [route_version]
            ),
        )

        print(f"[API] Loaded Route {route_name}")

    if cleanup:
        for root, dirs, _ in os.walk(folder, topdown=False):
            if "__pycache__" in dirs:
                pycache_path = os.path.join(root, "__pycache__")
                shutil.rmtree(pycache_path, ignore_errors=True)
                print(f"[API] Removed __pycache__ at {pycache_path}")


def start_fastapi():
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=config["server"]["port"],
        workers=6,
        access_log=debug,
    )


if __name__ == "__main__":
    raise SystemExit("Please run main.py")
