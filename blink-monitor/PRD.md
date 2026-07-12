# PRD — "Nictate" (working name): Privacy-First Blink-Rate Monitor for Windows

**Version:** 1.1 · 2026-07-12 (v1.0 pressure-tested by two independent red-team passes + primary-source API verification; every found ambiguity resolved — see RESEARCH.md §6 and the changelog at the bottom)
**Status:** Ready for implementation. **Companion document:** [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) — phase-by-phase build order with exact file contents and gates. The PRD defines *what*; the plan defines *when/how*.
**Implementer target:** Claude Opus 4.8 — zero decisions left open. Product-tuning values are marked `TUNABLE` and live as named constants in `src-tauri/src/consts.rs`.

---

## 1. Product summary

A Windows 11 tray application that watches the user through the built-in camera or an external webcam, counts blinks, computes blinks-per-minute (BPM), and reminds the user to blink when the rate stays below a configurable threshold. Polished local dashboard (live rate, today, trends), always-on with a tiny footprint, Intel-NPU inference with CPU fallback, and **zero network capability**.

### Goals
- G1: Blink recall ≥ 90% and precision ≥ 90% (acceptance §23.4) at the default 15 analysis-FPS.
- G2: Tray-only monitoring: **< 60 MB RSS target / 80 MB hard max; < 5% of one CPU core average**.
- G3: NPU inference on Intel Core Ultra Series 1 (Meteor Lake) with silent CPU fallback.
- G4: Zero network I/O ever; frames never persisted; all data local.
- G5: Reminders: toast, subtle overlay, sound — independently toggleable, repeat-with-cooldown.
- G6: Persistent history + trends; one-click monitoring toggle from the tray.
- G7: **Camera Guard** (§7.1): while monitoring, the app holds the camera so the OS blocks all other apps; other apps get access only via an explicit, timed, user-approved release; any successful camera session by another app raises an alert.

### Non-goals (v1)
macOS/Linux, gaze tracking, drowsiness detection, posture, simultaneous multi-camera analysis, auto-update, MSIX/Store, localization (English-only v1), code signing (§22 SmartScreen note).

---

## 2. Hard constraints

| # | Constraint | Enforcement |
|---|---|---|
| C1 | **No network.** No socket-opening crate may be a dependency (`reqwest`, `hyper`, `ureq`, `curl`, `tauri-plugin-http`, `tauri-plugin-updater` all banned). CSP: `default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'` (the `data:` image source and inline styles are required by the preview and uPlot and reference no network origin). UI loads only bundled assets. | `deny.toml` ban-list in CI + §23.3 netstat soak test. |
| C2 | Camera frames live only in RAM, never leave the process. Preview streams only inside the app. | Code review gate each phase. |
| C3 | All third-party components MIT/Apache-2.0/BSD (MPL-2.0 tolerated if transitively unavoidable). §25 manifest is exhaustive; adding a dependency requires updating it + `deny.toml`. | `cargo deny check` in CI. |
| C4 | Single instance; pause/resume and quit always reachable from the tray. | `tauri-plugin-single-instance`. |
| C5 | Every user-facing behavior knob is in §16; no hidden knobs. | Settings UI maps 1:1 to §16. |

---

## 3. Target platform

Windows 11 x64 (22H2+). Primary hardware: Intel Core Ultra 7 (Meteor Lake NPU), 36 GB RAM. Must run correctly with **no NPU** (CPU fallback) and with **no camera** (error state, §7). WebView2 Evergreen is preinstalled on Windows 11 — never bundled; NSIS `webviewInstallMode: "skip"` keeps the installer offline-capable.

---

## 4. Architecture

**Single Rust process** (Tauri v2 host). No sidecar. Threads:

| Thread | Owns | Created |
|---|---|---|
| Main (Tauri event loop) | Tray, window lifecycle, TaskDialog display (via `run_on_main_thread`), plugin dispatch | at start |
| `worker` (std::thread) | Capture, inference, blink machine, minute accumulator, reminder engine, **the single RW SQLite connection**, settings snapshot | at start |
| `overlay` (std::thread) | The layered overlay window + its `GetMessage` pump (§12) | lazily, first reminder |
| `power` (std::thread) | Hidden 0×0 non-visible window (NOT message-only — it must receive `WM_WTSSESSION_CHANGE`); WTS session notifications, `GetLastInputInfo` 5 s poll timer | at start |
| `guard_watcher` (std::thread) | `RegNotifyChangeKeyValue` loop on the ConsentStore key (subtree watch covers `NonPackaged`) (§7.1) | at start |

**Shared state (exact mechanisms):**
- `Arc<RwLock<LiveSnapshot>>` — worker overwrites ≤1×/s: `{bpm: Option<f32>, band, monitoring_state, pause_reason, device_active, camera_name, today_agg}`. Read by IPC and tray tooltip. Never read from DB for live data.
- `crossbeam_channel::Sender<WorkerCmd>` in Tauri managed state — all mutations flow through it: `SetSettings(Settings)`, `SetMonitoring(bool)`, `Snooze(Option<Instant>)`, `ReleaseCamera(ReleaseUntil)`, `ReclaimCamera`, `StartPreview{camera_id}`, `StopPreview`, `Shutdown`.
- DB: worker owns the only **writer** connection. IPC reads use a separate `SQLITE_OPEN_READ_ONLY` connection in `Arc<Mutex<Connection>>` managed state (WAL allows concurrent read).

**Rules:**
- R1 — **destroy, not hide.** The dashboard's `CloseRequested` is never prevented; the window closes fully so WebView2 processes exit (verified: tauri#5611). `hide()` is forbidden. App stays alive via `RunEvent::ExitRequested → api.prevent_exit()` (except tray Quit, which sends `WorkerCmd::Shutdown`, closes the sessions row with `end_reason='quit'`, then exits).
- R2 — worker owns all mutable state; the UI is a stateless renderer.
- R3 — UI events are emitted only when a window exists (`app.get_webview_window("main").is_some()`).
- R4 — EcoQoS: at startup `SetProcessInformation(ProcessPowerThrottling, EXECUTION_SPEED enabled)`; on dashboard window creation disable process-level throttling, re-enable on window destroy; worker thread additionally `SetThreadInformation(ThreadPowerThrottling)` always-on.
- R5 — no per-frame heap allocation in the capture/inference hot path: all frame/crop/tensor buffers preallocated and reused.

