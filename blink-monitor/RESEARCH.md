# Blink Monitor — Research Report

**Date:** 2026-07-12
**Target machine:** Windows 11 laptop, Intel Core Ultra 7 (Meteor Lake, Series 1 — has Intel NPU), 36 GB RAM, SSD
**Product:** Always-on, privacy-first, fully-offline webcam blink-rate monitor with configurable reminders and a local dashboard. Will be released open-source; never sold.

---

## 1. Methodology

Four parallel research agents (running Claude Opus 4.8) each investigated one domain:

1. Existing open-source projects to fork or mine
2. Blink-detection model pipelines
3. Intel NPU runtimes on Windows
4. Lightweight always-on app shells

Their outputs were then **independently re-verified** (by Fable 5, the orchestrating model) for every load-bearing claim: licenses were confirmed from actual LICENSE files, model files were downloaded and inspected (input/output tensor shapes read from the ONNX graph itself), crate versions confirmed against crates.io API, and the two decision-critical technical claims (Tauri WebView2 teardown; Windows ML NPU hardware support) confirmed from primary sources. Section 6 is the full verification ledger.

---

## 2. Domain 1 — Existing open-source projects

**Conclusion: no existing project is simultaneously (a) a webcam blink-*rate* reminder, (b) lightweight enough for always-on use, and (c) cleanly licensed. Build from scratch; mine specific projects for reference.**

### Camera-based blink apps surveyed

