import logging

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from controller import router as controller
from container import CONFIG

_UI_DIR = (Path(__file__).parent.parent / "ui").resolve()

logging.basicConfig(level=logging.DEBUG,format="[%(levelname)s]: %(message)s")

app = FastAPI(title=CONFIG.app_name, version=CONFIG.app_version)

app.include_router(controller)

app.mount("/ui", StaticFiles(directory=_UI_DIR, html=True), name="ui")

