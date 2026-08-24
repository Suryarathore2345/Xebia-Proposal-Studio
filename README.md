# Xebia Proposal Studio

An AI-powered tool that turns a short conversation into a complete, branded Xebia proposal — a polished PowerPoint deck and matching Word document, generated end-to-end from a chat interface.

## What it does

1. **Chat** — describe the engagement (customer, objective, technologies, timeline, team, budget). The assistant asks clarifying questions if key details are missing, then produces a structured proposal plan (cover, executive summary, architecture, timeline, commercials, case studies, etc.).
2. **Design** — a design engine picks a cohesive visual theme and a blueprint (background, layout zones, accents) for every slide, so each deck looks intentionally designed rather than templated.
3. **Generate** — the plan is rendered into a `.pptx` and a `.docx`, including custom-drawn architecture diagrams, a week-ruled Gantt timeline, tables, and stock/uploaded imagery.

Content generation is powered by Claude (default) with an optional Gemini toggle for side-by-side testing.

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY at minimum
python src/web/app.py
```

Open `http://127.0.0.1:8000` and start describing a proposal.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude — proposal content, design theme, blueprint selection |
| `GEMINI_API_KEY_1..N` | No | Gemini — only used by the chat UI's provider toggle for testing |
| `PEXELS_API_KEY` | No | Stock photos on content/cover slides |

See `.env.example` for the full list.

## Architecture

```
src/
├── web/            FastAPI app + chat UI (src/web/static/index.html)
├── planner/         ProposalSession — orchestrates chat → plan → generate
├── llm/              Claude/Gemini clients (proposal plan, theme, blueprint prompts)
├── generation/
│   ├── design_engine/   Theme generation, blueprint registry, per-slide design selection
│   ├── diagrams/         Architecture & migration-flow diagram renderers
│   ├── slide_builders.py  Low-level PPTX slide rendering (the real renderer)
│   ├── pptx_generator.py  Orchestrates slide_builders.py per the plan's storyline
│   └── docx_generator.py  Word document generation
├── extraction/       Parses past Xebia decks/docs into structured JSON (reference mining)
├── retrieval/        Local embedding + semantic search over extracted reference material
└── images/            Tech icon library (Azure/AWS/Fabric/etc.) for architecture diagrams
```

See [`PROJECT_FLOW.md`](PROJECT_FLOW.md) for a step-by-step trace of a single request from chat message to downloaded files, and [`Xebia_Proposal_Studio_Project_Blueprint.md`](Xebia_Proposal_Studio_Project_Blueprint.md) for the original design blueprint.

## Reference material (optional)

Dropping past, approved Xebia decks into `references/approved/{ppt,docx}/` lets the tool mine real structural patterns (which layout fits which content, typical slide density) via semantic search — it's told explicitly never to copy client names or numbers from them, only structure and style. Run the pipeline after adding files:

```bash
python scripts/extraction/extract_all_pptx.py references/approved/ppt extracted/ppt
python scripts/indexing/embed_all.py
```

Embeddings run locally via `sentence-transformers` (no API key, but the model is fetched from Hugging Face on first run). Reference documents and everything derived from them (`extracted/`, `references/approved/**/*.pptx|docx|pdf`) are git-ignored — they never leave your machine.

## Development

- No automated test suite yet; verify changes by generating a deck through the chat flow and inspecting the output.
- `scripts/` contains standalone utilities (icon library build/validation, tech icon download, reference extraction/indexing).
