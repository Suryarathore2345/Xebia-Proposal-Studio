# Architecture-Diagram Generation: Gap Analysis & Improvement Plan

**Date:** 2026-08-25
**Scope:** How the proposal tool generates Azure/Fabric solution-architecture diagrams (the `architecture` and `migration_flow` slide layouts), compared against Xebia's own real client decks and current Microsoft reference-architecture practice.

This document is based on:
- A shape-level (python-pptx/XML) audit of 16 genuine architecture diagrams across the 10 reference decks in `Documents/` (see §2).
- A full read of the current generation code path: `src/llm/anthropic_client.py`, `src/generation/architecture_generator.py`, `src/generation/diagrams/migration_flow_renderer.py`, `src/generation/diagrams/architecture_renderer.py`, `src/generation/slide_builders.py`, `src/images/icon_library.py`.
- Microsoft's own published references: the [Fabric end-to-end analytics architecture](https://learn.microsoft.com/en-us/azure/architecture/example-scenario/dataplate2e/data-platform-end-to-end), [Cloud Adoption Framework landing zones](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/), [Azure hub-spoke topology](https://learn.microsoft.com/en-us/azure/architecture/networking/architecture/hub-spoke), [Fabric medallion architecture](https://learn.microsoft.com/en-us/fabric/onelake/onelake-medallion-lakehouse-architecture), and [Azure icon usage guidelines](https://learn.microsoft.com/en-us/azure/architecture/icons/).

---

## 1. Current system — what actually exists

There are **three separate diagram renderers**, but only two are reachable from the live pipeline. This matters because one of the unused ones already has capabilities the reference decks need.

| Layout key | Renderer | Reachable from LLM plan? | Visual model |
|---|---|---|---|
| `architecture` | `build_architecture_slide` (`slide_builders.py:1270`) | Yes | Simple top-to-bottom stack of 4-7 horizontal layer rows, down-arrows between them, colored label chip per row |
| `migration_flow` | `MigrationFlowRenderer` (`diagrams/migration_flow_renderer.py`) | Yes | Left-to-right zones (max **5**), each with max **5** groups of max **5** items, flat (no nesting), 0-2 bottom bands, optional journey-label brackets |
| `architecture_diagram` | `ArchitectureDiagramRenderer` (`diagrams/architecture_renderer.py`) | **No** — not in the LLM's `AVAILABLE SLIDE LAYOUTS` list, never selected by the planner | Recursive dashed-border zones-within-zones, source/sink side columns, named-node connectors — structurally the closest of the three to what real reference decks do |

There's also a standalone `generate_architecture_diagram()` in `architecture_generator.py` with its own Claude system prompt — it duplicates the `migration_flow` JSON schema but is **only called by `scripts/test_architecture_gen.py`**, never by the live proposal pipeline. The live pipeline instead has the planning LLM produce zones/layers directly as part of one giant proposal-plan JSON (`anthropic_client.py`, ~250 lines of a single system prompt covering all 15+ slide types).

**What's already good** (don't rebuild this):
- The planning prompt (`anthropic_client.py:86-136`) already has real sophistication: a mandatory bronze/silver/gold depth rule, a mandatory cross-cutting governance band, a "don't list two tools for the same job without explaining why" rule, and current-state vs. target-state diagram differentiation. This is ahead of where most of the *rendering* capability can express it.
- Icon coverage is **not a bottleneck**: `assets/icons/registry.json` resolves 1,293 of 1,318 registered technologies (98.1%) — AWS (867/867), Azure (311/320), Fabric (35/38), databases, DevOps, security, monitoring all well covered. The old `tech_icon_registry.py` (which only had ~35 icons downloaded) is superseded by `IconLibrary` and is effectively dead weight now.
- Color-by-pipeline-stage (`ZONE_THEMES`: orange=source, teal=migration, blue=target-cloud, purple=data-platform, green=outcomes, dark=governance) is actually the *majority* pattern in real decks (see §2.7) — don't replace it with vendor-brand color-coding as a default.

