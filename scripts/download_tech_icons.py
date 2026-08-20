"""Download official technology icons (PNG) for the architecture diagram library.

Downloads pre-rendered PNG icons from community GitHub repos that
host official AWS/Azure/Fabric architecture icons.

Sources:
  - Azure: nicolaparo/azure-icons (official icons pre-rendered to PNG)
  - Azure (fallback): benc-uk/icon-collection (SVG)
  - AWS: awslabs/aws-icons-for-plantuml (official AWS icons as PNG)
  - Fabric/General: various official sources

Usage:
    python scripts/download_tech_icons.py
    python scripts/download_tech_icons.py --category aws
    python scripts/download_tech_icons.py --list
"""

import sys
import argparse
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

ICONS_DIR = ROOT / "data" / "tech_icons"

try:
    from PIL import Image
    import io as _io
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


# ── URL Bases ─────────────────────────────────────────────────

AZURE_PNG = "https://raw.githubusercontent.com/nicolaparo/azure-icons/main"
AWS_PLANTUML = "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist"
PBI_ICONS = "https://raw.githubusercontent.com/marclelijveld/Power-BI-Icons/master/PNG"

# ── Icon Download Registry ────────────────────────────────────
# Each entry: canonical_name → {dir, urls: [url1, url2, ...]}
# URLs tried in order; first successful download wins.

ICON_SOURCES: dict[str, dict] = {
    # ── AWS Services (from awslabs/aws-icons-for-plantuml PNG dist) ──
    "ec2": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/Compute/EC2.png",
        ],
    },
    "lambda": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/Compute/Lambda.png",
        ],
    },
    "ecs": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/Containers/ElasticContainerService.png",
        ],
    },
    "eks": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/Containers/ElasticKubernetesService.png",
        ],
    },
    "s3": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/Storage/SimpleStorageService.png",
        ],
    },
    "rds": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/Database/RDS.png",
        ],
    },
    "dynamodb": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/Database/DynamoDB.png",
        ],
    },
    "redshift": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/Analytics/Redshift.png",
        ],
    },
    "api_gateway": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/NetworkingContentDelivery/APIGateway.png",
        ],
    },
    "sqs": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/ApplicationIntegration/SimpleQueueService.png",
        ],
    },
    "sns": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/ApplicationIntegration/SimpleNotificationService.png",
        ],
    },
    "cloudwatch": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/ManagementGovernance/CloudWatch.png",
        ],
    },
    "iam_aws": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/SecurityIdentityCompliance/IdentityandAccessManagement.png",
        ],
    },
    "glue": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/Analytics/Glue.png",
        ],
    },
    "emr": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/Analytics/EMR.png",
        ],
    },
    "kinesis": {
        "dir": "aws",
        "urls": [
            f"{AWS_PLANTUML}/Analytics/Kinesis.png",
        ],
    },

    # ── Azure Services (from nicolaparo/azure-icons PNG repo) ──
    "azure": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-azure.png",
            f"{AZURE_PNG}/64/icon-azure.png",
        ],
    },
    "azure_sql": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-azure-sql.png",
            f"{AZURE_PNG}/256/icon-sql-database.png",
            f"{AZURE_PNG}/64/icon-azure-sql.png",
        ],
    },
    "app_services": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-app-services.png",
            f"{AZURE_PNG}/64/icon-app-services.png",
        ],
    },
    "aks": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-kubernetes-services.png",
            f"{AZURE_PNG}/256/icon-azure-kubernetes-service-(aks).png",
            f"{AZURE_PNG}/64/icon-kubernetes-services.png",
        ],
    },
    "azure_functions": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-function-apps.png",
            f"{AZURE_PNG}/64/icon-function-apps.png",
        ],
    },
    "blob_storage": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-storage-accounts.png",
            f"{AZURE_PNG}/256/icon-blob-block.png",
            f"{AZURE_PNG}/64/icon-storage-accounts.png",
        ],
    },
    "data_factory": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-data-factory.png",
            f"{AZURE_PNG}/64/icon-data-factory.png",
        ],
    },
    "api_management": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-api-management-services.png",
            f"{AZURE_PNG}/64/icon-api-management-services.png",
        ],
    },
    "event_hubs": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-event-hubs.png",
            f"{AZURE_PNG}/64/icon-event-hubs.png",
        ],
    },
    "key_vault": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-key-vaults.png",
            f"{AZURE_PNG}/64/icon-key-vaults.png",
        ],
    },
    "monitor": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-azure-monitor.png",
            f"{AZURE_PNG}/256/icon-monitor.png",
            f"{AZURE_PNG}/64/icon-azure-monitor.png",
        ],
    },
    "entra_id": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-entra-id.png",
            f"{AZURE_PNG}/256/icon-azure-active-directory.png",
            f"{AZURE_PNG}/64/icon-azure-active-directory.png",
        ],
    },
    "cosmos_db": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-azure-cosmos-db.png",
            f"{AZURE_PNG}/64/icon-azure-cosmos-db.png",
        ],
    },
    "synapse": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-azure-synapse-analytics.png",
            f"{AZURE_PNG}/64/icon-azure-synapse-analytics.png",
        ],
    },
    "azure_devops": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-azure-devops.png",
            f"{AZURE_PNG}/64/icon-azure-devops.png",
        ],
    },
    "virtual_network": {
        "dir": "azure",
        "urls": [
            f"{AZURE_PNG}/256/icon-virtual-networks.png",
            f"{AZURE_PNG}/64/icon-virtual-networks.png",
        ],
    },

    # ── Microsoft / Fabric / Power BI ──
    "power_bi": {
        "dir": "microsoft",
        "urls": [
            f"{AZURE_PNG}/256/icon-power-bi.png",
            f"{AZURE_PNG}/256/icon-power-bi-embedded.png",
            f"{AZURE_PNG}/64/icon-power-bi-embedded.png",
            f"{PBI_ICONS}/Power-BI.png",
        ],
    },
    "fabric": {
        "dir": "microsoft",
        "urls": [
            f"{AZURE_PNG}/256/icon-microsoft-fabric.png",
            f"{AZURE_PNG}/64/icon-microsoft-fabric.png",
        ],
    },

    # ── General Technologies ──
    "databricks": {
        "dir": "general",
        "urls": [
            f"{AZURE_PNG}/256/icon-azure-databricks.png",
            f"{AZURE_PNG}/64/icon-azure-databricks.png",
        ],
    },
    "kubernetes": {
        "dir": "general",
        "urls": [
            f"{AZURE_PNG}/256/icon-kubernetes-services.png",
        ],
    },
    "sql_server": {
        "dir": "general",
        "urls": [
            f"{AZURE_PNG}/256/icon-azure-sql-vm.png",
            f"{AZURE_PNG}/64/icon-azure-sql-vm.png",
        ],
    },
}


