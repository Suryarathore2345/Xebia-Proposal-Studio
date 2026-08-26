# Deck Visual/Layout QA — Findings & Fix Plan

> **Addendum (same day, later testing)**: a full end-to-end test with an explicit "no individual team-member names" instruction revealed the request wasn't honored — the shared `SECTION_SCHEMA` prompt hard-codes a "realistic name" example for every team member with no opt-out, so the model fabricated 6 names anyway despite the inline chat instruction. Fixed with a deterministic, non-LLM-dependent mechanism in `proposal_planner.py`: `_wants_anonymous_team()` scans the conversation for phrases like "role only", "no names", "anonymiz*"; when matched, `_strip_team_names()` nulls every member's `name` field in the plan *after* generation, regardless of what the model actually returned. `SECTION_SCHEMA` also gained explicit guidance to set `name: null` itself when asked, so well-behaved runs get it right without needing the stripping fallback at all. Both renderers (`build_team_slide` in `slide_builders.py`, `_build_team_structure` in `docx_generator.py`) updated to render sensibly with no name — role becomes the card headline, initials derive from role instead of name, and the docx table drops its Name column entirely rather than showing one blank. Verified: named case renders byte-identical to before (same offsets, same 3-column docx table); no-name case shows zero names in either format, full pipeline regression passes. (One of the two "bugs" originally suspected here — an apparently-empty docx team table — turned out to be a verification mistake on my part: `doc.paragraphs` never includes table content in python-docx; `doc.tables` showed the table was fully populated all along.)

**Date:** 2026-08-25
**Subject deck:** `outputs/ppt/Meridian_National_Health_Autho_20260825_155625.pptx` (44 slides, generated live via the actual web app / Gemini provider — not a synthetic test fixture)

## Methodology and its limits

This environment has no PowerPoint or LibreOffice, so nothing here comes from actually looking at rendered pixels — it comes from parsing the OOXML shape geometry (position, size, fill, z-order, text, font size, word-wrap) with python-pptx and reasoning about what PowerPoint would do with those exact values. That's a real constraint worth being upfront about:

- **Overlap detection is reliable** — bounding-box math doesn't lie about whether two shapes' rectangles intersect.
- **Text-overflow detection is an estimate** — there's no real text-layout engine here, so "does this text fit in this box" is approximated from character count, font size, and box width (a monospace-ish per-character-width heuristic). It correctly flagged known-bad cases (confirmed by checking `auto_size`/`word_wrap` settings directly) but the exact wrap point in real PowerPoint will differ slightly.
- **A first automated pass was very noisy** — this deck's design language legitimately draws text on top of colored backgrounds constantly (title badges, pills, cards, bands) — every one of those looks like "overlap" to a naive bounding-box scan. The first pass flagged ~600+ "overlaps" on this basis; after excluding full-slide background rectangles and the deck's own nested-container pattern (zone → group → item, each a background rectangle with text legitimately drawn inside it), the list narrowed to a much smaller set of genuinely suspicious cases, which were then individually traced back to actual rendering code to confirm or reject them as real defects. **Every finding below was confirmed by reading the specific code that produces it**, not left as a raw heuristic hit.
- I could not verify the "excessive empty space" and "oversized architecture boxes" complaints visually — I quantified them geometrically instead (see Finding 4), which is a solid proxy but not the same as looking at the slide.

**Bottom line**: treat the findings below as high-confidence and code-grounded, but do a real visual pass in PowerPoint once these are fixed — this audit can catch geometry bugs, not "does this look good."

---

## Findings

