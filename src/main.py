import logging

from pathlib import Path
from fastapi import FastAPI
from contextlib import asynccontextmanager

from fastapi.staticfiles import StaticFiles
from controller import router as controller
from container import  Container
from settings import Settings

# 1. Configure logging 
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s]: %(message)s"
)

logger = logging.getLogger(__name__)
settings = Settings()

# 2. Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    app.state.container = Container(settings)
    yield
    logger.info("Shutting down application...")


# 3. Create FastAPI app and include routes
app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version=settings.app_version
)
app.include_router(controller)


# 4. Serve static files for the UI
app.mount(
    "/ui", 
    StaticFiles(
        directory=Path(__file__).parents[1] / "ui", 
        html=True
    ), 
    name="ui"
)

