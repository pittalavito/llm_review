from fastapi import APIRouter


class ReviewController:
    """Controller scaffold for future real-review endpoints."""

    def __init__(self):
        self.router = APIRouter(prefix="/review", tags=["review"])