| Project | License (verified) | Stack | Verdict |
|---|---|---|---|
| [ScreenBlink](https://github.com/katunli/ScreenBlink) | **No LICENSE file** → all-rights-reserved | Electron + Python (OpenCV, dlib) | Closest functional match, but heavy and **legally unforkable** (no license = no reuse rights). Mine the reminder-UX ideas only, not code. |
| [EyeCommander](https://github.com/AceCentre/EyeCommander) | MIT | Electron + Python + MediaPipe | Only mature, permissively-licensed, packaged webcam-blink desktop app — but it's a blink-as-switch accessibility tool, and Electron+Python is the opposite of lightweight. Reference for MediaPipe desktop packaging. |
| [BlinkWell](https://github.com/andregaeta/BlinkWell) | No LICENSE file | Python + PyQt | Best *architecture* reference (native tray app + target blink rate + on-screen stats), tiny/inactive (UFRJ thesis). Reference only. |
| [iBlink](https://github.com/zenithexpo/iblink) | Unspecified | Electron + Python (dlib) | Reference only. |
| [BlinkReminder](https://github.com/FrankWan27/BlinkReminder) | No LICENSE | Python | Haar cascades + eye classifier (2020). Dated; reference only. |
| [EyeGestures](https://github.com/NativeSensors/EyeGestures) | **GPL-3.0** | Python/Rust, MediaPipe | Active gaze-tracking project, not blink-focused. GPL — usable only if the app itself goes GPL; excluded to keep license freedom. |

### Detection engines worth mining

| Engine | License (Fable-verified) | Relevance |
|---|---|---|
| [OpenSeeFace](https://github.com/emilianavt/OpenSeeFace) | **BSD-2-Clause** ([LICENSE](https://github.com/emilianavt/OpenSeeFace/blob/master/LICENSE)) | Lightweight ONNX landmark tracker, documented <100% of one core at 30 fps; proven Windows face tracking. Good reference for tracking-loop design; its models are larger than our chosen pipeline needs. |
| [MediaPipe Face Landmarker v2](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker) | **Apache-2.0** ([LICENSE](https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE)) | 478 landmarks + 52 blendshapes incl. `eyeBlinkLeft`/`eyeBlinkRight`. The designated **v2 alternative backend** (see PRD §20); not primary because the MediaPipe graph can't target the Intel NPU and pulls in a large C dependency. |
| [CVZone](https://github.com/cvzone/cvzone) / [MediaPipe-EAR demo](https://github.com/Pushtogithub23/Eye-Blink-Detection-using-MediaPipe-and-OpenCV) | MIT / unverified | Canonical EAR blink-counting reference logic. |

### Shell/UX patterns (non-camera break reminders)

[Stretchly](https://github.com/hovancik/stretchly) (BSD-2, Electron) and [Pomatez](https://github.com/zidoro/pomatez) (Electron) are mature tray/break-UX references; both are Electron, so patterns only. Commercial validation: [BlinkEasy](https://blinkreminder.com/), [Blinkr](https://getblinkr.com/), and Mac-only [LookAway](https://lookaway.com/) all sell exactly this product with "on-device processing" as the pitch — the concept is validated and the open-source niche is empty.

---

## 3. Domain 2 — Model pipeline

### Approaches compared

| Approach | Robustness | Cost | Problem |
|---|---|---|---|
| Landmarks + Eye-Aspect-Ratio (EAR) threshold | Fragile in the field: needs **per-person calibration**, degrades with head yaw and glasses ([EAR overview](https://www.emergentmind.com/topics/eye-aspect-ratio-ear); [PeerJ adaptive-EAR](https://peerj.com/articles/cs-943/)) | Cheap | Single global threshold doesn't generalize |
| **Open/closed-eye CNN on eye crops** ✅ | Learns appearance, not geometry; MRL training data includes glasses and IR/low-light | ~0.0014 GFLOPs per eye — near-free | Needs a reliable eye locator (solved by YuNet's built-in eye landmarks) |
| MediaPipe blendshapes | Most robust turnkey signal | Heaviest (full 478-pt mesh + blendshape graph, ~5–15 ms CPU) | No Intel-NPU path; big dependency |

### Chosen pipeline (verified facts)

**Stage 1 — [YuNet face detector](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)** (`face_detection_yunet_2023mar.onnx`)
- License **MIT** (opencv_zoo [README](https://github.com/opencv/opencv_zoo/blob/main/models/face_detection_yunet/README.md))
- File downloaded & inspected: **232,589 bytes**, SHA-256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`
- Input tensor (read from the ONNX graph): **`[1, 3, 640, 640]` NCHW, static** — fully convolutional, so it is reshaped at conversion time to a smaller static input (PRD uses 320×192)
- Outputs (read from graph): raw multi-scale heads `cls/obj/bbox/kps` at strides 8/16/32 → **decode + NMS must be implemented** (normative reference: OpenCV `FaceDetectorYN`, [face_detect.cpp](https://github.com/opencv/opencv/blob/4.x/modules/objdetect/src/face_detect.cpp))
- Returns per face: bbox + **5 landmarks: right-eye center, left-eye center, nose tip, mouth corners** (verified in [demo.py](https://github.com/opencv/opencv_zoo/blob/main/models/face_detection_yunet/demo.py))
- WIDER Face AP 0.8844 / 0.8656 / 0.7503 (easy/medium/hard)
- Note: the newer `2026may` re-export has **dynamic** dims — unusable on NPU; pin `2023mar`.

**Stage 2 — eye crops** from the two YuNet eye-center landmarks (square crop ∝ inter-ocular distance, resized to 32×32).

**Stage 3 — [open-closed-eye-0001](https://github.com/openvinotoolkit/open_model_zoo/blob/master/models/public/open-closed-eye-0001/README.md)** classifier
- License **Apache-2.0** (model.yml → [openvino_training_extensions LICENSE](https://raw.githubusercontent.com/opencv/openvino_training_extensions/develop/LICENSE), verified Apache-2.0)
- Input `input.1`: `[1, 3, 32, 32]` BGR; preprocessing per [model.yml](https://raw.githubusercontent.com/openvinotoolkit/open_model_zoo/master/models/public/open-closed-eye-0001/model.yml): mean 127, scale 255; output node `19`: `[1, 2, 1, 1]` softmax **[open, closed]**
- 0.0014 GFLOPs, 0.0113 MParams, **95.84%** accuracy on MRL Eye Dataset test split; ONNX file 46,164 bytes, checksum pinned in model.yml
- Download: `https://storage.openvinotoolkit.org/repositories/open_model_zoo/public/2022.1/open-closed-eye-0001/open_closed_eye.onnx` (canonical URL from the official model.yml manifest; **unreachable from this research sandbox** — its egress proxy denies that host — so re-verify at first build; fallback: `omz_downloader --name open-closed-eye-0001` from `openvino-dev==2024.6.0`)

**Total model payload: ~280 KB.** Steady-state inference ≈ 1–2 ms/frame on one CPU core at 10–15 FPS (estimate from GFLOPs; measure with `benchmark_app` on the target machine — no first-party per-model benchmark exists for Core Ultra 7).

**License flag:** InsightFace detector/landmark packs are non-commercial-research-only — excluded; nothing in the chosen pipeline touches them. Open Model Zoo itself is deprecated (frozen at OpenVINO 2025.0, [notice](https://docs.openvino.ai/2024/documentation/legacy-features/model-zoo.html)) but the model files remain published and Apache-licensed; the PRD vendors them into the repo so the app never depends on Intel's storage staying up.

### Blink-rate science (product thresholds)

Relaxed adult blink rate ≈ **15–20/min**; during screen use it commonly drops to **~4.5–7/min** ([PubMed in-situ study](https://pubmed.ncbi.nlm.nih.gov/36763349/); [Review of Ophthalmology](https://www.reviewofophthalmology.com/article/its-time-to-think-about-the-blink)). A single blink lasts ~100–400 ms. → Default reminder threshold 8/min over a 60 s window; blink event = eye-closed interval of 66–500 ms (see PRD §9).

---

## 4. Domain 3 — Intel NPU runtime

**Conclusion: use OpenVINO directly (2026.2.x), device string `AUTO:NPU,CPU`. Do not use Windows ML or DirectML.**

| Option | Verdict | Decisive facts |
|---|---|---|
| **OpenVINO native** ✅ | Primary | `intel_npu` plugin targets Meteor Lake directly ([NPU device docs](https://docs.openvino.ai/2025/openvino-workflow/running-inference/inference-devices-and-modes/npu-device.html)). NPU requires **static input shapes** ([intel_npu README](https://github.com/openvinotoolkit/openvino/blob/master/src/plugins/intel_npu/README.md)) — both chosen models are static. `AUTO:NPU,CPU` runs on CPU while the NPU compiles, then switches, and silently falls back if NPU/driver is absent. First NPU compile is slow (AOT) → mitigate with `ov::cache_dir` ([model caching](https://docs.openvino.ai/2024/openvino-workflow/running-inference/optimize-inference/optimizing-latency/model-caching-overview.html)). Latest release **2026.2.1 (2026-06-17)** (verified, [releases](https://github.com/openvinotoolkit/openvino/releases)). |
| Windows ML (Windows App SDK) | **Rejected** | Its Intel OpenVINO EP documents NPU support as "**Intel ArrowLake (15th Gen) and above**, min driver 32.0.100.4239" — i.e. Core Ultra **Series 2+, excluding this laptop's Meteor Lake NPU** (verified: [supported EPs](https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/supported-execution-providers)). Also downloads EPs at runtime and needs Win11 24H2 — both incompatible with a never-touches-the-internet app. |
| DirectML EP | **Rejected** | In maintenance mode ("sustained engineering", [repo banner](https://github.com/microsoft/DirectML)); DX12 GPUs only, no Intel NPU. |
| ONNX Runtime + OpenVINO EP | Rejected | Strictly larger than native OpenVINO (ORT ~12 MB DLL *plus* all OpenVINO DLLs), and native C++/C# NPU builds require compiling ORT from source ([OV EP docs](https://onnxruntime.ai/docs/execution-providers/OpenVINO-ExecutionProvider.html)). |

**Rust binding:** [`openvino` crate](https://crates.io/crates/openvino) (intel/openvino-rs) — **v0.11.0, published 2026-05-06, Apache-2.0** (verified via crates.io API). Wraps the OpenVINO C API; ships no runtime — the app bundles the OpenVINO DLLs (core + CPU plugin + NPU plugin + IR frontend + TBB, ~60–150 MB on disk, dominated by `openvino_intel_cpu_plugin.dll`; [local distribution guide](https://docs.openvino.ai/2025/openvino-workflow/deployment-locally/local-distribution-libraries.html)).

**Honest NPU assessment** (kept in the PRD as a design principle): for ~0.3 MB of models at 10–15 FPS, CPU inference already costs ~1–2 ms/frame — the NPU's win is *power/thermals* (P-cores stay parked), not speed, and third-party wattage claims are blog-grade only. **Duty-cycling (frame pacing, pause on lock/idle, detector cadence) saves far more power than NPU offload.** So: CPU path is the guaranteed baseline, NPU is wired in via `AUTO:NPU,CPU` because it's nearly free to add with OpenVINO, and both are user-visible in Settings (Auto / CPU-only / NPU-only).

### Camera & OS integration facts (from Microsoft primary sources)

- Capture API: **Media Foundation** (`IMFSourceReader`); request 640×360 @ 15 fps, NV12/YUY2 preferred. In Rust, [`nokhwa`](https://crates.io/crates/nokhwa) v0.10.11 (2026-05-15, Apache-2.0, verified) provides the MSMF backend; direct `windows`-crate Media Foundation is the fallback.
- **Multi-app camera sharing** exists only on Win11 24H2+ (opt-in, KB5052093); default is exclusive access — "camera busy" must be handled gracefully.
- **Camera-in-use detection:** `HKCU\...\CapabilityAccessManager\ConsentStore\webcam[\NonPackaged]\*` — an app whose `LastUsedTimeStart` is set with `LastUsedTimeStop == 0` currently holds the camera.
- The Windows **privacy indicator** will show whenever the app holds the camera — surfaced honestly in the product UX.
- Power hygiene APIs: session lock `WTSRegisterSessionNotification`/`WM_WTSSESSION_CHANGE`; user idle `GetLastInputInfo`; **EcoQoS** via `SetProcessInformation(ProcessPowerThrottling)` ([Introducing EcoQoS](https://devblogs.microsoft.com/performance-diagnostics/introducing-ecoqos/)), exposed in the `windows` crate.

---

## 5. Domain 4 — App shell

**Conclusion: Tauri v2, single Rust process, dashboard window destroyed (not hidden) on close.**

| Stack | Idle RAM (window closed) | Fit |
|---|---|---|
| **Tauri v2** ✅ | Rust process ~5–15 MB; WebView2 processes **exit when the window is destroyed** | MIT/Apache; tray, real toasts, autostart, single-instance all first-party plugins |
| Avalonia (C#) | ~20–40 MB minimal + .NET runtime | Runner-up: MIT, native rendering, but can't drop to a ~5 MB idle core and native charting is heavier than uPlot |
| WinUI 3 | Documented failure to release memory on window close ([#4606](https://github.com/microsoft/microsoft-ui-xaml/issues/4606), [#9063](https://github.com/microsoft/microsoft-ui-xaml/issues/9063)) | Disqualified for always-on |
| Electron | 150–300 MB idle | Baseline to reject |
| egui / Slint | Lowest window-open RAM | Viable no-WebView2 alternatives, but far weaker dashboard/charting ergonomics; Slint is GPL-or-attribution for free tiers |

Decisive verified facts for Tauri:
- Closing a Tauri window **kills only the WebView2 processes; the Rust app keeps running** (verified: [tauri#5611](https://github.com/tauri-apps/tauri/issues/5611); tray-only pattern: [discussion #11489](https://github.com/orgs/tauri-apps/discussions/11489), hide-vs-destroy: [#6308](https://github.com/orgs/tauri-apps/discussions/6308)). Idle footprint = the Rust worker alone.
- WebView2 Evergreen runtime is **pre-installed on all Windows 11 devices** ([Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/evergreen-vs-fixed-version)) — nothing to download, consistent with offline-only.
- [`tauri-plugin-notification`](https://v2.tauri.app/plugin/notification/) produces **genuine WinRT Action Center toasts** (via `tauri-winrt-notification`); proper branding for an unpackaged app needs the Start-Menu shortcut + AUMID that the Tauri NSIS installer already creates ([MS Learn: toasts from unpackaged apps](https://learn.microsoft.com/en-us/windows/apps/develop/notifications/app-notifications/send-local-toast-other-apps)).
- Overlay: a Tauri transparent window would spin up a second WebView2 (100+ MB) — instead the reminder overlay is a **tiny native layered window** (`WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE`, `UpdateLayeredWindow`), a few MB, click-through.
- Charts: **uPlot** (~48 KB min; in its maintainer's benchmark ~10% CPU / 12 MB vs Chart.js 40% / 77 MB; [comparison](https://www.metabase.com/blog/best-open-source-chart-library)). Data lives in SQLite owned by the Rust worker; the JS/DOM exists only while the dashboard is open.
- Autostart: `tauri-plugin-autostart` (HKCU Run key) with a known removal flake ([#771](https://github.com/tauri-apps/plugins-workspace/issues/771)) → PRD mandates re-asserting the key at every launch.

---

## 6. Verification ledger

### Independently verified by the orchestrator (primary source fetched / file inspected)

| Claim | Evidence |
|---|---|
| YuNet MIT license; `2023mar` = fixed shape, `2026may` = dynamic | opencv_zoo README |
| YuNet input `[1,3,640,640]`; outputs cls/obj/bbox/kps @ 8/16/32; 5 landmarks incl. both eye centers | **ONNX graph inspected after download**; demo.py |
| YuNet file: 232,589 bytes, SHA-256 `8f2383…52fa4` | Downloaded via GitHub LFS media endpoint |
| open-closed-eye-0001: Apache-2.0; `input.1` [1,3,32,32] BGR; output `19` [1,2,1,1] softmax [open, closed]; mean 127 / scale 255; 0.0014 GFLOPs; 95.84% | OMZ README + model.yml + training-extensions LICENSE |
| MediaPipe `face_landmarker.task` URL live, **3,758,596 bytes**; MediaPipe Apache-2.0 | HTTP 200 + Content-Length; LICENSE file |
| OpenSeeFace BSD-2-Clause | LICENSE file |
| `openvino` crate 0.11.0 (2026-05-06, Apache-2.0); `nokhwa` 0.10.11 (2026-05-15, Apache-2.0) | crates.io API |
| OpenVINO latest = 2026.2.1 (2026-06-17) | GitHub releases |
| Windows ML OpenVINO EP: NPU = "ArrowLake (15th Gen) and above" → Meteor Lake excluded | Microsoft windows-ai-docs |
| Tauri: window close kills WebView2 processes only | tauri#5611 |

### Accepted from agent research with citation (primary-source-cited, not re-fetched)

Tauri plugin behaviors (notification/autostart/single-instance/tray), EcoQoS API surface, camera ConsentStore registry semantics, 24H2 multi-app camera, WTS/GetLastInputInfo, NPU static-shape + driver + AUTO-fallback + cache_dir details, DirectML maintenance mode, OMZ deprecation, blink-rate literature, stack RAM comparisons.

### Known-unverified (must be measured/checked during build — carried into PRD §22 risks)

1. `storage.openvinotoolkit.org` file URL reachability (sandbox egress blocked it; URL comes from the official manifest). Mitigation: vendor the 46 KB ONNX into the repo at project start.
2. Per-model latency/wattage on the actual Core Ultra 7 (only GFLOPs-derived estimates exist) → measure with `benchmark_app` in M3.
3. Exact idle-RSS numbers for the final app (stack numbers are reported anecdotes, not lab measurements) → acceptance test in M6.
4. YuNet decode formula details (sqrt score combination, exp box decode) → port from OpenCV `face_detect.cpp` and golden-test against OpenCV output (PRD §21).
5. `openvino` crate 0.11 property-API coverage for `ov::cache_dir` → if absent, skip caching (models compile in seconds) or set via C API.

---

## 7. Final decision summary

| Decision | Choice | Runner-up |
|---|---|---|
| Fork vs build | **Build from scratch** (nothing forkable is light + licensed) | Fork EyeCommander (MIT) — only if footprint didn't matter |
| Shell | **Tauri v2**, single process, destroy-on-close dashboard | Avalonia (C#) |
| Detection | **YuNet (MIT) → 32×32 eye crops → open-closed-eye-0001 (Apache-2.0)**, ~280 KB total | MediaPipe Face Landmarker blendshapes (Apache-2.0, CPU-only, 3.6 MB) as v2 alternative backend |
| Runtime | **OpenVINO 2026.2.x native**, `openvino` Rust crate 0.11, device `AUTO:NPU,CPU`, IR + static shapes | tract (pure-Rust, CPU-only) if OpenVINO disk weight ever becomes unacceptable |
| Microsoft AI stack | **Not used** — Windows ML excludes Meteor Lake NPUs and requires online EP download; DirectML is frozen | — |
| Charts | uPlot (48 KB) | Chart.js |
| Storage | SQLite via rusqlite (bundled) | — |

The complete build specification is in [`PRD.md`](./PRD.md).