---

## 5. Repository layout

```
nictate/
├── PRD.md  RESEARCH.md  IMPLEMENTATION_PLAN.md  README.md  LICENSE(placeholder)
├── rust-toolchain.toml            # [toolchain] channel = "stable"
├── deny.toml                      # license allow-list + C1 ban-list (full content in PLAN Phase 0)
├── .github/workflows/ci.yml      # fmt, clippy -D warnings, test, cargo-deny (windows-latest)
├── src-tauri/
│   ├── Cargo.toml  tauri.conf.json  build.rs  windows-manifest.xml
│   ├── src/
│   │   ├── main.rs        consts.rs      # every TUNABLE lives in consts.rs
│   │   ├── tray.rs        ipc.rs         settings.rs    db.rs
│   │   ├── worker/mod.rs  worker/capture.rs  worker/detector.rs
│   │   ├── worker/blink.rs  worker/stats.rs  worker/reminders.rs
│   │   ├── overlay.rs     notify.rs      power.rs       guard.rs
│   │   └── preview.rs
│   └── icons/                     # generated by tools/gen_assets.py
├── ui/                            # Vite + vanilla TS; src/pages/{dashboard,history,settings,camera,about}.ts
├── models/                        # two vendored ONNX (§6.1) + ir/ (generated, committed)
├── tools/prepare_models.py  tools/golden_gen.py  tools/gen_assets.py
├── tests/fixtures/                # golden tensors + eye-crop fixtures (§21)
├── third_party/openvino_dlls/     # NOT committed (gitignored); populated from the OpenVINO archive (PLAN Phase 0)
└── assets/  overlay_eye.png  reminder.wav   # generated by gen_assets.py, committed
```

---

## 6. Models — provenance, conversion, bundling

### 6.1 Files (vendored in `models/`; hashes verified by `prepare_models.py` before converting)

| Model | Source | License | Pinned identity |
|---|---|---|---|
| `face_detection_yunet_2023mar.onnx` | `https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx` | MIT | 232,589 B; SHA-256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`. Never substitute `2026may` (dynamic dims → NPU-incompatible). |
| `open_closed_eye.onnx` | `https://storage.openvinotoolkit.org/repositories/open_model_zoo/public/2022.1/open-closed-eye-0001/open_closed_eye.onnx` (canonical per official model.yml); fallback `omz_downloader --name open-closed-eye-0001` (`pip install openvino-dev==2024.6.0`) | Apache-2.0 | 46,164 B; SHA-384 `2615bce53b55620c629db21b043057600ccc53466f053c0a8277c43577c2db21e48f330cf9b15213016d17cddb8cba27` |

### 6.2 Conversion (`tools/prepare_models.py`, `pip install openvino==2026.2.*`)

```python
import openvino as ov
core = ov.Core()
m = core.read_model("models/face_detection_yunet_2023mar.onnx")
m.reshape({"input": [1, 3, 192, 320]})          # NCHW: H=192, W=320 (multiples of 32)
ov.save_model(m, "models/ir/yunet_320x192.xml", compress_to_fp16=True)
m2 = core.read_model("models/open_closed_eye.onnx")
ov.save_model(m2, "models/ir/open_closed_eye.xml", compress_to_fp16=True)
```
Eye-model normalization is done in Rust (§8.4); the IR stays canonical. The 4 IR files (~0.3 MB) are committed and bundled as resources under `models/ir/`.

### 6.3 OpenVINO runtime — linking and bundling (decided; API-verified)

- The `openvino` crate is used with the **`runtime-linking`** feature: the app **builds without any OpenVINO SDK present** and `dlopen`s the runtime at `Core::new()`.
- DLLs shipped as bundled resources under `resources/openvino/`: `openvino.dll`, `openvino_c.dll`, `openvino_intel_cpu_plugin.dll`, `openvino_intel_npu_plugin.dll`, `openvino_ir_frontend.dll`, `tbb12.dll`, `plugins.xml` (from the official "OpenVINO Runtime 2026.2.x Windows x64" archive; populated into `third_party/openvino_dlls/` at dev time — PLAN Phase 0).
- Before the first OpenVINO call, resolve `app.path().resource_dir()/openvino` and call `SetDllDirectoryW` on it (the Windows loader does not search resource subfolders by default). In `tauri dev`, a documented copy step places the DLLs in `target/debug/openvino/` and the same code path resolves them (PLAN Phase 0).
- **Load-failure behavior (defined):** if DLL load or IR read/compile fails on both devices, or IR files are missing/corrupt: log `events(kind='error')`, tray state **error**, keep tray + dashboard alive with a banner "Detection unavailable — <reason>", do not start the capture loop. Never crash.

---

## 7. Camera subsystem (`worker/capture.rs`)

- `nokhwa = "=0.10.11"` (exact pin; 0.10.10/11 are Windows-fix releases), features `["input-msmf"]`.
- Open: `Camera::new(index, RequestedFormat::new::<RgbFormat>(RequestedFormatType::Closest(CameraFormat::new(Resolution::new(w,h), frame_format, fps))))`; format ladder, first success wins:
  1. 640×360 YUYV @ 15 → 2. 640×360 NV12 @ 15 → 3. 640×480 YUYV @ 15 → 4. 640×360 MJPEG @ 15 → 5. 1280×720 MJPEG @ 10.