### Finding 1 — Migration-flow diagrams: content collides with the slide's own title
**Severity: High. Scope: every `migration_flow` slide in every deck** (confirmed on slides 18 and 19 of this deck; not new — predates this session's work).

`MigrationFlowRenderer.content_top = 1.15` ([migration_flow_renderer.py:111](../../src/generation/diagrams/migration_flow_renderer.py)) positions the diagram's first zone title badges starting around y≈1.02 (badges are drawn straddling `content_top`, half above/half below). The slide's own title placeholder occupies y≈1.0–1.4 (confirmed from the actual rendered geometry: box `[0.45, 1.0, 8.21, 0.4]`). These two ranges overlap by design distance, not by accident of this particular content — **every** migration_flow slide has this collision built in, regardless of what's in the diagram.

Verified via direct geometry: the slide title text box and the diagram's zone title badges ("On-Premises Data Center", "Connectivity Hub Subscription", "Data Platform Spoke Subscription") overlap at 100%, 100%, and 71% of the badge's own area respectively.

**Compounding issue**: the title placeholder itself has `auto_size = None` (no shrink-to-fit) with `word_wrap = True` — confirmed by direct inspection. A long AI-generated title like "End-to-End Microsoft Fabric Data Flow Architecture" (51 chars at 24pt) needs an estimated ~0.81in but the placeholder is only 0.4in tall, so it will wrap to a second line and bleed downward with nothing to stop it — directly into the diagram content below. This makes Finding 1 worse specifically on slides with long titles (which the AI reliably produces for architecture slides).

**Root cause location**: `MigrationFlowRenderer.__init__` (`content_top`), and `_fill_ph`'s title-placeholder handling in `slide_builders.py`.

**Proposed fix**:
1. Raise `content_top` in `MigrationFlowRenderer.__init__` from `1.15` to roughly `1.55–1.65` (enough to clear a 2-line title at 24pt plus margin). This is a single-constant change, isolated to this one renderer.
2. Give title placeholders on layouts that can carry long AI-generated titles (`migration_flow`, `architecture`, and worth checking others) `MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE` so PowerPoint shrinks oversized titles instead of letting them wrap-and-bleed with no floor. This is a small, targeted addition to `_fill_ph`, gated to specific layouts (not a global change to every slide's title behavior, since most titles are short and don't need it).

**Regression risk & how to check it**: Change 1 only affects `MigrationFlowRenderer`'s vertical layout math — it shifts everything below `content_top` down uniformly, and `render()` already computes `total_h`/the outer container size *from* `content_top` and the content it lays out, so nothing needs to be recomputed by hand. Re-render both `scripts/test_architecture_gen.py --static` and `--landing-zone` after the change and confirm (a) no shape's bottom edge now exceeds `content_height` (7.5in slide height minus margin) and (b) the outer diagram frame no longer overlaps the title placeholder's y-range. Change 2 touches `_fill_ph`, which is shared by every layout — restrict the autosize change to a `layout_name` allow-list parameter rather than making it unconditional, and re-render one slide from each layout type afterward to confirm no other slide's title regresses (a short title with autosize enabled should render identically to one without it — autosize only engages when text actually overflows).

---

### Finding 2 — Qualifier-labeled icon items risk text overflow (this session's own regression)
**Severity: Medium-High. Scope: any `migration_flow` icon-style group item that uses the new `qualifier` field** (added this session, Phase 2).

`_draw_item_icons`'s per-item label height is a fixed `label_h = 0.16` ([migration_flow_renderer.py](../../src/generation/diagrams/migration_flow_renderer.py), `_draw_item_icons`) — sized for a short single-line label like "Power BI". The `qualifier` field I added this session (rendering as `"Name · qualifier"`) makes labels meaningfully longer — e.g. the real generated label *"Microsoft Fabric Capacity · F128 reserved compute"* (49 chars, 5.5pt) needs an estimated ~0.28in but only gets 0.16in. Confirmed on 8 separate items across slides 18 and 19 of the real generated deck, all following the same pattern.

With `word_wrap = True` and no auto_size set on this textbox (same `add_textbox` helper used throughout the diagram renderer — confirmed no autofit anywhere in it), an overflowing 2-line label doesn't shrink or clip — it bleeds downward past its 0.16in box, into whatever sits below it (the next row of icons in a multi-row group, or the group's own border in a single-row group).

This is a direct consequence of a feature I added this session (the `qualifier` field) straining a size assumption (`label_h = 0.16`) that was correct for the old plain-string-only items but not for the new richer ones — exactly the kind of "does the new thing break something that used to work" risk to check, since plain-string items (no qualifier) are unaffected and will still fit fine.

