# Xebia Proposal Studio — Complete Project Flow

## Flow 1: User Input to Final Proposal Documents

This flow traces every step from the moment a user types a proposal request to when they download the finished PPT and DOCX files.

---

### Step 1: User Opens the Web App

**What happens:** The browser loads `http://127.0.0.1:8000` which serves the Xebia-branded chat UI.

**How:** FastAPI (`src/web/app.py`) serves the static HTML from `src/web/static/index.html`. The UI is a single-page chat interface with:
- A text input area for describing the proposal
- Quick-start template buttons (Fabric Migration, Data Platform, MDM, Workshop)
- A chat message area that shows the conversation

**Files involved:** `src/web/app.py` → `src/web/static/index.html`

---

### Step 2: User Submits a Proposal Request

**What happens:** The user types something like _"Create a Data & AI proposal for RetailMax Inc, recommendation engine, analytics, $500K, 6 months"_ and hits Enter.

**How:** The frontend sends a `POST /api/chat` request with:
```json
{
  "message": "Create a Data & AI proposal for RetailMax...",
  "session_id": null
}
```

**Files involved:** `src/web/static/index.html` (JavaScript fetch call)

---

### Step 3: Backend Creates a Proposal Session

**What happens:** The FastAPI endpoint receives the chat request and creates a new `ProposalSession` if one doesn't exist.

**How:** `app.py` calls `_get_or_create_session()` which instantiates a `ProposalSession` — a stateful object that tracks the entire lifecycle:
- `session_id`: Unique 12-char hex ID
- `history`: Full conversation log
- `plan`: The generated proposal structure (None until ready)
- `status`: One of `chatting` → `plan_ready` → `generating` → `complete`
- `generated_files`: Paths to the generated PPTX and DOCX

**Files involved:** `src/web/app.py` → `src/planner/proposal_planner.py`

---

### Step 4: Semantic Search for Reference Content

**What happens:** The system searches its knowledge base of previously extracted proposals to find relevant reference content that will be fed to the LLM.

**How:** `ProposalSession.chat()` calls `_find_references(user_message)` which:

1. **Embeds the query:** Uses `sentence-transformers/all-MiniLM-L6-v2` (a 384-dim local embedding model) to convert the user's text into a vector.

2. **Loads the embedding store:** Reads `extracted/embeddings/embeddings.json` — a JSON file containing pre-computed embeddings of all reference slides and document sections.

3. **Computes cosine similarity:** Compares the query vector against every stored vector, filtering by minimum score (0.25).

4. **Returns categorized results:** Separates results into:
   - `content_references`: Top 15 most relevant text chunks (used as context for the LLM)
   - `slide_references`: Reference slide examples
   - `section_references`: Reference document sections
   - `layout_references`: One of each slide type for layout guidance

**Why:** This gives the LLM real Xebia proposal content as examples, so the generated proposal uses domain-specific language and realistic data instead of generic filler.

**Files involved:** `src/planner/proposal_planner.py` → `src/retrieval/search.py` → `src/retrieval/embedder.py` → `src/retrieval/embedding_store.py`

---

### Step 5: LLM Generates the Proposal Plan

**What happens:** Claude Sonnet 5 receives the user's request + reference content (and any uploaded images) and generates a complete structured proposal plan as JSON, via a forced tool call.

**How:** `generate_proposal_plan()` in `llm/anthropic_client.py`:

1. **Constructs the prompt:** Combines:
   - A detailed SYSTEM_PROMPT (~3000 words, sent as a cached system block) that defines:
     - Conversational behavior (ask clarifying questions if needed)
     - The exact JSON output structure required (enforced via the `submit_proposal_plan` tool schema, not free-text parsing)
     - All 12 available slide layouts with their data schemas
     - Content quality rules (no empty sections, specific content, 6-7 different layouts, etc.)
     - The complete storyline structure (16 possible sections)
     - How to place user-uploaded "embed" images onto the most relevant slide via `image_placements`
   - The user's message
   - Reference content, layout references, and slide references from the search results
   - Conversation history (for multi-turn refinement)
   - Any reference or embed images attached to the session, sent as vision content blocks

