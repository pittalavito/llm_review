import logging

import httpx

logger = logging.getLogger(__name__)

_BASE_V1 = "https://api.openreview.net"
_BASE_V2 = "https://api2.openreview.net"


class OpenReviewClient:

    def fetch_notes(self, forum_id: str, api_version: str) -> list[dict]:
        base = _BASE_V2 if api_version == "v2" else _BASE_V1
        url = f"{base}/notes"
        params = {"forum": forum_id, "limit": 1000}
        logger.info("Fetching OpenReview notes forum=%s api=%s", forum_id, api_version)
        response = httpx.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json().get("notes", [])