**Root cause location**: `_draw_item_icons` in `migration_flow_renderer.py`.

**Proposed fix**: make `label_h` (and the row height `item_total_h` it feeds into) content-aware — when an item has a qualifier (or the label text is long enough that it's likely to wrap), allocate a taller label slot (e.g. 0.28–0.30in for two lines) instead of the flat 0.16in, and adjust `_estimate_group_h`'s icon-style branch (used for zone-height budgeting) to match, so the extra room is accounted for up in `_estimate_zone_content_h`/`zones_h` too — otherwise fixing the label box alone just moves the overflow into the group/zone boundary instead of removing it.

**Regression risk & how to check it**: This only changes icon-style item rendering height, and only for items that actually have a qualifier or long text — plain short items should compute the same `label_h` as before (verify with a diff-free re-render of the `STATIC_DIAGRAM` fixture in `test_architecture_gen.py`, which has no qualifier items, to confirm zero visual change there). Then re-render `--landing-zone` (which does have one qualifier item) and confirm its icon rows no longer estimate overflow per this same audit script. Since this also changes `_estimate_group_h`, re-verify the zone total-height math still stays within `max_zones_h` (no slide overflow) on a dense case.

---

### Finding 3 — Nested landing-zone / sparse-zone imbalance produces genuinely oversized, empty-looking boxes
**Severity: Medium. Scope: any `migration_flow` diagram where zones have very different content depth — most visible in the new landing-zone archetype (Phase 3), which by design mixes a deeply-nested zone against simple flat ones.**

This is the "architecture boxes that are unnecessarily large" / "excessive empty space" complaint, and it's real — I measured it directly rather than estimating it. On slide 18, the "On-Premises Data Center" zone (2 simple items: SQL Server, a data gateway) has a group card whose background rectangle runs from y=1.37 to y=2.70 (1.33in tall), but the actual icon+label content inside only extends to about y=2.18 — **roughly 0.52in (≈32% of the card's height) is empty space inside a visibly bordered box**, sitting right next to a much denser nested-subscription zone that genuinely needs that height.

Root mechanism, confirmed by reading the code:
- `render()` computes one shared `zones_h` for **all** top-level zones, sized to whichever zone's content needs the most room (`zones_h = min(max(natural_h across all zones), max_zones_h)`) — so a simple 2-item zone gets stretched to match a deeply-nested subscription/VNet zone sitting right next to it.
- Within a zone, `_draw_zone` divides available height **evenly** across however many groups it has (`group_h = available_h / num_groups`), with no cap based on what that specific group's content actually needs — so a group's own background card always fills its full allotted slice, whether or not the content inside needs that much room.

This isn't a bug I introduced this session, but Phase 3's nested landing-zone archetype makes it much more visible in practice than it was before, because that archetype inherently produces zones with wildly different natural content depth (a 2-item source list next to a multi-level subscription→VNet→workload nest) — exactly the scenario that exposes uniform-height allocation as a problem.

**Root cause location**: `render()`'s `zones_h` computation and `_draw_zone`'s `group_h` division, both in `migration_flow_renderer.py`.

**Proposed fix** (this one is more invasive than Findings 1-2, so it should be scoped carefully):
1. Cap each group's card height at what `_estimate_group_h` says it actually needs (plus a small fixed padding), rather than always filling the full even-division slice — center or top-align the group within its allotted slice instead of stretching the card to fill it. This keeps the *slice* allocation the same (so overall zone layout math doesn't change) but stops individual **cards** from visually ballooning past their content.
2. Consider **not** forcing every top-level zone to the same `zones_h` when the spread between zones' natural heights is large (e.g. only equalize when the tallest zone's need is within ~40% of the shortest's; otherwise let each zone size closer to its own natural height and vertically center the row). This is a bigger change to the layout algorithm and carries more risk of destabilizing the flat/simple pipeline diagrams that work fine today — it should be scoped and tested separately from fix (1), not bundled together.

