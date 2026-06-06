# Timeline Fullscreen Mode — Implementation Plan

## Goal
A true OS fullscreen mode for the Timeline tab where the current screenshot fills
the monitor and keyboard navigation (`←`/`→`, `Shift`, `Home`/`End`) works exactly
as it does in the normal timeline. Exiting fullscreen drops the user into the
existing lightbox for that image.

All changes are in `web/src/app/page.tsx` (single file).

## Behavior summary
- **Tech:** browser Fullscreen API (`requestFullscreen` / `exitFullscreen`),
  state synced to the `fullscreenchange` event.
- **Built on:** the timeline's existing `currentIndex` / `currentSnapshot`. No new
  navigation logic — the existing keydown handler is reused verbatim.
- **Scope:** Timeline tab only. Search/grid results keep using the lightbox.
- **Enter:** ⛶ button in the timeline header row, or the `F` key (timeline view,
  not typing in an input, snapshot exists).
- **Exit:** `Esc`, `F`, or ✕ button → opens the **lightbox** for the current image
  (layered exit). A second `Esc` closes the lightbox back to the timeline, still
  parked on the same image.
- **Overlay:** always-visible, low-opacity counter + timestamp in a corner.
- **Nav (keyboard only):** `←` older, `→` newer, `Shift` = 10, `Shift+⌘` = fast
  jump (~2% of total), `Home`/`End` = oldest/newest. Already implemented at
  `page.tsx:556-588`; works automatically because `activeView` stays `'timeline'`
  and `selectedImage` stays `null` while in fullscreen.

## Changes

### 1. State + ref (near line 72, by `selectedImage`)
```ts
const [isFullscreen, setIsFullscreen] = useState(false);
const fullscreenRef = useRef<HTMLDivElement>(null);
```

### 2. Enter/exit helpers + fullscreenchange sync (new useEffect + callbacks)
```ts
const enterFullscreen = useCallback(async () => {
  if (!currentSnapshot) return;
  try {
    await fullscreenRef.current?.requestFullscreen();
    // isFullscreen is set by the fullscreenchange listener below
  } catch (err) {
    console.error('Failed to enter fullscreen:', err);
  }
}, [currentSnapshot]);

// Sync React state to the browser's actual fullscreen state, and run the
// "layered exit -> lightbox" on the way out.
useEffect(() => {
  const onChange = () => {
    const active = document.fullscreenElement === fullscreenRef.current;
    setIsFullscreen(active);
    if (!active && currentSnapshot) {
      // Exiting fullscreen (via Esc, F, ✕, or browser) -> open lightbox
      setSelectedImage(currentSnapshot);
    }
  };
  document.addEventListener('fullscreenchange', onChange);
  return () => document.removeEventListener('fullscreenchange', onChange);
}, [currentSnapshot]);
```
Exit is always `document.exitFullscreen()` (from `F`/✕); the listener handles the
lightbox handoff so every exit path behaves identically.

Note: read `currentSnapshot` at exit time. Because the effect closes over it, it
must be in the dep array (it already changes as the user navigates, so the latest
value is captured).

### 3. Keyboard: add `F` toggle + keep Esc working
In the main keydown handler (`page.tsx:515`):
- Add an `F` branch (gated like the other keys: timeline view, `activeElement` not
  an INPUT, snapshot exists):
```ts
if (e.key === 'f' && activeView === 'timeline' && !selectedImage &&
    document.activeElement?.tagName !== 'INPUT') {
  e.preventDefault();
  if (document.fullscreenElement) document.exitFullscreen();
  else enterFullscreen();
  return;
}
```
- The existing nav block (`page.tsx:556`) already requires
  `activeView === 'timeline' && !selectedImage` — both hold in fullscreen, so
  `←/→/Shift/Home/End` keep working with **no change**.
- `Esc`: no code change needed. The browser exits fullscreen natively on Esc and
  fires `fullscreenchange`, which opens the lightbox. The second Esc then hits the
  existing handler (`page.tsx:516`) and closes the lightbox.
- Add `enterFullscreen` to this effect's dependency array.

