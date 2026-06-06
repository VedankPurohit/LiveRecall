# 03 — BackendRunner: unify subprocess and thread modes behind one protocol

**Status:** Ready to grill.
**Depends on:** Nothing.
**Risk:** Low — contained in `tray/backend.py`.

## Friction (current state)

`tray/backend.py:BackendManager` (lines 41–185) supports **two execution modes** for running the FastAPI server, with inconsistent semantics across them:

| Concern | Dev (subprocess) | Frozen (thread) |
|---------|------------------|------------------|
| Run | `subprocess.Popen` (lines 96–109) | `threading.Thread` running uvicorn (lines 76–82) |
| `is_running` check | `process.poll() is None` (line 64) | `thread.is_alive()` (line 59) |
| Stop | `terminate()` → `wait()` → `kill()` (lines 147–153) | **Cannot kill** — line 142 comment: "just mark it as stopped" |
| Auto-restart on crash | Works via `_monitor_loop` (lines 171–181) | Threads can't be restarted in-process if uvicorn dies; restart calls `start()` which re-creates the thread but the dead one lingers |

The class uses `self._frozen` as a runtime flag inside every method (lines 57–64, 76–84, 138–153). The two modes are **two adapters of "thing that runs the backend"** — the seam exists in practice but not in the type system. Code that wants to reason about "backend state" has to know which mode it's in.

### Deletion test

Delete either mode: the app no longer ships. Both are real. The waste isn't in either implementation — it's in the **branching inside every method** of `BackendManager`. Concentrating the branch in one place (the choice of which runner to instantiate) is the deepening move.

## Target shape (sketch)

A `BackendRunner` protocol (or abstract base) with:
- `start()` → bool (started successfully)
- `stop()` → None
- `is_alive()` → bool

Two adapters: `SubprocessRunner` and `ThreadRunner`. `BackendManager` picks one at construction time based on `is_frozen()` and then works against the protocol — no more `self._frozen` branches in every method.

Restart / monitor / health-check stays in `BackendManager` and is mode-agnostic.

## Open questions for `/grill-me`

1. **Protocol vs ABC?** `typing.Protocol` is duck-typed and lighter; `abc.ABC` is explicit. Project uses Python 3.10+ (CLAUDE.md). Slight preference for `Protocol` — but does anywhere in this codebase already pick one style for runtime interfaces?
2. **Where does the ready-event live?** Today `BackendManager._ready_event` is shared with `_run_api_server_thread` (line 51, 78–84). In the subprocess mode there's no such event — health check polls instead (lines 118–130). Should each runner expose `wait_for_ready(timeout)` (uniform API), or should `BackendManager` keep polling `api_client.health_check()` outside the runner (uniform but ignores the cheaper signal the thread runner has)?
3. **Restart semantics when threads can't die.** Thread runner today: `stop()` sets `_server_thread = None` but the thread keeps running. Restart would create a *second* thread bound to the same port → port-in-use crash. Options: (a) don't expose restart in frozen mode (manager checks); (b) make `ThreadRunner.stop()` actually stop uvicorn via `server.should_exit = True`; (c) accept that frozen builds don't auto-restart and document. (b) is correct but uvicorn shutdown semantics need verifying.
4. **Where does `_monitor_loop` live?** In `BackendManager` (mode-agnostic) — calls `runner.is_alive()`. That seems right. Confirm.
5. **API client coupling.** `BackendManager._wait_for_health` (line 118) reaches into `api_client`. After this refactor, is it cleaner to push health-check into the runner protocol too (so the runner knows when it's ready), or keep it as an external probe? External probe is what we have; protocol-internal is more cohesive but harder to test without uvicorn.
6. **What does `is_frozen()` selection logic look like?** Factory function `make_runner(host, port) -> BackendRunner`, or constructor-injected runner so tests can pass a fake?

## Test situation

`tray/api_client.py` has tests. `tray/backend.py` does not. After this refactor:
- Fake `BackendRunner` that scripts `start`/`stop`/`is_alive` outcomes → test `BackendManager`'s restart/monitor logic deterministically.
- Each real runner can be smoke-tested by starting a tiny dummy ASGI app on an ephemeral port.

## Files involved

- `tray/backend.py` — modify (split into `BackendManager` + runners)
- `tray/api_client.py` — likely unchanged
- `tray/app.py` — uses `backend_manager`; should be unaffected unless the factory call changes
- New: `tray/tests/test_backend.py`

## Not in scope

- Switching uvicorn for hypercorn / another server.
- Multi-process worker management (we run a single worker).
- Changing the `--api-only` CLI flag shape.
- Configuration of `API_HOST` / `API_PORT` (lives in `tray/config.py`).
