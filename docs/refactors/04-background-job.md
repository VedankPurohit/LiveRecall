# 04 — BackgroundJob: extract shared threading/progress from sync + compression

**Status:** Ready to grill.
**Depends on:** Nothing.
**Risk:** Medium — touches two live services; integration tests at the API surface are the safety net.
**Blocks:** [05 SyncPipeline](05-sync-pipeline.md).

## Friction (current state)

`core/processor.py:ProcessorService` and `core/compression.py:CompressionService` are **two adapters of an unnamed thing**: a long-running background job. Each independently re-implements:

| Concern | ProcessorService | CompressionService |
|---------|------------------|---------------------|
| Worker thread | yes | yes |
| `start()` / `stop()` / `is_running` | yes | yes |
| Progress dataclass | `SyncProgress`-ish state | `CompressionProgress` |
| Cancellation flag | yes | yes |
| Route returns `SyncStartResponse` | `api/routes/sync.py` | `api/routes/compression.py` |
| Status endpoint | yes | yes |

The two services were written at different times; the shape was copied. Every new background concept (re-embed, vacuum, future migrations) will copy the shape again unless we extract the seam.

### Deletion test

Delete either service: the other still works. Their *similarity* is the waste — the actual work each does (sync screenshots vs compress images) is distinct and earns its keep. The duplication is in the orchestration shell around the work.

**Two adapters = real seam.** The seam is "background job that progresses through items and reports status."

## Target shape (sketch)

A `BackgroundJob` module that owns:
- worker thread lifecycle
- `start()`, `stop()`, `is_running`
- cancellation signalling
- progress reporting (some shape callers/routes can observe)
- error handling per item

The *work* (process this screenshot / compress this image) becomes a callable or strategy supplied to the job. `ProcessorService` and `CompressionService` shrink to: configure a `BackgroundJob` with their respective per-item work and progress shape.

This refactor is **prerequisite for [05 SyncPipeline](05-sync-pipeline.md)** — once threading is extracted, what's left in `ProcessorService` is the pipeline.

## Open questions for `/grill-me`

1. **Generic over progress shape, or one fixed shape?** Sync and compression both report `current / total / phase` plus job-specific fields. Options:
   - (a) Generic `BackgroundJob[ProgressT]` with a type parameter.
   - (b) Fixed `JobProgress(current, total, phase, message, custom: dict)` — simple, no generics, easy serialization.
   - (c) Job owns nothing about progress; each service still has its own dataclass and `BackgroundJob` just hands it observation hooks.
   - Recommendation: (b) is least clever and serializes cleanly for API responses.
2. **Cancellation: cooperative flag or `threading.Event`?** Both today use a simple boolean. `Event` is friendlier (`event.wait(timeout)` doubles as sleep). Worth changing or leave alone?
3. **Restart semantics when already running.** Both services today reject `start()` while running. Keep that, or allow a queued restart? Today's behaviour is fine — confirm.
4. **Error policy.** Per-item errors today are logged and the loop continues. Total-failure policy (stop after N consecutive errors)? Don't introduce unless we have evidence it's needed — KISS.
5. **Progress observation: poll or push?** Status routes poll via `is_running` + progress getter. Anyone need a push channel (websocket, callback)? Today no. Keep poll-only.
6. **What's the test surface for `BackgroundJob`?** A trivial work function that increments a counter; the test asserts start → run → stop → progress is observable; cancellation interrupts mid-run.
7. **Naming.** `BackgroundJob`? `BackgroundService`? `Worker`? Three terms are already overloaded in this codebase (services everywhere). Pick something distinct. Recommendation: `BackgroundJob` — emphasizes the unit-of-work shape, not the long-lived service shape.
8. **Do we leave `processor_service` / `compression_service` module-level singletons intact?** Both modules expose globals (`processor_service = ProcessorService()`). Routes import these by name. Keep the singletons; refactor is internal.
9. **Force/quality params (compression-specific) and `mode=` (sync-specific) — do they survive cleanly?** These are *per-job* parameters, passed to `start()`. The interface for `BackgroundJob.start()` needs to accommodate per-call config without becoming `**kwargs` soup. Maybe `start(work_fn, total_estimator)` where `work_fn` is already partially bound by the service.

## Test situation

- `core/tests/test_compression.py` exists — keep passing.
- No direct tests for `core/processor.py` — integration tests at `api/tests/test_api.py` are partial coverage.
- After this refactor: `core/tests/test_background_job.py` exercising the shell with fake work. `test_compression.py` should still pass unchanged (or with minimal call-site updates).

## Files involved

- `core/processor.py` — refactor to use `BackgroundJob`
- `core/compression.py` — refactor to use `BackgroundJob`
- `api/routes/sync.py` — unlikely to change beyond what's already on this branch
- `api/routes/compression.py` — likely unchanged
- `api/schemas.py` — likely unchanged; `SyncStartResponse` already shared
- New: `core/background_job.py`
- New: `core/tests/test_background_job.py`

## Not in scope

- The actual pipeline inside the processor — that's [05](05-sync-pipeline.md).
- Adding new background jobs (re-embed, vacuum). The new shape should make them easy, but don't add them in this PR.
- Changing API response shapes that the web UI consumes.