### 4. Fullscreen container (new top-level overlay, near the lightbox at line 1724)
Rendered whenever a snapshot exists so `requestFullscreen` has a stable target;
the actual fullscreen visuals are driven by the `:fullscreen` state. The container
is a full-viewport flex box that centers the image; the image uses
`max-w-full max-h-full object-contain` (NOT `max-w-screen` — that is not a real
Tailwind class).
```tsx
{currentSnapshot && (
  <div
    ref={fullscreenRef}
    className="fixed inset-0 z-50 bg-black items-center justify-center
               hidden [&:fullscreen]:flex"
  >
    <img
      src={getImageUrl(currentSnapshot.image_path)}
      alt={`Screenshot from ${formatTimestamp(currentSnapshot.timestamp)}`}
      className="max-w-full max-h-full object-contain"
    />
    {/* always-visible minimal overlay (decorative position/time, not interactive) */}
    <div className="absolute bottom-4 left-4 px-3 py-1.5 bg-black/40 rounded
                    text-xs text-white/70 pointer-events-none tabular-nums">
      {currentIndex + 1} / {totalSnapshots} · {formatTimestamp(currentSnapshot.timestamp)}
    </div>
    {/* exit button — icon-only, so aria-label is required; ≥44px hit area */}
    <button
      onClick={() => document.exitFullscreen()}
      aria-label="Exit fullscreen"
      className="absolute top-4 right-4 p-2.5 rounded text-white/60 hover:text-white
                 hover:bg-white/10 transition-colors
                 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86efac]"
    >
      <svg className="w-5 h-5" aria-hidden="true" fill="none" viewBox="0 0 24 24"
           stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
)}
```
The element stays mounted (just `hidden` until fullscreen) so the Fullscreen API
keeps a valid target. `[&:fullscreen]:flex` flips it visible only while it is the
fullscreen element.

**Two assumptions to verify before/while building:**
- Tailwind version supports the `[&:fullscreen]:flex` arbitrary variant. If not,
  toggle visibility off the `isFullscreen` state class instead.
- `z-50` matches the lightbox; harmless because the browser promotes the
  fullscreen element to the **top layer**, so page z-index is irrelevant while
  fullscreen is active. Kept on the app's existing scale (40/50/60) regardless,
  rather than an arbitrary `z-[9999]`.

### 5. ⛶ button in the timeline header row (`page.tsx:1249-1254`)
Add a fullscreen-enter button next to the `currentIndex + 1 / totalSnapshots`
counter, shown only when `currentSnapshot` exists. Icon-only → `aria-label`
required, decorative svg `aria-hidden`, visible focus ring, `cursor-pointer`:
```tsx
<button
  onClick={enterFullscreen}
  aria-label="View fullscreen (F)"
  title="Fullscreen (F)"
  className="p-1.5 rounded text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#1c1c1c]
             cursor-pointer transition-colors
             focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86efac]"
>
  <svg className="w-4 h-4" aria-hidden="true" fill="none" viewBox="0 0 24 24"
       stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round"
          d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9
             M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15m11.25 5.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
  </svg>
</button>
```

## Edge cases
- **Window-load at edges:** while a new window loads, `currentSnapshot` can briefly
  be `null`. The fullscreen `<img>` keeps the last `src` until the new snapshot
  resolves (React keeps the prior render); no black flash. If `currentSnapshot`
  goes null the container unmounts — guard by holding the last non-null snapshot in
  a ref if flicker appears in testing.
- **No snapshots:** ⛶ button and `F` are inert (guarded on `currentSnapshot`).
- **Selection keys (Delete/h/⌘A) in fullscreen:** left active (harmless — no
  selection UI is shown in fullscreen and they no-op without a selection). Not
  suppressed, to avoid extra complexity.
- **Browser support:** Fullscreen API is standard in all evergreen browsers; the
  app already targets a desktop browser/webview.

## Design & accessibility (from ui-ux-pro-max review)
- **Icon button labels (Critical):** ⛶ and ✕ are icon-only → both carry
  `aria-label`; their svgs are `aria-hidden="true"`.
- **Visible focus (Critical):** both buttons use
  `focus-visible:ring-2 focus-visible:ring-[#86efac]` (replacing the default
  outline, not just removing it).
- **Image alt:** descriptive alt tied to the timestamp, not empty.
- **Z-index:** stays on the app scale (40/50/60); no arbitrary `z-[9999]`.
- **Touch target:** exit button uses `p-2.5` for a ≥44px hit area.
- **Motion:** overlay is always-visible (no fade) and entry has no animation, so
  there is nothing to gate behind `prefers-reduced-motion`.
- **No keyboard trap:** exit is reachable via Esc/F and a focusable ✕ button;
  arrow-key nav does not trap focus.
- **No emoji icons:** all glyphs are inline SVG (expand / close), consistent with
  the existing icon set in the file.

## Out of scope
- Mouse-driven prev/next arrows in fullscreen (keyboard only, by decision).
- Fullscreen for search/grid results (lightbox handles those).
- Zoom/pan within the fullscreen image.

## Test checklist (manual)
1. Timeline tab → `F` and ⛶ both enter OS fullscreen; image fills monitor.
2. `←/→` step; `Shift+←/→` jump 10; `Shift+⌘` fast jump; `Home`/`End` ends.
3. Navigate across a 500-item window boundary — no stall/black flash.
4. Counter + timestamp overlay update on every move.
5. `Esc` → lightbox on current image; `Esc` again → timeline on same image.
6. `F` and ✕ also exit → lightbox.
7. `F` does nothing while typing in the search box or on the Search tab.