2. **Calls the Claude API:** Sends to `claude-sonnet-5` with `max_tokens=16000`, `temperature=0.7`, and `tool_choice` forced to `submit_proposal_plan` so the response is always valid structured JSON.

3. **Reads the tool call:** Claude returns either:
   - `{"ready": false, "message": "...clarifying questions..."}` — if more info is needed
   - `{"ready": true, "title": "...", "customer": "...", "storyline": [...], "sections": {...}, "image_placements": [...]}` — the complete plan

4. **Review & improve pass:** Before the plan is shown to the user, `ProposalSession.chat()` sends it back through `review_and_improve_plan()` — a second Claude call (its own system prompt, `REVIEW_SYSTEM_PROMPT`) that checks content quality, storyline flow, layout variety, architecture realism, cross-section consistency, and completeness, and returns a corrected plan in the same schema. If this call fails for any reason, the original unreviewed plan is used instead so generation never blocks on it.

5. **The plan structure:** When ready, it contains:
   ```
   {
     "ready": true,
     "title": "Data & AI Platform Transformation",
     "customer": "RetailMax Inc.",
     "objective": "...",
     "storyline": ["cover", "table_of_contents", "executive_summary", ...],
     "sections": {
       "cover": { "title": "...", "subtitle": "..." },
       "executive_summary": { "title": "...", "summary": "...", "key_points": [...] },
       "proposed_solution": {
         "title": "...",
         "slides": [
           { "layout": "content", "title": "...", "bullets": [...] },
           { "layout": "two_column", "title": "...", "left": {...}, "right": {...} },
           { "layout": "architecture", "title": "...", "layers": [...] }
         ]
       },
       ...
     }
   }
   ```

**Why Claude decides the layout:** Each section can contain multiple slides, and each slide specifies a `layout` field (content, two_column, icon_grid, process_flow, architecture, stats_highlight, etc.). The LLM picks the best layout based on the content type — lists become icon_grid, comparisons become two_column, metrics become stats_highlight, etc.

**Files involved:** `src/planner/proposal_planner.py` → `src/llm/anthropic_client.py` → Claude API

---

### Step 6: Frontend Shows the Plan & Generate Button

**What happens:** The backend returns the plan summary and the frontend shows a "Proposal Plan Ready" card with title, customer, section count, and a "Generate Proposal Documents" button.

**How:** The `/api/chat` response comes back with `ready: true` and `plan_summary`. The frontend JavaScript renders the plan card and the generate button. The session transitions to `plan_ready` status.

**Files involved:** `src/web/static/index.html` (JavaScript rendering)

---

### Step 7: User Clicks "Generate Proposal Documents"

**What happens:** The frontend sends `POST /api/generate/{session_id}` which triggers the actual document generation.

**How:** `ProposalSession.generate()` runs two independent generators:

#### 7a. PPTX Generation

1. **Load template:** `create_presentation()` loads `templates/xebia_retail.pptx` — a clean Xebia template with 30 pre-designed slide layouts, branded backgrounds, decorative elements, and proper styling.

2. **Walk the storyline:** `ProposalPPTGenerator.generate()` iterates through the `storyline` array in order and dispatches each section to the appropriate builder method via `SECTION_BUILDERS` dict:
   ```
   "cover"              → _build_cover()
   "table_of_contents"  → _build_toc()
   "executive_summary"  → _build_exec_summary()
   "proposed_solution"  → _build_content_section()
   "architecture"       → _build_content_section()
   "timeline"           → _build_timeline()
   "team_structure"     → _build_team()
   "commercials"        → _build_commercials()
   "closing"            → _build_closing()
   ```

3. **Build each slide:** Each builder in `slide_builders.py`:
   - Finds the correct template layout by name (`_get_layout("Content_Basic")`)
   - Creates a new slide from that layout (`prs.slides.add_slide(layout)`)
   - Fills the template's placeholders with content (`_fill_placeholder(slide, idx, text)`)
   - For complex layouts (architecture, timeline, process_flow, stats), adds custom shapes on top of the template's built-in decorative elements

