"""Technology Icon Registry — manages a local library of tech/service icons.

Provides lookup by technology name (with aliases), downloads missing icons
from known CDN sources, and returns local file paths for use in slides.

Icon sources (in priority order):
1. Pre-downloaded local library (data/tech_icons/)
2. Official vendor icon CDNs (SVG Architecture Icons from MS/AWS)
3. Simple-icons.org for general tech logos
4. Fallback: colored circle with abbreviation (no download)

Usage:
    registry = TechIconRegistry()
    path = registry.get_icon("Power BI")       # returns Path or None
    path = registry.get_icon("Amazon S3")      # returns Path or None
    abbr, color = registry.get_fallback("S3")  # ("S3", "#569A31")
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "tech_icons"
CACHED_DIR = DATA_DIR / "cached"

ICON_EXTENSIONS = (".png", ".svg", ".jpg", ".jpeg")


# ── Technology Registry ───────────────────────────────────────
# Maps canonical names to: category, abbreviation, brand_color, aliases,
# and optional icon_url for auto-download.

TECH_REGISTRY: dict[str, dict] = {
    # ── AWS Services ──
    "aws": {"cat": "aws", "abbr": "AWS", "color": "#FF9900", "aliases": ["amazon web services"]},
    "ec2": {"cat": "aws", "abbr": "EC2", "color": "#FF9900", "aliases": ["amazon ec2", "aws ec2"]},
    "lambda": {"cat": "aws", "abbr": "λ", "color": "#FF9900", "aliases": ["aws lambda", "amazon lambda"]},
    "ecs": {"cat": "aws", "abbr": "ECS", "color": "#FF9900", "aliases": ["aws ecs", "amazon ecs"]},
    "eks": {"cat": "aws", "abbr": "EKS", "color": "#FF9900", "aliases": ["aws eks"]},
    "s3": {"cat": "aws", "abbr": "S3", "color": "#569A31", "aliases": ["amazon s3", "aws s3"]},
    "rds": {"cat": "aws", "abbr": "RDS", "color": "#3B48CC", "aliases": ["amazon rds", "aws rds"]},
    "dynamodb": {"cat": "aws", "abbr": "DDB", "color": "#3B48CC", "aliases": ["amazon dynamodb", "aws dynamodb"]},
    "redshift": {"cat": "aws", "abbr": "RS", "color": "#8C4FFF", "aliases": ["amazon redshift", "aws redshift"]},
    "api_gateway": {"cat": "aws", "abbr": "API", "color": "#FF4F8B", "aliases": ["amazon api gateway", "aws api gateway", "api gateway"]},
    "sqs": {"cat": "aws", "abbr": "SQS", "color": "#FF4F8B", "aliases": ["amazon sqs", "aws sqs"]},
    "sns": {"cat": "aws", "abbr": "SNS", "color": "#FF4F8B", "aliases": ["amazon sns", "aws sns"]},
    "cloudwatch": {"cat": "aws", "abbr": "CW", "color": "#FF4F8B", "aliases": ["amazon cloudwatch", "aws cloudwatch"]},
    "iam_aws": {"cat": "aws", "abbr": "IAM", "color": "#DD344C", "aliases": ["aws iam"]},
    "glue": {"cat": "aws", "abbr": "Glu", "color": "#8C4FFF", "aliases": ["aws glue", "amazon glue"]},
    "emr": {"cat": "aws", "abbr": "EMR", "color": "#8C4FFF", "aliases": ["aws emr", "amazon emr"]},
    "kinesis": {"cat": "aws", "abbr": "KIN", "color": "#8C4FFF", "aliases": ["aws kinesis", "amazon kinesis"]},

    # ── Azure Services ──
    "azure": {"cat": "azure", "abbr": "Az", "color": "#0078D4", "aliases": ["microsoft azure"]},
    "azure_sql": {"cat": "azure", "abbr": "SQL", "color": "#0078D4", "aliases": ["azure sql database", "azure sql db"]},
    "app_services": {"cat": "azure", "abbr": "App", "color": "#0078D4", "aliases": ["azure app service", "azure app services", "app service"]},
    "aks": {"cat": "azure", "abbr": "AKS", "color": "#326CE5", "aliases": ["azure kubernetes service", "azure aks"]},
    "azure_functions": {"cat": "azure", "abbr": "Fn", "color": "#0078D4", "aliases": ["azure functions"]},
    "blob_storage": {"cat": "azure", "abbr": "Blb", "color": "#0078D4", "aliases": ["azure blob storage", "azure blob", "blob storage"]},
    "data_factory": {"cat": "azure", "abbr": "ADF", "color": "#0078D4", "aliases": ["azure data factory", "adf"]},
    "api_management": {"cat": "azure", "abbr": "APM", "color": "#0078D4", "aliases": ["azure api management", "apim"]},
    "event_hubs": {"cat": "azure", "abbr": "EH", "color": "#0078D4", "aliases": ["azure event hubs"]},
    "key_vault": {"cat": "azure", "abbr": "KV", "color": "#0078D4", "aliases": ["azure key vault"]},
    "monitor": {"cat": "azure", "abbr": "Mon", "color": "#0078D4", "aliases": ["azure monitor"]},
    "entra_id": {"cat": "azure", "abbr": "Ent", "color": "#0078D4", "aliases": ["azure entra id", "azure ad", "azure active directory", "entra"]},
    "cosmos_db": {"cat": "azure", "abbr": "CDB", "color": "#0078D4", "aliases": ["azure cosmos db", "cosmos db", "cosmosdb"]},
    "synapse": {"cat": "azure", "abbr": "Syn", "color": "#0078D4", "aliases": ["azure synapse", "azure synapse analytics", "synapse analytics"]},
    "azure_devops": {"cat": "azure", "abbr": "ADO", "color": "#0078D4", "aliases": ["azure devops"]},
    "virtual_network": {"cat": "azure", "abbr": "VN", "color": "#0078D4", "aliases": ["azure vnet", "vnet", "virtual network"]},

    # ── Microsoft Fabric ──
    "fabric": {"cat": "microsoft", "abbr": "Fab", "color": "#117865", "aliases": ["microsoft fabric", "ms fabric"]},
    "onelake": {"cat": "microsoft", "abbr": "OL", "color": "#117865", "aliases": ["one lake"]},
    "lakehouse": {"cat": "microsoft", "abbr": "LH", "color": "#117865", "aliases": ["fabric lakehouse"]},
    "power_bi": {"cat": "microsoft", "abbr": "PBI", "color": "#F2C811", "aliases": ["power bi", "powerbi", "pbi"]},
    "data_warehouse_fabric": {"cat": "microsoft", "abbr": "DW", "color": "#117865", "aliases": ["fabric data warehouse", "fabric warehouse"]},
    "semantic_model": {"cat": "microsoft", "abbr": "SM", "color": "#117865", "aliases": ["semantic models", "fabric semantic model"]},
    "notebooks_fabric": {"cat": "microsoft", "abbr": "NB", "color": "#117865", "aliases": ["fabric notebooks", "fabric notebook"]},
    "real_time_intelligence": {"cat": "microsoft", "abbr": "RTI", "color": "#117865", "aliases": ["real-time intelligence", "fabric real-time"]},

    # ── General Technologies ──
    "databricks": {"cat": "general", "abbr": "DBX", "color": "#FF3621", "aliases": ["azure databricks"]},
    "spark": {"cat": "general", "abbr": "Spk", "color": "#E25A1C", "aliases": ["apache spark"]},
    "kafka": {"cat": "general", "abbr": "Kfk", "color": "#231F20", "aliases": ["apache kafka"]},
    "kubernetes": {"cat": "general", "abbr": "K8s", "color": "#326CE5", "aliases": ["k8s"]},
    "docker": {"cat": "general", "abbr": "Dkr", "color": "#2496ED", "aliases": ["containers"]},
    "terraform": {"cat": "general", "abbr": "TF", "color": "#7B42BC", "aliases": ["hashicorp terraform"]},
    "python": {"cat": "general", "abbr": "Py", "color": "#3776AB", "aliases": []},
    "sql_server": {"cat": "general", "abbr": "SQL", "color": "#CC2927", "aliases": ["microsoft sql server", "mssql"]},
    "postgresql": {"cat": "general", "abbr": "PG", "color": "#336791", "aliases": ["postgres"]},
    "mongodb": {"cat": "general", "abbr": "MDB", "color": "#47A248", "aliases": ["mongo"]},
    "snowflake": {"cat": "general", "abbr": "SF", "color": "#29B5E8", "aliases": []},
    "tableau": {"cat": "general", "abbr": "Tab", "color": "#E97627", "aliases": []},
    "git": {"cat": "general", "abbr": "Git", "color": "#F05032", "aliases": ["github", "gitlab"]},
    "jenkins": {"cat": "general", "abbr": "Jen", "color": "#D24939", "aliases": []},
    "elasticsearch": {"cat": "general", "abbr": "ES", "color": "#005571", "aliases": ["elastic"]},
    "redis": {"cat": "general", "abbr": "Red", "color": "#DC382D", "aliases": []},
    "nginx": {"cat": "general", "abbr": "Ngx", "color": "#009639", "aliases": []},
    "airflow": {"cat": "general", "abbr": "AF", "color": "#017CEE", "aliases": ["apache airflow"]},
    "dbt": {"cat": "general", "abbr": "dbt", "color": "#FF694B", "aliases": []},
}

_NAME_INDEX: dict[str, str] | None = None


def _build_name_index() -> dict[str, str]:
    global _NAME_INDEX
    if _NAME_INDEX is not None:
        return _NAME_INDEX

    index: dict[str, str] = {}
    for canonical, info in TECH_REGISTRY.items():
        norm = _normalize(canonical)
        index[norm] = canonical
        for alias in info.get("aliases", []):
            index[_normalize(alias)] = canonical
    _NAME_INDEX = index
    return index


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


class TechIconRegistry:
    """Manages technology icon lookup and caching."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR
        self.cached_dir = self.data_dir / "cached"
        self.cached_dir.mkdir(parents=True, exist_ok=True)
        self._index = _build_name_index()

    def resolve(self, name: str) -> str | None:
        """Resolve a technology name to its canonical registry key."""
        norm = _normalize(name)
        return self._index.get(norm)

    def get_icon(self, name: str) -> Path | None:
        """Get icon file path for a technology. Returns None if not found."""
        canonical = self.resolve(name)
        if not canonical:
            return None

        info = TECH_REGISTRY.get(canonical)
        if not info:
            return None

        local = self._find_local(canonical, info["cat"])
        if local:
            return local

        return None

    def get_fallback(self, name: str) -> tuple[str, str]:
        """Get abbreviation and brand color for a text-based icon fallback."""
        canonical = self.resolve(name)
        if canonical and canonical in TECH_REGISTRY:
            info = TECH_REGISTRY[canonical]
            return info["abbr"], info["color"]

        words = name.strip().split()
        if len(words) == 1:
            abbr = words[0][:3].upper()
        else:
            abbr = "".join(w[0] for w in words[:3]).upper()
        return abbr, "#6C1D5F"

    def get_icon_or_fallback(self, name: str) -> tuple[Path | None, str, str]:
        """Return (icon_path, abbreviation, brand_color).

        icon_path is None if no icon file exists — caller should use
        abbr + color to render a text-based placeholder.
        """
        icon = self.get_icon(name)
        abbr, color = self.get_fallback(name)
        return icon, abbr, color

    def list_available(self) -> list[str]:
        """List all technologies that have local icon files."""
        available = []
        for canonical, info in TECH_REGISTRY.items():
            if self._find_local(canonical, info["cat"]):
                available.append(canonical)
        return available

    def _find_local(self, canonical: str, category: str) -> Path | None:
        """Search for an icon in the local library."""
        search_dirs = [
            self.data_dir / category,
            self.cached_dir,
            self.data_dir,
        ]

        for d in search_dirs:
            if not d.exists():
                continue
            for ext in ICON_EXTENSIONS:
                candidate = d / f"{canonical}{ext}"
                if candidate.exists():
                    return candidate
        return None

    def download_icon(self, name: str, url: str) -> Path | None:
        """Download an icon from a URL and cache it locally."""
        canonical = self.resolve(name)
        if not canonical:
            canonical = _normalize(name)

        ext = Path(url).suffix.lower()
        if ext not in ICON_EXTENSIONS:
            ext = ".png"

        target = self.cached_dir / f"{canonical}{ext}"
        if target.exists():
            return target

        try:
            req = Request(url, headers={"User-Agent": "XebiaProposalStudio/1.0"})
            with urlopen(req, timeout=10) as resp:
                data = resp.read()
                if len(data) < 100:
                    return None
                target.write_bytes(data)
                return target
        except (URLError, OSError):
            return None
