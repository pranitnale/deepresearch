# PRD — "Nictate" (working name): Privacy-First Blink-Rate Monitor for Windows

**Version:** 1.0 · 2026-07-12
**Status:** Ready for implementation
**Implementer target:** Claude Opus 4.8 — this document is the single source of truth; every decision is made. Where a numeric constant is a product-tuning value (not a verified fact) it is marked `TUNABLE` and must be a named constant in code.
**Research basis:** [`RESEARCH.md`](./RESEARCH.md) — read §6 (verification ledger) before changing any pinned fact.

---

## 1. Product summary

A Windows 11 tray application that watches the user through the laptop's built-in camera or an external webcam, counts blinks, computes blinks-per-minute (BPM), and reminds the user to blink when their rate stays below a configurable threshold. It has a polished dashboard (live rate, today, 7-day trends), runs always-on with a tiny footprint, uses the Intel NPU when present (CPU otherwise), and **never touches the network**.

### Goals
- G1: Accurate blink counting at 10–15 analysis FPS (recall ≥ 90%, precision ≥ 90% on the §23 self-test).
- G2: Idle footprint (tray-only, monitoring active): **< 60 MB RSS target, 80 MB hard max; < 5% of one CPU core average** on the target machine.
- G3: NPU inference on Intel Core Ultra (Meteor Lake) with automatic, silent CPU fallback.
- G4: Zero network I/O, ever. All data local. Frames never persisted.
- G5: Configurable reminders: Windows toast, subtle overlay, sound — independently toggleable, repeat-with-cooldown.
- G6: Persistent history + trends dashboard; monitoring toggle in one click from the tray.

### Non-goals (v1)
- macOS/Linux, gaze tracking, drowsiness detection, posture, multiple simultaneous cameras, auto-update (forbidden by G4), cloud anything, MSIX/Store packaging.

---

## 2. Hard constraints

| # | Constraint | Enforcement |
|---|---|---|
| C1 | **No network.** No crate that opens sockets may be a dependency (`reqwest`, `hyper`, `tauri-plugin-updater`, `tauri-plugin-http` are all forbidden). Tauri `updater` disabled; CSP `default-src 'self'`; UI loads only bundled assets. | `cargo deny` list + M6 soak test: `netstat` shows zero connections from the process for 1 h. |
| C2 | Camera frames live only in RAM; never written to disk, never leave the process (the calibration preview streams within the app only). | Code review gate. |
| C3 | All third-party components MIT/Apache-2.0/BSD (app's own license: user's choice later; keep `LICENSE` placeholder). | §25 dependency table is exhaustive; adding a dependency requires updating it. |
| C4 | Single instance; user can pause/resume monitoring and quit from the tray at any time. | `tauri-plugin-single-instance`. |
| C5 | Everything user-facing configurable listed in §16 — no hidden knobs. | Settings UI maps 1:1 to §16. |

---

## 3. Target platform

- Windows 11 x64 (22H2+). Primary hardware: Intel Core Ultra 7 (Meteor Lake, NPU "Series 1"), 36 GB RAM.
- Must run correctly on machines **without** an NPU (any x64 Windows 11 laptop) via CPU fallback.
- WebView2 Evergreen runtime is preinstalled on Windows 11 — do **not** bundle it.

---

## 4. Architecture

**Single Rust process** (Tauri v2 host). No sidecar.

```
nictate.exe (Tauri v2, Rust)
├── Tray icon + menu (always alive)                     [tauri::tray]
├── Worker (std::thread, EcoQoS-throttled)
│   ├── Capture loop      (nokhwa/MSMF, 640×360 target)
│   ├── Inference         (OpenVINO AUTO:NPU,CPU — YuNet + open-closed-eye)
│   ├── Blink state machine → blink events
│   ├── Stats aggregator  (60 s sliding window → BPM, minute rollups)
│   └── Reminder engine   (threshold/cooldown → toast | overlay | sound)
├── Overlay: native layered Win32 window (created on demand, ~few MB)
├── SQLite (rusqlite, WAL) at %LOCALAPPDATA%\Nictate\nictate.db
├── Settings (JSON in SQLite `settings` table; hot-reloaded by worker)
└── Dashboard window (WebView2) — created on tray click, DESTROYED on close
    └── Vite + vanilla TypeScript + uPlot; IPC via tauri invoke/events
```

