import logging

from contextlib import asynccontextmanager
from container import Container
from controller import router as dev_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from uvicorn.logging import DefaultFormatter
from config import Config, UI_REACT_DIST_DIR

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


class SpaStaticFiles(StaticFiles):
    """Serve the built React SPA: no-cache headers (so browsers don't keep
    stale modules across deploys) plus an index.html fallback so client-side
    routes survive a browser refresh."""

    async def get_response(self, path, scope):
        try:
            response = await super().get_response(path, scope)
            if response.status_code == 404:
                response = await super().get_response("index.html", scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            response = await super().get_response("index.html", scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


# The React build is served at the root. The mount is added last, so the API
# router (/llm-review) and the docs routes (/docs, /openapi.json) still win;
# it only catches everything else. Guarded on the build existing so the
# backend (and tests) run without a compiled frontend.
if UI_REACT_DIST_DIR.is_dir():
    app.mount("/", SpaStaticFiles(directory=UI_REACT_DIST_DIR, html=True), name="ui")