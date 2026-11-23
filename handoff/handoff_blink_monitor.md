# Session Handoff — Blink Monitor ("Nictate", working name)

> Generated: 2026-11-23 | Branch: `claude/blink-monitor-research-aclz0i` | Agent: claude-code
> Task slug: `blink_monitor`

**Read this first.** This task is at the end of its research-and-specification stage. No application code exists yet. Three documents hold the full result, and this handoff tells you how to use them, what was decided and why, what is still open, and what to do next.

**Staleness warning.** All research, verification and the three documents date from 2026-07-12. This handoff was written on 2026-11-23, about four months later, without re-checking anything. Every version number, download URL and "latest release" claim below was true on 2026-07-12 and must be re-verified before Phase 0 (see Next Actions, step 2).

---

## Goal / Objective

Build a small, always-on Windows 11 tray app that watches the user through the laptop camera or an external webcam, counts blinks, computes blinks per minute, and reminds the user to blink when the rate stays below a configurable threshold. The user gets dry eyes from long screen sessions and wants a tool that runs all day without being noticed in Task Manager.

The stage this session covered: targeted research to choose what to build on and which models and runtime to use, then a PRD and implementation plan specific enough that an implementing agent makes no decisions of its own.

Definition of done for the whole task: the app passes all ten acceptance criteria in `blink-monitor/PRD.md` §23 on the user's own laptop.

### The user's hardware

Windows 11 laptop, Intel Core Ultra 7 (Meteor Lake, "Series 1", has an Intel NPU), 36 GB RAM, SSD. Built-in camera plus an external webcam. The camera has a physical shutter that the user will leave open while this app runs.

### Requirements the user stated (all are binding)

| # | Requirement | Where it is specified |
|---|---|---|
| 1 | Works with the built-in camera and an external webcam | PRD §7 |
| 2 | Blink threshold configurable in a settings panel; reminder when below it | PRD §11, §16 |
| 3 | As light as possible on RAM and CPU, because it runs all the time | PRD §1 G2, §4 |
| 4 | Uses the Intel NPU when present, falls back to CPU, and stays light in both cases | PRD §8.1 |
| 5 | Can be turned on and off at any time | PRD §14 (tray toggle) |
| 6 | A good-looking dashboard showing blink status and performance | PRD §17 |
| 7 | Fully offline. The app must never connect to the internet. Everything stays on the computer | PRD §2 C1, C2 |
| 8 | Privacy-first. Will be released open-source. Will never be sold | PRD §2 C3 |
| 9 | While the app holds the camera, no other app may use it until the user approves in the app | PRD §7.1 (Camera Guard) |

### Answers the user gave to clarifying questions

