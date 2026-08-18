# Xebia Proposal Studio
## End-to-End Project Blueprint, Prerequisites, Architecture & Pre-Implementation Questionnaire

> **Status:** Pre-implementation blueprint  
> **Purpose:** Build a reusable AI-assisted proposal platform for generating Xebia-branded PowerPoint decks and Word proposal documents using approved historical proposals, presentations, templates, brand assets, and new opportunity requirements.

---

# 1. Executive Summary

## 1.1 Objective

Build **Xebia Proposal Studio**, a reusable proposal-generation system that can:

- Ingest existing Xebia PPTX, DOCX, PDF and template files.
- Learn the organization's proposal structures, terminology, storytelling patterns, and visual patterns.
- Maintain a centralized Xebia design system.
- Retrieve relevant historical content using metadata, keyword search, and semantic embeddings.
- Retrieve appropriate slide/document layouts separately from content.
- Generate new Xebia-branded PPTX and DOCX proposals.
- Keep PPT and DOCX outputs aligned through a shared proposal plan.
- Perform structural, content, brand, and visual QA.
- Maintain provenance showing which references influenced the generated proposal.
- Support future scaling from a small reference library to hundreds/thousands of documents.

## 1.2 Core Principle

The system must **not copy old proposals**.

It should use old proposals as:

- Structural references
- Visual references
- Terminology references
- Storytelling references
- Domain references
- Reusable pattern references

while generating content specifically for the new opportunity.

The intended result is:

> **A new proposal that feels like an approved Xebia proposal, without incorrectly carrying forward customer-specific or project-specific information.**

---

# 2. Existing Foundation

Two existing skills are available and should be treated as the starting point:

- `Doc_Skill.md`
- `PPT_Skill.md`

The DOCX skill already covers creation/editing/analysis, document rendering, validation, tables, headings, TOC, tracked changes, comments, and document QA.

The PPTX skill already covers creation/editing/analysis, templates, slide duplication, thumbnails, OOXML handling, rendering, validation, charts, visual QA, typography, layout guidance, and presentation-specific generation rules.

## Mandatory rule

Do **not** rebuild these capabilities from scratch.

Before implementation:

1. Inspect both skills.
2. Identify reusable scripts and utilities.
3. Identify overlapping functionality.
4. Refactor where appropriate.
5. Extend them for Proposal Studio.
6. Keep existing low-level PPTX/DOCX engineering separate from proposal orchestration.

---

# 3. Target Architecture

```text
                           XEBIA PROPOSAL STUDIO
                                    |
                +-------------------+-------------------+
                |                                       |
        XEBIA DESIGN SYSTEM                    REFERENCE LIBRARY
                |                                       |
        +-------+--------+                     +--------+--------+
        |       |        |                     |        |        |
      Brand   PPTX     DOCX                  PPTX     DOCX     PDF
      Rules   Layouts  Styles                Files    Files    Files
        |       |        |                     |        |        |
        +-------+--------+                     +--------+--------+
                |                                       |
                |                                INGESTION PIPELINE
                |                                       |
                |                         +-------------+-------------+
                |                         |             |             |
                |                      Extract      Classify       Metadata
                |                         |             |             |
                |                         +-------------+-------------+
                |                                       |
                |                                  PostgreSQL
                |                                       |
                |                 +---------------------+---------------------+
                |                 |                                           |
                |          Relational Data                               pgvector
                |                 |                                           |
                |       Documents / Slides /                           Embeddings /
                |       Templates / Patterns /                          Semantic Search
                |       Tags / Provenance
                |                 |                                           |
                +-----------------+---------------------+---------------------+
                                                        |
                                                 HYBRID RETRIEVAL
                                                        |
                                               +--------+--------+
                                               |                 |
                                        CONTENT RETRIEVAL   LAYOUT RETRIEVAL
                                               |                 |
                                               +--------+--------+
                                                        |
                                                RERANKING ENGINE
                                                        |
                                                 PROPOSAL PLANNER
                                                        |
                                           +------------+------------+
                                           |                         |
                                      PPTX GENERATOR            DOCX GENERATOR
                                           |                         |
                                           +------------+------------+
                                                        |
                                                        v
                                                     QA
                                                        |
                                                        v
                                               FINAL DELIVERABLES
```

---

# 4. Technology Decisions

## 4.1 Recommended Stack