Rules:
- **R1 — destroy, not hide.** Dashboard close ⇒ `window.destroy()`; keep the app alive via `RunEvent::ExitRequested → api.prevent_exit()`. This is what makes idle RAM small (WebView2 processes exit — verified, tauri#5611).
- R2 — worker owns all state; UI is a stateless renderer that queries over IPC. No timers/polling in JS while window closed (it doesn't exist).
- R3 — worker communicates with the main/tray thread via `crossbeam-channel`; UI events via Tauri event emitter (only when a window exists).
- R4 — call `SetProcessInformation(ProcessPowerThrottling, EXECUTION_SPEED)` once at startup (EcoQoS), and `SetThreadInformation` on the worker thread. When the dashboard window is open, temporarily disable process-level throttling to keep the UI snappy; re-enable on destroy.

---

## 5. Repository layout

```
nictate/
├── PRD.md  RESEARCH.md  LICENSE(placeholder)  README.md
├── src-tauri/
│   ├── Cargo.toml  tauri.conf.json  build.rs
│   ├── src/
│   │   ├── main.rs            # bootstrap: single-instance, tray, worker spawn, EcoQoS
│   │   ├── tray.rs
│   │   ├── ipc.rs             # all #[tauri::command] handlers (§18)
│   │   ├── settings.rs        # typed Settings struct ⇄ settings table (§16)
│   │   ├── db.rs              # schema, migrations, queries (§15)
│   │   ├── worker/
│   │   │   ├── mod.rs         # loop orchestration, pause/resume state machine (§13)
│   │   │   ├── capture.rs     # nokhwa capture + format negotiation (§7)
│   │   │   ├── detector.rs    # OpenVINO session, YuNet decode+NMS, eye classifier (§8)
│   │   │   ├── blink.rs       # blink state machine + BPM window (§9,§10)
│   │   │   └── reminders.rs   # §11
│   │   ├── overlay.rs         # native layered window (§12)
│   │   ├── notify.rs          # toast + sound (§11)
│   │   ├── power.rs           # EcoQoS, session lock, idle, camera-busy (§13)
│   │   └── preview.rs         # calibration preview JPEG stream (§19)
│   └── icons/                 # app + tray icons (generated, 4 states §14)
├── ui/                        # Vite vanilla-ts; pages: Dashboard, History, Settings, Camera, About
├── models/
│   ├── face_detection_yunet_2023mar.onnx     # VENDORED, 232,589 B, sha256 8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4
│   ├── open_closed_eye.onnx                  # VENDORED, 46,164 B (see §6 provenance)
│   └── ir/                                   # generated .xml/.bin (build artifact, committed)
├── tools/
│   ├── prepare_models.py      # ONNX → OpenVINO IR conversion (§6)
│   └── golden_gen.py          # OpenCV-reference fixtures for decode tests (§21)
└── assets/  overlay_eye.png  reminder.wav
```

---

## 6. Models — provenance, conversion, bundling

### 6.1 Files (vendor both ONNX files into `models/` at project start)

| Model | Source | License | Pinned identity |
|---|---|---|---|
| `face_detection_yunet_2023mar.onnx` | `https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx` (GitHub LFS; verified live) | MIT | 232,589 bytes; SHA-256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`. Do **not** substitute `2026may` (dynamic shapes → NPU-incompatible). |
| `open_closed_eye.onnx` | `https://storage.openvinotoolkit.org/repositories/open_model_zoo/public/2022.1/open-closed-eye-0001/open_closed_eye.onnx` (canonical, from official [model.yml](https://raw.githubusercontent.com/openvinotoolkit/open_model_zoo/master/models/public/open-closed-eye-0001/model.yml)); fallback `omz_downloader --name open-closed-eye-0001` (`pip install openvino-dev==2024.6.0`) | Apache-2.0 | 46,164 bytes; checksum in model.yml (96-hex, SHA-384): `2615bce53b55620c629db21b043057600ccc53466f053c0a8277c43577c2db21e48f330cf9b15213016d17cddb8cba27` |

`prepare_models.py` must verify these hashes before converting and fail loudly on mismatch.

### 6.2 Conversion to OpenVINO IR (`tools/prepare_models.py`, run with `pip install openvino==2026.2.*`)

```python
import openvino as ov
core = ov.Core()

# YuNet: reshape static 640×640 → 320×192 (fully convolutional; W,H must be multiples of 32)
m = core.read_model("models/face_detection_yunet_2023mar.onnx")
m.reshape({"input": [1, 3, 192, 320]})            # NCHW: H=192, W=320
ov.save_model(m, "models/ir/yunet_320x192.xml", compress_to_fp16=True)

# open-closed-eye: bake preprocessing (BGR passthrough, mean 127, scale 255) via PrePostProcessor,
# or keep raw and normalize in Rust — CHOSEN: normalize in Rust (simpler, model stays canonical).
m2 = core.read_model("models/open_closed_eye.onnx")
ov.save_model(m2, "models/ir/open_closed_eye.xml", compress_to_fp16=True)
```

- Bundle the 4 IR files (`.xml`+`.bin` × 2) as Tauri resources. Total ≈ 0.3 MB.
- 320×192 rationale: aspect 1.67 ≈ camera 16:9 with minimal letterbox; strides 8/16/32 divide evenly → feature maps 40×24, 20×12, 10×6 → 960+240+60 = 1,260 priors per head.

### 6.3 OpenVINO runtime bundling

Ship these DLLs from the OpenVINO 2026.2.x Windows archive distribution next to `nictate.exe` (bundler `resources`): `openvino.dll`, `openvino_c.dll`, `openvino_intel_cpu_plugin.dll`, `openvino_intel_npu_plugin.dll`, `openvino_ir_frontend.dll`, `tbb12.dll`, `plugins.xml`. Omit ONNX/TF/Paddle frontends (we ship IR). Expected disk cost ~60–150 MB — accepted; RAM/CPU are the scarce resources, not SSD.

---

## 7. Camera subsystem (`worker/capture.rs`)

- Library: `nokhwa = "0.10.11"`, features `["input-msmf"]`. If MSMF via nokhwa cannot deliver a needed format, fall back to direct Media Foundation `IMFSourceReader` via the `windows` crate (keep behind a `CaptureBackend` trait from day one).
- Enumerate devices at startup and on `list_cameras` IPC; identify by MSMF symbolic link string (stable across reboots), display friendly name.
- Format ladder (first success wins): 640×360 @ 15 fps → 640×480 @ 15 → 640×360 @ 30 (then process every 2nd frame) → 1280×720 @ 10. Prefer NV12/YUY2; accept MJPG last (decode via nokhwa). Convert to BGR8 once per frame into a reusable buffer (no per-frame allocation).
- Analysis pacing: process at most `analysis_fps` (§16, default 15) frames/s; drop extras.
- Camera selection: `camera_id = "auto"` → last-used if present, else first enumerated. If the selected camera disappears (unplug): switch to any other available camera, set tray state *active*, log an `event` row (§15), show one toast "Switched to <name>". If none: tray state *no-camera*, retry enumeration every 15 s.
- **Camera-busy handling** (policy `camera_conflict_policy`, §16):
  - Detection: open failure/device-busy error from MSMF **plus** the ConsentStore probe (`HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam` and `...\webcam\NonPackaged`: any subkey with `LastUsedTimeStart != 0 && LastUsedTimeStop == 0` and not our own exe ⇒ busy).
  - `pause` (default): release device, tray state *camera-busy*, mark gap in DB (`sessions.end_reason = 'camera_busy'`), poll ConsentStore every 15 s, resume when free.
  - `share`: keep/attempt capture anyway (works only if Win11 24H2 multi-app camera is enabled); if open fails, behave as `pause` for that interval.

---

## 8. Detection pipeline (`worker/detector.rs`)

### 8.1 OpenVINO session

- Crate `openvino = "0.11"` (needs the bundled runtime DLLs; set up path in `build.rs`/at startup with `SetDllDirectoryW` to the resource dir).
- Device string from setting `inference_device`: `"AUTO:NPU,CPU"` (default) | `"CPU"` | `"NPU"`. Compile both models once at worker start with property `PERFORMANCE_HINT=LATENCY`; if the crate exposes `cache_dir`, set `%LOCALAPPDATA%\Nictate\ovcache` (if not exposed in openvino-rs 0.11, skip — models compile in seconds; note it in code).
- On any NPU/AUTO compile failure: log, recompile with `"CPU"`, set `device_active = "CPU (fallback)"`. Expose `device_active` via IPC (shown in dashboard footer and About).

### 8.2 Stage 1 — YuNet face + eye centers (input `[1,3,192,320]` BGR, pixel values 0–255 float, no normalization — matches OpenCV FaceDetectorYN)

- Letterbox the 640×360 BGR frame into 320×192 (scale 0.5, vertical pad 6 px top/bottom, pad value 0). Keep scale/pad to map outputs back.
- Decode the 12 output tensors (`cls_/obj_/bbox_/kps_` × strides 8/16/32; row-major over h×w feature maps: 40×24, 20×12, 10×6): for prior index i at stride s → `row = i / w_s`, `col = i % w_s`; score `= sqrt(clamp01(cls) * clamp01(obj))`; box center `cx = (col + bbox[0]) * s`, `cy = (row + bbox[1]) * s`; size `w = exp(bbox[2]) * s`, `h = exp(bbox[3]) * s`; landmark k: `x = (col + kps[2k]) * s`, `y = (row + kps[2k+1]) * s`. Landmarks order: right eye, left eye, nose, right mouth, left mouth. **Normative reference: OpenCV [`face_detect.cpp`](https://github.com/opencv/opencv/blob/4.x/modules/objdetect/src/face_detect.cpp) — port from it and golden-test (§21); if it differs from the formulas above, OpenCV wins.**
- Filter score ≥ 0.7 `TUNABLE`, NMS IoU 0.3, take the largest-area face.
- **Cadence:** run YuNet every 6th analysis frame `TUNABLE` (*track mode*); between runs, reuse last eye centers. If no face for > 10 s → *search mode*: drop whole pipeline to 2 fps until a face is found (saves power when user is away).

### 8.3 Stage 2 — eye crops

- For each eye center: square crop side `= 0.40 × inter-ocular-distance` `TUNABLE`, clamped to frame; bilinear-resize to 32×32 BGR.

### 8.4 Stage 3 — open/closed classifier (per eye)

- Input `input.1` `[1,3,32,32]` BGR, normalize `(px − 127.0) / 255.0`; output `19` `[1,2,1,1]` softmax `[p_open, p_closed]`.
- Frame blink signal: `p = max(p_closed_left, p_closed_right)` (robust to one-eye occlusion/glare).

Per-frame output struct: `{ts_ms, face: Option<{bbox, eyes}>, p_closed: Option<f32>}`.

---

## 9. Blink event detection (`worker/blink.rs`)

Hysteresis state machine on `p` (constants `TUNABLE`, all in one module):

```
CLOSE_ON = 0.60   OPEN_OFF = 0.40
MIN_CLOSED_MS = 60    MAX_CLOSED_MS = 500    REFRACTORY_MS = 150

state OPEN:   p > CLOSE_ON            → CLOSED (record t_close)
state CLOSED: p ≤ OPEN_OFF            → duration = now − t_close;
                                        if MIN..=MAX and now − last_blink ≥ REFRACTORY
                                          → emit Blink{ts, duration_ms}
                                        → OPEN
              now − t_close > MAX_CLOSED_MS → EYES_CLOSED (not a blink; e.g. long closure)
state EYES_CLOSED: p ≤ OPEN_OFF       → OPEN (no blink emitted)
```

- Frames with no face or no `p`: hold state, but a face-gap > 1 s resets to OPEN without emitting.
- Sensitivity setting (§16) shifts both thresholds: `CLOSE_ON/OPEN_OFF ± 0.15 × sensitivity` where sensitivity ∈ [−1, +1].

---

## 10. BPM computation

- Keep a ring buffer of blink timestamps + per-second face-present/monitored flags for the trailing 120 s.
- Every 1 s compute over the trailing 60 s: `monitored_s`, `face_present_s`, `blinks`.
- `bpm = blinks × 60 / face_present_s` **only if** `face_present_s ≥ 42` (70% coverage) **and** `monitored_s ≥ 42`; else `bpm = null` ("insufficient data" — never fires reminders).
- Minute rollup: at each wall-clock minute boundary insert `minute_stats` (§15).

---

## 11. Reminder engine (`worker/reminders.rs`, `notify.rs`)

Evaluate every 1 s:

```
fire iff  bpm != null
      AND bpm < threshold_bpm                 (default 8, §16)
      AND now − last_reminder ≥ cooldown_s    (default 180)
      AND now − monitoring_resumed ≥ 90 s     (grace period)
      AND NOT snoozed (tray snooze, §14)
```

On fire: trigger each enabled style, insert `reminders` row, set `last_reminder`.

- **Toast** (`tauri-plugin-notification`): title `Time to blink 👁`, body `Your blink rate is {bpm}/min (target ≥ {threshold}). Look away and blink slowly a few times.` Works with Action-Center branding because the NSIS installer creates the Start-Menu shortcut/AUMID; in dev runs generic branding is acceptable.
- **Overlay** (§12): 2 s animation.
- **Sound**: `PlaySound(assets/reminder.wav, SND_FILENAME | SND_ASYNC)` via `windows` crate (`Win32_Media_Audio`). Bundle a soft ~1 s chime (generate a gentle two-tone sine in a script or use a CC0 asset; document origin in README).
- Fullscreen suppression: if `SHQueryUserNotificationState` returns a busy/fullscreen state (`QUNS_BUSY`, `QUNS_RUNNING_D3D_FULL_SCREEN`, `QUNS_PRESENTATION_MODE`) and setting `suppress_when_fullscreen = true` (default), skip overlay+sound; toast is left to Focus Assist.

---

## 12. Overlay (`overlay.rs`) — native, never a WebView

- One Win32 window, created at first use, reused after: `WS_POPUP` + ex-styles `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW` (click-through, no taskbar entry, never steals focus).
- Content: `assets/overlay_eye.png` (pre-rendered ARGB eye glyph + "blink" word-mark, 280×160 logical px, ≤ 60% max alpha), shown top-center of the primary monitor, 48 px below the top edge. DPI-aware (scale by monitor DPI).
- Animation at ~30 fps via `UpdateLayeredWindow` with per-frame global alpha: fade-in 300 ms → hold 1,200 ms → fade-out 500 ms, then hide window. Decode PNG once (`png` crate) into a premultiplied-alpha DIB.
- Thread: runs on the main thread's message loop or a dedicated overlay thread with its own pump — never on the worker thread.

---

## 13. Lifecycle, pause/resume & power hygiene (`power.rs`, `worker/mod.rs`)

Monitoring state machine: `Active ⇄ Paused(reason)` where reason ∈ `user_toggle | session_locked | idle | camera_busy | no_camera | snooze(does NOT pause monitoring, only reminders)`.

- **User toggle:** tray menu + dashboard switch. Persisted (`monitoring_enabled`) — app starts in the last state.
- **Session lock:** `WTSRegisterSessionNotification` → `WM_WTSSESSION_CHANGE` (`WTS_SESSION_LOCK/UNLOCK`): always pause/resume (camera off while locked).
- **Idle:** if `GetLastInputInfo` idle > `pause_on_idle_min` (default 5 min; 0 = disabled) → pause (reason `idle`); resume instantly on input (poll idle every 5 s while idle).
- **Battery:** per user decision — **no behavior change on battery.**
- **EcoQoS:** as §4 R4 (worker thread throttled; visible as Task Manager green leaf).
- Every pause/resume writes a `sessions` row (§15) so the dashboard timeline can render gaps with reasons.

---

## 14. Tray (`tray.rs`)

- Left-click: open (create) dashboard window. Right-click menu:
  `Monitoring ✓ (toggle)` · `Snooze reminders → 30 min / 1 h / 2 h / until I resume` · `Open dashboard` · `Start with Windows ✓ (toggle)` · `Quit`.
- Icon states (4 distinct 16/32 px icons): **active** (eye), **paused** (eye with pause bars), **camera-busy/no-camera** (eye with slash), **error** (eye with !). Tooltip: `Nictate — {bpm}/min` refreshed at most every 5 s, or state description.
- Autostart: `tauri-plugin-autostart` (HKCU Run). **Re-assert the registry value on every launch** when the setting is on (mitigates plugins-workspace bug #771).
- Single instance: `tauri-plugin-single-instance` registered **before** any other plugin; second launch focuses/creates the dashboard.

---

## 15. Persistence (`db.rs`) — SQLite via `rusqlite` (bundled), WAL mode

`%LOCALAPPDATA%\Nictate\nictate.db`; all timestamps = Unix ms UTC (INTEGER).

```sql
CREATE TABLE schema_version(v INTEGER NOT NULL);
CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);          -- JSON values
CREATE TABLE blink_events(ts INTEGER PRIMARY KEY, duration_ms INTEGER NOT NULL);
CREATE TABLE minute_stats(
  minute_ts INTEGER PRIMARY KEY,          -- floor to minute
  blinks INTEGER NOT NULL,
  face_present_s REAL NOT NULL,
  monitored_s REAL NOT NULL);
CREATE TABLE sessions(                    -- monitoring segments
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  start_ts INTEGER NOT NULL, end_ts INTEGER,
  end_reason TEXT);                       -- user_toggle|session_locked|idle|camera_busy|no_camera|quit
CREATE TABLE reminders(ts INTEGER PRIMARY KEY, styles TEXT NOT NULL, bpm REAL NOT NULL);
CREATE TABLE events(ts INTEGER, kind TEXT, detail TEXT);                   -- device switch, fallback, errors
```

- Retention: purge `blink_events` older than 90 days and `events` older than 30 days, daily at first write after 03:00 local. `minute_stats` kept forever (~21 MB/year worst case — acceptable; expose "Delete all history" button in Settings).
- Writes are batched: blink events immediately (they're rare); minute_stats once/min; never per frame.

---

## 16. Settings (all persisted; defaults ↦ shipped values)

| Key | Type / range | Default |
|---|---|---|
| `monitoring_enabled` | bool | true |
| `camera_id` | `"auto"` \| MSMF symbolic link | `"auto"` |
| `camera_conflict_policy` | `"pause"` \| `"share"` | `"pause"` |
| `analysis_fps` | 5–30 | 15 |
| `inference_device` | `"auto"` (AUTO:NPU,CPU) \| `"cpu"` \| `"npu"` | `"auto"` |
| `threshold_bpm` | 4–20 | 8 |
| `cooldown_s` | 60–1800 | 180 |
| `reminder_toast` / `reminder_overlay` / `reminder_sound` | bool each | true / true / false |
| `suppress_when_fullscreen` | bool | true |
| `sensitivity` | −1.0…+1.0 (slider) | 0 |
| `pause_on_idle_min` | 0–60 (0 = off) | 5 |
| `autostart` | bool | true (asked once on first run) |
| `theme` | `"system"` \| `"light"` \| `"dark"` | `"system"` |

---

## 17. Dashboard UI (Vite + vanilla TypeScript + uPlot; no framework)

Pages (left nav): **Dashboard · History · Settings · Camera · About**

- **Dashboard:** big live BPM number + state ("Good ≥12" green / "Low <threshold" amber / "No data" gray `TUNABLE` bands); today's blink-rate sparkline (uPlot, minute_stats); stat tiles: today's average BPM, time below threshold, reminders today, monitoring coverage %; a 24 h timeline strip showing monitored/paused segments colored by reason.
- **History:** 7-day and 30-day charts (uPlot line: avg BPM per hour/day; bar: time-below-threshold); date-range picker; all queries via IPC, aggregate in SQL not JS.
- **Settings:** exactly §16 mapped to controls with the ranges given; instant-apply (worker hot-reloads via settings channel).
- **Camera (calibration):** camera picker; live preview ≤ 15 fps, 320×180 JPEG frames via Tauri events (§19) with detection overlay (face box, eye points, per-eye p_closed bars); live blink counter ("blink 5 times — we should count 5"); sensitivity slider with immediate visual feedback. **Preview never appears anywhere else; stops the moment the page is left (event unlisten + IPC `stop_preview`).**
- **About:** version, `device_active` (NPU/CPU), model licenses, "This app has no network capability" statement.
- Charting: uPlot only (~48 KB). Theme via `prefers-color-scheme` + manual override. Follow repo dataviz conventions if present.

---

## 18. IPC surface (`ipc.rs`) — complete list

Commands (request/response): `get_live_stats` → `{bpm, state, device_active, camera_name, today: {...}}` · `get_history(range)` → minute/hour aggregates · `get_sessions(range)` · `get_settings` / `set_settings(patch)` (validates ranges, persists, notifies worker) · `list_cameras` · `start_preview(camera_id)` / `stop_preview` · `set_monitoring(bool)` · `snooze(minutes)` · `delete_all_history`.
Events (worker → UI, only while a window exists): `stats_tick` (1 Hz) · `preview_frame` (base64 JPEG + detection metadata, ≤ 15 Hz) · `state_changed`.

---

## 19. Calibration preview (`preview.rs`)

While active: encode the current BGR frame downscaled to 320×180 as JPEG quality 60 (`image` crate), base64, emit `preview_frame` with `{jpeg, face_bbox, eye_points, p_closed_l, p_closed_r}` scaled to preview coordinates. Hard cap 15 Hz; auto-stop after 10 min as a safety net. In-memory only (C2).

---

## 20. Alternative backend (explicitly out of v1, designed-for)

`detector.rs` sits behind trait `BlinkSignalSource { fn process(&mut self, frame: &BgrFrame) -> FrameResult }` so a **MediaPipe Face Landmarker v2 blendshape backend** (Apache-2.0, `face_landmarker.task`, 3,758,596 bytes, `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`; thresholds CLOSE_ON≈0.5/OPEN_OFF≈0.3 on `max(eyeBlinkLeft,eyeBlinkRight)`) can be added later if classifier robustness disappoints (e.g., heavy glasses glare). Do not implement in v1.

---

## 21. Testing

1. **Golden decode tests:** `tools/golden_gen.py` runs OpenCV `FaceDetectorYN` (opencv-python, input 320×192) on 5 committed synthetic/CC0 face images; commit outputs as JSON fixtures. Rust unit test: our YuNet decode on identical letterboxed inputs matches boxes/landmarks within 1 px, scores within 1e-3.
2. **Classifier sanity test:** committed open-eye/closed-eye 32×32 fixtures → assert `p_closed` < 0.3 / > 0.7.
3. **Blink state-machine unit tests:** synthetic `p` sequences — normal blink, double blink inside refractory, long closure (no blink), flicker around 0.5 (hysteresis holds), face gap reset.
4. **BPM/reminder unit tests:** insufficient-coverage → null; cooldown & grace honored; snooze honored.
5. **DB tests:** migrations from empty; retention purge; minute rollup correctness.
6. Golden tests run in CI (`cargo test`); no test touches a real camera (capture behind trait, fake source in tests).

## 22. Risks & mandated mitigations

| Risk | Mitigation (mandatory) |
|---|---|
| `storage.openvinotoolkit.org` unreachable someday | Both ONNX files vendored in-repo at project start; hashes verified in `prepare_models.py`. |
| YuNet decode ported wrong | §21 golden tests vs OpenCV reference — gate merge on them. |
| nokhwa/MSMF format quirks on specific cameras | `CaptureBackend` trait + §7 format ladder + direct-MF fallback backend. |
| NPU driver absent/old (needs recent Intel NPU driver; in-plugin compile needs ≥ v2565) | `AUTO:NPU,CPU` + explicit CPU recompile fallback (§8.1); `device_active` visible in UI; never crash on NPU failure. |
| openvino-rs 0.11 missing a needed property API | Acceptable to skip `cache_dir`; if device-string compile itself is blocked, drop to `openvino-sys`/C API for that call. |
| Classifier weak on heavy glasses/low light | Sensitivity slider (§9); calibration screen for verification; §20 backend as designed escape hatch. |
| WinUI-style RAM creep | Architecture rules R1/R2; acceptance tests below. |

## 23. Acceptance criteria (all must pass on the target laptop before "done")

1. Tray-only + monitoring active for 1 h: **RSS < 80 MB** (target 60), **avg CPU < 5%** of one core (Task Manager / `typeperf`), green-leaf EcoQoS badge visible.
2. Dashboard closed ⇒ **no `msedgewebview2.exe` children of the app remain** (Process Explorer).
3. 1 h soak: **zero network connections** (`netstat -b` filtered to the process; also `cargo deny` passes with the C1 ban-list).
4. Blink accuracy self-test: 5 min at normal posture, manually count blinks on simultaneous phone video; app-vs-truth **recall ≥ 90%, precision ≥ 90%**; repeat with glasses if available (record result either way).
5. NPU: with `inference_device=auto` on the Core Ultra 7, About shows NPU active (and Windows Task Manager NPU graph shows activity); with driver disabled or `cpu` forced, app behaves identically (silent fallback, `events` row logged).
6. Reminders: threshold 20 + cooldown 60 s → reminder fires within 70 s of sustained low rate, repeats on cooldown, respects snooze and grace; all three styles verified.
7. Camera: unplug external cam mid-run → auto-switch + toast; occupy camera with the Windows Camera app → `pause` policy pauses and auto-resumes; lock screen → pauses; idle 5 min → pauses, instant resume on input.
8. Kill the process; relaunch → history intact, settings intact, autostart intact.
9. Installer (NSIS via `tauri build`): per-user install, no admin, Start-Menu shortcut, branded toast works from installed build; uninstall leaves no running process (DB may remain, documented).

## 24. Milestones

- **M1 Scaffold:** Tauri v2 app named Nictate; single-instance; tray with all menu items (stubs); settings table + typed struct; autostart; destroy-on-close dashboard shell with nav; CI (`fmt`, `clippy -D warnings`, `test`, `cargo deny`).
- **M2 Vision core:** capture (§7) + OpenVINO CPU inference (§8, device `"cpu"`) + blink machine (§9) + BPM (§10) + SQLite writes (§15). Golden tests green. Console/log proof of counted blinks.
- **M3 NPU:** device selection (§8.1), `AUTO:NPU,CPU`, fallback path, `device_active` IPC; measure and record CPU-vs-NPU wattage/latency on the target machine in `README` (benchmark_app + Task Manager).
- **M4 Reminders:** engine (§11), toast, overlay (§12), sound, snooze, fullscreen suppression.
- **M5 Dashboard:** all five pages, uPlot charts, calibration preview (§19), settings hot-apply.
- **M6 Hardening:** power hygiene (§13), camera-busy/switch flows, retention, packaging (NSIS + DLL bundling §6.3), full acceptance run (§23).

Each milestone ends with a code review against this PRD and general Rust/TS best practices (performed by the orchestrating model), and all tests green.

## 25. Dependency manifest (exhaustive — C3 gate)

**Rust:** `tauri = 2`, `tauri-plugin-single-instance`, `tauri-plugin-notification`, `tauri-plugin-autostart` (all v2 line, MIT/Apache) · `openvino = 0.11` (Apache-2.0) · `nokhwa = 0.10.11` feat `input-msmf` (Apache-2.0) · `rusqlite` feat `bundled` (MIT) · `windows` (MIT/Apache; features: `Win32_System_Threading`, `Win32_System_RemoteDesktop`, `Win32_UI_WindowsAndMessaging`, `Win32_Graphics_Gdi`, `Win32_Media_Audio`, `Win32_UI_Shell`, `Win32_System_Registry`, `Win32_UI_Input_KeyboardAndMouse`) · `crossbeam-channel` (MIT/Apache) · `serde`/`serde_json` (MIT/Apache) · `png` (MIT/Apache) · `image` (MIT — JPEG encode only) · `tracing` + `tracing-appender` (MIT, rotating file log in `%LOCALAPPDATA%\Nictate\logs`, 5 MB cap) · `anyhow`/`thiserror` (MIT/Apache).
**JS:** `vite` (MIT), `typescript` (Apache-2.0), `uplot` (MIT). **Nothing else without updating this table.**
**Explicitly forbidden:** any HTTP/socket crate, `tauri-plugin-updater`, `tauri-plugin-http`, telemetry/crash-reporting SDKs, Electron, Python runtime, InsightFace models, GPL/AGPL code (Slint GPL tier included), `face_detection_yunet_2026may.onnx`.