4. **Layout mapping:**
   | Content Type | Template Layout | What It Provides |
   |---|---|---|
   | Cover | Main-cover_dark | Purple gradient background, Xebia logo, decorative curves |
   | Section dividers | Chapter_dark | Dark purple background, chapter number area |
   | Content slides | Content_Basic | White background, title area, body area, branded footer |
   | Two columns | Content_2 Columns | Two-column layout with headers and icon placeholders |
   | Three columns | Content_3 Columns | Three-column grid with icons |
   | Table of contents | Table of contents | Two-column numbered list layout |
   | Closing | End-cover_dark | Dark branded closing with contact area |

5. **Content sections with multiple slides:** For sections like `proposed_solution` that contain a `slides` array, each slide is dispatched through `build_slide_by_layout()` which routes by the `layout` field (content, two_column, icon_grid, process_flow, comparison_table, stats_highlight, key_value, architecture, technology, challenges).

6. **Place uploaded images:** For every entry in the plan's `image_placements`, `ProposalPPTGenerator` inserts the referenced upload as a dedicated photo slide immediately after its target slide (never overlaid on top of an already-rendered layout, so architecture diagrams, tables, and stat grids are never disturbed).

7. **Save:** The finished Presentation object is saved to `outputs/ppt/{customer}_{timestamp}.pptx`.

#### 7b. DOCX Generation

1. **Create document:** Uses `python-docx` with `Document()` (no template — styling is applied programmatically).

2. **Walk sections:** Similar to PPTX — iterates the storyline and dispatches to builder functions.

3. **Extract content from all layout types:** The `_render_layout_content()` method handles converting every slide layout's data into appropriate Word content — items become bulleted lists, tables become Word tables, stats become formatted key-value pairs, architecture layers become nested lists, etc.