| Layer | Recommended Technology |
|---|---|
| AI/orchestration | Claude / Claude Code |
| Database | PostgreSQL |
| Vector search | pgvector |
| Keyword search | PostgreSQL Full Text Search |
| File storage | Local filesystem initially |
| Production file storage | Azure Blob Storage or equivalent object storage |
| PPT generation | Existing PPTX skill + pptxgenjs |
| DOCX generation | Existing DOCX skill + docx |
| PDF rendering | LibreOffice / Poppler as already used by skills |
| Metadata | PostgreSQL |
| Embeddings | Provider/model to be selected |
| Configuration | YAML/JSON |
| Version control | Git |
| Testing | Python/Node test framework as appropriate |
| Orchestration | Proposal Studio orchestrator skill |

## 4.2 Why PostgreSQL

PostgreSQL should be the system of record for:

- Documents
- Slides
- Sections
- Templates
- Slide patterns
- Tags
- Classifications
- Approval status
- Versioning
- Provenance
- Retrieval metadata
- Embeddings

PostgreSQL itself is open-source and free to use. Hosted PostgreSQL services may incur infrastructure/provider charges.

## 4.3 Why pgvector

Use pgvector so that:

- Relational metadata
- Full-text search
- Vector search
- Document relationships
- Provenance

can remain in one system.

Avoid introducing a separate vector database initially.

---

# 5. Critical Decisions Required Before Implementation

These questions must be answered before the architecture is finalized.

## 5.1 Business Questions

1. Who are the primary users?
   - Sales
   - Pre-sales
   - Solution architects
   - Data/AI teams
   - Delivery teams
   - Proposal management
   - Other

2. What proposal types must be supported first?

3. Is the initial target:
   - Internal proposals
   - Customer proposals
   - RFP responses
   - SOWs
   - Capability decks
   - Technical proposals
   - All of the above

4. What is the expected number of proposals generated per month?

5. What is the expected number of reference documents initially?

6. What is the expected reference-library growth over 1, 2 and 3 years?

7. Which existing proposals are officially approved for reuse?

8. Who owns proposal content approval?

9. Who owns brand approval?

10. What does "high quality" mean for this system?

11. What human review must happen before a proposal is sent externally?

---

# 6. Brand Questions

Before creating the Xebia design system, answer:

1. Is there an official Xebia brand guideline available?

2. Is there an official Xebia PPT template?

3. Is there an official Word template?

4. What is the approved Xebia logo set?

5. Which logo variants are allowed?

6. What are the official brand colors?

7. What are the approved fonts?

8. Are there separate regional/country brand guidelines?

9. Are there rules for:
   - Logo placement
   - Clear space
   - Backgrounds
   - Typography
   - Icons
   - Illustrations
   - Photography
   - Charts
   - Tables
   - Diagrams

10. Are there existing approved slide layouts that must be preserved?

11. Is there a preferred PowerPoint master/template file?

12. Should the system reproduce the current visual identity exactly or create a new proposal-specific Xebia theme inspired by existing approved decks?

13. Are there restrictions on AI-generated visuals?

---

# 7. Reference Library Questions

1. Where will reference documents come from?

2. Which folders/repositories contain them?

3. Are they local files, SharePoint, OneDrive, Git, Azure Blob, etc.?

4. Which files are approved for reuse?

5. Which files are confidential?

6. Can the system index confidential customer documents?

7. Should some documents be searchable but not reusable?

8. Should customer names be masked during indexing?

9. How should duplicate documents be handled?

10. How should revised versions be handled?

11. How should outdated proposals be marked?

12. Who can approve a reference for reuse?

13. Should references have an expiration/review date?

---

# 8. Embedding Questions

These decisions must be answered before building the embedding pipeline.

## 8.1 Embedding Provider

Choose one:

- OpenAI embeddings
- Azure OpenAI embeddings
- Cohere
- Voyage
- Another enterprise-approved provider
- Self-hosted embedding model

Questions:

1. Is external API usage permitted?
2. Is customer/proposal content allowed to leave Xebia-controlled infrastructure?
3. Is Azure OpenAI preferred for enterprise data governance?
4. What are expected embedding costs?
5. Is an on-prem/self-hosted model required?

## 8.2 Embedding Granularity

Recommended:

### PPT

Embed at:

