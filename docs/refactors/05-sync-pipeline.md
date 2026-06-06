# 05 — SyncPipeline: name and isolate the per-screenshot processing pipeline

**Status:** Ready to grill.
**Depends on:** [01 LazyModel](01-lazy-model.md) and [04 BackgroundJob](04-background-job.md).
**Risk:** High — this is the heart of the app.

## Friction (current state)

`core/processor.py:ProcessorService` (~lines 327–410 for `_process_ocr_for_screenshot` and surroundings) interleaves **the actual per-screenshot pipeline** with thread management, progress tracking, lazy model loading, and unload timing.

The pipeline for one screenshot is:

```
CLIP image embedding → OCR extract → chunk text (small + large) → text embeddings (batch) → DB writes
```

But there is no module named for this. To answer "what happens when OCR fails halfway through?" or "is text embedding batched per screenshot or per loop iteration?", you have to read through `ProcessorService` and trace control flow across lazy-loaders (`_get_ocr_service`, `_get_text_embedding_service`, `_get_chunking` at lines ~94–123), conditional skips, and try/except blocks.

The **pipeline is the depth** — but it has no name and no isolated interface.

### Deletion test

Delete `ProcessorService.run_loop()`: the individual modules (capture, db, embeddings, ocr, chunking) remain useful. But the *ordering*, the *failure semantics* ("if OCR fails, still write the CLIP embedding"), the *batching* ("collect chunks then embed in one batch") all vanish. They'd have to be rebuilt at every caller — and there's only one caller now, but that's because the pipeline is implicit. The pipeline earns its keep; it just doesn't exist as a module.

## Target shape (sketch)

A `SyncPipeline` module that takes one screenshot (path/id) and runs it through the stages, returning a structured result (or raising structured errors). It does **not** know about threads, progress, or the loop.

`ProcessorService` becomes: `BackgroundJob` (from [04](04-background-job.md)) configured with `SyncPipeline.process_one` as the per-item work.

This refactor pays off if and only if [01](01-lazy-model.md) is done (so the pipeline can hold model handles via clean interfaces) and [04](04-background-job.md) is done (so there's a clean place for the worker shell to live).

## Open questions for `/grill-me`

1. **Pipeline shape: function, class, or step-list?**
   - (a) `process_one(screenshot) -> Result` — single function calling each stage inline.
   - (b) `SyncPipeline` class with `__init__` injecting deps, `process_one(screenshot)` method.
   - (c) Explicit list of `Stage` objects, run in order — overengineered for 5 stages, but enables skipping/composing.
   - Recommendation: (b). Stages are well-known and unlikely to be reordered.
2. **Per-stage failure policy.** Today's behaviour (read it precisely): does an OCR failure block the CLIP embedding from being written, or are they independent? The pipeline interface must commit to a policy. Options:
   - "Best-effort per stage" — each stage's failure is recorded, others continue.
   - "Fail fast" — first failure aborts the rest.
   - Current behaviour is mixed; pin it down during grilling.
3. **DB writes: per-stage or end-of-pipeline transaction?** Currently each helper writes its own table. End-of-pipeline batched-commit would be more atomic but harder to recover from partial failure. Probably keep per-stage — but make it intentional.
4. **Chunk batching.** Today chunks for one screenshot get embedded in one batch call (see processor batching logic). Is the pipeline boundary one-screenshot or N-screenshots? One-screenshot is simpler; N-screenshot batching wins throughput. Worth measuring before deciding.
5. **Where does `SyncPipeline` get its model handles?** Three options:
   - Constructor-injected (best for testability — fakes are trivial).
   - Module-level imports (today's pattern; survives [01](01-lazy-model.md)).
   - Pulled from a registry at construction time.
   - Recommendation: constructor injection, since [01](01-lazy-model.md) makes that natural.
6. **Idempotency.** If `process_one` is called twice for the same screenshot, what happens? Today `has_embedding` / `has_ocr` flags gate the work. Should the pipeline check those, or should the caller (the job) filter?
7. **Progress reporting from inside the pipeline.** The pipeline runs one screenshot. Progress reporting (current of total) belongs to the job. But within one screenshot, do we need finer-grained phase reporting (e.g. "embedding CLIP" → "running OCR")? Today: no. Confirm.
8. **What does `Result` look like?** Options:
   - `Result(ok=True, embeddings_written, ocr_text, chunks_count, ...)`
   - Just `None` and side effects (today's pattern).
   - Typed dataclass with per-stage status (`StageStatus.SUCCESS | SKIPPED | FAILED`).
   - Last one enables observability and clean tests; pick it.
9. **Tests: fake every external thing, or use an in-memory DB and fake models?** Project's existing DB tests use a real SQLite — same approach here is realistic.

## Test situation

`SyncPipeline` is the kind of module a test suite would have written naturally if it had been factored out from the start. After this refactor:
- `test_sync_pipeline.py` — drive each stage with fakes; assert per-stage failure policy; assert ordering; assert idempotency.
- Existing API integration tests are the safety net during the refactor — they should not change.

## Files involved

- `core/processor.py` — gut and rebuild as a `BackgroundJob` consumer
- New: `core/sync_pipeline.py`
- New: `core/tests/test_sync_pipeline.py`
- `core/ocr.py`, `core/chunking.py` — likely unchanged; called through interfaces
- `core/embeddings.py`, `core/text_embeddings.py` — refactored under [01](01-lazy-model.md)

## Not in scope

- New stages (re-embedding, secondary OCR providers). The new shape should make them cheap; don't add them here.
- Restoring data, migrations, schema changes.
- Search-time concerns (those are [06](06-hybrid-search.md)).
- Renaming `screenshots` / `screenshot_embeddings` / `ocr_text_chunks` tables.
