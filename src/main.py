import logging

from contextlib import asynccontextmanager
from container import Container
from dev_controller import router as dev_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from config import Config, UI_DIR

# 1. Configure logging and load configuration
config = Config()
log_level = getattr(logging, config.app_log_level.upper(), logging.INFO)
logging.basicConfig(level=log_level, format="[%(levelname)s]: %(message)s")
logger = logging.getLogger(__name__)

# 2. Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application lifespan...")
    app.state.container = Container(config)
    logger.info("Graph compiled with default config.")
    yield
    logger.info("Shutting down application lifespan...")

# 3. Create FastAPI app and include routes
app = FastAPI(lifespan=lifespan, title=config.app_name, version=config.app_version)
app.include_router(dev_router)
app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")