- Slide level
- Optional section level
- Optional architecture description level

### DOCX

Embed at:

- Section level
- Subsection level where meaningful
- Case-study level
- Reusable content block level

Do NOT embed every XML shape or every individual text box.

## 8.3 Embedding Types

Potentially maintain:

```text
content_embedding
layout_embedding
visual_embedding
```

Start with:

```text
content_embedding
```

Add layout/visual embeddings later.

---

# 9. Retrieval Questions

1. Should retrieval be:
   - Metadata only
   - Keyword only
   - Semantic only
   - Hybrid

Recommended: **Hybrid**

2. Which fields should be filterable?

Recommended:

- Industry
- Technology
- Proposal type
- Customer type
- Approval status
- Date
- Confidentiality
- Language
- Region
- Document type

3. How many candidates should vector search return?

4. Should a reranker be used?

5. What should have the highest retrieval weight?

Recommended initial ranking:

```text
Approval status
+
Proposal type
+
Industry
+
Technology
+
Semantic relevance
+
Keyword relevance
+
Recency
```

6. Should the system retrieve content and layout independently?

Recommended: **Yes**

---

# 10. Security Questions

1. Is the system internal-only?

2. Which users can access it?

3. Should users have roles?

Recommended roles:

```text
Admin
Proposal Author
Reviewer
Brand Manager
Read Only
```

4. Which documents can each role access?

5. Should customer-specific proposals be isolated?

6. Should retrieval respect document-level permissions?

7. What audit logs are required?

8. What retention policy applies?

9. What data can be sent to external AI APIs?

10. Is encryption required at rest and in transit?

---

# 11. PostgreSQL Prerequisites

Before implementation, install/configure:

- PostgreSQL
- pgvector extension
- PostgreSQL client tools
- Database migration tooling
- Database backup process

Recommended local development setup:

```text
Docker
  |
  +-- PostgreSQL
       |
       +-- pgvector
```

Create a dedicated database:

```text
xebia_proposal_studio
```

Recommended environments:

```text
development
testing
production
```

Do not use one database/schema for all environments.

---

# 12. PostgreSQL Initial Setup Checklist

Before starting implementation:

- [ ] PostgreSQL installed
- [ ] pgvector installed
- [ ] Database created
- [ ] Application user created
- [ ] Credentials stored securely
- [ ] Connection tested
- [ ] Migration system selected
- [ ] Backup strategy defined
- [ ] Development database initialized
- [ ] `.env` created locally
- [ ] `.env` excluded from Git

Example configuration:

```env
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/xebia_proposal_studio
```

Never commit credentials.

---

# 13. Sample Documents Required Before Starting

Do not begin serious template/embedding work with only one PPT.

Recommended minimum:

## PPT

At least:

- 5-10 approved proposal decks
- 2-3 technical proposal decks
- 2-3 executive/sales decks
- 1 official Xebia template if available

Preferably:

- 20+ decks for meaningful pattern discovery

## DOCX

At least:

- 5 approved proposal documents
- 2 technical documents
- 1 official Word template if available

## Brand Assets

Provide:

- Official logo files
- SVG preferred
- PNG fallback
- Brand guidelines
- Fonts if legally distributable
- Official PPT theme/template
- Official Word template
- Approved icons
- Approved imagery rules

---

# 14. Recommended Reference Directory

```text
references/
│
├── approved/
│   ├── ppt/
│   ├── docx/
│   └── pdf/
│
├── templates/
│   ├── ppt/
│   └── docx/
│
├── brand/
│   ├── logos/
│   ├── fonts/
│   ├── icons/
│   └── guidelines/
│
├── restricted/
│
└── archive/
```

Never treat `archive/` as automatically reusable.

---

# 15. Proposed Repository Structure