- **Software pacing (mandatory):** nokhwa/MSMF has documented wrong-frame-rate negotiation bugs. Never trust the negotiated rate: pull `frame()` in a loop and *drop* frames so that analysis runs at `min(analysis_fps, actual_rate)` using wall-clock timestamps (process a frame only if `now − last_processed ≥ 1/analysis_fps − 2 ms`).
- Decode with `decode_image_to_buffer::<RgbFormat>` into a preallocated RGB buffer; BGR swap happens fused into the letterbox/crop pass (§8.2) — no separate conversion pass.
- **Device identity:** use nokhwa's device path if exposed for MSMF; otherwise `"<friendly_name>#<enumeration_index>"`. If stable per-device identity proves impossible in practice, that is the designated trigger to implement the direct-Media-Foundation `CaptureBackend` (the capture code sits behind trait `CaptureBackend` from day one).
- **Selection:** `camera_id="auto"` resolves to internal persisted key `last_used_camera` (written on every successful open), else first enumerated. If an explicitly-selected camera disappears: auto-switch to any available device **without** overwriting `camera_id`; when the selected device reappears, switch back; toast + `events` row on both transitions. No camera at all: tray *no-camera*, re-enumerate every 15 s.
- **Access denied (Windows privacy toggle):** treat `E_ACCESSDENIED`-class open errors distinctly from busy: tray **error**, one-time toast + Camera-page banner "Camera access for desktop apps is off. Enable it in Settings ▸ Privacy & security ▸ Camera." Retry every 30 s. Never attempt to change the setting.
- **Policy** `camera_conflict_policy` ∈ `guard` (default) | `pause` | `share`:
  - `guard`: §7.1.
  - `pause`: on device-busy open error or foreign ConsentStore session: release, tray *camera-busy*, `sessions.end_reason='camera_busy'`, poll every 15 s, auto-resume.
  - `share`: attempt concurrent capture (works only with Win11 24H2 multi-app camera enabled); open failure ⇒ behave as `pause` for that interval.

### 7.1 Camera Guard (`guard.rs`, default policy)

**Windows facts the design is built on (do not re-litigate in code):** exclusive Frame-Server access means *holding the device blocks every other app* (unless the user enabled 24H2 "multi-app camera"); there is **no user-mode API to observe or veto another app's camera-open attempt** (that needs a kernel filter driver — out of scope); *successful* sessions are observable via ConsentStore (`HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam`, subtree incl. `NonPackaged`): a subkey with `LastUsedTimeStart != 0 && LastUsedTimeStop == 0` is an app currently using **a** camera (ConsentStore is per-app, not per-device — alerts therefore cover all cameras, and the UI copy must say "a camera", never "your camera").

**Hold matrix (resolves the v1.0 hold-vs-pause contradiction):**

| State | Camera held? | Inference running? | Rationale |
|---|---|---|---|
| Active | yes | yes | normal |
| Paused(idle) | **yes — held** | no (frames grabbed at 2 fps and discarded to keep the stream alive) | guard integrity at near-zero cost |
| Paused(session_locked) | **no — released** | no | holding the RGB camera through the lock screen could block Windows Hello face sign-in; deliberate guard boundary, documented in README + Camera page |
| Paused(user_toggle) | no — released | no | user turned monitoring off; guard is a monitoring feature |
| Paused(camera_released) | no — released | no | user-approved lend-out |
| Paused(camera_busy / no_camera / error) | n/a | no | device unavailable |

