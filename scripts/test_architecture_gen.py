"""Test script for AI-driven architecture diagram generation.

Calls the architecture content generator with a user prompt,
then renders the result as a migration flow diagram in a PPTX.

Usage:
    python scripts/test_architecture_gen.py
    python scripts/test_architecture_gen.py --static   # skip LLM, use hardcoded data
"""

import sys
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pptx import Presentation
from generation.design_generator import DesignPalette, SlideStyle
from generation.slide_builders import build_migration_flow_slide
from generation.template_engine import TEMPLATES_DIR


OUTPUT_DIR = ROOT / "outputs" / "ppt"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _default_style() -> SlideStyle:
    palette = DesignPalette(
        primary="#6C1D5F", secondary="#5A1750", accent1="#7A2A7B",
        accent2="#9B3F9B", accent3="#B75EB7",
        bg_light="#FFFFFF", bg_dark="#1A1A1A", bg_warm="#F5EFF5",
        bg_card="#FAFAFA", text_dark="#222222", text_medium="#595959",
        text_light="#FFFFFF",
    )
    return SlideStyle(
        heading_font="Arial", body_font="Arial",
        composition="none", accent_color="#6C1D5F",
        card_style="flat_bordered", title_color="#222222",
        body_color="#595959", card_bg="#FAFAFA",
        border_color="#EAEAEA", palette=palette,
    )


STATIC_DIAGRAM = {
    "title": "AWS to Azure & Microsoft Fabric Migration Architecture",
    "zones": [
        {
            "id": "aws_current",
            "title": "AWS — Current State",
            "color": "orange",
            "width_ratio": 1.0,
            "groups": [
                {"label": "Business Applications", "items": ["Custom Web Apps", "CRM", "ERP"]},
                {"label": "Compute & Services", "items": ["EC2", "Lambda", "ECS"], "style": "icons"},
                {"label": "Databases & Storage", "items": ["RDS", "DynamoDB", "S3", "Redshift"], "style": "icons"},
                {"label": "Integration & APIs", "items": ["API Gateway", "SQS", "SNS"], "style": "icons"},
            ],
        },
        {
            "id": "migration",
            "title": "Migration & Modernization",
            "color": "teal",
            "width_ratio": 0.85,
            "groups": [
                {"label": "Discovery & Assessment", "items": ["App Assessment", "Dependency Mapping", "Migration Planning"]},
                {"label": "Migration Execution", "items": ["App Migration", "DB Migration", "Data Integration"]},
                {"label": "Strategy", "items": ["Rehost", "Replatform", "Refactor", "Modernize"], "style": "flow"},
                {"label": "Validation & Cutover", "items": ["Testing", "Security Review", "Cutover", "Optimization"]},
            ],
        },
        {
            "id": "azure_foundation",
            "title": "Azure — Cloud Foundation",
            "color": "blue",
            "width_ratio": 1.1,
            "groups": [
                {"label": "Landing Zone", "items": ["Subscriptions", "Networking", "Identity", "Governance"]},
                {"label": "Application Platform", "items": ["App Services", "AKS", "API Management"], "style": "icons"},
                {"label": "Data Platform", "items": ["Azure SQL", "Blob Storage", "Data Factory"], "style": "icons"},
            ],
        },
        {
            "id": "fabric_analytics",
            "title": "Microsoft Fabric",
            "color": "purple",
            "width_ratio": 1.1,
            "groups": [
                {"label": "Data Integration", "items": ["Data Factory", "OneLake", "Lakehouse"], "style": "icons"},
                {"label": "Analytics & Processing", "items": [
                    {"name": "Data Warehouse", "qualifier": "Bronze/Silver/Gold medallion"},
                    "Notebooks", "Spark",
                ], "style": "icons"},
                {"label": "Business Intelligence", "items": ["Semantic Models", "Power BI", "Real-Time Intel"], "style": "icons"},
            ],
        },
        {
            "id": "outcomes",
            "title": "Business Outcomes",
            "color": "green",
            "width_ratio": 0.55,
            "groups": [
                {"label": "Unified Analytics", "items": ["Single Pane of Glass", "Self-Service BI"]},
                {"label": "Business Value", "items": ["Cost Optimization", "Data-Driven Decisions", "Faster Insights"]},
            ],
        },
    ],
    "bottom_bands": [
        {
            "label": "Governance",
            "items": ["Purview", "Data Catalog", "Compliance"],
            "color": "dark",
        },
        {
            "label": "Platform & Security",
            "items": ["Entra ID", "Key Vault", "Azure Monitor", "Azure DevOps", "Cost Management"],
            "color": "dark",
        },
    ],
    "journey_labels": [
        {"label": "Cloud Transformation", "from_zone_index": 0, "to_zone_index": 2},
        {"label": "Data & Analytics Transformation", "from_zone_index": 2, "to_zone_index": 4},
    ],
    "legend": [
        {"symbol": "dashed", "label": "Subscription boundary"},
        {"symbol": "arrow", "label": "Data flow"},
    ],
}