**What's structurally capped, regardless of prompt quality:**
- 5 zones / 5 groups / 5 items is a hard ceiling in `MigrationFlowRenderer`. The reference decks' real architecture diagrams run 70-193 shapes on one slide.
- No nesting — a zone can't contain a bounded sub-region (a "subscription" containing a "VNet" containing a "subnet"). This makes the entire hub-spoke/landing-zone archetype (§2.10, archetype #2) unrepresentable today.
- No legend construct in the schema at all.
- Inner groups are hard-coded to always render with a dashed border (`migration_flow_renderer.py:323`, `set_dash_style(grp, dash="dash", ...)` unconditionally) — this inverts the convention real decks use (see §3.2).
- Bottom bands cap at 2, with items rendered as a flat `·`-joined text string — real decks give governance and platform/security **each their own band**, ~5-6 named items apiece, laid out as discrete boxes not a text run.

---

## 2. What the reference decks actually do

Full findings are in the appendix-style detail below; this is the synthesis.

### 2.1 Two dominant top-level layouts
- **Left-to-right pipeline** (~9 of 16 diagrams): vertical zones `Sources → Ingestion → Storage/Medallion → Transformation → Serving/Consumption`, with governance/security as **full-width bands pinned along the bottom**, underneath everything. Best examples: PNB MetLife slide 17, MOHESR slides 51/53/14, MIgration_Fabric slide 8.
- **Top-to-bottom banded stack**: full-width bands stacked vertically, no left-right pipeline at all. Agthia MDM slide 11 puts a `Data Governance & Security` band at the very **top** (not bottom), then a 3-column sources/storage/consumption row, then MDM/Integration/Delivery/Operations bands beneath — closed with a literal text ribbon "Sources → MDM → Integration → Storage → Analytics & AI → Consumption".

### 2.2 A third archetype the current system cannot produce at all: hub-and-spoke landing zone
Nested rectangles-within-rectangles (management group → subscription → VNet → subnet), services placed inside the innermost box. MOHESR slide 15, PNB MetLife slide 19, HCT slide 16. This is one of the most common single-slide types in Xebia's own enterprise-grade decks and the current schema has **no way to express it**.

Critically, these decks **don't use real recursive PPTX grouping** to achieve 4 conceptual nesting levels — they fake it with **z-order + progressively smaller overlapping rectangles** (draw the biggest zone rectangle first/lowest, smaller ones on top, leaf content last). Max actual XML group depth observed: 1 (and that's only used for icon+label leaf pairs, not zone hierarchy). This is good news for implementation cost — replicating this needs layered rectangle placement, not a real recursive layout engine.

### 2.3 Two more archetypes worth naming
- **Current → Migration → Target 3-column comparison** with numbered transformation moves in the middle column (HCT slide 11 — 8 numbered steps like "1 · MOVE the data", "2 · RE-ENGINEER pipelines"), closed with a "HOW TO READ THIS" explanatory panel.
- **Capability/service tile grid** — flat grids with no flow, no zones, no connectors (Apollo Tyres slide 4, Synapse-to-Fabric slides 4/11). Important as a *negative* example: these get caught by naive "many shapes + Fabric keywords" heuristics but are **not** architecture diagrams — they're what the current system's `icon_grid` layout already correctly handles, so no change needed there, just confirmation not to conflate the two.

### 2.4 Notation: dashed = boundary, solid = component (a real, consistently-applied rule)
Verified against actual XML dash values: dashed rectangles are always subscription boundaries, on-prem/cloud dividers, or workspace boundaries — never a deployed service. Solid rectangles are always actual services/data stores. The current renderer does the opposite by default (groups always dashed, zones solid) — a one-line semantic bug, not a redesign.

### 2.5 Legends are rare but cheap and high-signal
Only 2 of 16 diagrams have one (PNB MetLife slide 17, HCT slide 13) — but both are the most polished, most "enterprise-grade" diagrams in the corpus. Format: small horizontal row, bottom-left, swatch + label pairs (e.g. "⋯ On-prem  ⋯ Azure boundary  → Data flow  ↔ read/write"). The schema has no legend field today.