def _download(url: str, timeout: int = 15) -> bytes | None:
    try:
        req = Request(url, headers={"User-Agent": "XebiaProposalStudio/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = resp.read()
                if len(data) > 100:
                    return data
    except (URLError, HTTPError, OSError):
        pass
    return None


def _ensure_square_png(path: Path, size: int):
    """Resize/pad PNG to square with transparent background."""
    if not HAS_PILLOW:
        return
    try:
        img = Image.open(path)
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        w, h = img.size
        max_dim = max(w, h)
        if w != h:
            square = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))
            square.paste(img, ((max_dim - w) // 2, (max_dim - h) // 2))
            img = square

        if img.size[0] != size:
            img = img.resize((size, size), Image.LANCZOS)

        img.save(path, "PNG")
    except Exception:
        pass


def download_icon(name: str, source: dict, icon_size: int = 128) -> bool:
    category_dir = ICONS_DIR / source["dir"]
    category_dir.mkdir(parents=True, exist_ok=True)

    png_path = category_dir / f"{name}.png"
    if png_path.exists() and png_path.stat().st_size > 100:
        print(f"  {name}: already exists, skipping")
        return True

    for url in source["urls"]:
        filename = url.split("/")[-1]
        print(f"  {name}: trying {filename}...")

        data = _download(url)
        if data is None:
            continue

        png_path.write_bytes(data)
        _ensure_square_png(png_path, icon_size)

        final_size = png_path.stat().st_size
        print(f"  {name}: OK ({final_size:,} bytes)")
        return True

    print(f"  {name}: FAILED (all URLs returned 404)")
    return False


def download_category(category: str | None = None, icon_size: int = 128):
    sources = ICON_SOURCES
    if category:
        sources = {k: v for k, v in sources.items() if v["dir"] == category}

    total = len(sources)
    success = 0
    failed = []

    print(f"\nDownloading {total} icons to {ICONS_DIR}...\n")

    for name, source in sources.items():
        if download_icon(name, source, icon_size):
            success += 1
        else:
            failed.append(name)

    print(f"\n{'='*50}")
    print(f"Results: {success}/{total} icons downloaded successfully")
    if failed:
        print(f"Failed: {', '.join(failed)}")
    print(f"Icon library: {ICONS_DIR}")


def list_icons():
    print("\nRegistered icons:")
    for cat in ["aws", "azure", "microsoft", "general"]:
        icons = [k for k, v in ICON_SOURCES.items() if v["dir"] == cat]
        if icons:
            print(f"\n  {cat.upper()} ({len(icons)}): {', '.join(icons)}")

    print(f"\nLocal icon files:")
    total = 0
    for cat_dir in sorted(ICONS_DIR.iterdir()):
        if cat_dir.is_dir():
            pngs = list(cat_dir.glob("*.png"))
            svgs = list(cat_dir.glob("*.svg"))
            files = pngs + svgs
            if files:
                total += len(files)
                names = sorted(f.stem for f in files)
                print(f"  {cat_dir.name}/ ({len(files)} files): {', '.join(names)}")
    print(f"\nTotal local icons: {total}")


def main():
    parser = argparse.ArgumentParser(description="Download technology icons")
    parser.add_argument("--category", choices=["aws", "azure", "microsoft", "general"],
                        help="Download only this category")
    parser.add_argument("--list", action="store_true", help="List registered and local icons")
    parser.add_argument("--size", type=int, default=128,
                        help="Icon size in pixels (default: 128)")
    args = parser.parse_args()

    if args.list:
        list_icons()
        return

    download_category(args.category, args.size)


if __name__ == "__main__":
    main()