# Landing-zone / hub-spoke archetype fixture — exercises the nested
# boundary_type/children/divider schema (Phase 3), which the AWS→Fabric
# STATIC_DIAGRAM above deliberately does not use. Modeled on the pattern
# found in MOHESR slide 15 / PNB MetLife slide 19: on-prem sources,
# separated by a dashed divider from an Azure subscription boundary that
# contains nested VNet boundaries, each containing the actual workloads.
LANDING_ZONE_DIAGRAM = {
    "title": "Reference Azure Landing Zone Architecture",
    "zones": [
        {
            "id": "onprem",
            "title": "On-Premises",
            "color": "orange",
            "width_ratio": 0.55,
            "groups": [
                {"label": "Source Systems", "items": ["SQL Server", "SAP ECC"], "style": "icons"},
            ],
        },
        {
            "id": "azure_landing_zone",
            "title": "Azure Subscription — Enterprise-Scale Landing Zone",
            "color": "blue",
            "width_ratio": 2.4,
            "boundary_type": "subscription",
            "children": [
                {
                    "id": "connectivity_sub",
                    "title": "Connectivity",
                    "color": "blue",
                    "width_ratio": 1.0,
                    "boundary_type": "vnet",
                    "children": [
                        {
                            "id": "hub_vnet",
                            "title": "Hub VNet",
                            "color": "blue",
                            "width_ratio": 1.0,
                            "groups": [
                                {"label": "Shared Services", "items": ["Azure Firewall", "VPN Gateway", "Bastion"], "style": "icons"},
                            ],
                        },
                    ],
                },
                {
                    "id": "identity_sub",
                    "title": "Identity",
                    "color": "blue",
                    "width_ratio": 0.8,
                    "groups": [
                        {"label": "Identity", "items": ["Entra ID", "Domain Controllers"], "style": "icons"},
                    ],
                },
                {
                    "id": "landing_zone_sub",
                    "title": "Landing Zone",
                    "color": "purple",
                    "width_ratio": 1.3,
                    "boundary_type": "vnet",
                    "children": [
                        {
                            "id": "workload_vnet",
                            "title": "Workload VNet",
                            "color": "purple",
                            "width_ratio": 1.0,
                            "groups": [
                                {"label": "Workloads", "items": ["Azure Databricks", "ADLS Gen2", "AKS"], "style": "icons"},
                            ],
                        },
                    ],
                },
            ],
        },
        {
            "id": "consumption",
            "title": "Consumption",
            "color": "green",
            "width_ratio": 0.55,
            "groups": [
                {"label": "BI", "items": ["Power BI"], "style": "icons"},
            ],
        },
    ],
    "bottom_bands": [
        {"label": "Governance", "items": ["Purview", "Azure Policy"], "color": "dark"},
    ],
    "divider": {"position_after_zone": 0, "label": "On-prem | Azure"},
    "legend": [
        {"symbol": "dashed", "label": "Subscription/VNet boundary"},
        {"symbol": "arrow", "label": "Data flow"},
    ],
}


