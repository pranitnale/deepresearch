# Auto-Zoom Screen Recorder — Detailed Feasibility Report & PRD Input

**Date:** 2026-07-04
**Author:** Claude Code research session
**Companion document:** [screen-zoom-recorder-research.md](screen-zoom-recorder-research.md) (tool landscape with verification log)
**Purpose:** Everything needed to write the PRD for "the app": user context, requirements catalog, verified landscape, source-level feasibility analysis of the recommended foundation, options with effort estimates, risks, MVP scoping, and open questions.

**Verification standard:** Every claim about Recordly's capabilities in this document is verified at the **source-code level** (files fetched from `webadderallorg/Recordly@main` on 2026-07-04), not from marketing copy. GitHub metadata verified via the GitHub API the same day. Anything not verified is explicitly marked.

---

## 1. User & workflow context

**Persona:** Solo content creator producing short-form educational videos about AI tools for the energy sector. Not a professional video editor; values speed of production over cinematic perfection. Windows PC (note: an AI PC with Intel NPU, per prior sessions — irrelevant for capture, potentially relevant for on-device captions later).

**Video format:**
- Vertical **4:5** aspect ratio (Instagram/LinkedIn feed format), short-form
- Main content: screen recording of a tool being demonstrated
- **Circular talking-head overlay** at bottom-right or bottom-left
- Zooms toward the area of interest (usually where the mouse is heading / clicking), then back out
- Clicks visually highlighted

**Current workflow and pain:**
1. Record screen (tool demo)
2. Import into CapCut
3. Manually keyframe zoom-in/zoom-out animations for every point of interest ← **the pain: slow, fiddly, hard to get smooth easing, must be redone if timing changes**
4. Composite talking-head circle, export 4:5

**Target workflow:**
1. Hit record, demo the tool naturally (mouse + clicks captured as data)
2. Stop → editor opens with **zoom animations already proposed** at the right moments
3. Adjust: delete/add/retime zooms with drag-and-drop; user stays in control of *what* gets zoomed, but each zoom costs seconds, not minutes
4. Click highlights and cursor polish applied automatically per saved style
5. Talking-head circle placed by preset
6. Export 4:5 MP4 → finish captions/music in CapCut or post directly

**Explicit requirements from the user (traceability for the PRD):**
- R1. Quick screen recording (low friction to start/stop)
- R2. Zoom follows mouse movement "when I want to" — i.e., **controllable**, not always-on
- R3. Zooms can be created/edited **after** recording (post-hoc control)
- R4. Smooth, slow zoom-in toward a target (e.g., a button being approached)
- R5. Click highlighting when a button is clicked
- R6. Lightweight — must not be heavy on the computer
- R7. Very easy zoom UX (the whole point vs CapCut keyframes)
- R8. Windows
- R9. 4:5 vertical output
- R10. Circular talking-head overlay, bottom corner (implied from format description)
- R11. Low/no cost preferred; open to building on open source

---

## 2. Landscape summary (full details in companion doc)

| Candidate | Verdict for this use case |
|---|---|
| **Recordly** (18.6k★, AGPL-3.0, Electron/TS, very active) | **Meets R1–R11 out of the box** (source-verified below). Recommended foundation. |
| OpenScreen (39k★, MIT) | Recordly's ancestor; **archived 2026-06-17**. Use only as MIT-licensed reference code. |
| getopenscreen/openscreen (445★, MIT, active) | Official community continuation; smaller momentum. MIT fallback if AGPL is a concern. |
| Cap (19.9k★, AGPL+MIT, Rust/Tauri, very active) | Excellent but Loom-shaped (cloud/sharing). Zoom automation less mature; heavy monorepo to modify. |
| ScreenArc (513★, GPL-3.0) | Fully automatic zoom, but no 4:5 preset, 2K cap, unsigned installer, small community. |
| Screenity (18.4k★, GPL-3.0) | Chrome extension only — can't capture desktop apps properly. Out. |
| screen-demo (49★, no license, stale) | Windows-first Tauri proof-of-concept; useful as architecture reference only. |
| OBS + zoom scripts (MIT/various) | Live zoom baked into recording; no post-hoc control (fails R3). Fallback only. |
| FocuSee (commercial, $49.99/yr–$199.99 lifetime) | The Windows commercial benchmark; UX reference for "auto-detect clicks → editable zoom segments". |
| Screen Studio (commercial) | Still macOS-only; Windows waitlist ("Windows version ready?") as of 2026-07-04. |