### 2.6 Component vocabulary actually used (this is the real target vocabulary — use it verbatim, don't invent)
- **Ingestion:** Azure Data Factory (Copy/Data Flows/CDC/SHIR), Fabric Data Factory Pipelines, Databricks LakeFlow Connect/Pipelines, Auto Loader, Dataflow Gen2, Eventstream, Eventhouse, Event Hubs, IoT Hub, Azure Data Box, self-hosted integration runtime (SHIR)
- **Storage:** ADLS Gen2, OneLake, Delta Lake, Lakehouse, Unity Catalog-governed tables — medallion naming actually **varies by deck** (Bronze/Silver/Gold vs. Landing/Raw/Staged/Curated vs. Landing/Bronze/Silver/Gold) — there is no single canonical naming to force
- **Compute:** Azure Databricks (Notebooks/Jobs/Serverless/Photon), Synapse, Fabric Notebooks (PySpark), Azure AI Foundry/OpenAI, Doc Intelligence
- **Serving:** Power BI (Direct Lake), Databricks SQL/Genie Dashboards, Delta Sharing, KQL Dashboards, Semantic Models
- **Governance:** Microsoft Purview, Unity Catalog, Profisee (MDM), Data Catalog/Marketplace
- **Security/Identity:** Entra ID (SSO/PIM/Conditional Access), RBAC, MFA, Key Vault, Private Link/Endpoints, NSG, Azure Firewall Premium, Bastion, DDoS Standard, Azure Policy, Defender for Cloud, Sentinel
- **Networking:** Hub-Spoke VNet, ExpressRoute+VPN (with explicit fallback noted), NAT Gateway, VNet Peering, named subnet types, Private DNS
- **Monitoring:** Azure Monitor, Log Analytics, Alerts, Data Activator
- **DevOps:** Azure DevOps, Terraform, Bicep — **always a single tile inside the governance/platform band, never its own lane**
- **FinOps:** Azure Cost Management/FinOps appears as **its own named box** repeatedly — the current prompt doesn't call this out as a distinct item

### 2.7 Data flow arrows
One-sided triangle arrowheads for genuine data-direction flow; plain unarrowed lines for callout/leader lines or zone-boundary joins (these actually outnumber true arrows). Flow is left→right, top→bottom within a column — no diagram reverses this. No arrow-color-coding by data type was found even in the most detailed diagrams — flow-type differentiation lives in the legend text, not connector color. **The current renderer's single-triangle-arrow-between-zones already matches this reasonably well** — no major change needed here beyond adding an optional legend when flow types genuinely differ (batch vs. streaming vs. virtualization).

### 2.8 Icon+label leaf pattern
Real icon (embedded PNG, typically 0.09-0.72in, clustering under 0.35in) + text label, grouped as icon-left/label-right in a single row, no background chip behind the icon. The current renderer's `_draw_item_icons` does **icon-on-top/label-below in a grid** — different orientation, not wrong, but worth knowing it diverges from the house style when the goal is closest fidelity to Xebia's own decks.

### 2.9 "Term · qualifier" two-tier labeling — the actual house-style differentiator
The most polished decks (PNB MetLife, HCT, MOHESR) consistently pair a short bold name with a smaller qualifier via a middle-dot: *"Delta Lake · Unity Catalog-governed tables"*, *"ExpressRoute (S2S VPN fallback) · Dedicated circuit: on-prem Central DC ⇄ Azure UAE North"*. The lighter workshop/case-study decks don't do this. The current schema's group `items` are flat strings — no qualifier field exists.

### 2.10 Color coding: monochrome-brand is the norm, vendor-color-coding is the exception
Only 1 of 16 diagrams (PNB MetLife) uses real vendor-brand colors (Databricks red `#FF3621` vs. Azure blue `#0078D4`) to semantically distinguish owning platform. Everything else uses a single brand hue family differentiated by shade/tint, or theme neutrals + one accent. **This validates the current `ZONE_THEMES` approach** (color by pipeline stage) as the right default — vendor-color-coding should be an opt-in for explicitly multi-vendor/multi-cloud migration stories, not the default.