**Regression risk & how to check it**: Fix (1) is the safer, more contained change — it only affects how a group's *own* card is drawn within its already-computed slice, not the slice sizes themselves, so it shouldn't change any diagram's overall footprint or trigger new overflow elsewhere. Verify by re-rendering both `STATIC_DIAGRAM` (flat, roughly-even zones — should look nearly identical, maybe slightly tighter cards) and `LANDING_ZONE_DIAGRAM` (the uneven case — should show visibly less empty space in the simple zones) and comparing card heights before/after. Fix (2) is higher-risk and changes the layout algorithm's core sizing logic — it needs its own before/after comparison across *all* existing `migration_flow` test fixtures (not just the two here) before being considered, and I'd recommend shipping fix (1) alone first and re-assessing whether (2) is still needed.

---

### Finding 4 — Icon-grid card titles: fixed-height label doesn't scale with title length
**Severity: Medium. Scope: `icon_grid` layout (`build_icon_grid_slide`) — pre-existing, unrelated to this session's work.** Confirmed on slides 5 ("About Xebia") and 15 ("Key Solution Components").

`build_icon_grid_slide` ([slide_builders.py:743-744](../../src/generation/slide_builders.py)) draws each card's title label in a fixed `0.35in`-tall box regardless of how long the title text is:
```python
_add_textbox(slide, x + 0.75, y + 0.22, card_w - 0.95, 0.35,
             item.get("label", ""), SZ_SUBTITLE, style.title_color, ...)
```
Real generated titles like *"Healthcare & Regulated Sector Focus"* (36 chars) and *"Azure Enterprise Hub-Spoke VNet"* (32 chars) at 14pt in a ~2.93in-wide box need an estimated ~0.47in — about a third more than allocated. Same overflow mechanism as Finding 2: `word_wrap=True`, no autofit, so it bleeds into the description text directly below it rather than clipping.

**Root cause location**: `build_icon_grid_slide` in `slide_builders.py`.

**Proposed fix**: either (a) allocate title-label height dynamically based on estimated wrapped-line count (same estimation approach used elsewhere), pushing the description text start down to match per-card, or (b) cap/shrink the title font size for longer labels so they reliably fit one line, or (c) increase the fixed budget to accommodate 2 lines everywhere (simplest, but wastes space on short titles — probably the wrong tradeoff since most titles here are one line).

**Regression risk & how to check it**: `build_icon_grid_slide` is used across many slide types (capability grids, tech component grids, etc.), so this needs a broader spot-check than the architecture-diagram fixes — re-render a few different `icon_grid` content sets (short titles and long titles both) and confirm short-title cards look unchanged while long-title cards no longer overflow. This is a shared, frequently-used builder, so treat it as higher blast-radius than Findings 1-3 even though the fix itself is small.

---

### Finding 5 — World-map slide: dense city/country labels overlap each other
**Severity: Medium. Scope: the global-presence/world-map slide (likely `build_global_presence_slide`) — pre-existing, unrelated to this session's work.** Confirmed on slide 7.

Country labels placed on the world-map image collide with each other in geographically dense regions — e.g. "UK" (box `[5.75, 2.28, 1.1, 0.22]`) and "Belgium" (box `[5.73, 2.44, 1.1, 0.22]`) overlap by 27% of the smaller label's area, since European countries sit close together on the map but each label reserves a fixed 1.1in-wide box regardless of how many neighbors are nearby.

