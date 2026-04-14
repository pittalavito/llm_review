import logging

from contextlib import asynccontextmanager
from pathlib import Path
from container import Container
from controller import router as controller
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from settings import Settings

# 1. Configure logging and load settings
logging.basicConfig(level=logging.INFO, format="[%(levelname)s]: %(message)s")
logger = logging.getLogger(__name__)
settings = Settings()

# 2. Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application lifespan...")
    app.state.container = Container(settings)
    yield
    logger.info("Shutting down application lifespan...")

# 3. Create FastAPI app and include routes
app = FastAPI(lifespan=lifespan, title=settings.app_name, version=settings.app_version)
app.include_router(controller)

# 4. Mount static files for the UI
_ui_dir = Path(__file__).parents[1] / "ui"
app.mount("/ui", StaticFiles(directory=_ui_dir, html=True), name="ui")