**Watcher (`guard_watcher` thread, all policies, always running):** one `RegNotifyChangeKeyValue(hkey_webcam, TRUE /*subtree*/, REG_NOTIFY_CHANGE_LAST_SET, event, TRUE)` loop; on each signal, enumerate subkeys of both `webcam\*` and `webcam\NonPackaged\*`, diff against the previous snapshot, exclude our own exe (NonPackaged names encode the exe path with `\` → `#`; compare case-insensitively). On a foreign session **start**:
- state Active/idle-held (guard armed): emit alert (below) + `events(kind='camera_guard', detail=json{app, exe_path, action:"started"})`.
- state `camera_released`: log only (the user approved a lend-out; no alert — we cannot attribute sessions to the approved app).
- state `session_locked`: log + defer; on unlock, if a foreign session is still active, alert then.
- The watcher never blocks on UI: it sends over a channel; the **main thread** shows the alert via `run_on_main_thread`.

**Alert:** toast + native `TaskDialogIndirect` (comctl32 v6 — provided by the app manifest, §22/PLAN) — title "Camera in use", body "<App name> started using a camera.", buttons **[Block — reclaim camera] [Allow for 30 min] [Open dashboard]**; if the dashboard is open, also emit `guard_alert` for an in-app modal.

**Release flow:** tray `Release camera → 15 min / 30 min / 1 h / until I resume`, dashboard button, or alert "Allow": release device, `sessions.end_reason='camera_released'`, tray *released*, start release timer (`until_resume` = no timer). Reclaim when **both** (a) no foreign session is active in ConsentStore and (b) the timer has expired (checked every 30 s and on watcher events); for `until_resume`, only an explicit user resume reclaims. On reclaim: reopen, resume monitoring, toast "Camera reclaimed — monitoring resumed."

**Block/reclaim ("Block" button):** attempt immediate reopen; if the foreign app still holds the device, retry every 5 s up to 60 s, then TaskDialog "Could not reclaim — <app> is still using the camera" with [Retry] [Release for 30 min].

**Sharing-enabled anomaly:** a foreign session starting while we hold the device ⇒ 24H2 multi-app camera must be on ⇒ the alert body appends: "Windows multi-app camera sharing is enabled, so holding the camera cannot block other apps. Turn it off: Settings ▸ Bluetooth & devices ▸ Cameras ▸ <camera> ▸ Advanced."

**Honest limits (README + Camera page, verbatim requirement):** Guard is an awareness/convenience control, not a security boundary; admin- or kernel-level software can bypass it; it cannot cover cameras the app is not holding (including Windows Hello IR sensors); the physical shutter remains the strongest protection when not monitoring; the Windows camera privacy indicator stays lit while Nictate holds the camera — expected.

---

## 8. Detection pipeline (`worker/detector.rs`)

### 8.1 OpenVINO session (API-verified against openvino-rs 0.11)

- `Core::new()` after `SetDllDirectoryW` (§6.3). Models: `core.read_model_from_file("<res>/models/ir/yunet_320x192.xml", "<res>/models/ir/yunet_320x192.bin")` etc.
- **Device selection (explicit two-step — deliberately NOT `AUTO:NPU,CPU`,** to avoid loading the ~40 MB CPU plugin alongside the NPU plugin, protecting the G2 RAM budget, and to keep `device_active` deterministic):
  1. Read `available_devices`; if setting is `auto` and `"NPU"` present → set `core.set_property(&DeviceType::NPU, &RwPropertyKey::CacheDir, "%LOCALAPPDATA%\\Nictate\\ovcache")` and `(&RwPropertyKey::HintPerformanceMode, "LATENCY")`, then `compile_model(&model, DeviceType::NPU)` for both models. On any error → fall through.
  2. CPU path: same two properties on `DeviceType::CPU` (CacheDir optional for CPU; set it anyway — harmless), `compile_model(..., DeviceType::CPU)`. Settings `cpu`/`npu` force the respective single path (forced-`npu` failure ⇒ §6.3 error state, not silent CPU).
  3. A runtime inference error on NPU (e.g. driver reset) ⇒ one-shot recompile on CPU, `device_active="CPU (fallback)"`, `events` row.
- Note: openvino-rs 0.11 has no per-compile properties (verified) — properties are set on `Core` per device *before* compiling, exactly as above. `DeviceType::Other("AUTO:NPU,CPU".into())` would work but is rejected by this design.
- `device_active` ∈ `"NPU" | "CPU" | "CPU (fallback)"` exposed in `LiveSnapshot`.

### 8.2 Stage 1 — YuNet (every 6th analysis frame `DETECTOR_CADENCE=6 TUNABLE`; reuse last box/eyes between runs; *search mode* at 2 fps full-pipeline when no face > 10 s)

- **Preprocessing (verified from OpenCV source):** raw BGR, float, 0–255 — `blobFromImage` defaults: scale 1.0, no mean subtraction, no channel swap.
- **Letterbox (generalized):** `scale = min(320/W, 192/H)`; `w' = round(W·scale)`, `h' = round(H·scale)`; centered, `pad_x = (320−w')/2`, `pad_y = (192−h')/2`, pad value 0. RGB→BGR swap fused here. Keep `(scale, pad_x, pad_y)`; map all outputs back by `p_full = (p_model − pad) / scale`. (640×360 ⇒ scale 0.5, pad_y 6 — matches the worked example.)
- **Decode (verified line-by-line from OpenCV `face_detect.cpp`):** for each stride s ∈ {8,16,32} with feature map `w_s×h_s` = 40×24, 20×12, 10×6 (row-major; `row = i / w_s`, `col = i % w_s`):
  - `cls = min(cls_raw, 1.0)`, `obj = min(obj_raw, 1.0)` (upper clamp only), `score = sqrt(cls·obj)`
  - `cx = (col + bbox[0])·s`, `cy = (row + bbox[1])·s`, `w = exp(bbox[2])·s`, `h = exp(bbox[3])·s`; box = `(cx−w/2, cy−h/2, w, h)`
  - landmark k∈0..4: `x = (kps[2k]+col)·s`, `y = (kps[2k+1]+row)·s`; order: right eye, left eye, nose, right mouth, left mouth.
- Filter `score ≥ 0.7` (`YUNET_SCORE_THR TUNABLE`), greedy IoU-NMS at 0.3 (`YUNET_NMS_IOU`), top-k 50, eta 1.0; keep the largest-area face. Golden-tested against committed OpenCV reference tensors (§21.1).

### 8.3 Stage 2 — eye crops (full-frame coordinates)

Square side `= 0.40 × inter-ocular distance` (`EYE_CROP_SCALE TUNABLE`) centered on each eye landmark. **Edge clamping:** keep the side fixed and *translate* the square fully inside the frame (no distortion); only if side > frame dimension, clamp and pad the crop with black. Bilinear-resize to 32×32, BGR.

### 8.4 Stage 3 — open/closed classifier (per eye)

Input `input.1` `[1,3,32,32]` BGR, normalize `(px − 127.0)/255.0`; output `19` `[1,2,1,1]` = `[p_open, p_closed]` (documented as softmax). **Robustness rule:** if `|p_open + p_closed − 1| > 0.01`, apply softmax in Rust (protects against a raw-logits export; do **not** softmax unconditionally — re-softmaxing true probabilities distorts them). The §21.2 fixture test validates which branch runs. Frame signal: `p = max(p_closed_L, p_closed_R)`.

---

## 9. Blink event detection (`worker/blink.rs`)

Constants in `consts.rs`, all `TUNABLE`: `CLOSE_ON_BASE=0.60`, `OPEN_OFF_BASE=0.40`, `SENS_GAIN=0.15`, `MIN_CLOSED_MS=66`, `MAX_CLOSED_MS=500`, `REFRACTORY_MS=150`.

**Sensitivity mapping (sign defined):** `s ∈ [−1,+1]`, positive = more sensitive (detects more/lighter blinks): `CLOSE_ON = CLOSE_ON_BASE − SENS_GAIN·s`, `OPEN_OFF = OPEN_OFF_BASE − SENS_GAIN·s`; clamp both to `[0.05, 0.95]` and enforce `CLOSE_ON − OPEN_OFF ≥ 0.10`.

State machine on per-frame `p` (frames with `p` unavailable hold state; a face-gap > 1 s resets to OPEN without emitting):

```
OPEN:        p > CLOSE_ON                       → CLOSED (record t_close)
CLOSED:      p in (OPEN_OFF, CLOSE_ON]          → stay CLOSED (hysteresis band)
             p ≤ OPEN_OFF                       → dur = now − t_close;
                                                   emit Blink{ts:now, duration_ms:dur}
                                                   iff MIN_CLOSED_MS ≤ dur ≤ MAX_CLOSED_MS
                                                   and now − last_blink ≥ REFRACTORY_MS;
                                                   → OPEN
             now − t_close > MAX_CLOSED_MS      → EYES_CLOSED (long closure, not a blink)
EYES_CLOSED: p ≤ OPEN_OFF                       → OPEN (no blink)
```

A single closed frame counts (at 15 fps one frame ≈ 66 ms ⇒ `dur ≥ MIN_CLOSED_MS` holds). Below 10 fps short blinks fall between samples; Settings copy for `analysis_fps` states "values below 10 reduce detection accuracy" (G1 is only guaranteed at the default 15).

---

## 10. BPM & aggregation (`worker/stats.rs`)

- **Ring buffer** (in-memory, 90 s capacity): blink timestamps + per-second `{monitored, face_present}` flags. Only the trailing 60 s is read (extra 30 s is safety margin; no other consumer).
- Every 1 s over the trailing 60 s: `bpm = blinks·60/face_present_s` **iff** `face_present_s ≥ 42 && monitored_s ≥ 42`; else `bpm = null` ("insufficient data"; never fires reminders). Band: `good` (bpm ≥ threshold_bpm), `low` (< threshold), `nodata` (null) — bands derive **only** from `threshold_bpm` (no fixed constants).
- **Minute rollup:** a separate per-calendar-minute accumulator (`blinks`, `face_present_s`, `monitored_s`; reset at each minute boundary) — *not* the sliding window (which would double-count). At each boundary insert into `minute_stats`, **including fully-paused minutes** (`monitored_s=0`) while the app runs; minutes with no row = app not running. Both mean "unmonitored" to the UI.
- **Day boundaries / timezone:** all storage is UTC ms. "Today"/day-buckets use the OS local offset resolved **at query time**: `day = (ts + local_offset_ms) / 86_400_000`. DST day = 23/25 h — accepted and documented.
- Coverage% (dashboard tile) = `Σ monitored_s since local midnight / seconds elapsed since local midnight × 100`.

---

## 11. Reminder engine (`worker/reminders.rs`, `notify.rs`)

Evaluated every 1 s: fire iff `bpm != null && bpm < threshold_bpm && now − last_reminder ≥ cooldown_s && now − monitoring_resumed ≥ GRACE_S(=90, TUNABLE) && !snoozed && monitoring Active`.

- **Snooze is NOT a pause reason** — it is `snooze_until: Option<Instant>` (tray-set; `until I resume` = `Instant::MAX` cleared by explicit resume). Monitoring and stats continue during snooze; only reminders are suppressed.
- On fire: run every enabled style, insert `reminders(ts, styles, bpm)` with `styles` = comma-joined lowercase tokens, e.g. `"toast,overlay"`; `INSERT OR IGNORE` on ts collision.
- **Toast** (`tauri-plugin-notification` 2.3.x; Rust: `app.notification().builder().title(...).body(...).show()` — verified window-independent): title `Time to blink 👁`, body `Your blink rate is {bpm:.0}/min (target ≥ {threshold}). Look away and blink slowly a few times.` Branded correctly in installed builds (NSIS shortcut/AUMID = `com.nictate.app`); generic in `tauri dev` — accepted.
- **Overlay** §12. **Sound**: `PlaySound(reminder.wav resource path, None, SND_FILENAME|SND_ASYNC|SND_NODEFAULT)`.
- Fullscreen suppression (`suppress_when_fullscreen=true` default): skip overlay+sound when `SHQueryUserNotificationState` ∈ {`QUNS_BUSY`, `QUNS_RUNNING_D3D_FULL_SCREEN`, `QUNS_PRESENTATION_MODE`}; toast is left to Focus Assist.

---

## 12. Overlay (`overlay.rs`) — native, never a WebView

Dedicated thread; own window class `"NictateOverlay"`; `CreateWindowExW` with `WS_POPUP` + `WS_EX_LAYERED|WS_EX_TRANSPARENT|WS_EX_TOPMOST|WS_EX_NOACTIVATE|WS_EX_TOOLWINDOW`; its own `GetMessage` pump. The reminder engine triggers it by `PostMessageW(hwnd, WM_APP+1, 0, 0)`.

Content: `assets/overlay_eye.png` (generated by `gen_assets.py`: 280×160 logical px rounded pill, eye glyph + the word "blink", max alpha 60%), positioned top-center of the **primary** monitor, 48 px below the top edge, scaled by `GetDpiForWindow`. Animation ≈ 30 fps via `UpdateLayeredWindow` with premultiplied-ARGB DIB and per-frame global alpha: fade-in 300 ms → hold 1200 ms → fade-out 500 ms → hide. PNG decoded once (`png` crate). Note: layered windows cannot appear over the secure desktop or elevated fullscreen apps — accepted.

---

## 13. Lifecycle & power (`power.rs`, `worker/mod.rs`)

- States: `Active | Paused(reason)`, reason ∈ `user_toggle | session_locked | idle | camera_busy | camera_released | no_camera | error`. (`snooze` removed — see §11.)
- **Precedence (highest wins):** `camera_released > session_locked > user_toggle > camera_busy/no_camera/error > idle > Active`. Concretely: idle/lock resume events never reclaim a released camera; unlocking while `camera_released` returns to `camera_released`, not Active.
- Session lock/unlock: `WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_THIS_SESSION)` on the power thread's hidden window; `WM_WTSSESSION_CHANGE` → `WTS_SESSION_LOCK/UNLOCK`.
- Idle: `GetLastInputInfo` polled every 5 s; idle > `pause_on_idle_min` (default 5; 0=off) ⇒ `Paused(idle)` with **camera held** (§7.1 matrix); any input resumes instantly.
- Battery: no behavior change (user decision).
- Every state transition writes/closes `sessions` rows. **Crash recovery at startup:** `UPDATE sessions SET end_ts = COALESCE((SELECT MAX(minute_ts)+60000 FROM minute_stats WHERE minute_ts >= start_ts), start_ts), end_reason='crash' WHERE end_ts IS NULL`.
- **First run** (no `schema_version` row): create schema, insert §16 defaults, auto-open the dashboard once on a first-run view (privacy statement, autostart yes/no question, camera check); subsequent launches are tray-only with **no window**.

---

## 14. Tray (`tray.rs`)

- Left-click: create dashboard (`WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))`, 1100×720, min 900×600, title "Nictate") or focus it if it exists. Second app instance (single-instance plugin, registered **first**) does the same.
- Menu: `Monitoring ✓` · `Release camera → 15 min / 30 min / 1 h / until I resume` · `Snooze reminders → 30 min / 1 h / 2 h / until I resume` · `Open dashboard` · `Start with Windows ✓` · `Quit`.
- Icon states (5 icons from `gen_assets.py`): active / paused / released / camera-busy‑no-camera / error. Tooltip `Nictate — {bpm:.0}/min` (or state text), refreshed ≤ every 5 s from `LiveSnapshot`.
- Autostart: `tauri-plugin-autostart` (HKCU Run); **re-assert on every launch** when enabled (mitigates plugins-workspace#771).

---

## 15. Persistence (`db.rs`) — rusqlite 0.40 `bundled`, WAL

`%LOCALAPPDATA%\Nictate\nictate.db`; timestamps INTEGER Unix-ms UTC. Schema v1 created in one transaction; `INSERT INTO schema_version(v) VALUES(1)`; no migration framework in v1 (future migrations key off `v`).

```sql
CREATE TABLE schema_version(v INTEGER NOT NULL);
CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);            -- JSON-encoded values
CREATE TABLE blink_events(ts INTEGER PRIMARY KEY, duration_ms INTEGER NOT NULL);
CREATE TABLE minute_stats(minute_ts INTEGER PRIMARY KEY, blinks INTEGER NOT NULL,
                          face_present_s REAL NOT NULL, monitored_s REAL NOT NULL);
CREATE TABLE sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, start_ts INTEGER NOT NULL,
                      end_ts INTEGER, end_reason TEXT);
  -- end_reason: user_toggle|session_locked|idle|camera_busy|camera_released|no_camera|error|quit|crash
CREATE TABLE reminders(ts INTEGER PRIMARY KEY, styles TEXT NOT NULL, bpm REAL NOT NULL);
CREATE TABLE events(ts INTEGER, kind TEXT, detail TEXT);  -- kind: camera_guard|camera_switch|device_fallback|error
```

- All inserts that can collide on a ms-PK use `INSERT OR IGNORE`.
- Retention: daily at first write after 03:00 local — purge `blink_events` > 90 days, `events` > 30 days. `minute_stats` kept forever (≈21 MB/year max). "Delete all history" button truncates all data tables in one transaction.
- Write policy: blink events immediately; minute_stats at minute boundaries; never per frame.
- Connections: exactly two (§4) — worker RW, IPC read-only.

---

## 16. Settings (persisted in `settings` table; JSON values)

| Key | Type / range | Default |
|---|---|---|
| `monitoring_enabled` | bool | true |
| `camera_id` | `"auto"` \| device id (§7) | `"auto"` |
| `last_used_camera` | device id — **internal, not shown in UI** | `""` |
| `camera_conflict_policy` | `"guard"`\|`"pause"`\|`"share"` | `"guard"` |
| `analysis_fps` | int 5–30 (UI copy: "below 10 reduces accuracy") | 15 |
| `inference_device` | `"auto"`\|`"cpu"`\|`"npu"` | `"auto"` |
| `threshold_bpm` | int 4–20 | 8 |
| `cooldown_s` | int 60–1800 | 180 |
| `reminder_toast` / `reminder_overlay` / `reminder_sound` | bool | true / true / false |
| `suppress_when_fullscreen` | bool | true |
| `sensitivity` | float −1.0…+1.0 | 0.0 |
| `pause_on_idle_min` | int 0–60 (0=off) | 5 |
| `autostart` | bool | set on first run (question) |
| `theme` | `"system"`\|`"light"`\|`"dark"` | `"system"` |

`set_settings(patch)` validates every key against these ranges; **any** invalid value rejects the whole patch atomically with `{error:{key, reason}}`. Valid patches persist in one transaction, then the full new `Settings` struct is pushed to the worker (never a partial state).

---

## 17. Dashboard UI (Vite + vanilla TypeScript + uPlot 1.6.x; no framework)

Pages (left nav): **Dashboard · History · Settings · Camera · About** (+ hidden first-run view, §13).

- **Dashboard:** live BPM number colored by band (`good` green / `low` amber / `nodata` gray); today sparkline = per-minute bpm from `minute_stats` smoothed with a 5-minute simple moving average (uPlot line); tiles: today avg BPM (`Σblinks·60/Σface_present_s`), minutes below threshold, reminders today, coverage% (§10); 24 h timeline strip of monitored/paused segments colored by `end_reason`.
- **History:** `7d` = hourly avg-bpm uPlot line + horizontal `threshold_bpm` reference line; `30d` = daily bars of minutes-below-threshold + daily avg-bpm line (second axis). Range switcher only (`7d`/`30d`) — no free date picker in v1.
- **Settings:** §16 controls with exact ranges; instant apply; invalid input shows the IPC error inline.
- **Camera:** device picker; policy picker (guard/pause/share with one-line explanations incl. the §7.1 honest-limits text); live preview ≤ 15 fps with face box, eye points, per-eye p_closed bars, live blink counter ("blink 5 times — the counter should read 5"); sensitivity slider with immediate effect. Preview requires the device: if released/busy it shows "Camera in use by <app>" (`start_preview` → `{error:"camera_unavailable"}`) and **never** reclaims a released camera. Preview runs regardless of `monitoring_enabled`, auto-stops on page leave or after 10 min.
- **About:** version, `device_active`, model licenses, "This app has no network capability."
- Bucketing is fixed per range: today→minute, 7d→hour, 30d→day — aggregation in SQL, never in JS (§18 queries). uPlot receives ≤ 1,440 points.

---

## 18. IPC surface (`ipc.rs`) — complete contract

`range` is `"today" | "7d" | "30d"`. All responses are `Result`-shaped: success payload or `{error:{key?:string, reason:string}}`.

- `get_live_stats() → {bpm: number|null, band:"good"|"low"|"nodata", monitoring_state:"active"|"paused", pause_reason:string|null, snoozed_until:number|null, device_active:string, camera_name:string|null, today:{avg_bpm:number|null, minutes_below:number, reminders:number, coverage_pct:number}}` (from `LiveSnapshot`, no DB).
- `get_history(range) → {bucket:"minute"|"hour"|"day", points:[{ts:number, avg_bpm:number|null, minutes_below:number}]}` — SQL (hour example): `SELECT (minute_ts/3600000)*3600000 AS b, SUM(blinks) blinks, SUM(face_present_s) fps_, SUM(monitored_s) mon, SUM(CASE WHEN monitored_s>30 AND blinks*60.0/MAX(face_present_s,1)<:thr THEN 1 ELSE 0 END) mins_below FROM minute_stats WHERE minute_ts>=:from GROUP BY b ORDER BY b` with `avg_bpm = blinks*60.0/fps_` computed per bucket (null when `fps_ < 0.5·mon` or `mon=0`); day buckets add `local_offset_ms` before division (§10). Full query set lives in `db.rs` as named consts (PLAN Phase 6).
- `get_sessions(range) → [{start_ts, end_ts, end_reason}]`; `get_guard_events(range) → [{ts, detail}]` (`events` where kind='camera_guard').
- `get_settings() → Settings`; `set_settings(patch) → {applied: Settings} | {error}`.
- `list_cameras() → [{id, name, active:boolean}]`.
- `start_preview(camera_id) → {} | {error:"camera_unavailable"}`; `stop_preview() → {}`.
- `set_monitoring(bool) → {}`; `snooze(minutes:number|"until_resume") → {}`; `release_camera(minutes:number|"until_resume") → {}`; `reclaim_camera() → {}`; `delete_all_history() → {}`.
- Events (emitted only when the window exists): `stats_tick` (payload = `get_live_stats` shape, 1 Hz) · `state_changed {monitoring_state, pause_reason, device_active}` · `guard_alert {app, exe_path, ts}` · `preview_frame {jpeg_b64, face, eyes, p_closed_l, p_closed_r, blink_count}` (≤ 15 Hz).

---

## 19. Calibration preview (`preview.rs`)

Downscale the current frame to 320×180, JPEG quality 60 (`image` crate, jpeg feature only), base64 (`base64` crate), emit `preview_frame` with detection metadata scaled to preview coordinates. Encoding runs **only** while a preview subscriber is active (`start_preview`…`stop_preview`). Hard caps: 15 Hz, 10 min auto-stop. In-memory only (C2).

---

## 20. Alternative backend (out of v1, designed-for)

`detector.rs` implements trait `BlinkSignalSource { fn process(&mut self, frame:&BgrFrame) -> FrameResult }`. The designated v2 alternative: MediaPipe Face Landmarker v2 blendshapes (Apache-2.0, `face_landmarker.task`, 3,758,596 B, `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`; `p = max(eyeBlinkLeft, eyeBlinkRight)`, CLOSE_ON≈0.5/OPEN_OFF≈0.3). Do not implement in v1.

---

## 21. Testing (all CI-runnable without camera, NPU, or OpenVINO)

1. **Golden decode tests:** `tools/golden_gen.py` (opencv-python, run locally once) letterboxes 5 CC0/synthetic face images to 320×192, runs `FaceDetectorYN`, and commits **both** the raw 12 output tensors **and** the decoded faces as JSON fixtures. The Rust test feeds the committed raw tensors through our decode+NMS and requires boxes/landmarks within 1 px, scores within 1e-3 — so CI never needs OpenVINO.
2. **Classifier sanity fixtures:** committed open/closed 32×32 crops + their expected `[p_open,p_closed]` captured by `golden_gen.py` via OpenVINO Python; Rust test validates preprocessing + §8.4 sum-check branch. (This single test category *does* need the tensors precomputed — they are fixtures, so CI still runs pure Rust.)
3. **Blink state machine:** synthetic `p` sequences — normal blink; double blink inside refractory; long closure; flicker inside the hysteresis band; face-gap reset; sensitivity extremes (`s=±1`) respect clamps.
4. **BPM/reminders:** insufficient coverage ⇒ null; grace, cooldown, snooze, fullscreen-suppression honored (SHQueryUserNotificationState behind a mockable trait).
5. **DB:** schema creation; crash-recovery UPDATE; retention purge; minute-rollup and bucketing SQL correctness (fixed fixture rows, including DST-crossing set).
6. **Settings:** patch validation (atomic reject), serialization round-trip.
7. Capture/OpenVINO/Win32 sit behind traits (`CaptureBackend`, `BlinkSignalSource`, `SystemProbe`) — unit tests use fakes; no test opens a real device.

## 22. Risks & mandated mitigations

| Risk | Mitigation |
|---|---|
| nokhwa MSMF frame-rate negotiation bugs (documented issues) | §7 software pacing by wall clock; negotiated-rate validation logged; direct-MF `CaptureBackend` as designated fallback. |
| Model URLs unreachable someday | Both ONNX vendored in-repo; hashes verified by `prepare_models.py`. |
| YuNet decode ported wrong | §21.1 golden tensors; merge-gated. |
| NPU driver absent/old (in-plugin compile needs ≥ v2565 on Meteor Lake) | Two-step device selection (§8.1); forced-`npu` errors are surfaced, `auto` falls back silently with an `events` row; never crash. |
| OpenVINO RSS blows G2 budget | NPU-only compile path avoids loading the CPU plugin when NPU works (§8.1); measured at Phase-3 gate; > 80 MB is a build-stopping failure. |
| openvino-rs property/API gaps | API verified for 0.11 (`set_property`, `RwPropertyKey::{CacheDir, HintPerformanceMode}`, `DeviceType`, runtime-linking). If a call is still missing in practice, drop to `openvino-sys` for that call only. |
| TaskDialog needs comctl32 v6 | Custom manifest (PLAN Phase 0) keeps Tauri's Common-Controls v6 block **and** adds PerMonitorV2 DPI + longPathAware; overriding Tauri's manifest without the Common-Controls block is a known failure mode — forbidden. |
| Classifier accuracy is vendor-reported only (95.84% on MRL) | Hysteresis machine; calibration page; sensitivity slider; acceptance §23.4 on-device; §20 fallback backend. |
| Guard misread as interception | §7.1 release-based copy mandated; watcher covers only successful sessions; README states kernel-driver limitation + shutter caveat + Windows-Hello lock-screen boundary. |
| 24H2 multi-app sharing defeats exclusivity | Watcher detects concurrent sessions; alert instructs disabling it; no programmatic toggle exists. |
| Unsigned installer → SmartScreen | Ship unsigned in v1; README documents the "unknown publisher" flow; §23.9 passes despite it. |

## 23. Acceptance criteria (on the target laptop)

1. Tray-only + monitoring 1 h: RSS < 80 MB (target 60), avg CPU < 5% of one core, EcoQoS leaf visible.
2. Dashboard closed ⇒ no `msedgewebview2.exe` children remain.
3. 1 h soak: zero network connections (`netstat -b`) + `cargo deny check` passes.
4. Blink accuracy: 5 min self-test vs simultaneous phone-video manual count — recall ≥ 90% and precision ≥ 90% at default settings; repeat with glasses if available (record both).
5. NPU: `auto` on the Core Ultra 7 shows `device_active="NPU"` and Task-Manager NPU activity; with `cpu` forced or NPU driver disabled, identical behavior via CPU (events row logged). Forced `npu` without NPU ⇒ visible error state, no crash.
6. Reminders: threshold 20/cooldown 60 ⇒ first fire within 70 s of sustained low rate, repeats on cooldown, honors snooze, grace, and fullscreen suppression; all three styles verified.
7. Camera: unplug external cam → auto-switch + toast + switch-back on reattach; `pause` policy pauses/resumes around Windows Camera app; lock ⇒ camera released and monitoring paused; idle 5 min ⇒ paused **with camera still held** (privacy LED stays on — verify); input resumes instantly.
7a. **Guard:** while monitoring, Windows Camera app and one conferencing app fail to open the camera; tray release 30 min lets them in; a `guard_alert` names the app when it starts (during Active, not during the approved release window — verify both); after the borrower exits and the timer laps, auto-reclaim + resume toast; "Block — reclaim" restores the hold ≤ 60 s after the borrower exits; §7.1-step-5 warning appears if multi-app sharing is ON; alerts defer across a lock/unlock cycle.
8. Kill process; relaunch → dangling session closed as `crash`, history/settings/autostart intact.
9. NSIS per-user install: no admin, Start-Menu shortcut, branded toast from installed build, first-run dashboard appears once, uninstall leaves no running process (DB remains, documented). SmartScreen "unknown publisher" prompt is expected and documented.
10. Camera privacy toggle off (Settings ▸ Privacy) ⇒ error state with instructive banner; toggle on ⇒ auto-recovery ≤ 30 s.

## 24. Build phases

The authoritative build order, per-phase file lists, exact config file contents, commands, and done-gates live in [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) (Phases 0–7). Each phase ends with all tests green and a code review against this PRD.

## 25. Dependency manifest (exhaustive — C3 gate; versions verified on crates.io/npm 2026-07-12)

**Rust** (pin minor; commit `Cargo.lock`): `tauri = "2.11"` features `["tray-icon"]` · `tauri-plugin-notification = "2.3"` · `tauri-plugin-autostart = "2.5"` · `tauri-plugin-single-instance = "2.4"` · `openvino = "0.11"` features `["runtime-linking"]` · `nokhwa = "=0.10.11"` features `["input-msmf"]` · `rusqlite = "0.40"` features `["bundled"]` · `windows` (latest 0.6x; features `Win32_Foundation, Win32_System_Threading, Win32_System_RemoteDesktop, Win32_System_Registry, Win32_UI_WindowsAndMessaging, Win32_UI_Controls, Win32_UI_Input_KeyboardAndMouse, Win32_UI_Shell, Win32_Graphics_Gdi, Win32_Media_Audio, Win32_System_LibraryLoader, Win32_System_Power`) · `crossbeam-channel = "0.5"` · `parking_lot = "0.12"` · `serde = {version="1", features=["derive"]}` · `serde_json = "1"` · `base64 = "0.22"` · `png = "0.17"` · `image = {version="0.25", default-features=false, features=["jpeg"]}` · `tracing = "0.1"` · `tracing-subscriber = {version="0.3", features=["fmt"]}` · `tracing-appender = "0.2"` (daily rotation + `max_log_files(7)` — it has **no** size-based rotation; the earlier "5 MB cap" wording is void) · `anyhow = "1"` · `thiserror = "2"`. `tokio` is transitive via Tauri (not a direct dep; not banned — C1 bans socket-*opening* dependencies, and no code may open sockets).
**JS:** `vite` (current major), `typescript`, `uplot = "1.6.x"`. **Nothing else without updating this table and `deny.toml`.**
**Forbidden:** `reqwest`, `hyper`, `ureq`, `curl`, `tauri-plugin-http`, `tauri-plugin-updater`, telemetry/crash SDKs, Electron, Python runtime, InsightFace models, GPL/AGPL code, `face_detection_yunet_2026may.onnx`.

---

### Changelog v1.0 → v1.1 (pressure-test resolutions)
Camera-hold matrix resolves guard/pause contradiction (idle holds, lock releases for Windows Hello); explicit two-step NPU→CPU device selection replaces `AUTO:NPU,CPU` (RSS budget + verified openvino-rs 0.11 property API, set on Core per device); runtime-linking build mode + DLL loader-path step defined; DB two-connection model + `LiveSnapshot` + `WorkerCmd` channel defined; CSP fixed for `data:` images/inline styles; sensitivity sign defined; generalized letterbox; eye-crop edge rule; per-calendar-minute accumulator + paused-minute rows; local-offset-at-query-time day bucketing; crash recovery of sessions; bands derived from threshold only; snooze demoted from pause-reason to independent deadline; state/pause precedence order; preview-vs-released rules; `last_used_camera` + explicit-selection switch-back; camera-id stability fallback; access-denied path; model/DLL load-failure state; first-run flow; softmax sum-check rule (not unconditional); `MIN_CLOSED_MS=66`; `styles` CSV + `INSERT OR IGNORE`; atomic settings patches; overlay/power/guard thread ownership + hidden-window (not message-only) for WTS; deferred lock-screen alerts; complete IPC JSON contract + SQL bucketing; CI fixture strategy (raw tensors, no OpenVINO in CI); manifest = Common-Controls v6 + PerMonitorV2; `tracing-appender max_log_files(7)`; missing deps added (`base64`, `tracing-subscriber`, `parking_lot`, serde derive); exact verified versions; asset-generation tool mandated; unsigned/SmartScreen stance; identifier `com.nictate.app`; window 1100×720/min 900×600.