**Root cause location**: whichever function places city/country labels for the global-presence map — not yet identified precisely (didn't trace this one into source this session; flagging the symptom and location pattern for the next pass).

**Proposed fix**: needs investigation into the actual label-placement source before proposing a specific fix — likely either a collision-avoidance nudge (offset overlapping labels vertically/horizontally by a small amount) or filtering to fewer, better-spaced markers when the country list is dense in one region. Not resolved in this pass.

---

### Finding 6 — One shape 2.1in off-slide on both axes (slide 13)
**Severity: Low, likely a non-issue.** A single shape with no text, sized 3.6×3.6in, sits at `[11.83, 6.0]`, extending 2.1in past both the right and bottom slide edges. No fill/text data was captured for it in this pass, but a shape with no text bleeding equally off two edges near a corner is a common intentional decorative technique (a large accent circle/blob bleeding off the slide corner) — consistent with the blueprint/composition system's documented "floating circles"/corner-accent style. **Recommend a quick visual confirmation only** (open slide 13 in PowerPoint) rather than treating this as a bug to fix — if it turns out to be unintentional, it's a one-line position fix in whichever blueprint placed it.

---

## Suggested order of work

1. **Finding 1** (title/content collision) — single-constant fix, isolated to one renderer, highest visual impact (every migration_flow slide), do first.
2. **Finding 2** (qualifier label overflow) — this session's own regression, should ship alongside/soon after Finding 1 since both touch the same renderer and can be verified together.
3. **Finding 4** (icon-grid title overflow) — independent of the architecture-diagram work, but small and contained; safe to do in the same pass.
4. **Finding 3, fix (1) only** (group-card empty space) — do after 1/2 are verified stable, since it's a layout-algorithm change with more moving parts; hold fix (2) (uneven zone heights) for a separate, dedicated pass with its own before/after comparison.
5. **Finding 5** (world-map label collisions) — needs source investigation first; separate pass.
6. **Finding 6** — just look at it; likely no code change needed.

None of these fixes are implemented yet — this is the plan only, per the request. Each finding above includes its own regression-risk note and verification approach so that when you're ready to proceed, each fix can be scoped, applied, and checked independently rather than as one large change.

---

## Decided implementation plan (2026-08-25) — ✅ ALL BUILT AND VERIFIED

Every fix below is implemented and verified (each against real rendered output, not just code review — see the specific numbers noted per finding). Full pipeline regression (`generate_proposal_pptx`/`generate_proposal_docx` against `outputs/test_content_plan.json`) and a full compile check both pass after all five changes together.

### 1. Finding 1 — content_top + gated title autofit (both fixes)
- `MigrationFlowRenderer.content_top`: raise from `1.15` to `1.60` in `migration_flow_renderer.py:111`. (1.60 clears the title placeholder's actual bottom edge, y≈1.4, plus a ~0.2in margin before the first zone title badge, which itself sits half above `content_top`.)
- `_fill_ph` in `slide_builders.py`: add an optional `autosize: bool = False` parameter that sets `MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE` on the placeholder's text frame when true. Pass `autosize=True` only from `build_migration_flow_slide` and `build_architecture_slide` (the two layouts that carry AI-generated, potentially-long titles) — every other call site keeps today's behavior unchanged by default.
- **Verify**: re-render `test_architecture_gen.py --static` and `--landing-zone`; confirm (a) no shape's top edge is now above the title placeholder's bottom, (b) a short title (e.g. "AWS to Azure & Microsoft Fabric Migration Architecture" — already in `STATIC_DIAGRAM`) still renders full-size, not shrunk. Also spot-check one `icon_grid`/`content` slide to confirm the untouched `_fill_ph` call sites (autosize left at its `False` default) are byte-for-byte unaffected.

**✅ Shipped — with a correction to the plan.** A flat `1.60` turned out to be wrong: title-placeholder height varies by template (`xebia_carrington`, the one the real Meridian deck used, bottoms out ~1.4; `xebia_retail`/`xebia_synapse` extend to 1.84-1.85 — confirmed by checking all three directly). A single hardcoded constant can't be correct for both. Shipped instead: `content_top` is now computed at render time from the *actual* title placeholder on `self.slide` (`_safe_content_top`, reads `title_ph.top + title_ph.height`, adds a 0.20in margin, floors at 1.60), so it's correct per-template rather than tuned to one data point. `content_height` shrinks correspondingly (target bottom boundary ~7.15in, unchanged). Verified: 0 real title-collisions (0 off-slide shapes) on both fixtures using `xebia_retail` (the stricter case); full pipeline regression still passes; autosize confirmed applied only to the 2 intended layouts.

### 2. Finding 2 — qualifier-only label height (scoped fix)
- In `_draw_item_icons`, detect per-item whether it's a qualifier object (`isinstance(item, dict) and item.get("qualifier")`) and use a taller `label_h` (e.g. `0.16` → `0.30`, two lines at 5.5pt) and matching `item_total_h` for that item's row only — plain-string items keep `label_h = 0.16` exactly as today.
- Note this makes per-item height non-uniform *within a row* when only some items in a group have qualifiers — the row layout math (`item_total_h` currently computed once for the whole group) needs to take the row's own tallest item, not a single group-wide constant. Small but real change to the loop structure, not just the constant.
- Mirror the same conditional sizing in `_estimate_group_h`'s `"icons"` branch so `_estimate_zone_content_h`/`zones_h` budget the extra room too — otherwise the fix moves the overflow from the label box into the zone/group boundary instead of removing it.
- **Verify**: re-render `STATIC_DIAGRAM` (no qualifier items) and confirm identical output to before this change (same shape count, same positions) — this is the key regression check per your instruction to confirm nothing that worked before changes. Then re-render `--landing-zone` (has one qualifier item) and confirm that item's label box now clears the audit script's `TEXT_OVERFLOW_RISK` check.

**✅ Shipped as planned.** Shipped whole-group (not per-item) height switching — a group's row height grows to the 2-line budget if *any* item in it has a qualifier, keeping the icon grid's rows aligned rather than trying true per-item mixed heights (which would misalign columns). Mirrored in `_estimate_group_h`'s `"icons"` branch. Verified: zero `TEXT_OVERFLOW_RISK` hits on both fixtures post-fix (was 8 on `--landing-zone` pre-fix).

### 3. Finding 3 — cap card height to content, don't stretch (safer fix only)
- In `_draw_group`, after computing the group's allotted slice height (`group_h`, from `_draw_zone`'s even division — unchanged), compute the group's own natural height via `_estimate_group_h` and draw the card background at `min(group_h, natural_h + padding)` instead of always `group_h`. Top-align the card within its slice (don't center or stretch) so groups later in the zone don't shift position — only the card's own height shrinks to fit its content, the slice boundaries used for positioning subsequent groups stay as they are today.
- Explicitly **not** in scope for this pass: the `zones_h` uniform-across-zones computation in `render()` stays as-is. Zone *row* height is unchanged; only *card* height inside a zone changes.
- **Verify**: re-render `STATIC_DIAGRAM` (zones with roughly even content) and confirm cards look the same or marginally tighter, no position shift of later groups. Re-render `--landing-zone` and confirm the "On-Premises Data Center" zone's group card no longer extends ~0.5in past its content (measure via the same audit approach used to find this issue).

