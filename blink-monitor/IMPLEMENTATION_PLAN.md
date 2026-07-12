# Nictate — Implementation Plan (Phases 0–7)

**For:** Claude Opus 4.8. **Authority:** [`PRD.md`](./PRD.md) v1.1 defines every behavior; this plan defines build order, exact file contents, and per-phase gates. If this plan and the PRD ever disagree, the PRD wins and the disagreement must be reported, not resolved silently.

**Ground rules**
1. Zero improvisation: every constant, string, and format is in the PRD or this plan. If something is genuinely unspecified, STOP and report it — do not decide.
2. All `TUNABLE` constants go in `src-tauri/src/consts.rs` with a one-line comment naming the PRD section.
3. Every phase ends with: `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test && cargo deny check` green, the phase gate below passed, a commit per the repo's message conventions, and a code review against the PRD (performed by the orchestrating reviewer).
4. Commit `Cargo.lock` and `ui/package-lock.json`. Never add a dependency outside PRD §25.
5. Development machine note: capture/NPU behavior can only be fully exercised on the target Windows laptop; CI (and any non-Windows dev) relies on the trait fakes (PRD §21.7).

---

## Phase 0 — Toolchain, scaffold, assets, models

**Deliverables:** building empty app (tray-less), CI, all generated assets, converted models.

1. **Toolchain:** `rust-toolchain.toml` → `[toolchain] channel = "stable"`; target `x86_64-pc-windows-msvc`. Node 22 LTS + npm for `ui/`.
2. **Scaffold:** create the repo layout of PRD §5 by hand (do not use `create-tauri-app`; the layout is nonstandard). `ui/` is a plain Vite vanilla-ts app (`npm create vite@latest ui -- --template vanilla-ts`), then remove all demo content; add `uplot` dependency.
3. **`src-tauri/tauri.conf.json`** (exact; only `version` changes later):
```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "Nictate",
  "version": "0.1.0",
  "identifier": "com.nictate.app",
  "build": {
    "frontendDist": "../ui/dist",
    "devUrl": "http://localhost:1420",
    "beforeDevCommand": "npm run dev --prefix ../ui",
    "beforeBuildCommand": "npm run build --prefix ../ui"
  },
  "app": {
    "windows": [],
    "security": {
      "csp": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'"
    }
  },
  "bundle": {
    "active": true,
    "targets": ["nsis"],
    "windows": { "nsis": { "installMode": "perUser" }, "webviewInstallMode": { "type": "skip" } },
    "resources": {
      "../models/ir": "models/ir",
      "../assets": "assets",
      "../third_party/openvino_dlls": "openvino"
    },
    "icon": ["icons/32x32.png", "icons/128x128.png", "icons/icon.ico"]
  }
}
```
   (`devUrl` is dev-only tooling and does not violate C1 — release builds serve `frontendDist` via the internal protocol.)
4. **`src-tauri/windows-manifest.xml`** (exact — Common-Controls v6 is REQUIRED for TaskDialog; do not drop it):
```xml
<?xml version="1.0" encoding="utf-8"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <dependency>
    <dependentAssembly>
      <assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls"
        version="6.0.0.0" processorArchitecture="*"
        publicKeyToken="6595b64144ccf1df" language="*"/>
    </dependentAssembly>
  </dependency>
  <asmv3:application xmlns:asmv3="urn:schemas-microsoft-com:asm.v3">
    <asmv3:windowsSettings>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
      <longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>
    </asmv3:windowsSettings>
  </asmv3:application>
</assembly>
```
   **`src-tauri/build.rs`:**
```rust
fn main() {
    let attrs = tauri_build::Attributes::new().windows_attributes(
        tauri_build::WindowsAttributes::new().app_manifest(include_str!("windows-manifest.xml")),
    );
    tauri_build::try_build(attrs).expect("tauri-build failed");
}
```
5. **`Cargo.toml`:** exactly PRD §25 (start with `tauri`, `tauri-build`, plugins, `serde*`, `anyhow`, `thiserror`, `tracing*`; add the others in the phase that uses them — the manifest table is the ceiling, not a requirement to pre-add).
6. **`deny.toml`** (exact):
```toml
[licenses]
allow = ["MIT", "Apache-2.0", "Apache-2.0 WITH LLVM-exception", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Zlib", "Unicode-3.0", "MPL-2.0", "CC0-1.0", "BSL-1.0", "OpenSSL"]
[bans]
deny = [
  { name = "reqwest" }, { name = "hyper" }, { name = "ureq" }, { name = "curl" },
  { name = "tauri-plugin-http" }, { name = "tauri-plugin-updater" },
]
[advisories]
version = 2
```
   (If a transitive license outside the allow-list appears, STOP and report — do not extend the list silently.)
