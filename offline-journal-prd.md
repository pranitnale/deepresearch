# PRD — "Mindvault" (working title): A Fully Offline, Privacy-First Personal Journaling App

**Base:** Fork of [Notesnook](https://github.com/streetwriters/notesnook) (GPLv3)
**Author:** Prepared from a code-level analysis of the Notesnook monorepo (web v3.4.3 / mobile v3.4.5 / core v8.1.3, cloned 2026-07-12) plus targeted research on LAN P2P sync, Samsung S Pen input, and the self-hostable Notesnook sync server.
**Date:** 2026-07-12
**Status:** Draft for review

---

## 1. Vision

A journaling app for exactly one person and three devices — a Windows PC, a Samsung Galaxy S23 Ultra, and a Galaxy Tab S9 — that **never connects to the internet**. All data lives encrypted on the user's own devices, syncs automatically and quickly whenever two devices share the same Wi-Fi network (no hub, no cloud, no interaction), supports handwriting with the S Pen, and hides a "secret" tier of notes behind a vault that is invisible in normal use. When the user later runs their own VPS, the same data layer must be able to sync through it by changing configuration — not architecture.

**Design principle, in priority order:** Privacy > Correctness (never lose a journal entry) > Convenience > Features.

## 2. Goals and Non-Goals

### Goals
- **G1 — Zero internet.** The app makes no network connection except to explicitly paired personal devices on the local network (and, in a later phase, to a user-configured self-hosted endpoint).
- **G2 — Everything encrypted at rest.** Databases, note content, attachments, sync queues/cursors, and any exported change files are never written to disk in plaintext, on any platform.
- **G3 — App lock.** The whole app is locked behind a password/PIN + biometrics; the lock is cryptographic (wraps the database key), not cosmetic.
- **G4 — Hidden vault.** Vault notes are invisible in every normal view, search, and count until the vault is unlocked; a visible "Vault" section exists but reveals nothing while locked.
- **G5 — Serverless LAN sync.** Any two of the three devices sync automatically when on the same Wi-Fi, with no user interaction, no always-on hub (phone↔tablet must sync with the PC off), and near-real-time latency when both apps are open.
- **G6 — S Pen journaling.** Handwrite entries with the S Pen on the S23 Ultra / Tab S9 — either converted to text on-device and offline, or kept as freehand ink with conversion turned off entirely (user's choice, per entry).
- **G7 — Future VPS path.** The sync layer is a pluggable endpoint; pointing it at a self-hosted server later is a configuration change.
- **G8 — Keep everything Notesnook already does well:** rich-text editor, notebooks/tags/colors, reminders, attachments, full-text search, note history, backups.

### Non-Goals (explicit)
- **Multi-user, sharing, collaboration, publishing.** Monographs (public publishing) are removed.
- **Real-time concurrent editing** of the same note on two devices (CRDT). Conflicts are rare for one person; the existing conflict-flag + manual resolution is sufficient.
- **Custom handwriting-recognition model / "self-learning" ink engine.** Research confirmed no off-the-shelf, offline, personalizable recognizer exists beyond what Samsung ships on-device. We ride Samsung's engine (which does adapt to the user's writing over time) rather than building one. Revisit only if Samsung's engine proves inadequate.
- **iOS support.** Devices are Windows + two Samsung Androids.
- **App-store distribution.** Personal sideloaded APK + local desktop build.

## 3. Why Fork Notesnook (Decision Record)

Code-level analysis found Notesnook unusually well-suited as the base — the alternative ("borrow parts, build fresh") is strictly more work for less reliability:

1. **Local-only operation is already a supported mode.** `database.setup()` runs with no account; `Sync.start()` returns immediately if no user is logged in (`packages/core/src/api/sync/index.ts:183`). Never logging in already yields a fully functional offline app.
2. **Encryption at rest already exists on every platform.** The entire SQLite database is encrypted: `better-sqlite3-multiple-ciphers` on desktop (`apps/desktop/src/api/sqlite-kysely.ts`), encrypted `wa-sqlite` on web (`apps/web/src/common/db.ts:74`), SQLCipher-keyed `react-native-quick-sqlite` on Android (`apps/mobile/app/common/database/index.ts`). Note content and attachments are additionally encrypted with XChaCha20-Poly1305 (libsodium), keys derived with Argon2 (`packages/crypto/src/encryption.ts`). Attachments are chunked encrypted files, never plaintext on disk.
3. **Cloud coupling is loose and centralized.** All server URLs flow through one constants object (`packages/core/src/utils/constants.ts`) overridable at runtime via `db.host()`; both apps already ship a self-hosted-server settings screen. No telemetry or analytics SDK exists anywhere in the codebase. The only hardcoded phone-home outside this layer is the desktop auto-updater (`apps/desktop/src/utils/autoupdater.ts:26`).
4. **App lock already exists** on all platforms, and on Android it re-encrypts the database key with an Argon2-derived key from the lock password (`apps/mobile/app/common/database/encryption.ts`) — cryptographically real.
5. **Vault (per-note encryption) already exists** (`packages/core/src/api/vault.ts`); we only need to add the "hidden" behavior.
6. **The sync engine's design is P2P-friendly.** Sync items are opaque per-record encrypted blobs merged by last-write-wins timestamps (`packages/core/src/api/sync/merger.ts`) — the merge logic works peer-to-peer unchanged; only the transport (SignalR client→server) must be replaced.
7. **License:** GPLv3. A personal fork is unproblematic; if ever distributed, source must be published.

**Main gaps to build:** (a) LAN P2P transport, (b) hidden vault, (c) S Pen input path, (d) cloud-strip hardening. Codebase is ~225k lines TS/TSX but well-modularized; the touched surface is small.

## 4. Users and Devices

| Device | OS | Role |
|---|---|---|
| PC | Windows 11, Electron desktop build | Long-form writing, archive, backup origin |
| Galaxy S23 Ultra | Android (One UI 5.1+), sideloaded APK | Capture on the go, S Pen quick notes |
| Galaxy Tab S9 | Android (One UI 5.1+), sideloaded APK | Primary handwriting/journaling surface |

Single user. All devices trusted after one-time pairing. Threat model: (1) data must never leave the devices or the paired LAN links; (2) a person with casual access to an unlocked device must not see that secret notes exist; (3) a person with the device but not the app-lock secret must not read anything (encrypted at rest).

## 5. Functional Requirements

### F1 — Offline-Only Operation (Cloud Strip)

**Requirement:** The app must make zero network calls to non-paired hosts, verifiable by running it behind a packet capture.

Work items (all locations code-verified):

| # | Item | Where | Effort |
|---|---|---|---|
| F1.1 | Remove/neutralize account & login UI; app boots straight into local-only mode | `apps/web/src/dialogs/`, `apps/mobile/app/components/auth/` | S |
| F1.2 | Point all 7 hosts (`API_HOST`, `AUTH_HOST`, `SSE_HOST`, `SUBSCRIPTIONS_HOST`, `ISSUES_HOST`, `MONOGRAPH_HOST`, `NOTESNOOK_HOST`) at empty/invalid values by default | `packages/core/src/utils/constants.ts` | XS |
| F1.3 | Stub desktop auto-updater (the one hardcoded URL outside the hosts layer) | `apps/desktop/src/utils/autoupdater.ts:26-28` | XS |
| F1.4 | Remove mobile update check (`react-native-check-version`) | `apps/mobile` deps | XS |
| F1.5 | Remove subscriptions/IAP/pricing (Paddle, `react-native-iap`, `subscriptions.ts`, `pricing.ts`, `offers.ts`, `circle.ts`) — most tangled strip, but gated and non-blocking | `packages/core/src/api/`, both app UIs | M |
| F1.6 | Remove monograph publishing (`packages/core/src/api/monographs.ts`, publish UI in both apps) | see left | S |
| F1.7 | Remove bug-report uploader (`packages/core/src/api/debug.ts`) and announcements/version fetch (`packages/core/src/api/index.ts:483-487`) | see left | XS |
| F1.8 | Android manifest: keep `INTERNET` permission (needed for LAN sockets) but add a debug-build network-security config restricting cleartext to RFC1918 ranges; verify with mitmproxy that no other traffic exists | `apps/mobile/native/android/` | S |
| F1.9 | Acceptance test: 24h run on all 3 platforms behind packet capture → only mDNS + paired-peer traffic observed | — | S |

Note: telemetry removal is **not** a work item — the codebase ships no analytics SDK (verified by dependency and source grep).

### F2 — Encryption at Rest (Invariant)

**Requirement:** every byte the app persists is encrypted.

- **Already true (keep + verify in CI/tests):** SQLite DB encrypted on all platforms; note content XChaCha20-Poly1305; attachments chunked-encrypted (`packages/core/src/database/fs.ts`, `@notesnook/streamable-fs`, `react-native-blob-util` cache of encrypted chunks); FTS index lives inside the encrypted DB.
- **New surfaces this PRD adds — must inherit the invariant:**
  - P2P sync payloads: already ciphertext (sync items are `Cipher` blobs encrypted with the data key before leaving the collector — `packages/core/src/api/sync/collector.ts`); transport adds TLS on top.
  - Per-peer sync cursors/pairing keys: store in the encrypted SQLite `kv`/`config` tables, or Android Keystore / Windows DPAPI via the existing key-store abstractions — never plaintext files.
  - Any debug logs must not contain note plaintext (audit `packages/logger` usage in new code).
- **Acceptance:** open every file the app writes with a hex viewer / `strings` — no journal plaintext anywhere; DB fails to open without key.

### F3 — App Lock

**Requirement:** PIN/password + biometric lock on app open and on resume after timeout.

**Status: already implemented — adopt, don't build.**
- Android: `apps/mobile/app/components/app-lock/index.tsx` + `apps/mobile/app/services/biometrics.ts` (fingerprint) + `applock-password` dialog; the lock password re-encrypts the DB key (Argon2, `NOTESNOOK_APPLOCK_KEY_SALT`) and removes the plaintext key from Keychain.
- Desktop: `apps/web/src/views/app-lock.tsx` + `apps/web/src/interfaces/key-store.ts` (password or WebAuthn security key wrapping the WebCrypto-held DB key).
- **Work item:** make app lock mandatory in onboarding (currently optional), default lock-on-background timeout ≤ 1 min on mobile. Effort: XS.

### F4 — Hidden Vault (Secret Notes)

**Requirement (user's chosen semantics):** vault notes are excluded from every normal view, search, and count. A visible "Vault" section exists in the UI, but shows nothing (and leaks no counts) until unlocked with the vault password. After unlock, vault notes appear in the Vault section (and remain excluded from normal lists). Auto-relock on timeout (existing `getVaultLockAfter`) and on app restart (vault password is memory-only — already true).

**Implementation (code-verified plan; ~110–140 LOC across 8–9 files):**

All note-list reads funnel through two core query builders — inject one "not in vault unless unlocked" SQL predicate at each:
1. Collection getters in `packages/core/src/collections/notes.ts` (`all`, `favorites`, `pinned`, `archived`, `conflicted`) — wrap their `createFilter` callbacks.
2. `RelationsArray.selector` in `packages/core/src/collections/relations.ts:275` (notebook/tag/color context lists) — inject **only** when the target is notes and the querying reference is *not* the vault itself (that carve-out is what makes the Vault section work).
3. Search: add vault-note IDs to the existing `excludedIds` mechanism in `packages/core/src/api/lookup.ts` (4 functions) — the same pattern already used to exclude trashed notes. FTS already indexes locked content as an empty string; this additionally hides titles.
4. Counts: `packages/core/src/collections/notebooks.ts` `totalNotes()`/`notes()`.

The predicate reuses the correlated relations subquery already built for the `locked:` search filter (`lookup.ts:190-193`) — it uses the relations index and avoids the 200-parameter SQL limit that an ID-list approach would hit. Gate on `db.vault.unlocked` (existing in-memory state, `packages/core/src/api/vault.ts`) plus a new cached `defaultVaultId` in `collections/vaults.ts`. Wire list refreshes to the existing `EVENTS.vaultLocked/vaultUnlocked/vaultAutoLocked` events (web `stores/note-store.ts` + `app-store.ts`; mobile `hooks/use-app-events.tsx` + `stores/use-notes-store.ts`).

**Side channels (checklist from code audit):**
- Notebook/sidebar counts: leak today → covered by item 4 above.
- Mobile home-screen note widget: purge pinned notes that enter the vault on lock (`apps/mobile/app/services/note-preview-widget.ts`); do not filter the single-note accessor `db.notes.note(id)` itself (needed to open vault notes).
- Reminders: a reminder linked to a hidden note still shows its own title in the reminders list. **Decision: block creating reminders on vault notes** (simplest, no leak) — v1 policy.
- Export-all: keep `db.notes.exportable` unfiltered (it's reused by search sorting — filtering it would corrupt results); instead require vault unlock in the export UI.
- Note history: already cleared when a note is locked. Sync and full backup intentionally bypass the filtered paths — hidden notes still sync and back up (required).

**Acceptance:** with vault locked — no vault note appears in any list/search/count/widget; the Vault section shows only an unlock prompt with no count. After unlock — notes appear in Vault section only. Restart app → locked again.

### F5 — LAN P2P Sync (the core new engineering)

**Requirement:** any two of the three devices, on the same Wi-Fi, discover each other and sync automatically with zero interaction after a one-time pairing. No hub required; phone↔tablet syncs with the PC off. Latency: seconds when both apps are foregrounded; best-effort otherwise. Later, the same data layer can sync through a self-hosted server instead/additionally.

**Chosen architecture (decision from comparative research — see §8 Alternatives):** **Embedded peer endpoint** — keep Notesnook's collector/merger, replace the SignalR transport with a small LAN protocol.

**Why this wins:** sync items are already opaque encrypted blobs with per-item `dateModified` LWW merging plus conflict-flagging for note content (`packages/core/src/api/sync/merger.ts`) — that merge logic is symmetric and works peer-to-peer unchanged. Every building block is actively maintained (verified July 2026), and no rewrite of the encryption or data model is needed. Alternatives were rejected on maintenance risk or model mismatch (§8).

**Design:**

1. **`SyncEndpoint` abstraction (the future-VPS seam).** Define in `packages/core`: `pull(sinceCursor) → SyncTransferItem[]`, `push(items)`. Implementations: `LanPeerEndpoint` (Phase 3) and `RemoteServerEndpoint` (Phase 5, wrapping the existing SignalR client or a thin relay). Switching to a VPS later = enabling the second endpoint in settings.
2. **Discovery:** DNS-SD service `_mindvault._tcp` on the LAN. Android: `react-native-zeroconf` (active, v0.14.0, Dec 2025). Windows/Electron: `bonjour-service` (active, pure-JS). Each device advertises `{deviceId, port}` and browses for peers.
3. **Transport:** TLS over TCP. Android server socket via `react-native-tcp-socket` (active, v6.4.1, Jan 2026); Electron uses Node `https`/`ws` natively. Protocol: `GET /pull?since=<ts>` streams `collector.collect()` batches; `POST /push` feeds `merger.mergeItem()`; `GET /attachment/:hash` serves content-addressed encrypted attachment chunks (replaces the S3 presigned-URL path on LAN).
4. **Per-peer cursors:** each device stores, per paired peer, the max acknowledged `dateModified` (modeled on the existing `sync/devices.ts` device-state tracking), persisted in the encrypted DB. Any pair of devices converges; transitive sync through the third device also converges (LWW is order-independent for metadata; content conflicts get flagged for manual resolution exactly as today).
5. **Pairing/trust:** one-time QR key exchange (Syncthing/Signal-style). Device A shows a QR encoding its device ID + public key; B scans, both pin each other; connections are mutually authenticated TLS thereafter. Unknown peers are refused. Note: payloads are DEK-encrypted regardless — pinning defends against junk injection, not confidentiality. The data encryption key itself is transferred once during pairing (QR or manual phrase), since there is no cloud account to derive it from.
6. **Sync triggers:** on app foreground, on Wi-Fi connect, on local DB change (debounced ~5 s, mirroring the existing `auto-sync.ts`), and periodic WorkManager wakes on Android. **Android background constraint (researched):** no 24/7 listening socket — Android 15 caps `dataSync` foreground services at 6 h/24 h, but the `connectedDevice` FGS type is exempt from that cap; use it only during active sync windows. Practical model: whichever device is in use initiates; a backgrounded device syncs opportunistically. This satisfies "quick sync when connected to the same Wi-Fi" without battery abuse.
7. **Clock skew:** LWW depends on device clocks. The existing 60 s merge threshold absorbs jitter; add a pairing-time clock-sanity check (warn if peers differ > 2 min) since NTP is unavailable offline.
8. **Windows firewall:** first run must register an inbound allow rule (private networks) for the sync port and UDP 5353 — one-time guided step in onboarding.

**Acceptance:** create a note on the phone → appears on the foregrounded tablet within ~10 s on the same Wi-Fi, PC powered off, airplane-mode-with-Wi-Fi on both (no mobile data). Edit the same note on two offline devices → conflict flagged, both versions preserved, manual resolution UI works (existing feature). Kill and restart any device mid-sync → no data loss, cursors resume.

### F6 — S Pen Input: Handwriting → Text AND Freehand Ink

**Requirement:** the S Pen supports **two modes**, switchable per entry, on the S23 Ultra / Tab S9:
- **F6a — Convert mode:** handwriting is converted to text on-device, offline, with recognition that adapts to the user's handwriting.
- **F6b — Ink mode:** conversion is off; the user writes freely in their own handwriting and the strokes are **kept as ink** — stored, encrypted, synced, and rendered on all devices like any other note content. Even without any recognition, a page of the user's own handwriting is a first-class journal entry.

Neither stock Notesnook nor its editor has any ink/drawing support (verified: no canvas/freehand/stylus extension exists anywhere in `packages/editor` or the mobile app) — F6b is net-new work.

#### F6a — Convert mode (Samsung Direct Writing)

**Chosen approach (user decision + research verification):** rely on Samsung's system-level **S Pen to text / Direct Writing** (One UI 5.1+, on-device, offline via installable language packs, with vendor-documented adaptation to the user's writing).

**Critical research finding:** Direct Writing does engage on `contenteditable` fields inside Android WebViews (it's default-on at the platform level; Samsung Keyboard must be the active IME) — so it will reach Notesnook's TipTap editor with **zero code**. However, ProseMirror-family editors have well-documented Samsung-IME composition bugs (spurious newlines, dropped characters, scroll jumps — reproduced in ProseMirror, Obsidian, and CKEditor issue trackers). There is no WebView flag that fixes this; the platform switches are already default-on.

**Therefore, two-stage plan:**
- **Stage 1 (zero code):** document setup (Samsung Keyboard as default IME, offline handwriting language pack installed, autocorrect/predictive text disabled — much of the corruption is prediction-driven) and dogfood directly in the editor for 2 weeks.
- **Stage 2 (if Stage 1 is too flaky — likely):** build a **native `EditText` handwriting capture overlay**: a React Native native view (`EditText` is the first-class, rock-solid handwriting target) summoned by an S Pen toolbar button; recognized text is inserted into TipTap at the cursor via the existing RN↔WebView command bridge (`apps/mobile/app/screens/editor/tiptap/commands.ts`). Effort: M (one native module + toolbar button + bridge call).

"Self-learning": Samsung's on-device engine adapts to the user's writing over time; corrections made in the `EditText` before insertion feed that engine. Building our own trainable recognizer stays a non-goal (§2).

#### F6b — Ink mode (keep my handwriting as handwriting)

**Turning conversion off is trivial and needs no app code:** Direct Writing is a system toggle (Settings → Advanced features → S Pen → "S Pen to text", or Samsung Keyboard's handwriting setting). Additionally, an ink canvas is not an editable text field, so the handwriting-to-text IME never triggers on it — ink mode is inherently conversion-free. For belt-and-braces, an in-app "disable handwriting-to-text" setting can call the View-level `setAutoHandwritingEnabled(false)` on the editor WebView.

**Implementation — a custom TipTap "ink" block node (recommended):**
- An `<ink>` node type in `packages/editor` rendering a canvas/SVG surface that can be inserted anywhere in a note and interleaved with text blocks (ideal journaling model: type a paragraph, handwrite a paragraph).
- Stroke capture via standard PointerEvents in the existing WebView: accept `pointerType === "pen"` only while inking (automatic palm rejection), record `(x, y, pressure, t)` per point — Chromium WebView delivers stylus pressure.
- Stroke rendering via [perfect-freehand](https://github.com/steveruizok/perfect-freehand) (MIT, ~5.4k stars, actively maintained — last release Feb 2026), which turns pressure-annotated point arrays into natural pressure-sensitive outlines rendered as SVG paths.
- **Storage:** stroke data is serialized as JSON inside the node attributes, i.e. inside the normal note-content blob. This means encryption at rest (F2), vault hiding (F4), LAN sync (F5), backups, and note history all apply to ink **automatically, with zero extra work** — ink is just content.
- Desktop/web: the same editor package renders ink read/write everywhere; on the PC the mouse can view, erase, or annotate.
- Basic tools for v1: pen (2–3 widths/colors), eraser, undo. No shape recognition, layers, or lasso — this is a journal, not a whiteboard.
- Eraser/editing granularity: per-stroke (hit-test against stroke outlines), which perfect-freehand's point model supports directly.

**Known risk — WebView ink latency:** a WebView canvas adds some pen-to-ink latency versus native low-latency drawing surfaces. Mitigations, in order: pointer event coalescing + `desynchronized` canvas hint; if still unsatisfying on the Tab S9, fall back to a **native ink view** using Google's Jetpack [androidx.ink](https://developer.android.com/jetpack/androidx/releases/ink) low-latency Ink API (purpose-built for stylus apps, though still alpha as of mid-2026) writing the same stroke-JSON format into the node via the bridge. Same storage model either way.

**Effort:** M–L (~2–3 weeks for the TipTap ink node incl. mobile toolbar; +1–2 weeks if the native low-latency fallback proves necessary).

**Acceptance (F6 combined):** (a) with the overlay (Stage 2), a handwritten paragraph lands in the note as text, offline, with no dropped characters; (b) with conversion off, a freehand handwritten page is captured with pressure, stored only inside the encrypted content blob, appears on the other devices after LAN sync, and renders identically on desktop; (c) switching between convert mode and ink mode requires no more than one tap in the editor toolbar plus the documented one-time system toggle.

### F7 — Retained Notesnook Features (regression scope)

Rich-text editor (TipTap: headings, lists, tasks, tables, code, math, images, audio, attachments), notebooks/tags/colors/favorites/pinned/archive, reminders (minus vault notes, F4), full-text search (FTS5), note version history, encrypted local backups (existing `database/backup.ts` full-backup path), import/export (Markdown/HTML/PDF where already supported), dark mode/themes (bundled only — themes marketplace is removed with the cloud strip).

## 6. Future Phase — Self-Hosted Server (VPS or Home Server)

When the user has a VPS (or wants a LAN hub as an additional always-on peer):

- **Option A (stock):** deploy `streetwriters/notesnook-sync-server` via its official docker-compose (identity, sync API, SSE, monograph, MongoDB, MinIO — ~1–2 GB RAM estimated; runs under Docker Desktop on Windows too). Caveats (researched): self-hosting is officially "alpha/unsupported"; **SMTP credentials are mandatory** (compose validation fails without them; no email-bypass switch exists) — create the account once with any working mailbox, then set `DISABLE_SIGNUPS=true`. The stock client requires a logged-in, email-confirmed account for sync (`sync/index.ts:183,120-127`); our fork will have patched this gate out for LAN P2P, so re-integrating means implementing `RemoteServerEndpoint` against the hub with a stored token.
- **Option B (lean, preferred long-term):** run our own `LanPeerEndpoint` protocol as a small always-on Node peer on the VPS/home server — the server is just a fourth "device" with a big disk. No .NET stack, no MongoDB, no SMTP, same code path. This is the natural consequence of the `SyncEndpoint` abstraction and is recommended over Option A unless stock-server compatibility matters.
- Off-LAN access to a VPS must go through WireGuard/Tailscale-style private networking — the app itself still never talks to the public internet unauthenticated.

## 7. Delivery Plan (phased, solo dev + AI tooling, Windows + Android targets)

| Phase | Deliverable | Scope | Est. effort* |
|---|---|---|---|
| **0. Build & baseline** | Both apps built from source and running (Electron on Windows; sideloaded APK), local-only by never logging in | Node 22.20.0, `npm run bootstrap`, Android Studio/JDK/Gradle toolchain; editor-mobile bundle build. Heaviest lift is the RN native-module build | 1–2 weeks |
| **1. Cloud strip** | Verified zero-network app (F1) + packet-capture acceptance | F1.1–F1.9 | 1–2 weeks |
| **2. Hidden vault + app-lock hardening** | F4 + F3 work item | ~8–9 files, ~110–140 LOC + Vault section UI | 1–2 weeks |
| **3. LAN P2P sync** | F5 end-to-end across 3 devices | `SyncEndpoint` abstraction, discovery, TLS transport, per-peer cursors, QR pairing, triggers, firewall onboarding | 4–8 weeks (the big one) |
| **4. S Pen** | F6a Stage 1 dogfood → Stage 2 overlay if needed; F6b ink block node (+ native low-latency fallback only if WebView latency disappoints) | native module + bridge; TipTap ink node + perfect-freehand | 3–5 weeks |
| **5. VPS endpoint** | §6 Option B (or A) | when VPS exists | 1–2 weeks |

*Own estimates for a solo developer working part-time with AI coding tools; Phase 3 carries the most uncertainty (Android background/network edge cases dominate).

Ship order rationale: Phases 0–2 produce a fully usable single-device (or manually-backed-up) journal early; sync risk is isolated in Phase 3; S Pen is independent and can proceed in parallel with 3.

## 8. Alternatives Considered (research-backed rejections)

| Alternative | Verdict | Reason (verified July 2026) |
|---|---|---|
| **PC as LAN hub** running stock notesnook-sync-server (zero client changes) | Rejected as primary; useful as de-risking milestone / Option A later | Structurally fails "phone↔tablet with PC off"; also drags in .NET+MongoDB+MinIO+SMTP stack |
| **cr-sqlite** (CRDT SQLite extension) | Rejected | Unmaintained — last commit Oct 2024, last release Jan 2024; unproven on encrypted DBs across Electron/RN/wasm; cell-level merging buys nothing on Notesnook's opaque encrypted content blobs |
| **Yjs / Automerge** CRDT sync layer | Rejected | Model mismatch: CRDTs need readable structured state, Notesnook stores encrypted blobs → would force a rewrite of core + crypto. LAN transports stale (y-webrtc last commit Apr 2024, needs signaling server); Automerge wasm needs RN 0.84+ (fork is on 0.82). Revisit only if collaborative editing ever becomes a goal |
| **Syncthing as transport** (app writes append-only encrypted change files; Syncthing-Fork replicates the folder) | Held as Plan B | Official Android app discontinued Dec 2024, but Catfriend1 fork is active (v2.1.2.0, Jul 2026). Zero networking code — but requires a sidecar app + manual device pairing (violates zero-interaction), scoped-storage friction, scan-bound latency. Adopt only if Phase 3's Android background story proves too painful |
| **Couchbase Lite P2P / Ditto / PowerSync / ElectricSQL / iroh / p2panda** | Rejected | Respectively: RN plugin lacks P2P; commercial/closed; server-authoritative (×2); no RN binding (Kotlin-only FFI); research-grade mobile bindings |
| **Rebuild fresh, borrowing parts** (e.g. from Joplin/other OSS) | Rejected | Notesnook already provides encrypted-at-rest storage, app lock, vault, sync collector/merger, and a mature editor; every gap identified is additive. Joplin's E2EE and vault story is weaker; nothing offers a better starting ratio of kept-vs-built |

## 9. Risks

| Risk | Sev. | Mitigation |
|---|---|---|
| Android background sync flakiness (Doze, FGS limits, NSD quirks) | **High** | `connectedDevice` FGS during sync windows only; foreground-initiated model; WorkManager wakes; Syncthing-folder Plan B kept warm |
| S Pen direct input corrupts text in ProseMirror (documented bug class) | High | Two-stage plan; the `EditText` overlay is a known-good pattern, budgeted from the start |
| WebView ink canvas latency feels worse than Samsung Notes | Med | perfect-freehand + desynchronized canvas first; native androidx.ink fallback (alpha, watch stability) writing the same stroke format; latency bar is "pleasant journaling", not art-app |
| Solo-maintained fork drifts from upstream (security fixes) | Med | Keep changes additive/behind seams (`SyncEndpoint`, vault predicate, host config); pin a fork point; cherry-pick upstream security fixes; crypto core is untouched |
| Data loss from a sync bug (worst outcome for a journal) | Med | Merger is reused, not rewritten; conflicts flag rather than overwrite; automatic daily encrypted local backups with retention on every device before Phase 3 ships; restore drill in acceptance tests |
| LWW clock skew merges the wrong direction | Low-Med | Existing 60 s threshold; pairing-time clock check; content conflicts are flagged, not silently merged |
| RN 0.82 native build toolchain pain (sodium, quick-sqlite, mmkv…) | Med | Phase 0 exists precisely to burn this down first; all modules are open-source and currently building upstream |
| Vault side-channel leak via a forgotten query path | Low | Full side-channel checklist in F4 baked into acceptance tests |

## 10. Acceptance Summary (v1 "done")

1. Packet capture on all 3 devices over 24 h shows only mDNS + paired-peer TLS traffic.
2. Every persisted file is ciphertext (spot-check with `strings`); DB unopenable without key; app lock wraps the DB key.
3. Vault locked → zero trace of secret notes anywhere in the UI or search; unlock → visible only in Vault section; relocks on restart/timeout.
4. Phone-only + tablet-only edit while apart → both converge within seconds of joining the same Wi-Fi, PC off, zero taps; same-note concurrent edits produce a resolvable conflict, never silent loss.
5. A handwritten S Pen paragraph becomes correct text in a note, fully offline; with conversion off, a freehand ink page is stored encrypted, syncs across devices, and renders on desktop.
6. Daily encrypted backup exists on each device and a restore drill succeeds.

---

*Sources: code-level analysis of the Notesnook monorepo (file references inline); maintenance status of react-native-zeroconf, react-native-tcp-socket, bonjour-service, cr-sqlite, Yjs/y-webrtc, Automerge, Syncthing/Catfriend1 fork, iroh, p2panda verified against GitHub/npm on 2026-07-12; Android FGS limits from developer.android.com (Android 15 behavior changes / FGS timeout docs); S Pen/Direct Writing behavior from Android stylus-input docs, Chromium stylus_handwriting component, AndroidPolice coverage, and ProseMirror/Obsidian/CKEditor issue trackers; notesnook-sync-server self-hosting from its README, docker-compose, and issue #20; ink-mode libraries verified 2026-07-12: perfect-freehand (github.com/steveruizok/perfect-freehand, active, Feb 2026) and Jetpack androidx.ink (developer.android.com/jetpack/androidx/releases/ink, alpha). Effort estimates and the cr-sqlite-on-encrypted-DB risk call are own assessments.*