```text
xebia-proposal-studio/
│
├── README.md
├── PROJECT_BLUEPRINT.md
├── CHANGELOG.md
├── LICENSE
│
├── .env.example
├── .gitignore
├── docker-compose.yml
│
├── config/
│   ├── brand.yaml
│   ├── database.yaml
│   ├── retrieval.yaml
│   ├── embeddings.yaml
│   ├── proposal.yaml
│   ├── templates.yaml
│   └── qa.yaml
│
├── database/
│   ├── migrations/
│   ├── seeds/
│   └── README.md
│
├── references/
│   ├── approved/
│   │   ├── ppt/
│   │   ├── docx/
│   │   └── pdf/
│   ├── templates/
│   ├── brand/
│   ├── restricted/
│   └── archive/
│
├── extracted/
│   ├── ppt/
│   ├── docx/
│   └── pdf/
│
├── indexes/
│   ├── metadata/
│   ├── text/
│   └── embeddings/
│
├── xebia_design_system/
│   ├── brand/
│   │   ├── colors.json
│   │   ├── typography.json
│   │   ├── spacing.json
│   │   ├── logo_rules.md
│   │   └── theme.json
│   │
│   ├── assets/
│   │   ├── logos/
│   │   ├── icons/
│   │   ├── illustrations/
│   │   ├── backgrounds/
│   │   └── images/
│   │
│   ├── ppt/
│   │   ├── layouts/
│   │   ├── components/
│   │   ├── charts/
│   │   ├── diagrams/
│   │   └── templates/
│   │
│   └── docx/
│       ├── styles/
│       ├── components/
│       ├── headers/
│       ├── footers/
│       └── templates/
│
├── patterns/
│   ├── ppt/
│   │   ├── cover/
│   │   ├── executive_summary/
│   │   ├── challenge/
│   │   ├── solution/
│   │   ├── architecture/
│   │   ├── roadmap/
│   │   ├── methodology/
│   │   ├── team/
│   │   ├── governance/
│   │   ├── kpi/
│   │   └── closing/
│   │
│   └── docx/
│       ├── cover/
│       ├── executive_summary/
│       ├── solution/
│       ├── architecture/
│       ├── implementation/
│       └── appendix/
│
├── templates/
│   ├── ppt/
│   │   ├── xebia_executive/
│   │   ├── xebia_technical/
│   │   ├── xebia_sales/
│   │   └── xebia_rfp/
│   │
│   └── docx/
│       ├── xebia_proposal/
│       ├── xebia_technical/
│       └── xebia_rfp/
│
├── skills/
│   ├── proposal_orchestrator/
│   │   └── SKILL.md
│   ├── reference_analyzer/
│   │   └── SKILL.md
│   ├── reference_retriever/
│   │   └── SKILL.md
│   ├── xebia_brand/
│   │   └── SKILL.md
│   ├── ppt_template_engine/
│   │   └── SKILL.md
│   ├── ppt_generator/
│   │   └── SKILL.md
│   ├── docx_template_engine/
│   │   └── SKILL.md
│   ├── docx_generator/
│   │   └── SKILL.md
│   ├── proposal_storytelling/
│   │   └── SKILL.md
│   └── proposal_qa/
│       └── SKILL.md
│
├── scripts/
│   ├── ingestion/
│   ├── extraction/
│   ├── indexing/
│   ├── retrieval/
│   ├── generation/
│   ├── brand/
│   └── qa/
│
├── proposals/
│   ├── working/
│   ├── review/
│   └── final/
│
├── outputs/
│   ├── ppt/
│   ├── docx/
│   ├── pdf/
│   └── reports/
│
├── tests/
│   ├── ingestion/
│   ├── retrieval/
│   ├── embeddings/
│   ├── ppt/
│   ├── docx/
│   ├── brand/
│   └── end_to_end/
│
└── docs/
    ├── architecture/
    ├── database/
    ├── retrieval/
    ├── brand/
    └── operations/
```

---

# 16. Database Model

Recommended initial entities:

```text
documents
content_units
document_versions
slides
sections
templates
slide_patterns
document_patterns
tags
document_tags
classifications
embeddings
proposals
proposal_requirements
proposal_references
proposal_outputs
generation_runs
qa_results
users
audit_logs
```

## Important relationships

```text
Document
  ├── Versions
  ├── Content Units
  ├── Slides
  ├── Tags
  ├── Classifications
  └── Embeddings

Proposal
  ├── Requirements
  ├── References
  ├── Generated Outputs
  ├── Generation Runs
  └── QA Results

Template
  └── Patterns
```

---

# 17. Embedding Data Model

Recommended:

```text
embeddings
────────────────────────
id
entity_type
entity_id
embedding_type
model_name
model_version
dimensions
embedding
content_hash
created_at
```

Examples:

```text
entity_type = slide
embedding_type = content
```

or:

```text
entity_type = slide_pattern
embedding_type = layout
```