**✅ Shipped as planned.** `_draw_group` now computes `natural_h = self._estimate_group_h(group, w)` and draws the card at `max(0.35, min(h, natural_h + 0.10))` instead of always the full slice `h`. Verified: the on-prem zone's group card dropped from 1.33in to 0.91in (a 0.42in reduction) with the same content; no new overflow/off-slide issues on either fixture.

### 4. Finding 4 — dynamic title height in icon_grid
- In `build_icon_grid_slide`, replace the fixed `0.35` title-label height with an estimate (reuse the same wrapped-line-count approach as elsewhere: chars-per-line from `card_w - 0.95` and 14pt (`SZ_SUBTITLE`), round up to whole lines × line-height). Push the description textbox's `y` down by however much the title grew past one line, and shrink the description's own height by the same amount so it doesn't get pushed past the card's bottom edge.
- **Verify**: re-render with both a short title set (existing behavior — should be pixel-identical, single line fits in the base height) and a long title set (e.g. the real *"Healthcare & Regulated Sector Focus"* / *"Azure Enterprise Hub-Spoke VNet"* cases from the audit) and confirm the description text no longer starts inside the title's overflow zone. Since `build_icon_grid_slide` is used broadly (capability grids, tech grids, etc. — check call sites before assuming scope), spot-check at least 2 different real call sites, not just one.

