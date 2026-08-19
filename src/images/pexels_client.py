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


TECH_KEYWORDS = {
    "azure": "microsoft azure cloud platform",
    "aws": "amazon web services cloud",
    "gcp": "google cloud platform",
    "databricks": "databricks data analytics platform",
    "snowflake": "snowflake data warehouse cloud",
    "kubernetes": "kubernetes container orchestration",
    "docker": "docker container technology",
    "terraform": "terraform infrastructure code",
    "python": "python programming code",
    "java": "java programming technology",
    "react": "react frontend development",
    "sql server": "microsoft sql server database",
    "postgresql": "postgresql database server",
    "mongodb": "mongodb nosql database",
    "kafka": "apache kafka streaming data",
    "spark": "apache spark big data processing",
    "tableau": "tableau data visualization dashboard",
    "power bi": "power bi analytics dashboard",
    "fabric": "microsoft fabric data analytics",
    "synapse": "azure synapse analytics",
    "machine learning": "machine learning artificial intelligence",
    "deep learning": "deep learning neural network",
    "devops": "devops ci cd pipeline",
    "microservices": "microservices architecture",
    "api": "api integration technology",
    "blockchain": "blockchain technology",
    "iot": "internet of things sensors",
    "cybersecurity": "cybersecurity network protection",
    "data lake": "data lake storage architecture",
    "etl": "etl data pipeline integration",
    "data warehouse": "data warehouse analytics",
    "cloud migration": "cloud migration infrastructure",
    "agile": "agile scrum team methodology",
    "ai": "artificial intelligence technology",
}


def _enhance_tech_query(query: str) -> str:
    """Detect tech terms in the query and use specific search terms."""
    query_lower = query.lower()
    for tech, search_term in TECH_KEYWORDS.items():
        if tech in query_lower:
            return search_term
    return query


def fetch_slide_image(query: str, slide_type: str = "content") -> str | None:
    """Fetch an image appropriate for a slide type.

    Detects technology/platform names and searches for their specific imagery.
    Falls back to context-enhanced general queries.
    """
    enhanced = _enhance_tech_query(query)
    if enhanced != query:
        result = search_image(enhanced, orientation="landscape")
        if result:
            return result

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