### 2.11 The enterprise-grade vs. conceptual split, and what actually earns "enterprise-grade"
It's not icon density alone. The diagrams that read as genuine solution architecture (HCT 13, PNB MetLife 19, MOHESR 15, HCT 16) earn it through: **named IaC tooling** (Terraform/Bicep called out), **explicit security/compliance decisions written as prose inside the diagram** ("Egress via Azure Firewall Premium (no NAT), forced tunnelling, hub-spoke only, DDoS on hub+Prod"), **real subnet/RG naming conventions**, and **numbered layer taxonomy with a legend** — not just "more icons." A diagram can have 70+ real icons and still read as "proposal-level" (MIgration_Fabric slide 8) if it lacks these decision-callout details.

---

## 3. Recommended redesign

### 3.1 Fix the schema/renderer mismatch first (cheap, high-leverage)
Wire `ArchitectureDiagramRenderer`'s existing recursive-zone and column capability into the actual pipeline instead of leaving it orphaned. It already supports the nested-container and side-column shapes the hub-spoke archetype needs — it just needs the LLM schema exposed to the planner and the z-order-based nesting approach from §2.2 (draw outer→inner by size, not real recursive layout math).

### 3.2 Fix the dashed/solid inversion
One-line fix in `migration_flow_renderer.py:323` and `_draw_zone`: dashing should be a property of **boundary-type containers** (subscription/VNet/workspace/on-prem-vs-cloud divider), not unconditionally applied to every group. Solid should be the default for anything that's an actual deployed component.

### 3.3 Extend the schema, don't replace it
Add, as backward-compatible optional fields on the existing `zones`/`groups`/`bottom_bands` schema (used by both the planning prompt and `MigrationFlowRenderer`):

```json
{
  "zones": [{
    "id": "...", "title": "...", "color": "...", "width_ratio": 1.0,
    "boundary_type": "none|subscription|vnet|workspace",   // NEW — drives dashed vs solid
    "children": [ /* recursive zones, for nested boundaries */ ],  // NEW
    "groups": [{
      "label": "...", "style": "icons|pills|flow|text",
      "items": [
        {"name": "Delta Lake", "qualifier": "Unity Catalog-governed tables"}  // NEW — items may be
        // objects with name+qualifier (renders "Name · qualifier") instead of bare strings
      ]
    }]
  }],
  "bottom_bands": [
    {"label": "Governance", "items": [...], "color": "dark"},        // now explicitly 2 bands
    {"label": "Platform & Security", "items": [...], "color": "dark"} // governance ≠ platform/security
  ],
  "legend": [  // NEW — optional, only when the diagram uses dashed boundaries or mixed flow types
    {"symbol": "dashed", "label": "Azure subscription boundary"},
    {"symbol": "arrow", "label": "Data flow"}
  ],
  "divider": {"orientation": "vertical", "position_after_zone": 0, "label": "On-prem | Azure"}  // NEW, optional
}
```

