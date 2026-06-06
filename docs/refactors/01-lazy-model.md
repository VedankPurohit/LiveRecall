# 01 — LazyModel: consolidate the two embedders' lifecycle

**Status:** Ready to grill.
**Depends on:** Nothing.
**Risk:** Low — two existing adapters validate the seam immediately.

## Friction (current state)

`core/embeddings.py` (CLIP, 326 lines) and `core/text_embeddings.py` (BGE, 397 lines) carry **two identical copies** of the same lifecycle:

| Concept | `embeddings.py` | `text_embeddings.py` |
|---------|------------------|----------------------|
| Module-level state | `_model`, `_device`, `_last_used`, `_auto_unload_timer`, `_lock` | same |
| Device pick | `_get_device()` lines 33–39 | lines 65–71 (identical) |
| Lazy load | `_load_model()` lines 42–71 | lines 74–108 (near-identical) |
| Auto-unload schedule | lines 74–89 | lines 111–123 (near-identical) |
| Idle check | `_check_and_unload()` lines 92–102 | lines 126–136 (identical) |
| Unload | `unload_model()` lines 105–132 | lines 139–166 (identical) |
| `is_loaded` / `is_downloaded` / `get_model_status` / `set_auto_unload_timeout` | lines 135–176 | lines 169–209 (~identical) |

Callers in `core/processor.py` (line ~123) reach into both modules by name — `unload_model()` and `unload_text_embedding_model()` — so the **interface** to "an embedding model that auto-unloads" exists implicitly across module names but has no single seam.

**Two adapters of the same lifecycle = real seam.** It is not extracted today.

### Deletion test

Delete the lifecycle code from either file: complexity does **not** vanish — it would have to be re-derived. So the lifecycle isn't a pass-through, but the *duplication* of it is — the second copy adds zero behaviour beyond the first.

## Target shape (sketch)

A `LazyModel` module that owns:
- model load (given a factory callable)
- device selection
- `_last_used` bookkeeping
- auto-unload timer
- `unload()`, `is_loaded()`, `get_status()`, `set_auto_unload_timeout()`

The two existing files become **thin domain wrappers** that supply the factory and the model-specific `encode`-style functions. CLIP keeps its image/text/combined embeddings + safe-mode helper. BGE keeps its query-vs-document instruction prefix and batch path.

Where the seam lives is open for grilling — see below.

## Open questions for `/grill-me`

1. **Class or module-level singleton?** Today both files use module-level globals. A `LazyModel` class instantiated once per embedder is cleaner for tests (multiple instances, each independent) but changes import sites. A module-level pattern with a registry keeps imports stable. Which is acceptable?
2. **Where do the model-specific encode functions live?** Three options: (a) stay as free functions in `embeddings.py`/`text_embeddings.py` and reach into a shared `LazyModel`; (b) become methods on a subclass `CLIPModel(LazyModel)`/`BGEModel(LazyModel)`; (c) the model stays a plain attribute and callers pass it to encode helpers. Each has different testability properties.
3. **Auto-unload coupling to `is_downloaded`.** Today each file knows how to look up its own HuggingFace cache (different config filenames, different model IDs). Does `LazyModel` take a `is_downloaded` callable, or does this stay in the wrappers?
4. **Backwards-compat of free functions.** `processor.py`, `api/routes/*` import free functions like `unload_model`, `get_model_status`. Do we keep those as thin shims for one PR's grace period, or change call sites in the same PR? (Recommend: same PR; this is a structural refactor, not a feature.)
5. **Device fallback policy.** Both modules currently print + try CPU on failure. Does that policy belong in `LazyModel` (uniform), or stay per-wrapper (some models may legitimately refuse CPU)? Today both are identical, suggesting it belongs in `LazyModel`.
6. **Test surface.** A fake `SentenceTransformer`-like factory that records `encode` calls and can be made to "fail to load" once. Should `LazyModel` accept a factory callable in its constructor so tests don't have to monkey-patch?

## Test situation

Neither embedder has direct tests today. After this refactor:
- `LazyModel` should be testable with a fake factory — verify load, unload, idle-unload, re-load, timeout reset on use, threadsafe concurrent loads.
- Each wrapper (`embeddings.py`, `text_embeddings.py`) should have a small test using a fake model that asserts the right calls are forwarded.

## Files involved

- `core/embeddings.py` — modify
- `core/text_embeddings.py` — modify
- `core/processor.py` — call-site update (likely line ~123 and lazy-loader helpers around 94–118)
- `api/routes/status.py` — likely calls `get_model_status()` for both; update if needed
- New: `core/lazy_model.py` (or similar — name is open for grilling)
- New: `core/tests/test_lazy_model.py` + small wrapper tests

## Not in scope

- Switching models or changing embedding dimensions.
- The `get_combined_embedding`/`safe_search` logic (lives in CLIP wrapper; just stays).
- Touching `core/chunking.py` or OCR.