**Strategic takeaway:** the "Screen Studio for Windows" gap was real until ~2025; it has now been filled by the OpenScreen→Recordly lineage. Building an equivalent from scratch would be re-implementing an actively-maintained 18.6k★ project. The value-add opportunity is **personalization on top** (your style, your format, your speed), not the base recorder.

---

## 3. Recordly deep-dive (source-verified)

### 3.1 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Electron main process (electron/)                             │
│  ├─ Recording: ipc/recording/windows.ts (+ windowsFallbacks) │
│  │    → native WGC capture; WASAPI system+mic audio          │
│  │    → ffmpeg (bundled binary) for encode/mux               │
│  ├─ Cursor telemetry: ipc/cursor/{monitor,telemetry,          │
│  │    interaction}.ts + native/bin/win32-x64/cursor-monitor.exe│
│  ├─ Export: ipc/export/* + ipc/ffmpeg/filters.ts             │
│  │    + native/bin/win32-x64/recordly-gpu-export.exe          │
│  │    (C++ GPU export helper, source in native/gpu-export-probe)│
│  ├─ Captions: ipc/captions/* + bundled whisper binaries       │
│  │    (on-device, offline)                                    │
│  └─ Extensions: extensions/{extensionLoader,Marketplace}.ts   │
├──────────────────────────────────────────────────────────────┤
│ Renderer (src/, React + TypeScript + Tailwind)                │
│  ├─ Launch/record HUD incl. floating webcam preview          │
│  ├─ Video editor: timeline, zoom regions, cursor overlay,    │
│  │    webcam bubble, frame styling, export settings          │
│  └─ Extension host (render hooks into the pipeline)          │
└──────────────────────────────────────────────────────────────┘
```

Key design property (the Screen Studio technique): **the screen is recorded clean; the cursor is recorded as a telemetry stream** (`CursorTelemetryPoint`: position + `interactionType` of `click`, `double-click`, `right-click`, `middle-click`, plus heuristic kinds). Cursor rendering, zooms, click effects are all **computed at edit/export time** — which is exactly what makes R3 (post-hoc control) and R7 (easy zoom) possible.

### 3.2 The auto-zoom engine (`src/components/video-editor/timeline/zoomSuggestionUtils.ts`)

Verified algorithm:
1. Normalize cursor telemetry samples.
2. Classify **interaction candidates**: `dwell` (cursor hovers ≥450 ms within a 2% movement radius), `click-like`, `double-click-like`, `text-focus-like`, `dropdown-open`, `text-selection`, `text-field-click` — each with an explicit-vs-heuristic source tag and strength score.
3. **Cluster clicks**: consecutive clicks ≤2,500 ms apart merge into one zoom region; ±500 ms padding around clusters.
4. Emit `SuggestedZoomRegion { start, end, focus }` list, surfaced in the timeline as suggestions the user accepts/edits/deletes.
5. Fresh recordings auto-apply zooms only when the **source** aspect ratio ≥1.2 (landscape screens — your case when recording a desktop tool).

All thresholds are named exported constants at the top of the file → **tuning the zoom personality to your taste is a constants-level change**, and per-user configurability would be a small settings feature.

Manual control (R2/R3): zoom regions are first-class timeline objects (`useTimelineZoomActions.ts`, `zoomRegionUtils.ts`, `zoomTransform.ts` with eased animation math in `zoomAnimation`), draggable/retimable in the editor.

### 3.3 Export & aspect ratio (`src/utils/aspectRatioUtils.ts`, `exportDimensions.ts`)

Verified: preset list is `["native", "16:9", "9:16", "1:1", "4:3", "4:5", "16:10", "10:16"]` **plus arbitrary custom `W:H` ratios** with validation. **R9 (4:5) is already a one-click preset. No code needed.** Dimensions are normalized to even values (codec-safe); quality tiers scale 0.6/0.75/0.9/source. MP4 (H.264) and GIF export; GPU-accelerated export path on Windows via `recordly-gpu-export.exe`.

### 3.4 Webcam / talking head (verified in `src/components/launch/floatingWebcamPreview.ts`, `src/components/video-editor/videoPlayback/webcamSync.ts`, `webcamOverlay.ts`, `WebcamCropControl.tsx`)

- Webcam is **recorded live during screen recording** (floating preview overlay on the recording HUD; recorded stream carries a start-offset that the editor uses for sync: `getWebcamMediaTargetTimeSeconds({currentTime, webcamDuration, timeOffsetMs})`).
- Editor overlay bubble: preset + custom X/Y position, size, margin, **roundness (→ full circle)**, mirroring, shadow, crop control, and **zoom-reactive scaling** (bubble stays proportionate while the screen zooms — a subtle detail that would be painful to build yourself).
- R10 fully covered.

### 3.5 Extension system (`EXTENSIONS.md`, `electron/extensions/*`)

Verified: extensions are user-installable JS bundles (`recordly-extension.json` + `index.js`, TypeScript-authorable) running in the editor renderer with a **permission-gated API**: `registerRenderHook("final", ctx => …)` draws directly into the render/export pipeline; plus playback/export event hooks, `registerCursorStyle()`, `registerFrame()`, `registerWallpaper()`, `registerSettingsPanel()`, `playSound()`. Local install via `Extensions → Open Directory`; marketplace for distribution; examples in `extension-examples/`.

**Implication:** custom click-highlight visuals, branded frames, and some workflow settings can ship as an **extension — zero fork, zero merge maintenance.**

### 3.6 Performance & footprint (R6)

- Capture path is **native** (WGC helper + WASAPI + ffmpeg), not Electron's `getUserMedia` — capture overhead is low; the Electron UI is idle during recording. GPU switches handled explicitly (`gpuSwitches.ts`).
- Export uses a native GPU helper on Windows.
- Cost is typical Electron RAM (~a few hundred MB for the UI). Assessment: comfortably "not heavy" for a content-creation PC; lighter alternatives (Tauri) only matter if you build from scratch.
- *(Unverified: no independent benchmark numbers; validate during hands-on testing — see §8.)*

### 3.7 Health & governance

- 18,579★, pushed 2026-07-02; CI for Windows builds + winget releaser workflow (auto-publishes to winget); issue templates, CONTRIBUTING.md, CodeRabbit review bot; "Accepting PRs" in README; i18n (13 languages); `.recordly` project files for re-editing.
- License **AGPL-3.0** (LICENSE.md verified). Consequences: free for your use, modifications for personal use carry **no** disclosure obligation; only if you *distribute* a modified app must you publish its source under AGPL. Extensions you write are yours (the API even lets you declare MIT).
- Lineage risk: this project relicensed/rebranded from MIT OpenScreen; the ecosystem churned once already (OpenScreen archived). Mitigations in §7.

---

## 4. Gap analysis — requirements vs Recordly (evidence-based)

| # | Requirement | Status | Evidence | Gap / action |
|---|---|---|---|---|
| R1 | Quick recording | ✅ | Native WGC recording, HUD, "jump directly from recording into the editor" | Validate start-to-recording latency hands-on |
| R2 | Controllable zoom-to-mouse | ✅ | Suggestions are opt-in per region; manual regions; auto-apply only for landscape sources | Optional: record-time "mark zoom" hotkey (not present — candidate feature F3) |
| R3 | Zoom in post | ✅ | Zoom regions on timeline, drag-and-drop | — |
| R4 | Smooth slow zoom toward target | ✅ | `zoomTransform`/`zoomAnimation` easing; focus point from telemetry | Tune defaults to your taste (F2) |
| R5 | Click highlight | ✅/⚠️ | Cursor click **bounce** built in; click *sounds* via extension; a visible ring/pulse at click point ≈ verify in app | If missing: extension via `registerRenderHook` + telemetry (F4) |
| R6 | Lightweight | ✅ (design) | Native capture/export helpers | Benchmark on your machine (§8) |
| R7 | Easy zoom UX | ✅ | The core product thesis; FocuSee-style suggest→edit flow | — |
| R8 | Windows | ✅ | Win10 19041+; WGC + WASAPI + GPU export helper; winget CI | — |
| R9 | 4:5 export | ✅ | `"4:5"` in `ASPECT_RATIOS` + custom ratios | **None — closed.** |
| R10 | Circular talking head | ✅ | Live webcam recording + bubble with roundness, zoom-reactive | Verify your camera works; check bubble at 4:5 |
| R11 | Free / OSS | ✅ | AGPL-3.0, no paid tiers | — |

**Net gap: near-zero for the core.** The buildable value is in personalization (below), not in the base app.

---

## 5. Options analysis

### Option A — Use Recordly as-is
**Effort:** ~1 hour. **Cost:** €0.
Install (winget or GitHub release), record a real demo, accept/edit zoom suggestions, set webcam bubble, export 4:5.
**Choose when:** the hands-on test (§8) passes with no dealbreakers. **This is the mandatory first step regardless of what follows** — it converts every remaining ⚠️ into a fact.

### Option B — Recordly + custom **extension** (no fork) ← cheapest customization
**Effort:** ~1–3 days with Claude Code. **Maintenance:** near-zero (survives app updates).
Ship a "MyStyle" extension that:
- registers your click-highlight visual (expanding ring / pulse at click coordinates) via `registerRenderHook("final", …)` if the built-in bounce isn't enough,
- registers a branded frame/wallpaper set for your energy-AI channel look,
- adds a settings panel for your defaults.
**Limits:** extensions run in the editor renderer; they can't change recording behavior, zoom-suggestion constants, or add export presets (those are already fine). *(Exact permission surface beyond render/events/assets/settings not fully verified — check marketplace docs during F4.)*

### Option C — Fork Recordly (recommended if B's limits bite)
**Effort:** days, not weeks; Electron+TS+React is the friendliest stack for AI-assisted modification. Windows build CI already exists.
Candidate delta features (each independently shippable, PRD line items):

| ID | Feature | Difficulty | Where (verified files) |
|---|---|---|---|
| F1 | "My format" one-click profile: 4:5 + quality + bubble position/size/roundness defaults applied to every new project | Easy | `exportStartSettings.ts`, project defaults, settings store |
| F2 | Zoom personality presets ("calm/slow" default: longer ease-in, deeper dwell threshold, fewer suggestions) | Easy | Expose `zoomSuggestionUtils.ts` constants + `zoomTransform` easing defaults in settings |
| F3 | Record-time "zoom here" hotkey → marker stream → guaranteed zoom region in editor | Medium | `electron/ipc/recording/*` (hotkey + marker), `ipc/cursor/telemetry.ts` (event type), `zoomSuggestionUtils.ts` (explicit-source candidate) |
| F4 | Click-highlight ring (if not built in) | Easy | Extension (Option B) or `src/components/video-editor` cursor overlay |
| F5 | Safe-zone guides for 4:5 (caption/UI margins for IG/LinkedIn) | Easy | Editor canvas overlay |
| F6 | Auto-captions for your voiceover | Already built in | whisper on-device (verify German/English quality) |

**Maintenance strategy:** keep the fork as a thin patch series on top of upstream `main`; upstream accepts PRs, so push F2/F3/F5 upstream to shrink your diff to ~zero over time. AGPL obligations only trigger if you distribute the fork.

### Option D — Build from scratch (Tauri + Rust)
**Effort:** realistically 4–8+ weeks to reach Recordly's current polish, then permanent maintenance.
Only justified if the goal becomes **shipping a product** (e.g., "Screen Studio for Windows, energy-creator edition") rather than fixing your workflow. Verified architecture if pursued:
- Shell: **Tauri** (Rust core, React UI) — low RAM, small binary.
- Capture: **windows-capture** (MIT, active; WGC + DXGI + hardware H.264 encoder) or **scap** (MIT, Cap's cross-platform crate).
- Input telemetry: **rdev** (MIT, active) global mouse hooks → `(t, x, y, event)` sidecar stream; hide real cursor, render synthetic cursor in post.
- Render/export: wgpu (WGSL) GPU pass or FFmpeg filter graph (`crop`+`scale` keyframe expressions); compose webcam bubble in the same pass.
- Auto-zoom: reimplement click-clustering (Recordly's AGPL algorithm can't be copied into a non-AGPL product; the *ideas* — dwell ≥450 ms, cluster gap 2.5 s — are reimplementable, or copy code and stay AGPL).
**Not recommended now.** Revisit only after months of daily Recordly use proves a product thesis.

### Option E — Fallbacks
- **OBS + Smooth-Zoom script** (free, live zoom — fails R3),
- **FocuSee** ($49.99/yr or $199.99 lifetime — if you'd rather pay than tinker; Windows build quality complaints in reviews, unverified),
- **CapCut keyframes** (status quo).

### Decision recommendation
**A → (B and/or C) pipeline.** Test as-is this week; write the PRD as a *delta spec* (F1–F5) against whatever the test reveals; implement the cheapest layer first (extension), fork only for F1/F2/F3.

---

## 6. Effort & cost summary

| Option | Calendar effort | Running cost | Risk | Fit to R1–R11 |
|---|---|---|---|---|
| A: Recordly as-is | 1 hour | €0 | Low | ~95% (pending hands-on) |
| B: + extension | 1–3 days | €0 | Low | ~98% |
| C: fork (F1–F5) | 3–10 days | low (rebase on releases) | Medium (upstream churn) | ~100% |
| D: from scratch | 4–8+ weeks | high (you own everything) | High | 100% eventually |
| E: FocuSee | 1 hour | $49.99/yr or $199.99 once | Low | ~90% (no extensibility) |

---

## 7. Risks & mitigations

1. **Project churn** (OpenScreen was archived once already; Recordly relicensed from that codebase). *Mitigation:* Recordly has independent momentum (18.6k★, marketplace, CI, sponsors); fallbacks exist (getopenscreen MIT continuation, Cap); your recordings are standard MP4 + `.recordly` JSON projects — no lock-in for finished videos.
2. **AGPL** if you ever distribute a modified build. *Mitigation:* publish your fork's source (it's a content-creator tool, not secret sauce), keep custom bits as extensions, or upstream them.
3. **Windows edge cases** (multi-monitor DPI scaling, HDR screens, window-capture of specific apps). *Mitigation:* hands-on test checklist (§8); `windowsFallbacks.ts` suggests the project already handles capture fallbacks.
4. **Auto-zoom quality on your actual content** (web dashboards with lots of hover/scroll may over- or under-suggest). *Mitigation:* suggestions are editable; F2 tuning; F3 hotkey gives deterministic control.
5. **Webcam capture quality/sync on your hardware** — *unverified until tested.* Fallback: record face on phone, use Recordly's upload-webcam-footage path (explicitly supported).
6. **Electron RAM on low-spec machines** — likely fine on your machine; benchmark in §8.

---

## 8. Hands-on validation checklist (do before writing the PRD)

Record one real ~60–90 s demo of an actual AI-energy tool and check:

- [ ] Time from app launch → recording started (target <10 s)
- [ ] CPU/RAM during recording (Task Manager; target: no fan spin, <15% CPU on your machine)
- [ ] Auto-zoom suggestions: how many are right/wrong on your content? How many seconds to fix?
- [ ] Zoom feel: default speed/easing vs your CapCut style (note desired depth & duration for F2)
- [ ] Click visibility: is cursor click-bounce enough, or do you want a ring/pulse? (decides F4)
- [ ] Webcam: does live capture work with your camera? Circle bubble at bottom-left/right at 4:5 — does zoom-reactive scaling look right?
- [ ] Export: 4:5 preset, quality, export duration, file size; does the result drop into CapCut/IG cleanly?
- [ ] Multi-monitor / DPI: record on your actual monitor setup
- [ ] Captions: try on-device captions on one voiceover (English + German)
- [ ] Total wall-clock time vs your current CapCut workflow for the same clip

Each unchecked box that fails becomes a PRD requirement; each that passes gets deleted from scope.

---

## 9. PRD skeleton (ready to fill after §8)

1. **Problem statement** — §1 pain paragraph, plus measured time-per-video from §8 baseline.
2. **Goals / non-goals** — Goal: cut zoom-editing time by >80%; ship videos same-day. Non-goal (initially): building a distributable product; cloud sharing; macOS.
3. **Users** — you (single-user tool); secondary: other short-form tool-demo creators if upstreamed.
4. **Approach** — Option A+B(+C) per §5 decision; name the foundation (Recordly fork/extension) and pin the upstream commit.
5. **Functional requirements** — R1–R11 mapped to F1–F6 with the §4 evidence table; each F-item gets acceptance criteria (e.g., F1: "new project defaults to 4:5, bubble bottom-right circle 22% width, one keystroke to flip corner").
6. **Non-functional** — recording overhead budget, export time budget, works offline, data stays local.
7. **Milestones** — M0: validated as-is workflow (§8). M1: extension (F4/F5 + branding). M2: fork with F1/F2. M3: F3 hotkey. M4: upstream PRs.
8. **Risks** — §7.
9. **Success metric** — minutes from "stop recording" to "4:5 MP4 exported" ≤ 5 for a typical short.

---

## 10. Privacy / network audit (source-level, commit 641d223, 2026-07-02)

Full clone of `webadderallorg/Recordly` audited for outbound network activity.

**No telemetry, no analytics, no crash reporting.** Dependency list contains no Sentry/PostHog/Mixpanel/Segment/GA or similar SDK; no such call sites exist in code. (All "telemetry" hits in the codebase are *cursor* telemetry — local mouse-position data stored on disk.)

**Recordings never leave the machine.** Video, audio, webcam, cursor data, and `.recordly` projects are written locally only. The editor's internal media server binds `127.0.0.1` exclusively (`mediaServer.ts:217`) — not reachable from the network. All renderer `fetch()` calls target that localhost server or blob URLs.

**Complete inventory of outbound connections:**

| Connection | When | What is sent | Control |
|---|---|---|---|
| GitHub releases (update check) | Automatic, every 6 h (`UPDATE_CHECK_INTERVAL_MS`); metadata only — `autoDownload=false`, `autoInstallOnAppQuit=false` | Standard HTTP request; no user data | Set env var `RECORDLY_DISABLE_AUTO_UPDATES=1` to disable entirely |
| `marketplace.recordly.dev` | **Only** when you open the extension marketplace / install an extension | Headers: app version + OS platform; on install, a fire-and-forget download-count POST (version header only) | Don't use the marketplace; install extensions from a local folder instead |
| `huggingface.co` (Whisper `ggml-small.bin`) | **Only** on first use of auto-captions (one-time model download) | Plain file download | Skip captions, or pre-download the model; transcription itself is 100% on-device |
| User-pasted font URL (`customFonts.ts`) | **Only** if you import a custom font by URL | Fetches the URL you provide | Use local font files |
| GitHub issues / Discord / X links | **Only** on click (opens system browser via `openExternal`) | Nothing from the app | — |

No raw sockets (`net`/`tls`/`dgram`), no WebSockets, no other hosts found in `electron/` or `src/`.

**Verdict:** with one firewall rule (or the env var) blocking the 6-hourly GitHub update check, Recordly is fully offline; even without it, no user content is ever transmitted. Caveats: (a) audit applies to this commit — re-check on major updates; (b) official installers are built by the repo's GitHub Actions CI — build from source if you require binary-level assurance; (c) Chromium/Electron platform networking (e.g., DNS) is outside app control but carries no app data.

## 11. Bottom line

- The app you described **exists and is healthy**: Recordly covers all eleven requirements, including the two you'd least expect (4:5 preset, zoom-reactive circular webcam bubble) — verified in source, not marketing.
- **Feasibility of "your app": high, because it's a customization project, not a build project.** The entire delta between Recordly and your dream tool is: your default style (F1/F2), an optional record-time zoom hotkey (F3), and possibly a click-ring visual (F4) — days of Claude Code work on a friendly TypeScript codebase, with an extension API that makes part of it fork-free.
- Building from scratch is technically feasible (all MIT building blocks verified: windows-capture, rdev, scap) but strategically wrong today — it recreates an 18.6k★ active project to save days of fork work.
- **Next action:** run the §8 checklist (~1 hour), then write the PRD from §9 with the checklist results filled in.