Raise the caps: zones stay capped around 5-6 for the pipeline archetype (that's genuinely what keeps a slide readable), but **groups per zone and items per group should scale with what the content needs**, not a flat 5/5 — the renderer already does dynamic height-estimation (`_estimate_zone_content_h`), so the cap is a prompt-level choice, not a rendering limitation. For the network/landing-zone archetype specifically, expect and support far higher shape density (matching the 70-190 shape range actually observed), via the nested `children` mechanism rather than by cramming more items into flat groups.

### 3.4 Add a fourth archetype: current → migration-steps → target
Extend (or add a variant of) `migration_flow` to support a numbered-steps middle zone — this is close to the existing `"style": "flow"` group style, just needs to support numbered step labels ("1 · MOVE the data") and an optional explanatory legend panel, matching HCT slide 11.

### 3.5 Give diagram generation its own LLM pass
Right now architecture content is one of ~15 things produced inside a single giant plan-generation call. The standalone `architecture_generator.py` already exists with a dedicated, focused system prompt and reference-content injection — but it's disconnected from the live pipeline. Recommendation: **revive it as a second, targeted pass**, not a replacement for the planner. Flow: (1) the main planning call decides *how many* architecture slides and their high-level purpose (current-state / target-state / network-topology / etc.) as it does today; (2) for each one, a focused follow-up call — using the reference vocabulary from §2.6 and the retrieval content already available via `search_for_proposal` — elaborates the actual zones/groups/items with a full token budget dedicated to that one diagram, instead of sharing budget with financials, staffing, timeline, etc. This directly targets the "shallow because it's competing for attention" root cause, not just a prompt-wording fix.

### 3.6 Adapt diagram depth to proposal scenario
`config/templates.yaml` already defines audience-differentiated templates (`xebia_executive`, `xebia_technical`, `xebia_rfp`, `xebia_sales`) but **nothing in the LLM prompt or layout selection currently reads `template_name` or audience**. Wire it in:
- `xebia_executive`/`xebia_sales` (CXO, procurement audience): prefer the simple `architecture` stacked-layer view or one clean `migration_flow`, skip the network/landing-zone archetype — a CXO doesn't need subnet detail.
- `xebia_technical`/`xebia_rfp` (architects, evaluation committees — this is what PNB MetLife/MOHESR/HCT actually are): this is where the network/landing-zone archetype, legends, and "Term · qualifier" labeling should be the default, and 2-3 distinct diagrams (current-state, target-state, network topology) are appropriate — matching what §3.5's existing "2-3 distinct migration_flow diagrams" prompt rule already intends, just not yet paired with a template-aware depth signal.

### 3.7 Visual/layout fixes, in priority order
1. Dashed = boundary / solid = component (§3.2) — one-line semantic fix.
2. Split bottom bands into Governance + Platform&Security by default for enterprise-scale proposals, each with named items (Purview, Entra ID, Key Vault, Monitor, Azure DevOps, Cost Management/FinOps) rendered as discrete boxes, not a `·`-joined string.
3. Add the optional `legend` element — bottom-left swatch+label row, rendered only when `boundary_type` or mixed flow semantics are present.
4. Add `qualifier` support to items for the "Term · qualifier" two-tier label style, gated to the technical/RFP template tier.
5. Wire up nested `children` zones via z-order layering for the hub-spoke/landing-zone archetype.
6. Pull `ZONE_THEMES` colors from `design_engine/palette.py` tokens instead of the hardcoded hex values currently duplicated in `migration_flow_renderer.py` — consistency with the rest of the design system, not a visual change.

### 3.8 Rules the AI should follow (additions to the existing prompt, not a rewrite)
The current prompt already has strong rules (depth requirement, mandatory governance band, tool-responsibility clarity — keep all of these). Add:
- Use the reference vocabulary in §2.6 verbatim when the proposal's actual technologies match it — don't paraphrase "Azure Data Factory Copy Activity" as "Data Copy Tool."
- When the proposal involves a regulated industry, government/education client, or explicit network/security scope (the pattern seen in MOHESR, PNB MetLife, HCT), include a dedicated network/landing-zone diagram — not folded into the main data-flow diagram.
- Split cross-cutting concerns into a **Governance** band and a **Platform & Security** band, not one merged band, whenever there are enough named items to justify two (≥3 items each) — matching §2.5/§3.7.
- Never fabricate CIDR ranges, resource names, or specific compliance certifications not present in the reference material — the real decks state actual named decisions ("Egress via Azure Firewall Premium, no NAT") because they're true for that client; an invented equivalent would be a factual claim the proposal can't back up. Prefer generic-but-real architectural decisions ("hub-spoke only, no spoke-to-spoke peering") over specific fabricated infrastructure values.
- Include a legend only when the diagram actually uses dashed boundaries or mixed flow semantics — don't add one by default to every diagram (matches the 2-of-16 real-world frequency).

---

## 4. Implementation plan

**Phase 1 — Correctness fixes (no schema change, low risk) — ✅ DONE**
1. ✅ Fixed the dashed/solid inversion in `migration_flow_renderer.py` (§3.2) — groups now default solid, opt into `"border_style": "dashed"`.
2. ✅ Moved `ZONE_THEMES` hex values to a new `STAGE` token namespace in `design_engine/palette.py`.
3. ⚠️ **Correction**: `tech_icon_registry.py` was NOT retired — verification showed it's the only source for a real Kubernetes icon (`IconLibrary`'s registry is cloud-vendor-icon-set-focused and has no plain Kubernetes logo). It's already correctly ordered as `IconLibrary`'s fallback; left as-is.

