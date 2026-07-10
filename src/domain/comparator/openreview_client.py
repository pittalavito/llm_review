import json
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_BASE_V1 = "https://api.openreview.net"
_BASE_V2 = "https://api2.openreview.net"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class OpenReviewClient:

    def __init__(self, cache_dir: Path | None = None):
        self._cache_dir = cache_dir

    def fetch_notes(self, forum_id: str, api_version: str, cache_name: str | None = None) -> list[dict]:
        cached = self._load_cached_notes(cache_name)
        if cached is not None:
            logger.info("Using cached OpenReview notes for %s (%d notes)", cache_name, len(cached))
            return cached

        base = _BASE_V2 if api_version == "v2" else _BASE_V1
        url = f"{base}/notes"
        params = {"forum": forum_id, "limit": 1000}
        logger.info("Fetching OpenReview notes forum=%s api=%s", forum_id, api_version)
        response = httpx.get(url, params=params, headers=_HEADERS, timeout=20)
        if response.status_code == 403:
            self._raise_for_challenge(response, forum_id)
        response.raise_for_status()
        return response.json().get("notes", [])

    def _load_cached_notes(self, cache_name: str | None) -> list[dict] | None:
        if not self._cache_dir or not cache_name:
            return None
        path = self._cache_dir / f"{cache_name}.json"
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError):
            logger.warning("Failed to read OpenReview cache file: %s", path)
            return None
        notes = (data.get("response") or {}).get("notes")
        if not notes:
            return None
        return notes


    @staticmethod
    def _raise_for_challenge(response: httpx.Response, forum_id: str) -> None:
        try:
            body = response.json()
        except ValueError:
            return
        if body.get("name") != "ChallengeRequiredError":
            return
        challenge_url = body.get("details", {}).get("challengeUrl", "https://openreview.net")
        logger.warning("OpenReview challenge required for forum=%s: %s", forum_id, challenge_url)
        raise ValueError(
            "OpenReview richiede una verifica anti-bot per questo paper. "
            "Apri questo link nel browser, completa la verifica e riprova: "
            f"{challenge_url}"
        )
