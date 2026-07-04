# Auto-Zoom Screen Recorder for Windows — Deep Research Report

**Date:** 2026-07-04
**Goal:** Replace the manual CapCut keyframe-zoom workflow for short-form vertical (4:5) videos: screen recording of a tool + circular talking-head overlay, with smooth zoom toward mouse/click targets and click highlighting. Windows, lightweight, easy to control.

**Verification note:** All GitHub facts below (existence, license, stars, archived status, last activity, README feature claims) were verified directly against the GitHub API and raw README/LICENSE files on 2026-07-04. Commercial pricing/platform claims were checked against the vendors' own pages. Items marked *(unverified)* could not be independently confirmed.

---

## TL;DR

**The tool you want already exists, open source, and runs on Windows: [Recordly](https://github.com/webadderallorg/Recordly)** (18.6k★, AGPL-3.0, actively developed — last push 2 days before this report). It is the actively maintained successor of OpenScreen (the 39k★ "free Screen Studio alternative" that was archived in June 2026) and does: automatic zoom suggestions from cursor activity, manual drag-and-drop zoom regions on a timeline, click-bounce/cursor effects, a circular webcam bubble overlay that reacts to zooms, native Windows Graphics Capture, and aspect-ratio-controlled MP4 export.

**Recommended path:** Try Recordly first (1 hour). If it covers ~90% of your workflow, either use it as-is or **fork it** and add the missing 10% (e.g., a 4:5 export preset, your zoom style defaults) — that is a far smaller project than building from scratch, and it's exactly the kind of task Claude Code handles well in an Electron/TypeScript codebase. Building from scratch only makes sense if you want a product, not a workflow fix.

---

## 1. Landscape

### 1.1 Open-source desktop apps (the "Screen Studio clone" category)

| Project | Stars | License | Windows | Auto-zoom | Activity (verified 2026-07-04) |
|---|---|---|---|---|---|
| [Recordly](https://github.com/webadderallorg/Recordly) | 18,579 | AGPL-3.0 | ✅ native WGC + WASAPI | ✅ auto suggestions + manual regions | ✅ Very active (pushed 2026-07-02) |
| [OpenScreen](https://github.com/siddharthvaddem/openscreen) | 39,164 | MIT | ✅ winget / .exe | ✅ auto follows cursor | ⚠️ **Archived 2026-06-17** |
| [getopenscreen/openscreen](https://github.com/getopenscreen/openscreen) (community continuation) | 445 | MIT | ✅ | ✅ (inherits OpenScreen) | ✅ Active (pushed 2026-07-03) |
| [Cap](https://github.com/CapSoftware/Cap) | 19,945 | AGPL-3.0 + MIT sub-crates | ✅ | ⚠️ zooms in Studio Mode editor (manual-leaning) | ✅ Very active (pushed 2026-07-04) |
| [ScreenArc](https://github.com/tamnguyenvan/screenarc) | 513 | GPL-3.0 | ✅ (unsigned installer) | ✅ fully automatic pan-zoom on clicks | ✅ Active (pushed 2026-04-26) |
| [Screenity](https://github.com/alyssaxuu/screenity) | 18,373 | GPL-3.0 | Chrome extension only | ⚠️ zoom exists, not cursor-driven | ✅ Active |
| [screen-demo](https://github.com/njraladdin/screen-demo) | 49 | none declared | ✅ Windows-first (Tauri/Rust) | ⚠️ manual + early auto-zoom (v0.1.5) | ❌ Stale (last push 2025-03-16) |

**The OpenScreen → Recordly lineage is the story here.** OpenScreen was the breakout free Screen Studio alternative (Electron/TypeScript, MIT). Its verified feature list is essentially your requirements spec:

> "Auto or manual zooms with adjustable depth, duration, easing, and pixel-precise position; auto-zoom follows your cursor as you work. Custom cursor size, smoothing, and click effects, with cursor themes and post-recording path smoothing. Webcam overlay with picture-in-picture, drag-to-position, mirroring, and shape options. Export to MP4 or GIF in multiple aspect ratios." — OpenScreen README (verified)

The author archived it on 2026-06-17 ("started as a side project that blew up; not production grade"). Two continuations exist:
- **[getopenscreen/openscreen](https://github.com/getopenscreen/openscreen)** — the community spin-off the archived README officially points to, led by a core contributor. MIT, active, but small (445★).
- **[Recordly](https://github.com/webadderallorg/Recordly)** — "substantially modifies the OpenScreen foundation," relicensed AGPL-3.0, and has become the main successor (18.6k★, extension marketplace, active PR flow).

**Recordly verified feature set** (from README, 2026-07-04):
- Runs on macOS 14+, **Windows 10 Build 19041+** (native Windows Graphics Capture helper + WASAPI system/mic audio), Linux.
- Record full display or single window; jump straight into the editor.
- **Automatic zoom suggestions based on cursor activity** + manual drag-and-drop zoom regions on a timeline.
- Cursor polish: size, smoothing, motion blur, **click bounce**, sway, macOS-style cursor assets, show/hide rendered cursor.
- **Webcam bubble overlay**: preset/custom position, mirroring, size, roundness (→ your circle), shadow, and *zoom-reactive scaling* so the bubble stays balanced during zooms.
- Frame styling: wallpapers/gradients/blur/padding/shadows.
- Export: MP4/GIF with quality, **aspect ratio and output dimension controls**.
- Extension marketplace (click sounds, device frames, render hooks…).
- Projects saved as `.recordly` files; speed-up/slow-down regions; annotations.

Because it renders the cursor as an *overlay from recorded mouse data* (the Screen Studio technique), zooms and cursor effects are computed in post — you can re-style everything after recording, which is exactly the "record fast, decide zooms later" workflow you asked for.

**Cap** (Rust + Tauri) is the other heavyweight. It's excellent and very active, but it's positioned as an open-source **Loom** alternative (instant share links, cloud, teams). Its Studio Mode editor has zooms, backgrounds, captions, and it captures cursor data for post-render effects via a GPU (WGSL shader) pipeline — but the zoom UX is less automation-centric than Recordly's, and the codebase (Rust + a full web platform monorepo) is much heavier to modify. License is AGPLv3 with MIT capture crates.

**ScreenArc** is the "fully automatic, zero keyframing" option: it auto-generates cinematic pan-zoom from your clicks, with one-click aspect ratio presets — but only 16:9, 9:16, and 1:1 (no 4:5), export capped at 2K, small community (513★), unsigned Windows installer, GPL-3.0 (copyleft matters if you ever distribute a modified version).

### 1.2 OBS route (live zoom while recording)

If you ever want the zoom to happen **live during recording** instead of in post:
- [obs-zoom-to-mouse](https://github.com/BlankSourceCode/obs-zoom-to-mouse) (1.1k★, MIT, Lua script) — hotkey-triggered zoom toward the cursor with optional follow mode. Works on Windows. Dormant since mid-2024.
- [OBS-Smooth-Zoom](https://github.com/JustAdumbPrsn/OBS-Smooth-Zoom) (78★, active Feb 2026) — explicitly aims to replicate Screen Studio-style smooth zoom in real time.
- "Zoom to Mouse ULTIMATE" and "Zoom and Follow" scripts on the OBS forum offer multi-level zoom + auto-follow.

**Verdict:** workable and free, but zoom decisions are baked into the recording (no fixing in post), OBS setup is fiddly, and it doesn't give you click highlights or the webcam-bubble compositing. This is a fallback, not the recommendation.

### 1.3 Commercial reference points

- **Screen Studio** — still effectively macOS-only; its homepage currently shows a *"Windows version ready?"* waitlist prompt (verified 2026-07-04), i.e., announced but not shipped.
- **FocuSee (iMobie)** — the closest commercial Windows equivalent. AI detects click locations after recording and auto-generates zoom animations; auto-generated zooms are editable *(feature claims from vendor pages)*. Verified pricing on their site: **$49.99/yr Standard, $79.99/yr Advanced ($24.99/$29.99 monthly), $199.99 lifetime** (listed against a $719.99 "regular" price). Third-party reviews report the Windows build is less polished than the Mac one *(unverified)*.
- Cursorful (Chrome extension), Tella, Trupeer, Komodo — web/browser tools; none beat FocuSee as a native Windows reference and none were verified in depth.

The commercial UX pattern worth copying into your PRD: **record → AI proposes zoom segments at click points → user edits/deletes/retimes each zoom on a timeline → export**. Both FocuSee and Recordly converge on this.

---

## 2. Gap analysis vs. your requirements

| Your requirement | Recordly | ScreenArc | Cap | OBS scripts | CapCut (today) |
|---|---|---|---|---|---|
| Quick screen recording, Windows, lightweight | ✅ native WGC | ✅ (Electron) | ✅ | ✅ | n/a |
| Zoom follows mouse, controllable | ✅ auto suggestions + manual regions | ✅ fully auto (less control) | ⚠️ manual-leaning | ⚠️ live only, hotkey | ❌ manual keyframes |
| Add/adjust zooms **after** recording | ✅ timeline editor | ✅ | ✅ | ❌ | ✅ (painfully) |
| Click highlighted | ✅ click bounce + extension click sounds | ⚠️ implicit (zoom on click) | ✅ cursor effects | ⚠️ | manual |
| Circular talking-head overlay | ✅ webcam bubble w/ roundness + zoom-reactive | ✅ webcam overlay | ✅ | via OBS scene | manual |
| 4:5 vertical export | ⚠️ aspect controls exist; **4:5 preset unconfirmed — test, or add in a fork** | ❌ 16:9/9:16/1:1 only | ⚠️ unconfirmed | ❌ | ✅ |
| Free / open source | ✅ AGPL-3.0 | ✅ GPL-3.0 | ✅ AGPL | ✅ | freemium |
| Easy to extend with Claude Code | ✅ Electron + TypeScript + React, accepts PRs | ⚠️ smaller community | ⚠️ large Rust monorepo | ⚠️ Lua | ❌ |

The only requirement not positively confirmed anywhere is a **4:5 preset**. Recordly exposes "aspect ratio and output dimension controls," so it may already handle 4:5 via custom dimensions — verify in the app; if it's preset-only, adding a 4:5 preset to an Electron/React codebase is a trivial patch.

One workflow note: Recordly's webcam feature is footage-overlay based (upload/record webcam and composite as a bubble). If you record your face separately (e.g., phone), you can still drop it in; test whether simultaneous webcam recording on Windows meets your needs.

---

## 3. Build vs. adopt vs. extend

### Option A — Adopt Recordly (start here, ~1 hour)
Install from [recordly.dev](https://www.recordly.dev) / GitHub releases. Record one of your usual AI-tool demos, accept the auto-zoom suggestions, tweak two of them, set the webcam bubble, export at 4:5 (custom dimensions if needed), and compare against your CapCut time. If this beats CapCut — and on the verified feature list it should — you're done without writing code.

**Risks:** young project lineage (post-OpenScreen churn), Electron (moderate RAM, but recording uses a native WGC helper so capture overhead is low), 4:5 preset unconfirmed.

### Option B — Fork & extend Recordly (recommended if A leaves gaps)
This is the sweet spot for your "hand a PRD to Claude Code" plan. The PRD becomes a **delta spec**, e.g.:
1. Add 4:5 (and 9:16) one-click export presets sized for Reels/TikTok/LinkedIn.
2. A "my style" preset: default zoom depth/easing/duration, click-highlight ring color, bubble position/size — applied automatically to every new project.
3. Optional: hotkey during recording to *mark* a moment ("zoom here"), turned into a zoom region automatically in the editor (Recordly already stores cursor data; this is a marker stream + region generator).
4. Optional: smarter auto-zoom tuning (e.g., zoom only on clicks, not hover; minimum dwell time).

Electron + TypeScript + React is the friendliest possible stack for AI-assisted modification. AGPL-3.0 is a non-issue for personal use; it only obliges source disclosure if you distribute the modified app publicly. The project explicitly accepts PRs, so your improvements could even land upstream.

**Alternative fork bases:** getopenscreen/openscreen if you prefer MIT licensing and a smaller codebase (same DNA, less momentum); ScreenArc if you want the fully-automatic philosophy (GPL, smaller community); Cap if you later want cloud sharing (heavier Rust monorepo).

### Option C — Build from scratch (only if you want a *product*)
Feasible and well-supported by verified building blocks, but it's a multi-week project to reach Recordly's current quality. Architecture if you go this way:

- **Shell:** Tauri (Rust) — much lighter than Electron on RAM/disk; UI in React/TypeScript.
- **Capture:** [windows-capture](https://github.com/NiiightmareXD/windows-capture) (MIT, active, Rust) — wraps Windows.Graphics.Capture with DXGI Desktop Duplication support and a built-in hardware H.264 encoder; or [scap](https://github.com/CapSoftware/scap) (MIT, Cap's cross-platform capture crate).
- **Input telemetry:** [rdev](https://github.com/Narsil/rdev) (MIT, active) — global mouse position + click hooks; record `(t, x, y, event)` as a sidecar stream next to the raw video. Hide the real cursor in capture and render a synthetic cursor in post (the Screen Studio trick).
- **Effects & export:** record untouched full-res video; apply zoom/pan/cursor/click effects at export time via a GPU pass (wgpu/WGSL like Cap) or an FFmpeg filter graph (`zoompan`/`crop`+`scale` driven by generated keyframe expressions). Composite webcam bubble in the same pass. Auto-zoom = cluster click events in time → generate zoom regions with ease-in/out curves → user edits regions on a timeline before export.
- 4:5 output = crop/pad the composed frame; trivial once the render pipeline exists.

**Verdict: don't start here.** Every component exists, but Option B gets you 90% of this by writing 5% of the code.

---

## 4. Recommended next steps

1. **Today:** Install Recordly, record one real demo, test the 4:5 export question. (Also glance at ScreenArc for its zero-effort auto-zoom feel.)
2. **If gaps found:** Write the PRD as a *fork-delta spec* against Recordly (Section 3, Option B has the candidate feature list). Clone the repo, hand both to Claude Code.
3. **Keep as reference:** FocuSee's flow (auto-detect clicks → editable zoom segments) is the UX benchmark; Screen Studio's Windows waitlist means the commercial gap on Windows is still real.

---

## Appendix: verification log

- GitHub API metadata (name/license/stars/archived/pushed_at) pulled 2026-07-04 for: siddharthvaddem/openscreen, getopenscreen/openscreen, webadderallorg/Recordly (+2 forks), CapSoftware/Cap, CapSoftware/scap, alyssaxuu/screenity, njraladdin/screen-demo, tamnguyenvan/screenarc, BlankSourceCode/obs-zoom-to-mouse, JustAdumbPrsn/OBS-Smooth-Zoom, NiiightmareXD/windows-capture, Narsil/rdev.
- READMEs fetched raw and feature claims quoted verbatim for OpenScreen, Recordly, Cap, ScreenArc. Recordly LICENSE.md confirmed AGPL-3.0; Cap LICENSE confirmed AGPLv3 + MIT sub-crates.
- screen.studio homepage checked: shows "Windows version ready?" waitlist copy → no shipped Windows version.
- focusee.imobie.com/pricing.htm scraped: $49.99/$79.99 yearly, $24.99/$29.99 monthly, $199.99 lifetime (vs $719.99 list) present on page.
- *(Unverified, from search-phase snippets only):* FocuSee Windows-build quality complaints; screen-demo's v0.1.5 "Auto Zooms Update" details; Screenity's exact zoom behavior; OBS forum script details ("ULTIMATE", "Zoom and Follow" specifics).