| Question | Answer |
|---|---|
| Tech stack | "Whatever is lightest" (the session's choice) |
| History | Persistent history with trends |
| Reminder styles | Toast, on-screen overlay and sound, each switchable by the user |
| Licensing | Asked for permissive-only at first, then clarified: open-source, never sold |
| When another app uses the camera | Configurable. Later superseded by requirement 9: `guard` is now the default policy, `pause` and `share` remain as options |
| On battery | Always full monitoring. No change of behavior on battery |
| Live camera preview | Only on the settings/calibration screen, never on the dashboard |
| Reminder repetition | Repeat with a cooldown, same intensity each time, no escalation |

### How the user wants the work run

- Sub-agents must use Opus 4.8. Do not spawn several copies of the orchestrating model.
- The orchestrating model reviews every agent's output against the PRD and general coding practice.
- Ask clarifying questions before starting research.
- Spend tokens only where needed, but precision, specificity and accuracy outrank token cost.
- The PRD must leave the implementer (Opus 4.8) nothing to decide.

---

## Progress Made

### Completed

- [x] Research report — `blink-monitor/RESEARCH.md` (209 lines)
  - §2 (line 22) existing open-source projects, §3 (line 51) model pipeline and how well each model is validated, §4 (line 98) Intel NPU runtime and camera/OS facts including Camera Guard feasibility, §5 (line 132) app shell, §6 (line 154) verification ledger, §6a (line 185) pressure-test round, §7 (line 197) decision summary.
- [x] PRD v1.1 — `blink-monitor/PRD.md` (425 lines, 25 sections)
  - Complete product and technical specification. v1.0 was pressure-tested and rewritten; the changelog is at the bottom of the file.
- [x] Implementation plan — `blink-monitor/IMPLEMENTATION_PLAN.md` (198 lines)
  - Phases 0 to 7 with deliverables, exact file contents for the load-bearing configs (`tauri.conf.json`, `windows-manifest.xml`, `build.rs`, `deny.toml`), a gate per phase, and a reviewer checklist (line 189).
- [x] All three documents are on `main` (fast-forwarded on 2026-07-12 at the user's request).
- [x] Name brainstorm with collision checks (not yet decided; see Pending decisions).

Nothing has been built, compiled or run. No model has been executed. Neither the camera nor the NPU has been touched.

### What the research concluded (short form)

1. **Build from scratch.** No existing project is a blink-rate reminder, lightweight, and properly licensed all at once. ScreenBlink is the closest functional match but has no LICENSE file (so no reuse rights) and is Electron plus Python. EyeCommander (MIT) is the only mature permissive codebase, but it is an Electron accessibility tool.
2. **Detection pipeline, about 280 KB of models.** YuNet face detector (MIT) returns the face box and both eye centers. Two 32×32 eye crops go into Intel's `open-closed-eye-0001` classifier (Apache-2.0). A hysteresis state machine turns per-frame "probability closed" into blink events.
3. **Runtime.** OpenVINO 2026.2.x used directly through the `openvino` Rust crate. Not Windows ML, not DirectML, not ONNX Runtime.
4. **Shell.** Tauri v2, one Rust process, dashboard window destroyed on close so the WebView2 processes exit.

### Decisions & Logic

- **Decision:** Build from scratch, borrowing ideas only.
  - **Alternatives considered:** Fork ScreenBlink, EyeCommander, BlinkWell.
  - **Rationale:** Unlicensed code cannot be reused; Electron and bundled Python idle at hundreds of MB.
  - **Reversibility:** Easy. Nothing is built yet.

- **Decision:** YuNet → eye crops → `open-closed-eye-0001`.
  - **Alternatives considered:** Landmarks plus eye-aspect-ratio threshold (needs per-person calibration, fragile with glasses and head turn). MediaPipe Face Landmarker blendshapes (most robust, but CPU-only with no Intel NPU path and a large dependency).
  - **Rationale:** Tiny, static-shaped (NPU needs static shapes), permissive licenses, and YuNet gives eye locations for free.
  - **Reversibility:** Designed in. `detector.rs` sits behind a `BlinkSignalSource` trait; MediaPipe blendshapes are the named fallback (PRD §20).

- **Decision:** OpenVINO directly, not Microsoft's AI stack.
  - **Alternatives considered:** Windows ML, DirectML, ONNX Runtime with the OpenVINO execution provider.
  - **Rationale:** Microsoft's own table lists the Windows ML Intel provider's NPU support as "Intel ArrowLake (15th Gen) and above", which excludes this laptop's Meteor Lake NPU. Windows ML also downloads providers at run time, which breaks the offline rule. DirectML is in maintenance mode and has no Intel NPU support. ONNX Runtime plus OpenVINO is strictly larger than OpenVINO alone.
  - **Reversibility:** Moderate. Re-check the Windows ML table; it changes with servicing.

- **Decision:** Explicit two-step device selection (compile for NPU; on failure compile for CPU). The `AUTO:NPU,CPU` device string from PRD v1.0 was removed.
  - **Alternatives considered:** OpenVINO's `AUTO` virtual device.
  - **Rationale:** `AUTO` keeps the CPU plugin (about 40 MB, the largest DLL) loaded next to the NPU plugin, which threatens the 80 MB memory ceiling. The Rust crate sets properties per device on `Core`, and how they route through `AUTO` could not be verified. The explicit path also makes the "active device" display truthful.
  - **Cost:** On the very first launch the app waits a few seconds for the NPU compile instead of running on CPU meanwhile. Later starts use the compile cache.
  - **Reversibility:** Easy. One function in `detector.rs`.

- **Decision:** `openvino` crate with the `runtime-linking` feature; DLLs shipped under `resources/openvino/` and found with `SetDllDirectoryW`.
  - **Rationale:** The app builds without the OpenVINO SDK installed, and CI needs no OpenVINO at all.

- **Decision:** Tauri v2, single process, no sidecar.
  - **Alternatives considered:** Avalonia (runner-up), WinUI 3 (documented failure to release memory on window close), Electron, egui, Slint.
  - **Rationale:** Closing a Tauri window kills only the WebView2 processes and the Rust process keeps running, so idle cost is the worker alone.
  - **Reversibility:** Hard once Phase 1 is done.

- **Decision:** The reminder overlay and the guard alert are native Win32 (layered window; `TaskDialogIndirect`), never a second WebView.
  - **Rationale:** A transparent Tauri window would start another WebView2 (100 MB or more).

- **Decision:** Camera Guard is release-based, not intercept-based.
  - **Rationale:** Windows has no user-mode API to see or veto another app's attempt to open the camera; that needs a kernel filter driver, which is out of scope. But while this app holds the camera, Windows itself refuses every other app (unless the user turned on Windows 11 24H2 "multi-app camera"). So: holding is the block, the user approves a timed release in the app, and a registry watcher raises an alert when any other app gets a camera session.
  - **Reversibility:** Not a choice. This is the limit of what Windows allows.

- **Decision:** Camera hold matrix (PRD §7.1). When the user is idle the camera stays held and inference stops. When the screen locks the camera is released.
  - **Rationale:** v1.0 said "hold continuously" and also "pause on lock and idle", which contradicted each other. Holding through idle keeps the guard intact at almost no cost. Releasing on lock is deliberate: holding the RGB camera through the lock screen could block Windows Hello face sign-in. Guard events during lock are logged and alerted on unlock.
  - **Reversibility:** Easy, but the Windows Hello risk should be tested before changing it.

- **Decision:** Idle-pause defaults to 5 minutes even though the user said "always full monitoring" on battery.
  - **Rationale:** These are different things. Battery state changes nothing. Idle-pause only stops inference when nobody is at the keyboard. It is a setting (`pause_on_idle_min`, 0 turns it off).

- **Decision:** Default reminder threshold 8 blinks/min over a 60-second window, cooldown 180 s, 90 s grace after resume.
  - **Rationale:** Relaxed blink rate is about 15 to 20 per minute; screen use commonly drops it to about 4.5 to 7. These are product-tuning values, marked `TUNABLE`, not verified facts.

- **Decision:** Ship unsigned; no auto-update; English only; NSIS per-user installer.
  - **Rationale:** No certificate for an open-source personal project; auto-update would need network access.

### Pressure test of the PRD (v1.0 → v1.1)

Two Opus 4.8 agents attacked v1.0. One played an implementer with no freedom to decide and returned 38 findings (9 blockers). The other checked the exact API surfaces against crates.io, docs.rs and library source. The orchestrator accepted 36 findings and corrected 2 (the agent proposed always applying softmax to the eye classifier output, which would distort values that are already probabilities; v1.1 applies softmax only when the two outputs do not sum to 1). The YuNet decode maths was checked line by line against OpenCV's `face_detect.cpp`. Full record: `blink-monitor/RESEARCH.md` §6a and the changelog at the end of `blink-monitor/PRD.md`.

---

## Files & Resources Used

### Files in this repository

- `blink-monitor/PRD.md` — the specification. Authoritative. If the plan and the PRD disagree, the PRD wins.
- `blink-monitor/IMPLEMENTATION_PLAN.md` — build order, exact config contents, phase gates, reviewer checklist.
- `blink-monitor/RESEARCH.md` — evidence and sources for every decision; §6 lists what was verified, what was accepted on citation, and what is still unverified.
- `handoff/handoff_blink_monitor.md` — this file.
- `business names/` — a separate project (naming a B2B parent company) added to `main` by another session. Not part of this task. `business names/02-sanskrit-roots.md` and `04-linguistic-pitfalls.md` may be useful when choosing this app's name.

### Files that do not exist yet

No `src-tauri/`, `ui/`, `models/`, `tools/` or `assets/`. The two model files are not vendored. The copy of YuNet that was downloaded for inspection lived in a temporary directory and is gone.

### Pinned facts the next session will need (verified 2026-07-12)

| Item | Value |
|---|---|
| YuNet file | `face_detection_yunet_2023mar.onnx`, MIT, 232,589 bytes, SHA-256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| YuNet download (worked) | `https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx` |
| YuNet tensors (read from the file) | input `input` `[1,3,640,640]` static; outputs `cls_/obj_/bbox_/kps_` at strides 8, 16, 32 |
| YuNet landmarks | right eye, left eye, nose tip, right mouth corner, left mouth corner |
| YuNet preprocessing (OpenCV source) | BGR, float, 0 to 255, no mean, no scaling |
| YuNet decode (OpenCV source) | `score = sqrt(min(cls,1) * min(obj,1))`; `cx = (col + dx) * stride`; `w = exp(dw) * stride`; NMS eta 1.0 |
| Do not use | `face_detection_yunet_2026may.onnx` (dynamic shapes; the NPU needs static shapes) |
| Eye model | `open-closed-eye-0001`, Apache-2.0, ONNX 46,164 bytes, checksum (96 hex digits) `2615bce53b55620c629db21b043057600ccc53466f053c0a8277c43577c2db21e48f330cf9b15213016d17cddb8cba27` |
| Eye model tensors | input `input.1` `[1,3,32,32]` BGR, normalise `(px - 127) / 255`; output `19` `[1,2,1,1]` = `[open, closed]` |
| Eye model download (from the official `model.yml`, not fetched) | `https://storage.openvinotoolkit.org/repositories/open_model_zoo/public/2022.1/open-closed-eye-0001/open_closed_eye.onnx` |
| OpenVINO | 2026.2.1, released 2026-06-17 |
| Rust crates | `openvino` 0.11.0, `nokhwa` 0.10.11, `tauri` 2.11.5, `tauri-plugin-notification` 2.3.3, `tauri-plugin-autostart` 2.5.1, `tauri-plugin-single-instance` 2.4.2, `rusqlite` 0.40.1, `tracing-appender` 0.2.5 |
| npm | `uplot` 1.6.32 |
| MediaPipe fallback model | `face_landmarker.task`, Apache-2.0, 3,758,596 bytes |

### Documentation consulted (primary sources)

- OpenCV `face_detect.cpp` — `https://raw.githubusercontent.com/opencv/opencv/4.x/modules/objdetect/src/face_detect.cpp`
- opencv_zoo YuNet README and `demo.py` — `https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet`
- Open Model Zoo `open-closed-eye-0001` README and `model.yml` — `https://github.com/openvinotoolkit/open_model_zoo/tree/master/models/public/open-closed-eye-0001`
- OpenVINO NPU plugin README — `https://github.com/openvinotoolkit/openvino/blob/master/src/plugins/intel_npu/README.md`
- Windows ML supported execution providers — `https://learn.microsoft.com/en-us/windows/ai/new-windows-ml/supported-execution-providers`
- openvino-rs — `https://github.com/intel/openvino-rs`
- Tauri issue showing window close kills only WebView2 — `https://github.com/tauri-apps/tauri/issues/5611`
- YuNet paper — `https://link.springer.com/article/10.1007/s11633-023-1423-y`
- All other sources are linked inline in `blink-monitor/RESEARCH.md`.

---

## Failed Approaches

- **Tried:** Find an existing blink-reminder app to fork.
  - **Failed because:** Every candidate is unlicensed, Electron/Python-heavy, or both.
  - **Do not retry** unless a new permissively licensed native project has appeared since July 2026.

- **Tried:** Windows ML and DirectML as the route to the NPU (the user had asked about using Microsoft's stack).
  - **Failed because:** Windows ML's Intel provider documents NPU support for Arrow Lake and newer only, and downloads providers at run time. DirectML is frozen and GPU-only.
  - **Retry if:** Microsoft's table adds Meteor Lake and offers an offline provider install.

- **Tried:** `AUTO:NPU,CPU` as the device string (PRD v1.0).
  - **Failed because:** Loads both plugins (memory budget) and property routing through `AUTO` could not be verified in openvino-rs 0.11.
  - **Retry if:** Measured memory with `AUTO` stays under 80 MB and the property behavior is confirmed.

- **Tried:** Intercept-and-approve camera access by other apps (the user's first wording of requirement 9).
  - **Failed because:** No user-mode Windows API exists for it.
  - **Do not retry** without a kernel driver, which is out of scope.

- **Tried:** Applying softmax to the classifier output unconditionally (a red-team proposal).
  - **Failed because:** If the output is already a probability pair, a second softmax compresses it and shifts the thresholds.
  - **Do not retry.** PRD §8.4 uses a sum check.

- **Tried:** Downloading `open_closed_eye.onnx` from `storage.openvinotoolkit.org` inside the cloud session.
  - **Failed because:** The session's network policy denied that host (HTTP 403 at the proxy). Hugging Face and `docs.opencv.org` were blocked the same way. This says nothing about whether the URL works elsewhere.
  - **Retry** from the user's own machine. Fallback: `pip install openvino-dev==2024.6.0` then `omz_downloader --name open-closed-eye-0001`.

- **Tried:** Reading YuNet's input size from documentation.
  - **Failed because:** No page states it; the README only says "fixed input shape".
  - **Resolved by** downloading the file and reading the ONNX graph: 640×640.

- **Tried:** Checking domain availability for the name candidates with the GoDaddy tool.
  - **Failed because:** Daily quota exceeded.
  - **Retry** any time; no domains have been checked.

- **Names ruled out by collision checks:** BlinkGuard (Ergopax sells a webcam blink-rate reminder under that name, a direct competitor), Nimi (active Windows software brand at mynimi.net), Netra (Netra AI, TATA AIG Netra, Sun Netra servers). Blinkr, BlinkEasy, BlinkWell, ScreenBlink, iBlink, Blink Eye and eyeblink are also existing products.

- **Process note:** Background sub-agents lost their task handles when the session's connection layer reconnected. Their final reports were recovered from the transcript files on disk. If this happens again, look under `~/.claude/projects/<project>/<session>/subagents/` and extract only the last assistant message.

---

## Pending decisions (the user must make these)

1. **App name.** "Nictate" is a placeholder used throughout the PRD and plan. The user asked for a name with an Indian-language root (Sanskrit, Marathi or Hindi) that Europeans can pronounce easily and that sounds cool. Shortlist offered, none chosen:
   - **Lochan** (Sanskrit, "eye"; also a Scottish word for a small lake). Recommended for brand feel. No software collision found.
   - **Nimesha / Nimesh** (Sanskrit, "blink of an eye"; also an old unit of time equal to one blink). Best meaning. No software collision found.
   - **Aksha** (Sanskrit, "eye"). Near-clean.
   - Also mentioned: Nayan, Kiran, Nazar, Palak, Unmesh, Papni.
   - Collision checks were single web searches, not trademark searches. Domains were not checked.
2. **Where the code lives.** The PRD's layout assumes its own repository root (`nictate/`). Whether to create a new repository or build inside this one has not been discussed.
3. **The app's own license.** `LICENSE` is a placeholder. All dependencies are MIT, Apache-2.0 or BSD, so any open-source license is possible.

---

## Next Actions

1. **Get the name decided, then rename.** Replace "Nictate" across `blink-monitor/PRD.md`, `blink-monitor/IMPLEMENTATION_PLAN.md` and `blink-monitor/RESEARCH.md`. The strings that matter: `productName`, the identifier `com.nictate.app`, the `%LOCALAPPDATA%\Nictate` paths (database, logs, OpenVINO cache), the overlay window class `NictateOverlay`, and the user-facing copy.
   - Expected outcome: `grep -ri nictate blink-monitor/` returns nothing.
   - Do this before Phase 0. It is two config strings now and a migration later.

2. **Re-verify everything time-sensitive.** Four months have passed.
   - Crate and npm versions in PRD §25 (crates.io API, npm registry).
   - Latest OpenVINO release and whether `openvino` 0.11 still matches it.
   - The Windows ML execution-provider table (has Meteor Lake NPU support been added?).
   - That both model URLs still serve files matching the pinned hashes.
   - Whether nokhwa has a release newer than 0.10.11 that fixes the Windows frame-rate issues.
   - Expected outcome: update PRD §25 and RESEARCH §6 with new dates, or record "unchanged".

3. **Run the build on the user's Windows laptop, not in a cloud session.** Every gate from Phase 2 on needs the real camera, the NPU and Task Manager readings. A Linux container can write code but cannot pass a gate.
   - Install: Rust stable (MSVC target), Node 22 LTS, Python 3 (for `tools/`).

4. **Start Phase 0 with this prompt** (one phase per request, never "build the app"):
   > Read `blink-monitor/PRD.md` (v1.1) and `blink-monitor/IMPLEMENTATION_PLAN.md` in full. Implement Phase 0 only, exactly as specified. Follow the plan's ground rules: if anything is unspecified, stop and report; do not decide. Stop at Gate 0 and show me the gate evidence.
   - Two manual steps inside Phase 0: download the OpenVINO 2026.2.x Windows x64 runtime archive and copy the seven files listed in PRD §6.3 into `third_party/openvino_dlls/`; download both ONNX files into `models/` and let `tools/prepare_models.py` verify the hashes.
   - Expected outcome: Gate 0 in `blink-monitor/IMPLEMENTATION_PLAN.md` (builds, manifest contains both the Common-Controls v6 block and PerMonitorV2, CI green, assets render).

5. **After each phase, review before continuing.** Check the diff against the PRD and the eight-point reviewer checklist at `blink-monitor/IMPLEMENTATION_PLAN.md` line 189. The user asked for this review loop explicitly.

6. **Phases 1 to 7** follow in order. The two gates that carry the real risk:
   - Phase 3: measure memory, CPU, latency and power for NPU and CPU on the laptop and write the numbers into the README. Memory above 80 MB in NPU mode means the design failed; stop and report.
   - Phase 7, acceptance test 4: blink recall and precision both at least 90% against a manually counted phone video.

---

## Learned

- The eye classifier's 95.84% accuracy is Intel's own figure on the test split of the dataset it was trained on (MRL Eye Dataset). No independent benchmark was found. YuNet, by contrast, is peer-reviewed and ships inside OpenCV. Treat the classifier as the component most likely to disappoint and the calibration screen, sensitivity slider and MediaPipe fallback as the answer.
- "Verified" in these documents means licenses, tensor shapes, file hashes and published claims were confirmed against primary sources. It does not mean anything was run. Latency, power and memory numbers in the documents are estimates.
- For models this small the NPU buys lower power draw, not speed. Frame pacing, pausing on idle and lock, and running the face detector only every sixth frame save more than NPU offload does.
- Tauri's default Windows manifest already contains the Common-Controls v6 dependency that `TaskDialogIndirect` needs, and nothing else. Replacing the manifest without re-adding that block breaks the dialog. The plan ships a merged manifest.
- openvino-rs 0.11 has no per-compile properties. Set `CacheDir` and `HintPerformanceMode` on `Core` per device before compiling.
- nokhwa on Windows has open issues about wrong negotiated frame rates. Pace frames by wall clock in the app.
- `tracing-appender` rotates by time only. Retention is `max_log_files(n)`; there is no size cap.
- Windows' camera usage registry (`ConsentStore\webcam`) records which app is using a camera, not which camera. Guard alerts must say "a camera".
- A window that must receive `WM_WTSSESSION_CHANGE` should be a hidden ordinary window, not a message-only window.
- opencv_zoo stores models in Git LFS. `raw.githubusercontent.com` returns a pointer file; `media.githubusercontent.com/media/...` returns the bytes.

→ Items also propagated to permanent memory: none. This session had no memory directory.

---

## Context

- **Branch:** `claude/blink-monitor-research-aclz0i`, fast-forwarded to `origin/main` (`14c43f1`) on 2026-11-23 so that it contains everything on `main`, plus the commit that adds this handoff.
- **`main`:** contains the three blink-monitor documents (commit `9392872`) and five later commits from other sessions for unrelated projects (`offline-journal-prd.md`, `business names/`). It does not contain this handoff file until the branch is merged.
- **Commits for this task:** `06d2a16` research report and PRD v1.0; `705e1a9` Camera Guard and model validation; `9392872` PRD v1.1 and implementation plan.
- **Uncommitted changes:** none after the handoff commit.
- **Failing tests:** none exist.
- **Pull request:** none opened.
- **Environment notes:** The cloud sessions used so far block `storage.openvinotoolkit.org`, `huggingface.co` and `docs.opencv.org`. GitHub, crates.io, npm and `storage.googleapis.com` were reachable.

## Session Log

- 2026-07-12 — claude-code — clarifying questions; four-domain research with sub-agents; research report and PRD v1.0; Camera Guard requirement added; PRD pressure-tested to v1.1; implementation plan written; everything pushed to `main`.
- Date not recorded (between 2026-07-12 and 2026-11-23) — claude-code — name brainstorm (English, then Indian-root names); no name chosen.
- 2026-11-23 — claude-code — initial handoff written; branch fast-forwarded to `main`.