7. **CI `.github/workflows/ci.yml`:** `windows-latest`; steps: checkout, install stable Rust + `cargo-deny`, Node 22, `npm ci --prefix ui`, `npm run build --prefix ui`, then `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test`, `cargo deny check` (all in `src-tauri/`). No OpenVINO, no camera in CI.
8. **Models:** download both ONNX files per PRD §6.1 into `models/`, verify hashes, run `tools/prepare_models.py` (write it per PRD §6.2 with hash verification that fails loudly), commit `models/` including `ir/`.
9. **OpenVINO DLLs (dev machine, one-time):** download the official "OpenVINO Runtime 2026.2.x Windows x64" archive from Intel's OpenVINO download page; copy the seven files of PRD §6.3 into `third_party/openvino_dlls/` (gitignored). Add a tiny `xtask`-style copy step (or documented `robocopy` command in README) that mirrors them to `src-tauri/target/debug/openvino/` for `tauri dev`.
10. **`tools/gen_assets.py`:** generates and commits: (a) `assets/overlay_eye.png` — 280×160 rounded-rect pill, dark translucent background (#101418 at 55% alpha), centered white eye glyph (two arcs + circle) and the word "blink" beneath, max alpha 60%; (b) `assets/reminder.wav` — 48 kHz 16-bit mono, two soft sine tones 660 Hz then 880 Hz, 180 ms each, 60 ms gap, 20 ms fade-in/out per tone, peak −12 dBFS; (c) the 5 tray icons (PRD §14) as 16 px + 32 px ICO/PNG: eye outline; eye + pause bars; eye + open-padlock badge; eye + slash; eye + "!" — monochrome, white-on-transparent with a dark outline so both light/dark taskbars work; (d) app icons `32x32.png`, `128x128.png`, `icon.ico`. Pillow only; deterministic output (no random seeds/dates).

**Gate 0:** `cargo build` succeeds with the manifest embedded (dump with `mt.exe -inputresource:nictate.exe -out:m.xml` and verify both the Common-Controls and dpiAwareness blocks); CI green on a pushed branch; `prepare_models.py` re-run is idempotent; all assets render (open PNGs, play WAV).

---

## Phase 1 — App shell: tray, lifecycle, settings, DB

**Deliverables:** tray app with dashboard shell, settings, DB, logging, first-run; no camera/inference yet.

1. `consts.rs`: every `TUNABLE` from PRD §§8–11 (values exactly as PRD).
2. `db.rs`: open/create at `%LOCALAPPDATA%\Nictate\nictate.db` (create dir); `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;` schema v1 DDL in one transaction (PRD §15); crash-recovery UPDATE (PRD §13) at startup; retention purge fn; the two-connection model (PRD §4): `open_rw()` (worker) and `open_ro()` (managed state, `OpenFlags::SQLITE_OPEN_READ_ONLY`).
3. `settings.rs`: `struct Settings` mirroring PRD §16 with `serde` (JSON per key in the table); `load(conn)`, `validate_patch(map) -> Result<Settings, IpcError>` (atomic; ranges exactly §16), `save(conn, &Settings)` in one transaction.
4. `main.rs` bootstrap order (exact): tracing init (daily rotation in `%LOCALAPPDATA%\Nictate\logs`, `max_log_files(7)`) → single-instance plugin (**first**; callback focuses/creates dashboard) → autostart plugin (re-assert if `settings.autostart`) → notification plugin → DB init + crash recovery → managed state (`SnapshotHandle`, `Sender<WorkerCmd>`, RO connection) → tray → power thread (stub this phase) → worker thread (stub loop) → EcoQoS process call (PRD §4 R4) → `RunEvent::ExitRequested → api.prevent_exit()`; tray Quit path per PRD §4 R1.
5. `tray.rs`: menu + 5 icon states + tooltip from `LiveSnapshot` (PRD §14); dashboard creation `WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))` 1100×720 / min 900×600; `CloseRequested` never prevented; R4 throttling toggle on window create/destroy.
6. `ipc.rs`: implement `get_settings`, `set_settings`, `get_live_stats` (stub snapshot), `set_monitoring`, `snooze`, `delete_all_history`; register all commands now with `todo!()`-free stubs returning typed errors for unimplemented ones (`{error:{reason:"not_implemented"}}`).
7. First-run flow per PRD §13; `ui/` minimal shell: nav + empty pages + first-run view with the autostart question and privacy statement ("Nictate has no network capability. Camera frames never leave your device or touch disk.").

**Gate 1:** app runs tray-only; dashboard opens/closes with zero residual `msedgewebview2.exe`; settings persist and hot-validate; first run shows once; kill/relaunch closes dangling session as `crash`; logs rotate; RSS tray-only < 30 MB at this phase.

---

## Phase 2 — Vision core on CPU

**Deliverables:** real blink counting on CPU; all §21 unit tests.

1. Add crates: `openvino` (runtime-linking), `nokhwa =0.10.11`, `crossbeam-channel`, `parking_lot`, `windows` (Phase-relevant features), `png`, `image`, `base64`, `rusqlite` already present.
2. `worker/capture.rs`: `trait CaptureBackend { fn open(&mut self, id:&CameraId, ladder:&[FormatReq]) -> Result<()>; fn frame_into(&mut self, buf:&mut RgbBuf) -> Result<FrameMeta>; fn close(&mut self); fn enumerate() -> Vec<CameraInfo>; }` + `NokhwaBackend` per PRD §7 (ladder, software pacing, decode_image_to_buffer, device-identity rule, access-denied classification). Fake backend for tests feeds PNG sequences.
3. `worker/detector.rs`: DLL dir resolution + `SetDllDirectoryW` (§6.3); `Core::new()`; CPU-only compile this phase (`DeviceType::CPU` + the two `set_property` calls); preallocated tensors; letterbox (generalized, fused BGR swap); YuNet decode + NMS exactly PRD §8.2; eye crops §8.3; classifier §8.4 with the softmax sum-check.
4. `worker/blink.rs` + `worker/stats.rs`: state machine (§9), ring buffer + 1 Hz BPM + band (§10), per-calendar-minute accumulator → `minute_stats` rows incl. paused minutes; blink writes.
5. `worker/mod.rs`: the real loop — pacing, detector cadence (`DETECTOR_CADENCE=6`), search mode (2 fps when no face > 10 s), `LiveSnapshot` writes, `WorkerCmd` handling for settings/monitoring.
6. `tools/golden_gen.py` + fixtures (PRD §21.1/21.2); Rust tests §21.1–21.7 for everything in this phase.
7. Wire `get_live_stats` + tray tooltip to real data.

**Gate 2:** on the dev laptop, console/log shows counted blinks matching a quick manual check (~10 deliberate blinks → 10 ± 1); golden tests green in CI; steady-state CPU at 15 fps < 5% of one core (Task Manager); no per-frame allocations (verify with a debug counter or heaptrack-equivalent spot check).

---

## Phase 3 — NPU

1. Implement PRD §8.1 device selection exactly (two-step, properties on Core per device, cache dir `%LOCALAPPDATA%\Nictate\ovcache`, runtime-error one-shot CPU recompile, `device_active` in snapshot + About).
2. `inference_device` setting honored end-to-end (`auto`/`cpu`/`npu`; forced-`npu` failure ⇒ PRD §6.3 error state).
3. **Measure on the target laptop** and record in README: per-stage latency CPU vs NPU (log timestamps around infer), package power via Task Manager/HWiNFO during 10-min runs of each, RSS in both modes. If NPU-mode RSS > 80 MB, the §8.1 NPU-only design failed — STOP and report (do not ship AUTO as a workaround without review).

**Gate 3:** acceptance §23.5 behaviors demonstrated on the target machine; measurements recorded; RSS/CPU budgets hold in both device modes.

---

## Phase 4 — Reminders

1. `worker/reminders.rs` per PRD §11 (fire condition verbatim; snooze deadline model; `reminders` writes).
2. `notify.rs`: toast via plugin builder; sound via `PlaySound` flags exactly §11; `SHQueryUserNotificationState` behind `SystemProbe` trait.
3. `overlay.rs` per PRD §12 (dedicated thread, window class `NictateOverlay`, `WM_APP+1` trigger, premultiplied DIB from `overlay_eye.png`, 300/1200/500 ms envelope at ~30 fps, `GetDpiForWindow` scaling, primary monitor top-center +48 px).
4. Tray snooze submenu wiring; §21.4 unit tests.

**Gate 4:** acceptance §23.6 demonstrated (threshold 20/cooldown 60 flow, all three styles, snooze, grace, fullscreen suppression with a fullscreen video test).

---

## Phase 5 — Camera Guard + power states

1. `power.rs`: hidden non-visible window (NOT message-only) on its own thread; `WTSRegisterSessionNotification(NOTIFY_FOR_THIS_SESSION)`; `GetLastInputInfo` 5 s timer; state transitions with the PRD §13 precedence order and §7.1 hold matrix (idle keeps device open, grabbing/discarding at 2 fps).
2. `guard.rs`: watcher thread (`RegNotifyChangeKeyValue`, subtree, diff snapshot, own-exe exclusion via `#`-encoded path compare); alert routing rules (Active vs released vs locked — PRD §7.1); TaskDialogIndirect on the main thread via `run_on_main_thread` (buttons + sharing-anomaly appendix text verbatim); release/reclaim state machine (timers, 30 s recheck, 5 s×12 reclaim retry); `events(kind='camera_guard')` writes.
3. `pause`/`share` policies (PRD §7); camera switch/return logic + `last_used_camera`; access-denied path (§7) with 30 s retry.
4. Tray Release submenu; `release_camera`/`reclaim_camera`/`get_guard_events` IPC; `guard_alert` event.

**Gate 5:** acceptance §23.7 + §23.7a demonstrated end-to-end on the target machine, including the lock/unlock deferred alert and the idle-hold LED check.

---

## Phase 6 — Dashboard UI

1. `db.rs`: the named query consts for `get_history` (minute/hour/day per PRD §18, local-offset day bucketing), `get_sessions`, `get_guard_events`, today-aggregates for the snapshot.
2. `ipc.rs`: finish every command + event with the exact PRD §18 shapes.
3. `ui/`: Dashboard (band-colored BPM, 5-min-SMA sparkline, four tiles, 24 h timeline strip), History (7d hourly line + threshold refline; 30d daily bars + avg line), Settings (1:1 §16, inline IPC errors), Camera (picker, policy with honest-limits copy, preview canvas with overlay drawing from `preview_frame` metadata, blink counter, sensitivity slider), About (version, `device_active`, licenses, no-network statement). uPlot only; `prefers-color-scheme` + manual theme override; no other JS deps.
4. `preview.rs` per PRD §19 with start/stop lifecycle and the camera-unavailable error.

**Gate 6:** every page functional against real data; preview overlays track the face at ≤ 15 Hz with dashboard-open CPU < 15% of one core; closing the dashboard returns to Gate-1 idle footprint; uPlot payloads ≤ 1,440 points verified for all ranges.

---

## Phase 7 — Packaging + full acceptance

1. `tauri build` → NSIS; verify resources land (`models/ir`, `assets`, `openvino/`) and `SetDllDirectoryW` resolves in the installed layout; installed-build branded toast; autostart; first-run.
2. README: dev setup (OpenVINO archive step, model prep), SmartScreen note, privacy/guard honest-limits section (PRD §7.1 verbatim points), Phase-3 measurement table, model/license attributions.
3. Run the complete PRD §23 checklist (1–10) on the target laptop; fix and re-run until all pass; bump versions to 1.0.0.

**Gate 7 (ship):** all §23 items pass and are recorded (numbers, screenshots where relevant) in `ACCEPTANCE.md`; final code review of the whole tree against PRD v1.1.

---

## Reviewer checklist (applied at every phase gate)

1. No dependency outside PRD §25; `deny.toml` untouched or PRD updated first.
2. No socket/network code anywhere (grep for `TcpStream`, `connect(`, `http`, `fetch(` in ui except tauri IPC).
3. All constants in `consts.rs`; no magic numbers in logic files.
4. Hot path allocation-free; no busy-wait loops; every thread blocks on an event/channel/timer.
5. Every DB write path uses the worker connection; IPC only reads.
6. UI copy matches PRD strings verbatim (guard limits, reminder text, settings notes).
7. Error paths: no `unwrap()`/`expect()` outside startup; failures land in `events` + tray state, never a crash.
8. Tests added for the phase's logic; fakes used, no device access in tests.
