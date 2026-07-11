import logging

from contextlib import asynccontextmanager
from container import Container
from controller import router as dev_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from uvicorn.logging import DefaultFormatter
from config import Config, UI_REACT_DIST_DIR, get_ui_dir

# 1. Configure logging and load configuration
config = Config()
log_level = getattr(logging, config.app_log_level.upper(), logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(DefaultFormatter("%(levelprefix)s %(message)s", use_colors=True))

logging.root.setLevel(log_level)
logging.root.handlers = [handler]
logger = logging.getLogger(__name__)

# 2. Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application lifespan...")
    container = Container(config)
    container.compile_graph()
    app.state.container = container
    logger.info("Graph compiled with default config.")
    yield
    logger.info("Shutting down application lifespan...")

# 3. Create FastAPI app and include routes
app = FastAPI(lifespan=lifespan, title=config.app_name, version=config.app_version)
app.include_router(dev_router)


class NoCacheStaticFiles(StaticFiles):
    """Serve the UI with no-cache: browsers keep stale JS modules across
    deploys otherwise (dev app, tiny files — revalidating every time is fine)."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


class SpaStaticFiles(NoCacheStaticFiles):
    """SPA fallback: unknown paths serve index.html so client-side routes
    (e.g. /v2/storico) survive a browser refresh."""

    async def get_response(self, path, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response


# React UI (built bundle) under /v2 — mounted only when the build exists,
# so backend tests and API-only setups don't require Node. The vanilla UI
# stays on / until the migration is validated.
if UI_REACT_DIST_DIR.is_dir():
    app.mount("/v2", SpaStaticFiles(directory=UI_REACT_DIST_DIR, html=True), name="ui-react")

app.mount("/", NoCacheStaticFiles(directory=get_ui_dir(), html=True), name="ui")