**Phase 2 — Schema extensions (additive, backward-compatible) — ✅ DONE**
4. ✅ Added `qualifier` support (`{"name", "qualifier"}` items render as "Name · qualifier") across `_draw_item_icons`/`_draw_item_pills`/`_draw_item_flow`/`_draw_group`'s text fallback, plus `_estimate_group_h`'s sizing math. Also fixed a regression this would otherwise have caused in `docx_generator.py`, which did a raw `", ".join(items)` that can't handle dict items.
5. ✅ Split `bottom_bands` into Governance / Platform & Security as the default 2-band pattern in the prompt; band items now render as discrete boxes (`_draw_bottom_bands`), not a `·`-joined string.
6. ✅ Added the optional `legend` field + `_draw_legend` — bottom-left swatch+label row (dashed/arrow/solid symbols).

**Phase 3 — New archetype: nested/hub-spoke landing zone — ✅ DONE**
7. ✅ Added `boundary_type` and `children` (recursive zones) to the schema.
8. ✅ Extended `MigrationFlowRenderer._draw_zone` to recurse into `children` via z-order + inset sizing (`_draw_children`), exactly as §2.2 describes — no general recursive layout engine needed. Also added an optional `divider` (vertical dashed connector line, e.g. on-prem/Azure split). **Removed** the orphaned `ArchitectureDiagramRenderer`/`"architecture_diagram"` layout entirely (`architecture_renderer.py` deleted; `slide_builders.py` and `diagrams/__init__.py` updated) rather than leave two incompatible nested-diagram code paths side by side.
9. ✅ Added a "NESTED LANDING-ZONE / NETWORK TOPOLOGY" guidance block to the LLM prompt (`anthropic_client.py`) so the planner can actually select it — gated to regulated-industry/government/explicit-network-scope proposals, not a default.

**Phase 4 — Dedicated diagram-elaboration pass**
10. ✅ **Done (Part B only, by explicit choice)**: revived `architecture_generator.py` as `elaborate_architecture_diagrams()`, a second-pass per-diagram call hooked into `ProposalSession.chat()` after the main plan is finalized. It's strictly additive — any failure (missing API key, bad JSON, retrieval error) is caught per-diagram and leaves that slide's original content untouched, verified via a fixture run. To avoid the exact "two schemas silently drift apart" problem this whole audit started from, the standalone prompt now builds itself from the same `ARCHITECTURE_DIAGRAM_GUIDANCE` constant the main planner prompt uses (extracted as a shared source of truth in `anthropic_client.py`), rather than duplicating it. **Known limitation**: this pass always calls Claude directly (`llm.anthropic_client.get_client()`), regardless of which provider generated the main plan — an all-Gemini proposal session will still make this one Claude call. It degrades gracefully (keeps the original diagram) if `ANTHROPIC_API_KEY` isn't set, but true Gemini parity for this specific pass wasn't built.
11. ⏭️ **Skipped (by explicit choice)**: `template_name`/audience-aware diagram depth (§3.6). This needs `template_name` threaded from the UI/API into the planning call — `ProposalSession.chat()` doesn't currently receive it (the template is picked later, at `generate()` time), so this would touch the session API and likely `src/web` too. Left as a separate follow-up.

**Phase 5 — Verification — done for what shipped**
12. ✅ Re-ran `scripts/test_architecture_gen.py --static` after every phase; added `--landing-zone` as the new nested/hub-spoke fixture (§2.2/§3.4 archetype) since none existed before. Verified via direct OOXML inspection that dash styles land on exactly the right shapes (boundary zones + divider, nothing else) and that all expected labels/qualifiers/bands render.
13. ✅ Full-pipeline regression: ran `generate_proposal_pptx`/`generate_proposal_docx` against the pre-existing `outputs/test_content_plan.json` fixture (old-format data, pre-dating this work) — still renders cleanly, confirming backward compatibility.
14. ⚠️ Not done: visual spot-check against the actual reference slides (HCT 13, PNB MetLife 17/19, MOHESR 15/51) — this environment has no PowerPoint/LibreOffice to render slides to images for side-by-side comparison. Verification here was structural (OOXML shape/text/dash inspection), not visual. Worth a manual look in PowerPoint before relying on this for a live proposal.

Phase 4's audience-awareness half (item 11) and the visual spot-check (item 14) are the two open items from this pass.
