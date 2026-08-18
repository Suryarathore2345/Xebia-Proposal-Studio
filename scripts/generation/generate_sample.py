"""Generate a sample Xebia proposal (PPT + DOCX) for testing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from generation.pptx_generator import generate_proposal_pptx
from generation.docx_generator import generate_proposal_docx


SAMPLE_PLAN = {
    "title": "Microsoft Fabric Data Platform Implementation",
    "customer": "Acme Corporation",
    "industry": "Retail",
    "proposal_type": "technical_proposal",
    "objective": "Modernize Acme's data infrastructure with Microsoft Fabric to enable real-time analytics and AI-driven insights",

    "storyline": [
        "cover",
        "table_of_contents",
        "executive_summary",
        "corporate_overview",
        "understanding_of_scope",
        "proposed_solution",
        "architecture",
        "timeline",
        "team_structure",
        "commercials",
        "next_steps",
        "closing",
    ],

    "sections": {
        "cover": {
            "title": "Microsoft Fabric Data Platform Implementation",
            "subtitle": "Modernizing Data Infrastructure for AI-Driven Retail Excellence",
            "customer": "Acme Corporation",
            "date": "August 2026",
        },

        "executive_summary": {
            "title": "Executive Summary",
            "summary": (
                "Acme Corporation seeks to modernize its legacy data warehouse by migrating "
                "to Microsoft Fabric, establishing a unified analytics platform that supports "
                "real-time reporting, advanced analytics, and AI-driven decision making. "
                "Xebia proposes a phased implementation approach that minimizes disruption "
                "while delivering early business value through priority use cases in demand "
                "forecasting, customer analytics, and supply chain optimization."
            ),
            "key_points": [
                "Full migration from legacy DW to Microsoft Fabric",
                "3-phase delivery over 16 weeks",
                "Real-time dashboards for C-suite and operations",
                "AI-ready data foundation for future ML workloads",
                "Dedicated Xebia team with 1500+ Microsoft specialists",
            ],
        },

        "corporate_overview": {
            "title": "About Xebia",
            "slides": [
                {
                    "title": "About Xebia",
                    "bullets": [
                        "Global IT consulting firm with 6,000+ professionals across 20+ countries",
                        "Leader in Data & AI services (Everest Group 2025)",
                        "1,500+ Microsoft specialists with 28 MVPs",
                        "4 Microsoft Solution Partner designations",
                        "Trusted by Tesco, Levi's, Sephora, Disney, Toyota, and 200+ enterprises",
                    ],
                }
            ],
        },

        "understanding_of_scope": {
            "title": "Understanding of Scope & Objectives",
            "slides": [
                {
                    "title": "Current Challenges",
                    "bullets": [
                        "Fragmented data across multiple legacy systems (SAP, Oracle, custom ETL)",
                        "Reporting latency of 24-48 hours impacting decision-making",
                        "Siloed analytics teams with inconsistent metrics and KPI definitions",
                        "Rising infrastructure costs with on-premises data warehouse",
                        "Limited self-service analytics capability for business users",
                    ],
                },
                {
                    "title": "Business Objectives",
                    "bullets": [
                        "Establish a single source of truth for enterprise reporting",
                        "Reduce time-to-insight from 48 hours to near real-time",
                        "Enable self-service analytics for 200+ business users",
                        "Build AI-ready data foundation for predictive analytics",
                        "Reduce total cost of ownership by 30-40%",
                    ],
                },
            ],
        },

        "proposed_solution": {
            "title": "Proposed Solution",
            "left": {
                "title": "What We Will Deliver",
                "bullets": [
                    "Microsoft Fabric workspace configuration and governance",
                    "Medallion architecture (Bronze → Silver → Gold)",
                    "Data pipeline migration from legacy ETL to Fabric",
                    "Semantic model and Power BI dashboard suite",
                    "Data governance framework and quality monitoring",
                ],
            },
            "right": {
                "title": "Key Differentiators",
                "bullets": [
                    "AI-accelerated data mapping and transformation",
                    "Pre-built retail industry data models",
                    "Automated data quality monitoring",
                    "Knowledge transfer and CoE setup",
                    "Post-implementation hypercare support",
                ],
            },
        },

        "architecture": {
            "title": "Solution Architecture",
            "slides": [
                {
                    "title": "Technical Architecture",
                    "body": "The solution follows a Medallion Architecture pattern within Microsoft Fabric:",
                    "bullets": [
                        "Bronze Layer: Raw data ingestion from SAP, Oracle, APIs via Fabric pipelines",
                        "Silver Layer: Cleaned, standardized data with business rules applied",
                        "Gold Layer: Curated semantic models optimized for reporting and analytics",
                        "OneLake: Unified data lake storage with Delta Lake format",
                        "Power BI: Executive dashboards, operational reports, self-service analytics",
                    ],
                }
            ],
        },

        "timeline": {
            "title": "Implementation Timeline",
            "phases": [
                {
                    "name": "Phase 1: Assessment & Foundation",
                    "duration": "4 weeks",
                    "description": "Environment setup, data discovery, architecture validation",
                },
                {
                    "name": "Phase 2: Core Migration",
                    "duration": "8 weeks",
                    "description": "Pipeline migration, Silver/Gold layer build, dashboard development",
                },
                {
                    "name": "Phase 3: Optimization & Handover",
                    "duration": "4 weeks",
                    "description": "Performance tuning, UAT, knowledge transfer, hypercare",
                },
            ],
        },

        "team_structure": {
            "title": "Project Team",
            "members": [
                {"name": "Sarah Chen", "role": "Engagement Director", "expertise": "15+ years in enterprise data transformation"},
                {"name": "Raj Patel", "role": "Technical Lead", "expertise": "Microsoft MVP, Fabric architecture specialist"},
                {"name": "Emma Rodriguez", "role": "Data Engineer", "expertise": "Azure, Fabric pipelines, Medallion architecture"},
                {"name": "David Kim", "role": "BI Developer", "expertise": "Power BI, semantic models, DAX optimization"},
            ],
        },

        "commercials": {
            "title": "Investment",
            "rows": [
                {"item": "Phase 1: Assessment & Foundation", "hours": "320", "rate": "$175", "cost": "$56,000"},
                {"item": "Phase 2: Core Migration", "hours": "640", "rate": "$175", "cost": "$112,000"},
                {"item": "Phase 3: Optimization & Handover", "hours": "320", "rate": "$175", "cost": "$56,000"},
                {"item": "Project Management", "hours": "160", "rate": "$200", "cost": "$32,000"},
            ],
            "total": "$256,000",
            "assumptions": [
                "Client provides timely access to source systems and data",
                "Required Microsoft Fabric licenses are procured by client",
                "Client SMEs are available for 4 hours/week during engagement",
                "Scope limited to agreed data domains; additional domains via change request",
            ],
        },

        "next_steps": {
            "title": "Next Steps",
            "bullets": [
                "Review and align on proposal scope and assumptions",
                "Schedule technical discovery workshop (2 days on-site)",
                "Finalize team availability and engagement start date",
                "Provision Microsoft Fabric environment and access",
                "Kick off Phase 1 within 2 weeks of contract signing",
            ],
        },

        "closing": {
            "title": "Let's Shape Tomorrow Together",
            "contact_name": "Sarah Chen — Engagement Director",
            "contact_email": "sarah.chen@xebia.com",
            "contact_phone": "+1 (404) 555-0142",
        },
    },
}


def main():
    output_dir = Path("outputs")

    print("Generating sample Xebia proposal...\n")

    # Generate PPT
    pptx_path = generate_proposal_pptx(SAMPLE_PLAN, output_dir / "ppt" / "sample_proposal.pptx")
    print(f"  PPT: {pptx_path}")

    # Generate DOCX
    docx_path = generate_proposal_docx(SAMPLE_PLAN, output_dir / "docx" / "sample_proposal.docx")
    print(f"  DOCX: {docx_path}")

    print("\nDone. Open the files to verify.")


if __name__ == "__main__":
    main()
