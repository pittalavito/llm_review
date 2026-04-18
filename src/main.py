import logging

from contextlib import asynccontextmanager
from container import Container
from controllers import ReviewController, dev_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from settings import Settings, UI_DIR

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
app.include_router(dev_router)
app.include_router(ReviewController().router)

# 4. Mount static files for the UI
app.mount("/ui", StaticFiles(directory=UI_DIR, html=True), name="ui")