**✅ Shipped, with one correction found during verification.** First pass used a gap constant that didn't reproduce the *old* fixed-height spacing for short titles (a real, if small, regression this audit approach was specifically meant to catch) — fixed by deriving the gap from the original formula (`0.75 - 0.22 - 0.35 = 0.18`) instead of an arbitrary new value. Also added a 0.2in inset allowance to the line-wrap estimate to match PowerPoint's default textbox margins, after the audit script (which already accounted for insets) caught one borderline title my first estimate missed. Verified: short-title case is now byte-for-byte identical to pre-fix output (description box at `t=4.1` exactly, both before and after); long titles get exactly the room they need (2-line titles measured at `h=0.534`) with zero `TEXT_OVERFLOW_RISK` remaining.

### 5. Finding 5 — DECIDED: adapt PNB MetLife's label design (asset swap not viable, so redo the label code)
Investigated whether a ready-made map-with-labels image could just replace the current one. Findings:
- The current base picture (`xebia_design_system/assets/maps/world_presence_map.png`) is already good — dots are baked into the image correctly; only the separately-drawn text labels are buggy.
- The best candidate in the reference decks, PNB MetLife's "Our Global Presence" slide, turned out to be a **vector map** (hundreds of individual freeform country-outline shapes) with labels as **separate shapes on top** — the same two-layer architecture ours already uses, just with a human designer's spacing. Not flattenable into a single picture without a rendering engine (still unavailable here), so a literal asset swap isn't viable.
- **Decision**: keep our map picture, but redo the label code using PNB MetLife's proven spacing pattern as the model.

**Concrete change**, extracted directly from PNB MetLife's real (non-confidential, Xebia's own corporate) office list:
- Extend `_GLOBAL_HUBS` entries with a city line: `(country, lon, lat, city_text, (dx, dy))`, e.g. `("UK", -0.13, 51.51, "London", (dx,dy))`, `("Netherlands", 5.18, 52.22, "Hilversum, Amsterdam", (dx,dy))`, `("India", 77.03, 28.46, "Gurgaon, Pune, Bangalore", (dx,dy))`, etc. — using the real city names from PNB MetLife's slide for every country already in our list (Xebia's own office locations, not customer data).
- Render as two lines — `"{country}\n{city}"` — bold country line + smaller city line, matching their format.
- Widen the label box from the fixed `1.1in` to a text-length-driven width (their boxes range ~0.65-1.4in) and increase height to fit 2 lines (~0.5-0.55in vs the current single-line 0.22in).
- Re-derive `(dx, dy)` offsets for the crowded Europe cluster (UK, Netherlands, Belgium, Germany, Switzerland, Poland) using PNB MetLife's actual relative spacing as a template (their boxes for this exact cluster are spread diagonally across a ~1.5×1.2in area, not stacked near-identically like ours) — scale their layout to fit around our map's dot positions (they won't be pixel-identical since the two maps have different projections/sizes, but the *pattern* — spread diagonally, stagger vertically, don't stack — transfers directly).

**Verify**: re-render `build_global_presence_slide` and run the same geometric overlap check used to find this issue in the first place — confirm zero `TEXT_ON_TEXT` hits among the 16 (now with city sub-labels) hub labels, and confirm all labels stay within the map picture's bounds. Since this is a static, deterministic layout (not AI-generated content), this should be a one-time fix verified once and done, not something needing per-proposal re-checking.

