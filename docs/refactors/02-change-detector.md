# 02 — ChangeDetector: split decision logic out of CaptureService

**Status:** Ready to grill.
**Depends on:** Nothing.
**Risk:** Low — fully contained in `core/capture.py`.

## Friction (current state)

`core/capture.py:_capture_loop` (lines 107–172) interleaves **two distinct concepts**:

1. **Screen capture** — `_grab_screen()`, `_image_to_array()`, `_save_screenshot()`.
2. **Change detection / save decision** — SSIM comparison (line 125), threshold check (128), 3-stability-check loop (133–146), `max_time_without_save` force-save counter (148–154).

The save decision logic is straight-line code inside the loop. There is no module that answers "given the previous frame, the current frame, and elapsed time, should I save?" — that question is implicit in the control flow.

**One concept (capture) and one concept (change detection) welded into a single class.** Tests cannot exercise the save-decision policy without driving the whole `CaptureService`. The save-decision policy has multiple knobs (`threshold`, `save_threshold`, `max_time_without_save`, 3 stability checks) and no isolated way to characterize them.

### Deletion test

- Delete the change-detection logic: you still have a screenshot grabber. Capture is independent.
- Delete the capture grabber: change detection has no input. Detection depends on capture.

So the dependency is one-directional — but today they're welded both ways inside `_capture_loop`. **Extracting detection is safe; both halves remain useful.**

## Target shape (sketch)

A `ChangeDetector` module that, given:
- the previous saved frame,
- a new candidate frame,
- elapsed time since last save,

returns a verdict: `SKIP`, `SAVE` (changed and stable), or `FORCE_SAVE` (chaotic but timeout exceeded).

`CaptureService._capture_loop` becomes: grab → ask detector → (maybe) save → record outcome.

The 3-stability-check loop is itself a small policy question — does it live inside the detector (detector returns "wait then ask again") or stay in the loop (loop orchestrates re-grabs)? Open for grilling.

## Open questions for `/grill-me`

1. **Detector API: stateful or stateless?** Stateless: pass it `(prev_frame, curr_frame, time_since_last_save)` and it returns a verdict. Stateful: the detector remembers the previous frame and the last save time; loop just feeds it the current frame. Stateful makes the loop trivial; stateless makes the detector trivial. Which trades better?
2. **Where does the 3-stability-check loop live?** Three options:
   - (a) Inside detector — it owns the "I think something changed, let me confirm" policy; loop hands it frames and it returns a verdict only when ready. Hard to test (detector now drives time).
   - (b) Outside — loop sees "looks changed," loop re-grabs N times, loop asks detector to evaluate stability. Detector stays pure; loop has more code.
   - (c) Split — detector returns `MIGHT_BE_CHANGE` and loop runs a confirmation phase.
3. **Force-save counter.** Belongs to the detector (since it's a decision input) or the loop (since it's clock-driven)? If the detector is stateless, the loop must pass `time_since_last_save` in; if stateful, the detector owns it.
4. **SSIM as a fixed dependency or pluggable?** Today SSIM (skimage) is the only similarity metric. Worth making detector accept an injectable similarity function for tests (a fake that returns scripted scores), or keep SSIM hardwired and test with real small arrays?
5. **Config wiring.** Detector takes thresholds in its constructor, or reads from `config.capture` each call? Constructor is more testable; live-read supports config reload at runtime. Does runtime reload exist anywhere else as a precedent?
6. **What should `_capture_loop` look like after?** Is the loop itself worth extracting too (a `CaptureLoop` class), or is it small enough to remain as a method on `CaptureService` once detection is gone?

## Test situation

`CaptureService` has no direct tests today. After this refactor:
- `ChangeDetector` should be tested with synthetic numpy arrays — drive verdict outcomes for: identical frames, large diff stable, large diff chaotic-then-timeout, repeated small drift staying below `save_threshold`.
- `CaptureService` can stay integration-only (it touches mss, disk, db) — but the loop should be small enough that integration tests are cheap.

## Files involved

- `core/capture.py` — modify
- New: `core/change_detector.py` (name open)
- New: `core/tests/test_change_detector.py`
- Possibly `core/config.py` — if config shape moves; likely unchanged.

## Not in scope

- The `_save_screenshot` path (DB write, incognito check) — that's a separate concern; leave it inside `CaptureService`.
- The `capture_now()` manual-capture API — stays as-is; bypasses the detector by design.
- Multi-monitor capture (currently primary only — line 58).