4. **Apply Xebia branding:** All text uses Arial font, section headings use the purple (#6C1D5F) color, tables have purple headers.

5. **Save:** Written to `outputs/docx/{customer}_{timestamp}.docx`.

**Files involved:**
- PPT: `src/generation/pptx_generator.py` → `src/generation/slide_builders.py` → `templates/xebia_retail.pptx`
- DOCX: `src/generation/docx_generator.py`
- Design system: `src/design_system/brand.py` → `xebia_design_system/brand/{colors,typography,spacing}.json`

---

### Step 8: User Downloads the Files

**What happens:** The frontend shows download cards for both PowerPoint and Word documents. Clicking either triggers a file download.

**How:** The frontend calls `GET /api/download/{session_id}/{format}` where format is `pptx` or `docx`. FastAPI returns the file with the appropriate MIME type using `FileResponse`.

**Files involved:** `src/web/app.py` (download endpoint) → file on disk

---

### Complete Request Flow Diagram

```
User types request
       │
       ▼
[Frontend] ──POST /api/chat──► [FastAPI app.py]
                                      │
                                      ▼
                              [ProposalSession.chat()]
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
              [Semantic Search]            [Claude LLM Call]
              search.py → embedder.py      anthropic_client.py
              embedding_store.py           claude-sonnet-5
                         │                         │
                         └────────────┬────────────┘
                                      │
                                      ▼
                              Plan JSON returned
                                      │
                                      ▼
                              [Review & Improve Pass]
                              anthropic_client.py
                              review_and_improve_plan()
                                      │
                                      ▼
                              Corrected plan JSON
                              (storyline + sections + image_placements)
                                      │
                                      ▼
                              [Frontend shows plan card]
                              [User clicks Generate]
                                      │
                                      ▼
                       POST /api/generate/{session_id}
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
              [PPTX Generator]            [DOCX Generator]
              pptx_generator.py           docx_generator.py
              slide_builders.py
              xebia_retail.pptx (template)
                         │                         │
                         ▼                         ▼
              outputs/ppt/*.pptx          outputs/docx/*.docx
                         │                         │
                         └────────────┬────────────┘
                                      │
                                      ▼
                              GET /api/download/...
                              [User downloads files]
```

---

## Flow 2: Adding New Reference Documents

This flow explains how new reference proposals (PPT or DOCX files) are processed and incorporated into the system's knowledge base, making future proposals more relevant and better informed.

---

### Step 1: Place the Reference File

**What happens:** A new reference proposal file (`.pptx` or `.docx`) is placed in the `Documents/` directory.

**How:** Simply copy the file into `Documents/`. The system supports:
- `.pptx` files — PowerPoint proposals, case studies, kickoff decks
- `.docx` files — Word proposals, SOWs, project documents

**Example:** `Documents/Xebia-NewClient-Azure-Migration-Proposal.pptx`

---

### Step 2: Run the Extraction Pipeline

**What happens:** The extraction pipeline reads the file and produces a structured JSON representation of all its content.

**How:** Run the appropriate extractor:

```bash
# For PPTX files
python -m src.extraction.pptx_extractor Documents/NewFile.pptx

# For DOCX files  
python -m src.extraction.docx_extractor Documents/NewFile.docx
```

#### PPTX Extraction (`src/extraction/pptx_extractor.py`):

For each slide, the extractor captures:
- **Text content:** All text from shapes, text boxes, and placeholders
- **Slide classification:** Automatically categorizes each slide as cover, executive_summary, architecture, timeline, team, commercials, case_study, closing, section_divider, or content — using keyword matching
- **Visual metadata:** Flags for has_chart, has_table, has_image, has_diagram
- **Layout info:** Shape count, image count, word count, content density

The output JSON looks like:
```json
{
  "metadata": {
    "filename": "NewFile.pptx",
    "slide_count": 25,
    "title": "...",
    "created_date": "...",
    "modified_date": "..."
  },
  "classification": {
    "industries": ["retail", "data"],
    "technologies": ["azure", "databricks"],
    "proposal_type": "implementation"
  },
  "slides": [
    {
      "slide_number": 1,
      "slide_type": "cover",
      "text": "Full extracted text...",
      "word_count": 42,
      "has_image": true,
      "shapes": [...]
    },
    ...
  ]
}
```

#### DOCX Extraction (`src/extraction/docx_extractor.py`):

Similar but section-based:
- **Section hierarchy:** Detects headings and groups content under them
- **Tables:** Extracts all table content
- **Image count:** Counts embedded images
- **Classification:** Detects industries, technologies, document type

Output saved to: `extracted/ppt/{filename}.json` (PPTX) or `extracted/docx/{filename}.json` (DOCX)

---

### Step 3: Generate Embeddings

**What happens:** The extracted text is converted into vector embeddings for semantic search.

**How:** Run the embedder:

```bash
# For PPTX extractions
python -c "
from src.retrieval.embedder import embed_pptx_extraction
result = embed_pptx_extraction('extracted/ppt/NewFile.json')
print(result)
"

# For DOCX extractions
python -c "
from src.retrieval.embedder import embed_docx_extraction
result = embed_docx_extraction('extracted/docx/NewFile.json')
print(result)
"
```

The embedder (`src/retrieval/embedder.py`):

1. **Reads the extraction JSON:** Loads all slides or sections from the extracted file.

2. **Filters short content:** Skips any slide/section with less than 20 characters of text (decorative slides, blank pages).

3. **Deduplicates:** Computes an SHA-256 hash of each text chunk and skips any that already exist in the embedding store — so re-running the pipeline on the same file is safe and idempotent.

4. **Generates embeddings:** Uses `all-MiniLM-L6-v2` (runs locally, no API needed) to encode each text chunk into a 384-dimensional vector. Batched at 32 items for efficiency.

5. **Saves to store:** Appends the new entries to `extracted/embeddings/embeddings.json` with:
   - `entity_type`: "slide" or "section"
   - `source_file`: Original filename
   - `entity_id`: Slide number or section index
   - `text`: The text content (truncated to 500 chars for display)
   - `content_hash`: For dedup
   - `embedding`: The 384-dim vector
   - `metadata`: Slide type, industries, technologies, word count

---

### Step 4: Verify the New Content is Searchable

**What happens:** Test that the new content appears in search results.

**How:**
```bash
python -c "
from src.retrieval.search import search
results = search('azure migration', top_k=5)
for r in results:
    print(f'{r[\"score\"]:.3f} [{r[\"entity_type\"]}] {r[\"source_file\"]} — {r[\"text\"][:80]}')
"
```

---

### Step 5: The Content is Now Live

**What happens:** The next time a user creates a proposal, the semantic search automatically finds relevant content from the new reference document and feeds it to Gemini as context.

**How:** No restart needed — the search function reads the embedding store fresh on each query. The new content is immediately available for:
- Providing domain-specific language and terminology
- Offering real-world examples and case studies
- Informing technology recommendations
- Guiding pricing and timeline estimates

---

### Adding New Reference Documents — Complete Pipeline

```
New .pptx or .docx file
         │
         ▼
  Documents/ directory
         │
         ▼
  [Extraction Pipeline]
  pptx_extractor.py  or  docx_extractor.py
         │
         ▼
  extracted/ppt|docx/{file}.json
  (structured text, metadata, classification)
         │
         ▼
  [Embedding Pipeline]
  embedder.py → all-MiniLM-L6-v2
         │
         ▼
  extracted/embeddings/embeddings.json
  (384-dim vectors + metadata)
         │
         ▼
  [Automatically Available]
  search.py uses cosine similarity
  to find relevant content for
  every new proposal request
```

---

### Automating the Pipeline (Future Enhancement)

Currently the extraction and embedding steps are manual. To automate:

1. **File watcher:** Add a `watchdog` service that monitors `Documents/` for new files and automatically runs extraction + embedding.

2. **API endpoint:** Add `POST /api/ingest` to the web app that accepts file uploads and runs the pipeline.

3. **Batch processing:** Add a management command:
   ```bash
   python -m src.scripts.ingest_all
   ```
   That scans `Documents/` for any files not yet in the embedding store and processes them.

---

## Project Directory Structure

```
Doc_Creation_Tool/
├── .env                          # ANTHROPIC_API_KEY (never committed)
├── .claude/launch.json           # Dev server config for Claude Code
├── templates/
│   ├── xebia_retail.pptx         # Primary Xebia template
│   └── from_documents/           # Other registry templates (xebia_synapse,
│                                  # xebia_pnb, xebia_mohesr, xebia_carrington,
│                                  # etc.) — see TEMPLATE_REGISTRY in
│                                  # src/generation/template_engine.py
├── Documents/                    # Reference proposals for knowledge base
├── extracted/
│   ├── ppt/ , docx/              # JSON extractions of reference docs
│   └── embeddings/               # Vector embedding store
├── outputs/
│   ├── ppt/                      # Generated PPTX files
│   └── docx/                     # Generated DOCX files
├── xebia_design_system/
│   └── brand/
│       ├── colors.json           # Purple #6C1D5F, accent palette
│       ├── typography.json       # Arial, size scales
│       └── spacing.json          # 13.33x7.50 canvas dimensions
└── src/
    ├── web/
    │   ├── app.py                # FastAPI backend
    │   └── static/index.html     # Chat UI
    ├── planner/
    │   └── proposal_planner.py   # Session orchestrator
    ├── llm/
    │   └── anthropic_client.py   # Claude API + system prompt + review pass
    ├── retrieval/
    │   ├── search.py             # Cosine similarity search
    │   ├── embedder.py           # Embedding generation
    │   └── embedding_store.py    # JSON-based vector store
    ├── extraction/
    │   ├── pptx_extractor.py     # PPT → JSON extraction
    │   └── docx_extractor.py     # DOCX → JSON extraction
    ├── generation/
    │   ├── pptx_generator.py     # Storyline → PPTX dispatcher
    │   ├── slide_builders.py     # 18 template-based slide builders
    │   └── docx_generator.py     # Storyline → DOCX generator
    └── design_system/
        └── brand.py              # Loads colors/typography/spacing from JSON
```

---

## Key Technologies

| Component | Technology | Why |
|---|---|---|
| Web Framework | FastAPI + Uvicorn | Async, auto-docs, fast |
| LLM | Claude Sonnet 5 | 16K output tokens, forced tool-call JSON, vision for uploaded images |
| Embeddings | all-MiniLM-L6-v2 | Local, fast, 384-dim, no API cost |
| PPT Generation | python-pptx | Full programmatic control of PPTX |
| DOCX Generation | python-docx | Full programmatic control of DOCX |
| Vector Store | JSON file | Simple, no DB needed for MVP |
| Frontend | Vanilla HTML/CSS/JS | No build step, single file |