**✅ Shipped.** Used one real city per hub (not PNB MetLife's full multi-city lists) to keep box heights uniform (~0.3in, 2 lines) rather than reintroducing tall 4-line boxes. Offsets were solved computationally, not hand-tuned blind — first attempt (simple 6-direction radial fan) actually pushed Netherlands into the slide's own title zone (a Finding-1-shaped bug for this *different* builder, since `build_global_presence_slide` uses a fixed `map_top` rather than reading the actual title placeholder) and left Spain/Belgium colliding. Re-solved with an explicit "stay below the title" floor constraint plus a wider horizontal fan (the map has ~4in of clear space on both sides of the crowded cluster, far more than vertically) — final offsets in the code comment. Verified against the actual rendering geometry: **0** `TEXT_ON_TEXT` hits across all 16 hubs (was 5 colliding pairs before), 0 off-slide shapes, 0 title-zone intrusions. One follow-up catch during verification: taller 2-line labels pushed Australia's label into the stats-card row below the map — caught by re-running the same audit after the fix, corrected by tightening its vertical offset.

### 6. Finding 6 — no code change planned
Recommend opening slide 13 in PowerPoint to confirm the off-slide shape is the intentional corner-bleed decoration it looks like. If it turns out not to be, it's a one-line position fix in whichever blueprint placed it (not yet identified) — but not worth guessing at blind.

**Update from later live testing**: the identical shape (`[11.83, 6.0, 3.6, 3.6]`, no text, same overhang) turned up on 3 separate slides in a real generated deck, always at the exact same position. A blueprint-driven decoration repeating identically across unrelated slides is strong evidence this is intentional, not a bug — confidence raised, still not opening a live viewer to confirm.

---

## Two more findings from later live end-to-end testing (2026-08-25, same day)

After the five fixes above shipped, live testing through the actual web app (not just the two static fixtures) surfaced two more instances of the *same root-cause patterns*, in slide builders the original audit hadn't reached. Both fixed the same day, same session.

### 7. Timeline slide — same root cause as Finding 1, different builder
`build_timeline_slide`'s "TOTAL PROJECT TIMELINE: N WEEKS" banner was positioned at a flat `CONTENT_TOP - 0.35`, the same kind of template-blind fixed offset Finding 1 fixed for `MigrationFlowRenderer`. Confirmed on a real generated deck (63% overlap with the title). Fixed with the same approach: added a shared `_safe_title_bottom(slide)` helper (reads the slide's actual title placeholder bottom) and made the banner position `max(CONTENT_TOP - 0.35, _safe_title_bottom(slide) + 0.05)` — unchanged on templates with a normal-height title, pushed down only on templates with a tall one. The header row below it (`header_y`) was re-derived from the banner's actual position instead of its own separate fixed constant, so it can't end up overlapping the banner if the banner moved.

**Verified**: tested against both a short-title template (`xebia_carrington`, title bottom 1.409) and a tall-title one (`xebia_retail_cases`/`Data & AI Retail Case Studies`, title bottom 1.839) — banner position unchanged (1.65) on the first, correctly pushed to 1.889 on the second, zero collision either way.

### 8. Stats-highlight slide — same root cause as Finding 4, different builder
`build_stats_highlight_slide`'s KPI label had the same fixed-height-regardless-of-text-length issue as Finding 4's `icon_grid` titles. Confirmed on a real generated deck: *"Target Data Freshness for Priority Store Inventory Feeds"* and *"Reconciled Financial & Sales Record Accuracy at Cutover"* both overflowed a fixed 0.40in box. Fixed with the same `_est_wrapped_lines`-based approach as Finding 4: label height grows with wrapped-line count, the sublabel/description below it shifts down and shrinks by the same amount.

**Verified**: reproduced the exact real-world case (4 stats, 2.61in-wide cards, matching the audit's measured box width) — long labels grew from `h=0.4` to `h=0.721`, sublabels correctly repositioned from `t=4.85` to `t=5.171`; short labels in the same render stayed at `h=0.4` unchanged. Zero `TEXT_OVERFLOW_RISK`/`TEXT_ON_TEXT` on a fresh audit pass.

Both fixes plus a full-pipeline regression check (`generate_proposal_pptx`/`generate_proposal_docx` against `outputs/test_content_plan.json`) and a full compile check all pass together with the original five.

### Build order — as executed
1 → 2 → 4 → 3 → 5 (original pass) → 7 → 8 (from later live testing), each verified individually plus full-pipeline regression runs after each batch. Finding 6 remains visual-check-only, no code change planned — confidence it's intentional is now higher after seeing it repeat identically across multiple real slides.

### What's still not verified
Everything above was checked structurally (OOXML geometry, the same audit approach used to find these issues) and against the existing full-pipeline test fixture — not visually, since this environment still has no PowerPoint/LibreOffice. Worth a real look in PowerPoint before relying on this for a live proposal, same caveat as the original findings.