USER_PROMPT = """Create a professional, client-facing AWS-to-Azure and Microsoft Fabric Migration & Modernization Architecture for an enterprise proposal.

The objective is to visually communicate how the client's existing AWS environment will be migrated and modernized on Azure, with Microsoft Fabric as the strategic data and analytics platform.

The architecture should focus on the overall solution and business story rather than low-level infrastructure implementation.

1. AWS — Current Environment: Show the major existing AWS capabilities grouped into Business Applications, Compute & Application Services, Databases & Data Sources, Object/File Storage, APIs & Integrations.

2. Migration & Modernization Layer: Show Discovery & Assessment, Migration Planning, Application & Database Migration, Data Integration & Transformation, Testing & Validation, Security & Governance, Cutover & Optimization. Include migration strategies: Rehost → Replatform → Refactor → Modernize.

3. Azure — Target Cloud Platform: Show Azure Landing Zone (Subscriptions, Networking, Identity, Governance), Application Platform (App Services, Compute, APIs, Containers), Data Platform (Azure databases, Storage, Data integration).

4. Microsoft Fabric — Data & Analytics Platform: Show Data Factory / Data Integration, OneLake, Lakehouse, Data Warehouse, Notebooks / Data Engineering, Semantic Models, Power BI, Governance & Security. Represent the data flow: Data Sources → Ingestion → OneLake → Transformation → Analytics → Semantic Model → Power BI.

5. Business Outcomes: Unified Analytics, Business Insights, Cost Optimization.

Structure left to right: AWS → Migration → Azure → Fabric → Business Outcomes.

Show two transformation journeys:
- Cloud Transformation: AWS → Azure
- Data & Analytics Transformation: Azure Data → Microsoft Fabric → Power BI & Business Insights

The final story: "We migrate the existing AWS estate to a secure Azure foundation, modernize the data platform using Microsoft Fabric, and enable unified analytics and business insights through Power BI."
"""


def run_static():
    print("Using static diagram data (no LLM call)...")
    return STATIC_DIAGRAM


def run_landing_zone():
    print("Using static landing-zone diagram data (no LLM call)...")
    return LANDING_ZONE_DIAGRAM


def run_ai():
    print("Generating architecture diagram via Claude...")
    from generation.architecture_generator import generate_architecture_diagram
    result = generate_architecture_diagram(USER_PROMPT)
    print("\nGenerated diagram JSON:")
    print(json.dumps(result, indent=2))
    return result


def render_pptx(diagram_data: dict, suffix: str = ""):
    template_path = TEMPLATES_DIR / "xebia_retail.pptx"
    prs = Presentation(str(template_path))
    style = _default_style()

    title = diagram_data.get("title", "Solution Architecture")
    build_migration_flow_slide(prs, style, title=title,
                               diagram=diagram_data, slide_number=1)

    import time
    ts = int(time.time())
    filename = f"test_migration_architecture{suffix}_{ts}.pptx"
    output_path = OUTPUT_DIR / filename
    prs.save(str(output_path))
    print(f"\nSaved: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--static", action="store_true",
                        help="Use hardcoded data instead of calling Claude")
    parser.add_argument("--landing-zone", action="store_true",
                        help="Use the static nested landing-zone/hub-spoke fixture")
    args = parser.parse_args()

    if args.landing_zone:
        diagram = run_landing_zone()
        path = render_pptx(diagram, "_landing_zone")
    elif args.static:
        diagram = run_static()
        path = render_pptx(diagram, "_static")
    else:
        diagram = run_ai()
        path = render_pptx(diagram, "_ai")

    print(f"\nDone! Open {path} in PowerPoint to review.")


if __name__ == "__main__":
    main()
