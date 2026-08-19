"""Pexels API client for fetching stock images for proposal slides."""

import os
import hashlib
import urllib.request
import urllib.parse
import json
from pathlib import Path


_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "image_cache"
_API_BASE = "https://api.pexels.com/v1"


def _get_api_key() -> str | None:
    key = os.environ.get("PEXELS_API_KEY")
    if key:
        return key
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "PEXELS_API_KEY":
                    return v.strip()
    return None


def _cache_path(query: str, orientation: str) -> Path:
    slug = hashlib.md5(f"{query}:{orientation}".encode()).hexdigest()
    return _CACHE_DIR / f"{slug}.jpg"


def search_image(query: str, orientation: str = "landscape") -> str | None:
    """Search Pexels for an image and return a local file path.

    Returns None if the API key is missing or the request fails.
    Results are cached to avoid redundant API calls.
    """
    cached = _cache_path(query, orientation)
    if cached.exists():
        return str(cached)

    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        params = urllib.parse.urlencode({
            "query": query,
            "orientation": orientation,
            "per_page": 1,
            "size": "medium",
        })
        url = f"{_API_BASE}/search?{params}"
        headers = {
            "Authorization": api_key,
            "User-Agent": "XebiaProposalStudio/1.0",
        }

        data = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())
                break
            except Exception:
                if attempt == 2:
                    return None
                import time
                time.sleep(1)

        photos = data.get("photos", [])
        if not photos:
            return None

        img_url = photos[0]["src"]["medium"]

        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        dl_req = urllib.request.Request(img_url, headers={"User-Agent": "XebiaProposalStudio/1.0"})
        with urllib.request.urlopen(dl_req, timeout=15) as resp:
            cached.write_bytes(resp.read())
        return str(cached)

    except Exception:
        return None


def fetch_slide_image(query: str, slide_type: str = "content") -> str | None:
    """Fetch an image appropriate for a slide type.

    Appends context keywords to improve search relevance.
    """
    context_map = {
        "cover": "business technology professional",
        "section_divider": "abstract corporate",
        "architecture": "technology network infrastructure",
        "timeline": "planning roadmap strategy",
        "team": "professional team collaboration",
        "closing": "partnership handshake success",
        "content": "business corporate",
    }
    context = context_map.get(slide_type, "business corporate")
    full_query = f"{query} {context}"
    return search_image(full_query, orientation="landscape")