Use `content_hash` to avoid re-embedding unchanged content.

---

# 18. Embedding Pipeline

```text
Reference File
      |
      v
Extract Content
      |
      v
Normalize
      |
      v
Classify
      |
      v
Create Semantic Units
      |
      v
Generate Embeddings
      |
      v
Store in PostgreSQL/pgvector
      |
      v
Create Search Index
```

Re-index only when:

- Content changes
- Embedding model changes
- Chunking strategy changes
- Metadata changes materially

---

# 19. Hybrid Retrieval Pipeline

```text
New Proposal Requirement
        |
        +--> Metadata Filtering
        |
        +--> Keyword Search
        |
        +--> Vector Search
        |
        v
Candidate Pool
        |
        v
Reranking
        |
        +--> Content References
        |
        +--> Layout References
        |
        v
Proposal Planner
```

Do not rely exclusively on embeddings.

---

# 20. Proposal Planning

Before generating PPT/DOCX, create a structured proposal plan.

Example:

```yaml
proposal:
  title: ""
  customer: ""
  industry: ""
  proposal_type: ""
  objective: ""

requirements:
  business:
    - ""
  technical:
    - ""

storyline:
  - executive_summary
  - challenge
  - objectives
  - proposed_solution
  - architecture
  - implementation
  - roadmap
  - outcomes
  - next_steps

references:
  content:
    - document_id: ""
      section_id: ""
  layouts:
    - pattern_id: ""

ppt:
  template: ""

docx:
  template: ""

assumptions:
  - ""

open_questions:
  - ""
```

This becomes the shared source of truth for PPT and DOCX.

---

# 21. PPT Generation Requirements

The PPT generator must:

- Use Xebia design system.
- Use approved templates/layouts.
- Select layouts based on content type.
- Avoid text-heavy slides.
- Use visual storytelling.
- Reuse approved visual patterns where appropriate.
- Never blindly copy old slides.
- Maintain consistent typography and spacing.
- Validate every generated deck.
- Render slides for visual QA.

The existing PPTX skill should remain the low-level engineering authority.

---

# 22. DOCX Generation Requirements

The DOCX generator must:

- Use Xebia document styles.
- Use approved templates.
- Maintain heading hierarchy.
- Generate TOC when required.
- Use professional tables.
- Maintain headers/footers.
- Use appropriate page breaks.
- Maintain consistent typography.
- Render and visually inspect the document.

The existing DOCX skill should remain the low-level engineering authority.

---

# 23. Xebia Design System

The design system should centrally define:

```text
Brand Colors
Typography
Logo
Grid
Spacing
Margins
Corner Radius
Shadows
Icons
Charts
Tables
Cards
Diagrams
Cover Pages
Section Dividers
Footer
Header
Page Number
Slide Number
```

Do not hard-code these values across generation scripts.

---

# 24. Template Strategy

Do not build one universal PPT template.

Create a template family:

```text
xebia_executive
xebia_sales
xebia_technical
xebia_rfp
xebia_architecture
xebia_case_study
```

Likewise for DOCX:

```text
xebia_proposal
xebia_technical_proposal
xebia_rfp_response
xebia_solution_document
xebia_sow
```

---

# 25. Reference Classification

Every document should receive metadata such as:

```yaml
document_type:
proposal_type:
industry:
technologies:
audience:
region:
approval_status:
confidentiality:
reusability:
created_date:
last_reviewed:
```

Every PPT slide should receive:

```yaml
slide_type:
layout_type:
content_density:
visual_density:
has_diagram:
has_chart:
has_table:
has_image:
```

---

# 26. Provenance

Every generated proposal must be traceable.

Example:

```text
Generated Proposal
|
+-- Requirements
|     +-- Customer Requirement Document
|
+-- Content References
|     +-- Proposal A / Slide 8
|     +-- Proposal B / Section 4
|
+-- Layout References
|     +-- Pattern Architecture-03
|     +-- Pattern Roadmap-02
|
+-- Brand
      +-- Xebia Design System v1.0
```

Do not expose confidential source content in the final proposal merely because it was retrieved.

---

# 27. QA Framework

## PPT QA

Check:

- File opens
- OOXML validity
- Slide order
- Missing content
- Placeholder text
- Text overflow
- Shape overlap
- Broken images
- Low contrast
- Alignment
- Spacing
- Branding
- Typography
- Footer
- Slide numbering

