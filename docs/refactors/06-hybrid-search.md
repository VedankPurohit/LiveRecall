# 06 — HybridSearch: move RRF fusion out of `database.py`

**Status:** Ready to grill.
**Depends on:** Nothing structurally; benefits from any learnings from 01–05.
**Risk:** Medium — search behaviour is user-visible; regressions are obvious.

## Friction (current state)

`core/database.py:search_hybrid` (~lines 1106–1262) does **two unrelated things**:

1. **Data access** — runs SQL against `screenshot_embeddings`, `ocr_text_embeddings`, `ocr_text_fts`, joins to `screenshots`, applies filters.
2. **Retrieval fusion** — Reciprocal Rank Fusion (RRF) across four signals: CLIP image, FTS trigram, small-chunk semantic, large-chunk semantic. Normalization, deduplication, source attribution (`match_sources`).

`api/routes/search.py` (~lines 35–223) is thin: generate embeddings, call `db.search_hybrid(mode, embeddings, ...)`, format response. The route stays thin only because the database swallowed the orchestration.

**The fusion logic is structural, not data-access.** Adding a reranker, swapping RRF for weighted fusion, adding a new modality (audio? metadata?), or tuning per-signal weights all force edits in the data-access module — the wrong place for those changes.

### Deletion test

- Delete `search_hybrid`: routes would need to either (a) reimplement RRF inline (worse — RRF leaves the DB module but lands in HTTP-handler land); or (b) call individual search methods (`search_text_embeddings`, `search_ocr_fts`) and combine. So the fusion isn't waste — it's earning its keep — but it's earning it in the wrong module.
- Delete the individual search methods: `search_hybrid` is the only caller of half of them. Hmm — verify this. If they aren't called elsewhere, they're already coupled to `search_hybrid` and the seam is even leakier than it looks.

## Target shape (sketch)

A `HybridSearch` module that:
- takes a query text (and/or image embedding),
- talks to `Database` for per-signal ranked results (each method returns `[(screenshot_id, score)]`),
- talks to embedders (CLIP + text) for query embedding generation,
- composes signals via RRF (with weights configurable),
- returns a fused, deduplicated result list.

`Database` retains only **per-signal** search methods, each focused on one table and one ranking. The route holds a `HybridSearch` instance, generates embeddings via injected embedders, and calls `hybrid.search(query, filters, mode)`.

## Open questions for `/grill-me`

1. **What's a "signal"?** Today four exist (CLIP image, FTS trigram, small-chunk semantic, large-chunk semantic). Are these named concepts in the codebase, or just inline branches? Probably worth giving them types (`Signal.CLIP`, `Signal.FTS`, `Signal.TEXT_SMALL`, `Signal.TEXT_LARGE`) for self-documenting fusion code.
2. **`SearchMode` interpretation.** `mode = AUTO | IMAGE | TEXT | OCR` (or similar — confirm). Each mode is a subset of signals. Define the signal-selection table explicitly in `HybridSearch`, not in conditionals.
3. **RRF parameters.** Today there's an `rrf_k`-style constant somewhere — find it. Should it be configurable per-signal (different `k` for FTS vs semantic)? Probably no — RRF's whole pitch is parameter-light. Confirm.
4. **Weighting.** Are signals weighted equally in RRF today, or are some scaled? If unequal, weights belong in `HybridSearch`'s constructor (with defaults matching today's behaviour exactly — no behaviour change in this PR).
5. **Dedup policy.** A screenshot might appear in multiple signal results. Today: collect into a dict keyed by `screenshot_id`, sum RRF scores, sort. Stays the same. But: the result includes `match_sources` (which signals matched). Decide where that's built — inside RRF combiner, or as a separate annotator pass.
6. **Embedder dependency.** Today the route reaches into `embeddings.get_image_embedding` / `text_embeddings.get_query_embedding`. After refactor: does `HybridSearch` take embedders in constructor (cleanest), or does the route still own embedding generation and pass embeddings in? Constructor injection means `HybridSearch` controls when (and whether) embeddings are generated — better for short-circuit cases.
7. **Filters.** `time_range`, `is_hidden`, `min_confidence` etc. — where do they apply? At the per-signal SQL level (DB filters), or in `HybridSearch` post-fusion? Per-signal is faster (fewer rows fused). Pin down current behaviour and preserve it.
8. **Behaviour-preserving refactor or improvement opportunity?** Strong recommendation: **behaviour-preserving only**. Any improvements (better weights, reranker, etc.) should be a follow-up PR — that's the only way to be confident no regression sneaked in.
9. **Snapshot tests.** Before refactoring, capture current search output for ~10 representative queries on a known DB. Replay after. Same outputs = green. The repo has no fixture DB today — need to decide if this gets built.

## Test situation

- `core/tests/test_database.py` covers `search_hybrid` partially (verify scope).
- After this refactor: `test_hybrid_search.py` with fake DB returning scripted per-signal results; assert RRF math; assert mode → signal selection; assert dedup + match_sources.
- The integration tests in `api/tests/test_api.py` should keep passing without change.

## Files involved

- `core/database.py` — remove `search_hybrid`, keep per-signal methods (possibly tighten their interfaces)
- `core/tests/test_database.py` — likely needs reworking
- `api/routes/search.py` — instantiate / call `HybridSearch`
- New: `core/hybrid_search.py`
- New: `core/tests/test_hybrid_search.py`

## Not in scope

- Adding new search signals (rerankers, image-to-image search, audio).
- Changing the public `/search` route's request/response shape (web UI depends on it).
- Re-tuning RRF weights or experimenting with alternatives — behaviour preserving only.
- FTS5 tokenizer changes.
