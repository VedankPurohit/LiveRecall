# Architecture Refactors

Six deepening refactors identified via `/improve-codebase-architecture`. Each doc in this folder is a **self-contained handoff** — a fresh Claude session should be able to pick it up, `/grill-me` on the open questions, and then `/tdd` the implementation.

Shared vocabulary lives in `~/.claude/skills/improve-codebase-architecture/LANGUAGE.md`. Use **module**, **interface**, **implementation**, **depth**, **shallow**, **seam**, **adapter**, **leverage**, **locality** — and apply the **deletion test** to anything suspected of being shallow.

## Order and dependencies

Recommended landing order — each PR builds on the ones above:

| # | Refactor | Depends on | Risk | Why this order |
|---|----------|------------|------|----------------|
| [01](01-lazy-model.md) | LazyModel (consolidate two embedders' lifecycle) | — | Low | Foundational; two adapters already exist so the seam is real. |
| [02](02-change-detector.md) | ChangeDetector (split from CaptureService) | — | Low | Fully contained in `core/capture.py`. |
| [03](03-backend-runner.md) | BackendRunner protocol (subprocess vs thread) | — | Low | Contained in `tray/backend.py`; closes a real cross-mode inconsistency. |
| [04](04-background-job.md) | BackgroundJob (extract threading/progress from sync + compression) | — | Medium | Two adapters (ProcessorService, CompressionService) confirm the seam. |
| [05](05-sync-pipeline.md) | SyncPipeline (extract the per-screenshot pipeline) | 01, 04 | High | Touches the heart of the app; benefits from foundations being in place. |
| [06](06-hybrid-search.md) | HybridSearch / fusion (move RRF out of `database.py`) | — | Medium | Most domain-decision-heavy; benefits from any learnings from 01–05. |

Independent threads — 01, 02, 03, 06 can land in any order. 04 → 05 is a hard dependency.

## Per-refactor workflow

1. Open the relevant doc.
2. `/grill-me` to walk the open-questions tree. Update the doc inline as decisions crystallize.
3. `/tdd` to implement red-green-refactor against the agreed shape.
4. Land as a single PR. No AI attribution in commit/PR.

## Test situation (read once)

- **Has tests:** `core/database.py`, `core/compression.py`, `core/config.py`, `core/platform.py`, `tray/api_client.py`, `tray/config.py`, `tray/icons.py`, `api/` (via `test_api.py`).
- **No direct tests:** `core/processor.py`, `core/capture.py`, `core/embeddings.py`, `core/text_embeddings.py`, `core/ocr.py`, `core/chunking.py`, `tray/backend.py`.

Every refactor below should leave the new module **testable through its public interface** without needing to start uvicorn or load a real model. If you can't write that test, the seam is in the wrong place.

## Out of scope (do not bundle)

- Renaming domain concepts. If a refactor wants a new name (e.g. `SyncPipeline`), that's allowed, but don't sweep through unrelated files renaming things.
- Adding `CONTEXT.md` / ADRs unless `/grill-me` produces a load-bearing decision worth recording.
- Web/Next.js changes.
- Anything in `web/`, build scripts, or installers.