## DOCX QA

Check:

- File opens
- XML validity
- Heading hierarchy
- TOC
- Tables
- Page breaks
- Headers
- Footers
- Page numbers
- Overflow
- Placeholder content
- Branding
- Typography

## Proposal QA

Check:

- Requirements coverage
- Business storyline
- Technical consistency
- No contradictions
- Assumptions
- Risks
- Deliverables
- Timeline
- Roles
- Outcomes
- Customer relevance

---

# 28. Security & Data Governance

Implement:

- Role-based access
- Document permissions
- Confidentiality metadata
- Approved-for-reuse flag
- Audit logging
- Secure credentials
- No secrets in Git
- Encryption in transit
- Encryption at rest where required
- AI provider governance
- Data retention rules

The retrieval layer must respect access permissions.

A user must never retrieve a document they are not authorized to access.

---

# 29. Development Phases

## Phase 0 — Discovery

Deliver:

- Answers to all critical questions
- Source inventory
- Brand inventory
- Reference inventory
- Security requirements
- AI/provider decision
- Database decision

## Phase 1 — Foundation

Build:

- Repository
- PostgreSQL
- pgvector
- Configuration
- Database migrations
- Reference folders
- Base skills

## Phase 2 — Reference Intelligence

Build:

- PPT ingestion
- DOCX ingestion
- PDF ingestion
- Extraction
- Classification
- Metadata
- Search
- Embeddings

## Phase 3 — Xebia Design System

Build:

- Brand configuration
- PPT layouts
- DOCX styles
- Reusable components
- Pattern catalog

## Phase 4 — Proposal Engine

Build:

- Requirement analyzer
- Reference retriever
- Proposal planner
- Template selector
- PPT generator
- DOCX generator

## Phase 5 — QA

Build:

- Structural QA
- Visual QA
- Brand QA
- Proposal QA

## Phase 6 — Productionization

Build:

- Authentication
- Permissions
- Audit
- Storage
- Backups
- Monitoring
- Deployment

---

# 30. Minimum Viable Product

The first working version should support:

```text
Input:
- New proposal requirements
- 5-20 approved PPT/DOCX references

Process:
- Ingest
- Extract
- Classify
- Embed
- Retrieve
- Plan
- Generate

Output:
- Xebia PPTX
- Xebia DOCX
- QA report
- Provenance report
```

Do not build advanced visual embeddings, complex reranking, or multi-tenant production infrastructure before this MVP works.

---

# 31. Pre-Implementation Checklist

## Organization

- [ ] Xebia brand guidelines obtained
- [ ] Approved logo assets obtained
- [ ] Approved PPT template obtained
- [ ] Approved Word template obtained
- [ ] Brand owner identified
- [ ] Proposal owner identified

## Reference Library

- [ ] 5-20 approved PPTs collected
- [ ] 5+ approved DOCXs collected
- [ ] Reference permissions confirmed
- [ ] Confidentiality classification defined
- [ ] Approved-for-reuse status defined
- [ ] Archive policy defined

## Development

- [ ] Claude Code environment ready
- [ ] Git repository created
- [ ] Node.js available
- [ ] Python available
- [ ] Existing PPTX skill available
- [ ] Existing DOCX skill available
- [ ] LibreOffice available
- [ ] Poppler available
- [ ] Required npm/Python dependencies available

## Database

- [ ] PostgreSQL installed
- [ ] pgvector installed
- [ ] Database created
- [ ] Application user created
- [ ] Connection tested
- [ ] Migration framework selected
- [ ] Backup strategy defined

## AI

- [ ] LLM provider approved
- [ ] Embedding provider selected
- [ ] API credentials configured securely
- [ ] Data-sharing policy approved
- [ ] Embedding model selected
- [ ] Embedding dimensions recorded

## Storage

- [ ] Reference directory created
- [ ] Output directory created
- [ ] Asset directory created
- [ ] Backup location defined

---

# 32. Acceptance Criteria

The project is considered successful when:

1. A user can provide new proposal requirements.
2. The system identifies relevant approved references.
3. The system separates content references from layout references.
4. The system applies the Xebia design system.
5. The system generates a coherent proposal plan.
6. The system generates PPTX.
7. The system generates DOCX.
8. PPT and DOCX share the same facts and storyline.
9. Generated files pass structural QA.
10. Generated files pass visual QA.
11. No unintended legacy customer information appears.
12. Provenance is recorded.
13. Reference permissions are respected.
14. Existing PPTX/DOCX skills are reused rather than duplicated.
15. The system can ingest additional reference documents without architectural changes.

