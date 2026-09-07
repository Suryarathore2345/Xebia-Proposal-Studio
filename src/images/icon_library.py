"""Technology Icon Library — central asset resolver for the proposal system.

Manages a large local library of technology/service/platform icons with
alias-based lookup, automatic fallback to colored abbreviation circles,
and support for progressive enrichment (new icons added over time).

The library reads from ``assets/icons/registry.json`` which maps every
known technology to its canonical metadata and local file path.

Usage::

    lib = IconLibrary()
    path = lib.get_icon("Amazon EC2")        # Path | None
    path = lib.get_icon("postgresql")        # Path | None
    abbr, color = lib.get_fallback("Kafka")  # ("Kfk", "#231F20")
    icon, abbr, color = lib.resolve("S3")    # (Path|None, "S3", "#569A31")
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS_DIR = ROOT / "assets" / "icons"
REGISTRY_PATH = ASSETS_DIR / "registry.json"

ICON_EXTENSIONS = (".png", ".svg", ".jpg", ".jpeg")

_NORMALIZE_RE = re.compile(r"[^a-z0-9]")


def _normalize(name: str) -> str:
    return _NORMALIZE_RE.sub("", name.lower())


class IconLibrary:
    """Resolve technology names to local icon files."""

    def __init__(self, assets_dir: Path | None = None):
        self.assets_dir = assets_dir or ASSETS_DIR
        self._registry: list[dict] = []
        self._index: dict[str, dict] = {}
        self._load_registry()

    def _load_registry(self):
        reg_path = self.assets_dir / "registry.json"
        if not reg_path.exists():
            return
        try:
            data = json.loads(reg_path.read_text(encoding="utf-8"))
            self._registry = data.get("icons", [])
        except (json.JSONDecodeError, OSError):
            self._registry = []

        self._index.clear()
        for entry in self._registry:
            eid = entry.get("id", "")
            norm_id = _normalize(eid)
            self._index[norm_id] = entry

            for alias in entry.get("aliases", []):
                self._index[_normalize(alias)] = entry

            tech_name = entry.get("technology", "")
            if tech_name:
                self._index[_normalize(tech_name)] = entry

            display = entry.get("display_name", "")
            if display and display != tech_name:
                self._index[_normalize(display)] = entry

            abbr = entry.get("abbreviation", "")
            if abbr:
                norm_abbr = _normalize(abbr)
                if norm_abbr not in self._index:
                    self._index[norm_abbr] = entry

        self._apply_short_aliases()

    _SHORT_ALIASES: dict[str, str] = {
        "ec2": "aws_e_c2",
        "s3": "aws_simple_storage_service",
        "ecs": "aws_elastic_container_service",
        "eks": "aws_elastic_kubernetes_service",
        "ecr": "aws_elastic_container_registry",
        "rds": "aws_r_d_s",
        "sqs": "aws_simple_queue_service",
        "sns": "aws_simple_notification_service",
        "iam": "aws_identity_and_access_management",
        "vpc": "aws_virtual_private_cloud",
        "elb": "aws_elastic_load_balancing",
        "efs": "aws_e_f_s",
        "ebs": "aws_elastic_block_store",
        "emr": "aws_e_m_r",
        "msk": "aws_managed_streaming_for_apache_kafka",
        "dms": "aws_database_migration_service",
        "waf": "aws_w_a_f",
        "kms": "aws_key_management_service",
        "ses": "aws_simple_email_service",
        "mq": "aws_m_q",
        "aks": "az_kubernetes_services",
        "acr": "az_container_registries",
        "apim": "az_api_management_services",
        "api management": "az_api_management_services",
        "app services": "az_app_services",
        "app service": "az_app_services",
        "azure sql": "az_azure_sql",
        "blob storage": "az_blob_block",
        "azure functions": "az_function_apps",
        "cosmos db": "az_azure_cosmos_db",
        "cosmosdb": "az_azure_cosmos_db",
        "event hubs": "az_event_hubs",
        "key vault": "az_key_vaults",
        "service bus": "az_service_bus",
        "azure monitor": "az_monitor",
        "entra id": "az_entra_id",
        "azure devops": "az_azure_devops",
        "azure sentinel": "az_azure_sentinel",
        "microsoft sentinel": "az_microsoft_sentinel",
        "virtual network": "az_virtual_networks",
        "vnet": "az_virtual_networks",
        "azure databricks": "az_azure_databricks",
        "azure synapse": "az_azure_synapse_analytics",
        "synapse": "az_azure_synapse_analytics",
        "hdinsight": "az_hd_insight_clusters",
        "azure migrate": "az_azure_migrate",
        "azure arc": "az_azure_arc",
        "azure openai": "az_azure_openai",
        "logic apps": "az_logic_apps",
        "azure firewall": "az_firewalls",
        "azure bastion": "az_bastions",
        "load balancer": "az_load_balancers",
        "front door": "az_front_doors",
        "application gateway": "az_application_gateways",
        "traffic manager": "az_traffic_manager_profiles",
        "expressroute": "az_expressroute_circuits",
        "azure dns": "az_dns_zones",
        "azure cdn": "az_cdn_profiles",
        "data lake storage": "az_data_lake_storage_gen1",
        "azure backup": "az_azure_backup_center",
        "site recovery": "az_recovery_services_vaults",
        "automation": "az_automation_accounts",
        "azure policy": "az_policy",
        "azure advisor": "az_advisor",
        "application insights": "az_application_insights",
        "log analytics": "az_log_analytics_workspaces",
        "stream analytics": "az_stream_analytics_jobs",
        "data explorer": "az_azure_data_explorer_clusters",
        "cognitive services": "az_cognitive_services",
        # az_machine_learning has no downloaded file; the Studio Workspaces
        # icon is the closest real asset actually on disk.
        "machine learning": "az_machine_learning_studio_workspaces",
        "azure machine learning": "az_machine_learning_studio_workspaces",
        "azure ml": "az_machine_learning_studio_workspaces",
        "bot services": "az_bot_services",
        "search services": "az_search_services",
        "signalr": "az_signalr",
        "static web apps": "az_static_apps",
        "iot hub": "az_iot_hub",
        "iot central": "az_iot_central_applications",
        "digital twins": "az_digital_twins",
        # Microsoft Fabric
        "onelake": "fabric_onelake",
        "lakehouse": "fabric_lakehouse",
        "data warehouse": "fabric_data_warehouse",
        "fabric warehouse": "fabric_data_warehouse",
        "notebooks": "fabric_notebook",
        "fabric notebooks": "fabric_notebook",
        "spark": "fabric_spark_job",
        "fabric spark": "fabric_spark_job",
        "semantic models": "fabric_semantic_model",
        "semantic model": "fabric_semantic_model",
        "real-time intelligence": "fabric_real_time_intelligence",
        "real time intelligence": "fabric_real_time_intelligence",
        "data factory": "fabric_data_factory",
        "fabric data factory": "fabric_data_factory",
        "fabric pipeline": "fabric_pipeline",
        "fabric pipelines": "fabric_pipelines",
        "dataflow gen2": "fabric_dataflow_gen2",
        "eventstream": "fabric_eventstream",
        "eventhouse": "fabric_eventhouse",
        "kql database": "fabric_kql_database",
        "kql queryset": "fabric_kql_queryset",
        "data science": "fabric_data_science",
        "fabric experiments": "fabric_experiments",
        "ml model": "fabric_ml_model",
        "fabric ml model": "fabric_ml_model",
        "data engineering": "fabric_data_engineering",
        "power bi": "fabric_power_bi",
        "copilot": "fabric_copilot",
        "real-time dashboard": "fabric_real_time_dashboard",
        "fabric report": "fabric_report",
        "fabric reports": "fabric_reports",
        "fabric dashboard": "fabric_dashboard",
        "paginated report": "fabric_paginated_report",
        "fabric scorecard": "fabric_scorecard",
        "purview": "fabric_purview",
        "microsoft purview": "fabric_purview",
        "data activator": "fabric_data_activator",
        "reflex": "fabric_reflex",
        "real-time intel": "fabric_real_time_intelligence",
        "real time intel": "fabric_real_time_intelligence",
        # Oracle has no dedicated icon anywhere in the registry (the
        # oracle_db stub entry has no source configured) — the closest
        # real Oracle-branded asset on file is AWS's "Oracle Database at
        # AWS" icon, which is a reasonable stand-in for a generic Oracle
        # Database source-system icon.
        "oracle": "aws_oracle_databaseat_a_w_s",
        "oracle database": "aws_oracle_databaseat_a_w_s",
        "oracle db": "aws_oracle_databaseat_a_w_s",
        "oracle exadata": "aws_oracle_databaseat_a_w_s",
        "oracle rac": "aws_oracle_databaseat_a_w_s",
        "gold layer": "fabric_warehouse",
        "gold warehouse": "fabric_warehouse",
        "bronze layer": "fabric_lakehouse",
        "silver layer": "fabric_lakehouse",
        "delta lake": "fabric_lakehouse",
        "delta tables": "fabric_lakehouse",
        # No dedicated "Self-Hosted Integration Runtime" icon exists anywhere
        # in the registry — a network gateway icon is the closest visual
        # stand-in for this hybrid on-prem/cloud connectivity concept.
        "self-hosted integration runtime": "az_local_network_gateways",
        "self hosted integration runtime": "az_local_network_gateways",
        "azure self-hosted ir": "az_local_network_gateways",
        "self-hosted ir": "az_local_network_gateways",
    }

    def _apply_short_aliases(self):
        for short, target_id in self._SHORT_ALIASES.items():
            norm_short = _normalize(short)
            if norm_short not in self._index:
                norm_target = _normalize(target_id)
                entry = self._index.get(norm_target)
                if entry:
                    self._index[norm_short] = entry

    def _resolve_entry(self, name: str) -> dict | None:
        norm = _normalize(name)
        entry = self._index.get(norm)
        if entry:
            return entry

        # LLM-generated labels are often compound/descriptive ("Fabric Data
        # Factory Pipelines", "Azure Self-Hosted IR") rather than an exact
        # registered name or alias. Fall back to substring matching against
        # every indexed key, preferring the longest match — long enough to
        # avoid short/generic words causing false positives, but catching
        # a registered term embedded inside a longer descriptive phrase.
        #
        # The `norm in key` direction (query hiding inside a longer key) is
        # only safe when the query itself is long enough — a short query
        # like "SAP" (3 chars) is a coincidental substring of dozens of
        # unrelated keys ("AWSAppFlow" normalizes to "awsappflow", which
        # contains "sap" purely by accident) and would confidently return
        # the wrong icon. The `key in norm` direction doesn't have this
        # problem since `key` is already guarded to >=5 chars — a whole
        # recognized term appearing intact inside a longer descriptive
        # phrase is a real match, not a coincidence.
        best_key = None
        for key in self._index:
            if len(key) < 5:
                continue
            if key in norm or (len(norm) >= 5 and norm in key):
                if best_key is None or len(key) > len(best_key):
                    best_key = key
        return self._index.get(best_key) if best_key else None

    def get_icon(self, name: str, png_only: bool = True) -> Path | None:
        entry = self._resolve_entry(name)
        if not entry:
            return self._scan_filesystem(name, png_only)

        search_keys = ("png_path", "file_path") if png_only else ("png_path", "svg_path", "file_path")
        for key in search_keys:
            rel = entry.get(key, "")
            if rel:
                full = self.assets_dir / rel
                if full.exists() and (not png_only or full.suffix.lower() != ".svg"):
                    return full

        return self._scan_filesystem(name, png_only)

    def _scan_filesystem(self, name: str, png_only: bool = True) -> Path | None:
        norm_id = _normalize(name)
        exts = (".png", ".jpg", ".jpeg") if png_only else ICON_EXTENSIONS
        for dirpath in self.assets_dir.rglob("*"):
            if dirpath.is_file() and dirpath.suffix.lower() in exts:
                if _normalize(dirpath.stem) == norm_id:
                    return dirpath
        return None

    def get_fallback(self, name: str) -> tuple[str, str]:
        entry = self._resolve_entry(name)
        if entry:
            abbr = entry.get("abbreviation", "")
            color = entry.get("brand_color", "#6C1D5F")
            if abbr:
                return abbr, color

        words = name.strip().split()
        if len(words) == 1:
            abbr = words[0][:3].upper()
        else:
            abbr = "".join(w[0] for w in words[:3]).upper()
        return abbr, "#6C1D5F"

    def resolve(self, name: str) -> tuple[Path | None, str, str]:
        icon = self.get_icon(name)
        abbr, color = self.get_fallback(name)
        return icon, abbr, color

    def stats(self) -> dict:
        categories: dict[str, dict] = {}
        for entry in self._registry:
            cat = entry.get("category", "uncategorized")
            if cat not in categories:
                categories[cat] = {"total": 0, "available": 0, "missing": 0}
            categories[cat]["total"] += 1
            found = False
            for key in ("png_path", "svg_path", "file_path"):
                rel = entry.get(key, "")
                if rel and (self.assets_dir / rel).exists():
                    found = True
                    break
            if found:
                categories[cat]["available"] += 1
            else:
                categories[cat]["missing"] += 1

        total = len(self._registry)
        available = sum(c["available"] for c in categories.values())
        return {
            "total_registered": total,
            "total_available": available,
            "total_missing": total - available,
            "coverage_pct": round(available / total * 100, 1) if total else 0,
            "categories": categories,
        }