---

# 33. Questions That Must Be Resolved Before Coding

This is the final gate.

Do not begin full implementation until these are answered:

### Business

- [ ] Who are the users?
- [ ] What proposal types are in scope?
- [ ] What is the MVP?
- [ ] What is the expected document volume?
- [ ] Who approves generated proposals?

### Brand

- [ ] What are the official Xebia brand guidelines?
- [ ] Which PPT template is authoritative?
- [ ] Which DOCX template is authoritative?
- [ ] Which fonts/colors/logo variants are approved?

### Data

- [ ] Which reference documents are approved?
- [ ] Which are confidential?
- [ ] Which are reusable?
- [ ] How are versions handled?

### AI

- [ ] Which LLM?
- [ ] Which embedding model?
- [ ] Can proposal data leave the organization's environment?
- [ ] Is Azure OpenAI preferred?
- [ ] Is visual embedding required for MVP?

### Retrieval

- [ ] What metadata filters are required?
- [ ] What should be embedded?
- [ ] What is the ranking strategy?
- [ ] Is reranking required for MVP?

### Infrastructure

- [ ] Local PostgreSQL or hosted PostgreSQL?
- [ ] Docker or native installation?
- [ ] Local file storage or cloud storage?
- [ ] Development/test/production environments?

### Security

- [ ] Authentication?
- [ ] Authorization?
- [ ] Document-level permissions?
- [ ] Audit logging?
- [ ] Retention policy?

### Output

- [ ] PPT only?
- [ ] DOCX only?
- [ ] Both?
- [ ] PDF required?
- [ ] Speaker notes required?
- [ ] Proposal provenance report required?

---

# 34. Recommended Starting Point

The recommended first implementation sequence is:

```text
1. Answer pre-implementation questions
          ↓
2. Collect approved Xebia reference material
          ↓
3. Obtain official Xebia brand assets
          ↓
4. Inspect existing DOCX/PPTX skills
          ↓
5. Create repository structure
          ↓
6. Set up PostgreSQL + pgvector
          ↓
7. Create database schema/migrations
          ↓
8. Build reference ingestion
          ↓
9. Build metadata/classification
          ↓
10. Build text embeddings
          ↓
11. Build hybrid retrieval
          ↓
12. Build Xebia design system
          ↓
13. Build slide/document pattern library
          ↓
14. Build proposal planner
          ↓
15. Build PPT generator
          ↓
16. Build DOCX generator
          ↓
17. Build QA
          ↓
18. Run end-to-end pilot
          ↓
19. Evaluate
          ↓
20. Add reranking/visual embeddings if justified
```

---

# 35. Important Architectural Principle

Do not allow embeddings to become the entire intelligence layer.

The system should combine:

```text
Structured Knowledge
        +
Keyword Search
        +
Semantic Embeddings
        +
Layout/Pattern Metadata
        +
Xebia Design System
        +
LLM Reasoning
        +
Deterministic QA
```

The strongest architecture is therefore:

> **PostgreSQL + pgvector for knowledge and retrieval, filesystem/object storage for files, a deterministic Xebia Design System for branding, existing PPTX/DOCX skills for document engineering, and Claude for reasoning/orchestration.**

---

# 36. Next Implementation Prompt

Once this blueprint and the prerequisite questions are answered, the implementation task given to Claude Code should be:

> Inspect the existing repository and existing DOCX/PPTX skills. Do not rewrite existing capabilities unnecessarily. Implement the Xebia Proposal Studio architecture defined in this blueprint. First create the repository structure, configuration, PostgreSQL/pgvector setup, migrations, reference ingestion pipeline, metadata/classification model, Xebia design-system foundation, and tests. Do not generate production proposal templates until the provided Xebia brand assets and approved reference decks/documents have been analyzed. Report all missing prerequisites before proceeding with dependent implementation.

---

# 37. Definition of Done

The project is not "done" when Claude can generate a PPT.

It is done when the system can reliably perform:

```text
New Requirement
      ↓
Understand
      ↓
Retrieve approved references
      ↓
Select content patterns
      ↓
Select Xebia layouts
      ↓
Build proposal storyline
      ↓
Generate PPT + DOCX
      ↓
Apply Xebia branding
      ↓
Validate
      ↓
Visually inspect
      ↓
Correct defects
      ↓
Record provenance
      ↓
Deliver
```

That is the target **Xebia Proposal Studio**.

---

# 38. Decisions Log — Pre-Implementation Answers

> **Last updated:** 2026-08-18

## 38.1 Brand Assets — RESOLVED (Testing Phase)

- **No formal brand guidelines exist for this phase.** The system is in a testing/prototyping stage.
- **PPT theme:** Inspired by the Xebia logo — purple organic blob shape (`~9B2D8B` / purple family) with white text. The design system will derive its palette and visual motifs from this logo.
- **DOCX theme:** Standard black text with selective use of brand purple and the Xebia logo at key positions (cover, headers/footers).
- **Logo:** Xebia logo PNG available (purple blob with white "Xebia" wordmark). SVG to be created or sourced later.
- **Fonts:** No mandated fonts — system will select professional safe fonts (see PPT skill typography guidance).
- **Rigid guidelines:** None enforced at this stage. The system should produce professional, brand-consistent output that *looks like Xebia* without needing a formal brand manual.

## 38.2 Existing Skills — RESOLVED

- **Location:** `Skills/PPT_Skill.md` and `Skills/Doc_Skill.md` in the project root.
- **Status:** Both skills are mature and cover creation, editing, analysis, QA, rendering, and validation.
- **Action:** Skills will be relocated/renamed as needed during project setup. They must be reused, not rebuilt.

## 38.3 Business Decisions — RESOLVED

- **Primary user (MVP):** Project owner (Suryadev Rathore) — single-user testing.
- **Future users:** Sales, pre-sales, and occasionally solution architects.
- **Proposal types (MVP):** All types in scope for testing — customer proposals, RFP responses, SOWs, capability decks, technical proposals.
- **Approval workflow (MVP):** Not needed — single user reviews output directly.

## 38.4 AI & Data Governance — RESOLVED

- **Goal:** Minimize cost during testing phase. Production will use Claude or equivalent.
- **Embedding provider:** To be selected — preference for free/open options. Candidates:
  - **Recommended for zero-cost testing:** Local embedding model via `sentence-transformers` (e.g., `all-MiniLM-L6-v2`, 384 dimensions) — runs locally, no API cost, good quality for MVP.
  - **Alternative:** Free-tier API such as Voyage AI free tier, Jina Embeddings free tier.
- **LLM for orchestration:** Claude Code is already available in the development environment. For programmatic API calls during generation, options:
  - Use Claude Code itself as the reasoning layer (no additional API cost during development).
  - For production: Claude API or Azure OpenAI.
- **Data governance:** No restrictions during testing phase — local data, local processing.

## 38.5 Infrastructure — RESOLVED

- **PostgreSQL:** Local native installation (not Docker, not hosted).
- **pgvector:** Installed as extension on local PostgreSQL.
- **File storage:** Local filesystem.
- **Language:** Python as the primary language for the pipeline.
- **Environments:** Development only for now.

## 38.6 Security — RESOLVED (MVP)

- **Access:** Internal only, single user.
- **Authentication/Authorization:** Not needed for MVP.
- **Role-based access:** Not needed for MVP.
- **Audit logging:** Not needed for MVP.
- **Document-level permissions:** Not needed for MVP.

## 38.7 Reference Documents — ⚠️ PENDING

- **Status:** No reference documents provided yet.
- **Required:** 5–20 approved Xebia proposal PPTs and 5+ approved DOCXs for pattern discovery, ingestion pipeline testing, and embedding generation.
- **Action needed:** Project owner to collect and place approved reference materials in the `references/approved/` directory.
- **Note:** The ingestion pipeline, embedding generation, and retrieval system cannot be meaningfully tested without real reference documents. Repository structure, database schema, design system foundation, and skill integration can proceed without them.

## 38.8 Output Requirements — RESOLVED

- **PPT:** Yes
- **DOCX:** Yes
- **PDF:** Not required for MVP (can be generated via LibreOffice from PPT/DOCX)
- **Speaker notes:** Not required for MVP
- **Provenance report:** Yes (part of core architecture)
