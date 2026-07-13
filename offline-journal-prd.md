# PRD v4 — "Mindvault" (working title): Pen-First, Fully Offline Personal Journal
## Implementation-Grade Specification

**Base:** Fork of [Notesnook](https://github.com/streetwriters/notesnook) (GPLv3) — monorepo at web v3.4.3 / mobile v3.4.5 / core v8.1.3.
**Date:** 2026-07-13 · **Status:** v4 — pressure-tested (adversarial code-level review) + all product decisions locked by the owner.
**Audience:** an implementing AI agent (Opus 4.8). **This document is the contract: implement exactly what is written. Where behavior is not specified, follow the Decision Protocol in §0. Do not invent product behavior.**

---

## 0. Implementation Ground Rules (read first)

1. **No product decisions.** Every deliberate choice is recorded here. If you hit a genuinely unspecified behavior, STOP and ask the owner; do not pick silently.
2. **Deterministic fallbacks.** A few items are marked `[GATE]` with an if/then rule — verify the stated condition at implementation time and follow the stated branch. That is not a decision; it is a conditional instruction.
3. **Priorities when constraints collide:** Privacy > Correctness (never lose an entry) > Pen experience > Convenience > Other features. Rich text is sacrificable; the three invariants (I1–I3, §2) are never sacrificable.
4. **File references** are to the Notesnook monorepo at the versions above and were verified against source on 2026-07-12.
5. Work in phases (§9); each phase has acceptance tests that must pass before the next starts.

## 1. Product Summary

A journaling app for exactly one person and three devices — Windows 11 PC (Electron), Samsung Galaxy S23 Ultra, Galaxy Tab S9 (both Android, sideloaded) — that **never connects to the internet**. Most content is handwritten with the S Pen and kept as ink on a native low-latency canvas. Devices sync automatically over local Wi-Fi with no hub, no cloud, and no interaction. A hidden vault conceals secret entries. A future self-hosted server is a configuration change, not an architecture change.

### Locked product decisions (owner, 2026-07-12/13)
| # | Decision |
|---|---|
| D1 | **Journal-first app model**: launches into a "Today" view; date-based navigation; secondary free-form Notes area retained (notebooks/tags survive there) |
| D2 | **Ink canvas = endless vertical page**, fixed logical width, with optional horizontal ruled guide lines like a paper notebook |
| D3 | **An entry is either ink or typed, never mixed.** A day can contain multiple entries of both kinds |
| D4 | **Ink conflicts resolve automatically by writing time**: earlier-written content sits higher on the page; later writing flows in below where the earlier writing ends; second-level precision; no conflict dialog for ink |
| D5 | **Vault: separate password, no biometrics.** App lock keeps PIN/password + fingerprint as today |
| D6 | **Backups: daily encrypted local backup on every device; weekly automatic copy to an owner-chosen folder on the PC** |
| D7 | **English only** for handwriting recognition (Samsung pack now; ML Kit ink search later) |
| D8 | **S23 Ultra runs the identical full app** (same editor, navigation, vault) |

## 2. Invariants (apply to every feature, every phase)

- **I1 — Zero internet.** No network traffic except mDNS discovery and TLS connections to explicitly paired personal devices (later: to one owner-configured self-hosted endpoint). Verified by packet capture (§9 acceptance).
- **I2 — Everything encrypted at rest.** SQLite databases (SQLCipher-family, already true on all platforms — `apps/desktop/src/api/sqlite-kysely.ts`, `apps/web/src/common/db.ts:74`, `apps/mobile/app/common/database/index.ts`), note content (XChaCha20-Poly1305, `packages/crypto/src/encryption.ts`), attachments (chunked encrypted, `packages/core/src/database/fs.ts`), **and every new artifact this PRD adds**: ink blobs, sync cursors, pairing keys, backups, logs. No journal plaintext in any persisted file.
- **I3 — Never lose writing.** Sync never silently discards strokes or text. All merge rules below are additive; destructive operations (delete, trash purge) happen only via explicit user action.

### Non-goals (explicit, final)
- Multi-user, sharing, collaboration, publishing (monographs removed). Real-time co-editing/CRDT for typed text.
- Custom/self-learning handwriting recognition (Samsung's on-device adaptation is the ceiling).
- Matching Samsung Notes' ~2.8 ms privileged pen latency (third-party ceiling ≈ 10–25 ms perceived; own estimate).
- Mixed ink+text entries (D3). Further rich-text investment (TipTap editor is retained but feature-frozen).
- iOS; app-store distribution.
- **v1 regression, accepted:** ink entries are **not content-searchable** (titles/dates only) until the post-v1 ink-transcription feature (§6.5) ships.

## 3. Why Fork Notesnook — and Two Corrections from the Adversarial Review

Notesnook remains the right base: encrypted SQLite + content crypto on all platforms, cleanly separated local persistence, app lock and vault exist, all cloud endpoints behind one config layer, no telemetry, GPLv3. **But two v1–v3 claims were falsified against the code and are corrected throughout this spec:**

1. **CORRECTION — keys require an account in stock Notesnook.** The data-encryption key (DEK) is derived from login credentials: `collector.collect()` → `db.user.getDataEncryptionKeys()` → `getMasterKey()` returns `undefined` without a user and the collector **throws** (`packages/core/src/api/sync/collector.ts:49-52`, `user-manager.ts:442-446`). "Never log in" gives a working local editor but **no sync and no DEK**. Therefore this fork builds a **LocalKeyring** (§5.1) that provisions all keys without any account. This is core work, not UI stripping.
2. **CORRECTION — the sync collector cannot serve multiple peers unchanged.** Items carry a single boolean `synced` flag set after one successful push (`sql-collection.ts:288,314`); with 3 peers, an item pushed to one peer would never be collected for the others. The **merger** is reused as-is (timestamp LWW, `merger.ts`); the **collector is replaced** for P2P by cursor-based collection (§5.4). The `synced` flag is left in place, untouched, for the future stock-server path only.

Minor correction: the vault key already syncs as a normal encrypted item in the `vaults` collection (`SYNC_COLLECTIONS_MAP`, `packages/core/src/api/sync/types.ts`); the `SendVaultKey` SignalR handler is a legacy migration path. No special vault-key transport is needed for P2P — the vaults collection syncs like any other (§5.4.6).

## 4. Product Specification

### 4.1 App model & navigation (D1)
- **Home = "Today" screen** on all three platforms: date header, vertically stacked previews of today's entries (newest last), two creation buttons: **New ink entry** (primary, default) and **New typed entry**.
- **Navigation:** swipe left/right (or ◀▶ buttons on desktop) = previous/next day. Calendar icon → month grid; days with entries show a dot; tap → that day's view. A "Journal" / "Notes" / "Vault" three-item primary navigation replaces Notesnook's sidebar root. "Notes" contains the retained free-form Notesnook experience (notes list, notebooks, tags, colors, favorites, archive, trash, reminders). "Vault" is the dedicated section per F-VAULT (§6.3).
- **Journal entry metadata:** new nullable column `journalDate` (TEXT, `YYYY-MM-DD`) on the `notes` table (§5.7 migration). Journal entries have it set (creation date by default; editable via an entry menu "Move to date…"); free-form notes have `NULL`. Journal views query by `journalDate`; the Notes area filters `journalDate IS NULL`. Entry default title: `HH:mm` creation time (user-editable).
- Deleting an entry uses the normal trash (retention: Notesnook default 7 days — keep the existing `trashCleanupInterval` default and settings UI).

### 4.2 Ink entry surface (D2, D3)
- One ink entry = one **endless vertical canvas**: fixed logical width **1000 units**, height grows with content (§5.2 coordinate spec). Rendered scaled-to-width on every screen (Tab S9, S23 Ultra, desktop window) — no reflow, no repagination; the phone simply shows the same page narrower (D8: identical app).
- **Paper style per entry** (persisted in the ink blob header, §5.2): `blank` (default) or `ruled`. Ruled = horizontal guide lines every **56 units**, rendered light gray (`#00000022` light theme / `#FFFFFF22` dark), non-exporting by default (export flag in §6.6). A toolbar toggle switches style at any time (affects rendering only, never stroke data).
- **Dark theme:** the canvas background follows the app theme. Strokes whose color is the default black `#FF262626` render as `#FFE8E8E8` in dark theme (display-time mapping only; stored color unchanged). Non-default colors render as stored. This mapping table lives in one shared constant used by both renderers.
- **Tools (v1, complete list):** pen (3 sizes: 3/5/8 units; 6 colors: black default, blue `#2E5AAC`, red `#B3261E`, green `#2E7D32`, amber `#B26A00`, purple `#6750A4`), highlighter (1 size: 24 units; same 6 colors at 40% alpha), stroke eraser (removes whole strokes on hit), undo/redo (session-local, unlimited within an open editing session), scroll mode toggle (finger always scrolls; pen writes — pen never scrolls). Nothing else: no lasso, no shapes, no layers, no zoom in v1.
- Stylus-only inking (`pointerType`/tool-type pen); finger touches scroll. Automatic palm rejection follows from pen-only input.
- Typed entries use the existing TipTap editor unchanged (feature-frozen).

### 4.3 First-run / onboarding flow (exact order)
**Device #1 (any device):**
1. Welcome → set **app-lock password** (mandatory) + offer fingerprint enrollment (Android) / WebAuthn key (desktop) — reuses existing app-lock implementation (`apps/mobile/app/components/app-lock/`, `apps/web/src/views/app-lock.tsx`).
2. LocalKeyring generates all keys (§5.1) — silent, no UI beyond a progress spinner.
3. (PC only) Windows Firewall step: register inbound allow rule for TCP port 53222 and UDP 5353, private networks profile, with a shown-and-confirmed dialog.
4. (PC only) Choose the **weekly backup folder** (D6) via directory picker; skippable, re-promptable from Settings with a persistent badge until set.
5. Land on Today.

**Devices #2, #3:** Welcome → set app-lock password → **"Pair with existing device"**: scan QR shown on any already-set-up device (§5.5). Pairing transfers the DEK; first sync then populates the journal. A "start fresh instead" path exists but requires typing CONFIRM (it forks the data set permanently — two independent DEKs can never merge).

**Vault creation** is not part of onboarding: first use of "Vault" in navigation prompts creation with its own password (D5).

### 4.4 Conflict handling (D4)
- **Ink entries: no conflicts, ever — by construction.** The ink data model is a grow-only set of *writing sessions* merged deterministically by time (§5.3). Concurrent edits on two devices produce a page where earlier-written content appears higher and later writing flows below it, to the second. No dialog, no conflicted copies.
- **Typed entries:** keep Notesnook's existing behavior verbatim — timestamp merge within a 60 s threshold, otherwise flag `conflicted` and resolve in the existing diff viewer (`packages/core/src/api/sync/merger.ts`, `apps/web/src/components/diff-viewer`).
- **Vault-locked ink entries** (content ciphered with the vault key, sessions unreadable at merge time): if both sides changed, store the remote version alongside local using the existing `conflicted` mechanism; on the next vault **unlock**, run the ink session-merge automatically and clear the flag. No user interaction.

### 4.5 Backups (D6)
- **Daily** (every device): on first app-foreground of a calendar day, write a full encrypted backup via the existing backup path (`packages/core/src/database/backup.ts`, encrypted mode) to app-private storage. Retention: keep newest **7 daily + 4 weekly** (weekly = the newest backup of each ISO week); delete older automatically.
- **Weekly (PC only):** after the daily backup on the first foreground of each ISO week, additionally copy that backup file into the owner-chosen folder (§4.3 step 4). Retention in that folder: keep newest **12**; delete older copies **that match this app's backup filename pattern only** (`mindvault-backup-YYYYMMDD-HHmmss.nnbackup`); never touch other files.
- Manual "Export encrypted backup now" button in Settings on all platforms (file-save dialog / SAF picker).
- Restore: existing Notesnook restore flow, gated behind app-lock authentication.

## 5. Technical Specifications (normative)

### 5.1 LocalKeyring — key hierarchy without accounts (replaces account-derived crypto; resolves Correction 1)

New module `packages/core/src/localkeyring.ts` + per-platform storage. **All keys are generated locally with libsodium CSPRNG on device #1 and never derived from any account.**

| Key | Size | Purpose | Storage |
|---|---|---|---|
| `dbKey` | 32 B random | SQLCipher database key | exactly as today: Android Keychain/MMKV path (`apps/mobile/app/common/database/encryption.ts`), web/desktop WebCrypto keystore (`apps/web/src/interfaces/key-store.ts`) — including the existing app-lock wrapping (password re-encrypts `dbKey`; unchanged) |
| `dek` | 32 B random | data encryption key for sync-item and attachment crypto — plays the role of stock Notesnook's account key | stored **inside the encrypted DB** `kv` table, additionally wrapped by `dbKey`-derived key (HKDF-SHA256, info=`"mv:dek:v1"`); synced only via pairing (§5.5), never via item sync |
| `deviceKeyPair` | Ed25519 + P-256 TLS cert | peer identity + TLS | private halves in platform keystore; public halves in `sync_peers` rows of paired devices |
| vault key | existing | per-vault, wrapped by vault password | unchanged (`packages/core/src/api/vault.ts`); rides normal item sync in the `vaults` collection |

**Integration:** implement `LocalKeyring.getDataEncryptionKeys()` with the same return shape as `db.user.getDataEncryptionKeys()` and route the collector, attachment fs (`getAttachmentsKey`), and content crypto through it. The `db.user` object remains present but permanently logged-out; every call-site that throws on missing user for crypto purposes is redirected to LocalKeyring (grep anchor: `getDataEncryptionKeys`, `getMasterKey`, `userEncryptionKey`). The `EVENTS.userSessionExpired` path must become unreachable.
**Key rotation is out of scope for v1.** Losing all three devices + all backups = data unrecoverable; the onboarding shows this in one sentence at DEK creation.

### 5.2 Portable ink format `mvink` v1 (canonical; both renderers build against THIS)

One ink entry's content blob = UTF-8 JSON (encrypted at rest like all content):

```jsonc
{
  "fmt": "mvink", "v": 1,
  "paper": { "style": "blank" | "ruled" },        // ruled line spacing is fixed: 56 u
  "sessions": [ /* ordered by (start, deviceId) ascending — ALWAYS stored sorted */
    {
      "id": "<uuidv4>",
      "deviceId": "<uuidv4 of authoring device>",
      "start": 1767312000000,                      // epoch ms UTC of first stroke's first point
      "end": 1767312245000,                        // epoch ms UTC of last stroke's last point
      "yShift": 0,                                 // merge-applied vertical offset in units (§5.3); render y = stored y + yShift
      "strokes": [
        {
          "id": "<uuidv4>",
          "t0": 1767312001234,                     // epoch ms of first point
          "brush": { "kind": "pen" | "highlighter", "size": 5, "color": "#FF262626" }, // size in units; color #AARRGGBB
          "pts": [ [x, y, p, tx, ty, dt], ... ]    // see units below
        }
      ]
    }
  ]
}
```

- **Units & coordinates:** logical canvas units; canvas width is exactly **1000 u**; origin top-left; +y downward; y unbounded ≥ 0. Device mapping: `1 u = deviceCanvasWidthPx / 1000` — resolution-independent by construction. `x,y` are floats, 2-decimal max precision.
- **Point fields:** `p` pressure normalized 0.0–1.0 (unavailable → 0.5); `tx, ty` tilt in degrees −90…90, integers (unavailable → 0); `dt` = ms since the stroke's `t0`, uint (monotone non-decreasing). Timestamps come from the device wall clock; §5.4.7 covers skew.
- **Erasing a stroke removes it from `strokes` and appends its id to a session-level `"deleted": ["<strokeId>", ...]` array** (tombstones — required so a deletion survives merge with a peer that still has the stroke). Undo of an erase removes the tombstone and restores the stroke.
- Writers MUST reject/ignore unknown `fmt`/`v` (render placeholder "newer format — update this device"); minor additive fields are allowed only with a `v` bump.
- Android MAY cache androidx.ink `ink-storage` binaries for fast rehydration, keyed by content hash, in app-private storage; the cache is disposable and never synced. The JSON above is the sole source of truth.

### 5.3 Ink merge algorithm (implements D4; runs inside the merger for content rows whose note content type is `ink`)

Input: `local`, `remote` mvink documents for the same entry. Output: merged document. Deterministic, commutative, associative:

1. **Union sessions by `id`.** For a session id present in both, union `strokes` by stroke `id`, union `deleted` arrays, then drop strokes whose id ∈ `deleted`. (`end` = max of both.)
2. **Sort sessions** by `(start, deviceId)` ascending.
3. **Recompute `yShift` for every session, in sorted order:**
   - Maintain `floor = 0` (the bottom of all earlier-session content) and `lastDevice = null`.
   - For each session S: let `top(S)`, `bottom(S)` = min/max stored stroke y (ignoring yShift).
     - If S was written **on the same device and same canvas lineage as the previous session** (i.e., `S.deviceId == lastDevice`), the author placed it deliberately (possibly annotating above): `S.yShift = prevShiftOfThatDevice` (sessions from one device keep their relative positions — track one running shift per deviceId).
     - Else (device change in the timeline): `S.yShift = max(perDeviceShift[S.deviceId] ?? 0, floor + GAP − top(S))` and record it as that device's running shift. `GAP = 24 u`.
   - After placing S: `floor = max(floor, bottom(S) + S.yShift)`.
4. Result is stored sorted with computed `yShift`s. Re-merging the same inputs yields byte-identical output (canonical JSON: sorted keys, fixed float formatting).

Effect: writing that happened first (by wall clock, to the second — D4) appears higher; a device's own writing never rearranges under it; two devices' concurrent writing stacks in time order instead of overlapping. A **session boundary** is created when: entry opened, or ≥ 5 min idle (no strokes), or entry closed/backgrounded.

### 5.4 P2P sync protocol `mvsync` v1 (replaces the SignalR transport; resolves Correction 2)

**Model: pull-only gossip.** Devices never push. When two paired peers meet, each pulls the other's changes since its per-peer cursor and merges locally with the existing merger (`mergeItem` LWW semantics preserved: remote wins only if `dateModified` strictly greater — this also makes echo pulls no-ops). Transitive propagation (phone→tablet→PC) follows automatically because merged items keep their original `dateModified` and ids.

1. **Discovery:** DNS-SD `_mvsync._tcp.local.`, TXT record `{"d":"<deviceId>","pv":1}`. Android: `react-native-zeroconf`; Electron: `bonjour-service`. Fixed TCP port **53222** (fallback: next free port up to 53232, advertised in the SRV record).
2. **Transport:** TLS 1.3, each device's self-signed P-256 cert (10-year validity, CN = deviceId). Trust = exact certificate-fingerprint pinning against the `sync_peers` table; anything else is rejected before HTTP. Every request additionally carries `Authorization: Bearer <pairToken>` (§5.5).
3. **Endpoints** (JSON bodies; all under `/v1`):
   - `GET /v1/manifest` → `{ deviceId, name, pv: 1, schema: <CURRENT_DATABASE_VERSION>, now: <epoch_ms> }`. If the caller's `pv` or `schema` differs → respond normally, but the **caller** must refuse to sync and surface "update your apps" (skew rule: sync only between identical `pv` AND identical `schema`).
   - `GET /v1/items?since=<cursor>&limit=500` → `{ items: [{ collection, id, v, dateModified, cipher }...], next: <cursor>, done: bool }`. Ordered by `(dateModified, id)` ascending; `cursor` is the opaque string `"<dateModified>:<id>"` of the last row returned; `since=0` = from the beginning. Items are the existing per-record encrypted `SyncItem` cipher envelopes (encrypted with the DEK exactly as the stock collector does), across all of `SYNC_COLLECTIONS_MAP`'s collections **including `vaults` and `attachments` metadata**. Server-side implementation: new `collectSince(cursor, limit)` in `packages/core` — `WHERE (dateModified, id) > cursor ORDER BY dateModified, id` per collection, interleaved by dateModified; it does **not** read or write the legacy `synced` flag.
   - `GET /v1/attachments/<hash>` → the encrypted chunk stream for that content-addressed attachment (existing encrypted chunk files served verbatim). Supports `Range`; puller resumes on disconnect. Pulled lazily: after item sync, fetch hashes referenced by attachment metadata rows that are missing locally.
   - `GET /v1/keys` → only valid during pairing (§5.5), else 403.
4. **Sync rounds:** triggered on app-foreground, on Wi-Fi-connect event, on local-DB-change (debounced 5 s, mirroring `auto-sync.ts`), and on mDNS peer-appearance; plus Android WorkManager periodic (15 min, network-required) best-effort rounds. During an active round Android holds a `connectedDevice` foreground service (exempt from the 6 h dataSync cap); the service stops when the round ends. No 24/7 listener promise: the HTTP server runs while the app process lives; a backgrounded/killed app simply syncs on next trigger.
5. **Cursors:** new table `sync_peers(peerId TEXT PK, name TEXT, certFp TEXT, pubKey TEXT, pairToken TEXT, pullCursor TEXT, lastSeen INTEGER, addedAt INTEGER)` inside the encrypted DB. `pullCursor` advances only after each page's items are fully merged and committed (crash-safe: re-pulling a page is idempotent by LWW).
6. **Vault items** sync as ordinary ciphered rows (vault key rides the `vaults` collection; note §4.4 for locked-ink conflict handling).
7. **Clock sanity:** each `manifest` exchange compares `now` values; if |Δ| > 120 s, sync proceeds but both devices show a persistent warning banner ("clock skew — fix device clocks"), because LWW and D4 ordering depend on wall clocks.
8. **Errors/retry:** network failures retry with exponential backoff 1 s → 60 s within a round, max 5 attempts, then the round ends silently (next trigger retries). Malformed responses abort the round and log (I2-compliant logging, §5.8).
9. **Legacy path:** SignalR sync client, `synced` flags, and `db.user` gating remain in the codebase untouched but permanently dormant behind the absent account; the future self-hosted phase (§8) re-uses `collectSince` with a `RemoteServerEndpoint`.

### 5.5 Pairing (one-time per device pair)
1. Existing device: Settings → "Pair new device" → generates `pairingSecret` (32 B random, 60 s TTL) and displays QR: `{"v":1,"deviceId","name","host","port","certFp","secret"}`.
2. New device scans → connects TLS to `host:port`, verifies `certFp`, then `POST /v1/pair {deviceId, name, certFp_new, pubKey_new, proof: HMAC-SHA256(secret, certFp_new)}`.
3. Existing device verifies proof, stores the new peer row, responds `{peer row of itself, pairToken: <32B random>, wrappedDek: XChaCha20-Poly1305(dek, key=HKDF(secret, info="mv:pair:v1"))}`.
4. New device unwraps and stores the DEK via LocalKeyring, stores the peer row + `pairToken`, and both sides run a first sync round. The QR/secret is single-use; the displaying screen shows the new device's name+fingerprint for visual confirmation.
5. Unpairing (Settings) deletes the peer row on both sides (best-effort remote notify `DELETE /v1/pair`); a lost device's row can be removed unilaterally. **Removing a peer does not rotate the DEK (rotation out of scope, §5.1) — the onboarding note covers this.**

### 5.6 Content-type integration for ink
- Extend the closed union: `NoteContent.type` gains `"ink"` (`packages/core/src/types.ts:396,704`). Compile with exhaustiveness checking and fix **every** switch site (grep anchor: `ContentType`); default behavior for ink at text-centric sites: title-only (search-index empty string, preview = "✍ Handwritten entry", clipper/web-extension skip).
- FTS: index ink content as empty string (mirror the locked-notes pattern, `packages/core/src/database/fts.ts:48`); titles remain searchable. (Accepted v1 regression, §2.)
- **Note history:** disabled for ink entries in v1 (sessions are append-mostly and every version is a full blob — cost without benefit). Implementation: `noteHistory` skips content type `ink`. Typed entries keep history unchanged.
- Word/character counts, Markdown/HTML export paths: ink returns empty/placeholder; PDF/PNG export per §6.6.
- DB migration in §5.7.

### 5.7 Database migrations (one migration, `CURRENT_DATABASE_VERSION` bump; applies to all three SQLite backends via the existing migration framework `packages/core/src/database/migrations.ts`)
1. `ALTER TABLE notes ADD COLUMN journalDate TEXT` + index `notes_journalDate` (§4.1).
2. `CREATE TABLE sync_peers (...)` per §5.4.5.
3. `kv` entries for LocalKeyring wrapped DEK (§5.1) — written by code, no DDL.
4. Content type `"ink"` is data-level (no DDL); the type union + validators updated in code.

### 5.8 Logging
Existing `packages/logger` retained. Rules: level `info` default; logs live in app-private storage, rotate at 5 MB × 3 files; **never log note titles, content, stroke data, keys, cursors' item payloads, or peer tokens** — an automated test greps a generated log corpus for seeded canary strings (a known title/phrase written during the test) and fails on any hit. No log ever leaves the device.

### 5.9 Performance budgets (acceptance-tested)
| Metric | Budget | Where |
|---|---|---|
| Wet-ink latency (pen to pixel, perceived) | subjectively close to Samsung Notes side-by-side; front-buffered + predicted path verified by systrace | Tab S9 |
| Cold start → Today view interactive | ≤ 2.5 s | Tab S9, release build |
| Open ink entry with 10 000 strokes | ≤ 700 ms to first full render | Tab S9 |
| Full sync round, 1 000 changed items | ≤ 30 s | any pair, same Wi-Fi |
| Ink storage | a dense handwritten page ≈ 100–300 KB JSON pre-encryption (own estimate) — no hard cap; monitor only | — |

### 5.10 Build, distribution, update skew
- Release builds: PC produces the Electron installer and the signed APK (single release script; version = one shared semver). Install on Android by sideload (file transfer + package installer; developer options already required once).
- **Skew safety is enforced by §5.4.3** (identical `pv` + `schema` or no sync): updating devices one-by-one is safe — they simply don't sync until versions match, and the UI says so.

## 6. Feature Work Packages (what to build, referencing all specs above)

### 6.1 F-STRIP — Offline hardening
As specified in v3, all items verified against source: neutralize login/account UI; blank the 7 hosts in `packages/core/src/utils/constants.ts`; stub `apps/desktop/src/utils/autoupdater.ts:26-28`; drop `react-native-check-version`; remove subscriptions/IAP/pricing (`subscriptions.ts`, `pricing.ts`, `offers.ts`, `circle.ts`, Paddle, `react-native-iap`) and monographs (`monographs.ts` + publish UI) and the bug-report uploader (`debug.ts`) and announcements/version fetch (`api/index.ts:483,487`); Android debug network-security config restricting cleartext to RFC1918. **Plus (Correction 1): LocalKeyring §5.1 and the crypto call-site redirection — sized M, not S.** No telemetry exists to remove (verified).

### 6.2 F-LOCK — App lock
Adopt existing implementation; make it mandatory in onboarding (§4.3); default lock-on-background timeout: 1 min mobile, 5 min desktop (both user-adjustable in the existing settings).

### 6.3 F-VAULT — Hidden vault
Implementation exactly as the file-level plan of v3 (verified choke points): predicate injection in `packages/core/src/collections/notes.ts` getters (`all/favorites/pinned/archived/conflicted`), `RelationsArray.selector` (`collections/relations.ts:275`, with the `reference.type === "vault"` carve-out), `excludedIds` in the 4 `api/lookup.ts` functions, counts in `collections/notebooks.ts`; cached `defaultVaultId` in `collections/vaults.ts`; refresh on `EVENTS.vault*`; subquery predicate (not id-lists) to avoid the 200-parameter limit; widget purge on lock; `db.notes.note(id)` stays unfiltered; export-all gated on vault unlock in UI (never filter `exportable` — it backs search sorting, `lookup.ts:276`); **reminders cannot be created on vault notes** (creation-time check). Vault password separate, no biometric path (D5). Journal integration: vaulted entries also vanish from Today/calendar views and day-dots (these run through the same filtered selectors — verify in acceptance).

### 6.4 F-INK — Native ink editor
androidx.ink stable 1.0.x: `InProgressStrokesView` wrapped as an RN Fabric Native Component; `MotionEvent.getHistorical*` + `requestUnbufferedDispatch`; dry rendering via `CanvasStrokeRenderer`; per-stroke erase via `ink-geometry`; JS thread out of the stroke path (commands/serialized bytes only); `requestDisallowInterceptTouchEvent` for touch ownership. Serialization to/from `mvink` (§5.2). Desktop renderer: perfect-freehand → SVG from `mvink` points (pressure honored; tilt stored-but-unused by this renderer — accepted). Editor UI per §4.2. **Week-1 spike (mandatory): Fabric embedding + front-buffer compositing inside the RN view tree on the Tab S9 — if `InProgressStrokesView` proves un-embeddable [GATE], fall back to a full-screen native Activity hosting the ink editor (RN navigates to it via intent; same mvink contract), and note it in the progress log.**

### 6.5 F-PENTEXT — Handwriting→text + future ink search
Samsung Direct Writing works on text fields (Samsung Keyboard as IME; English pack per D7); ink canvas never triggers it (not a text field). If direct input into TipTap misbehaves (documented ProseMirror/Samsung-IME bug class), build the native `EditText` capture overlay inserting via the RN↔WebView bridge (`apps/mobile/app/screens/editor/tiptap/commands.ts`).
**Post-v1 ink search:** ML Kit Digital Ink Recognition (English model) transcribing `mvink` points into a hidden searchable text column. **[GATE — I1 compliance]:** the model must be provisioned without the app touching the internet — bundle it in the APK at build time if ML Kit supports bundled digital-ink models at implementation time; otherwise download it once on the build machine and ship it as an app asset with a documented load path; if neither is possible, the feature is dropped and titles-only search remains. The app process itself never makes the download call.

### 6.6 F-EXPORT — Ink export
Ink entry → **PDF** (vector strokes, pages paginated at 1414 u height per page ≈ A4 aspect at 1000 u width; ruled lines included only if a checkbox "include guide lines" is ticked, default off) and **PNG** (2000 px wide, one image per 1414 u page). Typed entries: existing MD/HTML/PDF unchanged. Full backup covers everything regardless (§4.5).

### 6.7 F-SYNC — LAN P2P
Everything in §5.4 + §5.5. Building blocks (maintenance verified 2026-07-12): `react-native-zeroconf` 0.14.0, `react-native-tcp-socket` 6.4.1 (TLS server), `bonjour-service` (Electron), Node `https` on desktop.

### 6.8 F-WIDGET — Android home-screen widget
Retained for typed notes; for ink entries it shows title + date + "✍" glyph only (no stroke rendering in v1). Vault purge per §6.3.

## 7. Retained Notesnook Features (regression scope)
Typed editor (TipTap, feature-frozen), notebooks/tags/colors/favorites/pinned/archive/trash (in the Notes area), reminders (except on vault notes), FTS for typed content + all titles, note history (typed only), encrypted backups, import/export for typed content, bundled themes (marketplace removed).

## 8. Future Phase — Self-Hosted Endpoint
Preferred: a headless Node "fourth peer" speaking `mvsync` v1 on the VPS/home server (always-on, big disk); off-LAN reachability via WireGuard/Tailscale only. Alternative (stock notesnook-sync-server via docker-compose: identity+sync+SSE+MinIO+MongoDB; SMTP mandatory, `DISABLE_SIGNUPS=true` after account creation; officially alpha) — only if stock-client compatibility ever matters; it would require reviving the dormant account path. Decision deferred until a VPS exists; nothing in v1 blocks either.

## 9. Delivery Plan & Acceptance (each phase gates the next)

| Phase | Scope | Est.* | Acceptance (all must pass) |
|---|---|---|---|
| **0 Build & baseline** | Build desktop (Windows) + APK from source; Node 22.20.0, `npm run bootstrap`, editor-mobile bundle, Android toolchain | 1–2 wk | Both apps run; note created/edited offline on each |
| **1 Offline & keys** | F-STRIP incl. LocalKeyring (§5.1, §6.1); D6 backups (§4.5) | 2–4 wk | 24 h packet capture on all 3 platforms: zero non-LAN traffic; canary-string log audit passes; encrypted backup + restore drill passes; every persisted file is ciphertext (`strings` audit) |
| **2 Ink editor** | F-INK (§6.4) + journal model (§4.1–4.2) incl. migration §5.7(1) | 4–6 wk | Perf budgets §5.9 rows 1–3; ruled/blank toggle; dark-theme color mapping; mvink round-trip Android↔desktop renders equivalently (golden-file tests) |
| **3 Vault & lock** | F-VAULT + F-LOCK (§6.2–6.3) | 1–2 wk | Locked vault: zero trace in any list/search/count/widget/Today/calendar; restart relocks; separate password enforced; no biometric path to vault |
| **4 P2P sync** | F-SYNC (§6.7) incl. migrations §5.7(2) | 4–8 wk | 3-device convergence with PC off (phone↔tablet), zero taps, <10 s foreground latency; ink concurrent-edit produces D4 time-ordered page on all devices (golden merge tests §5.3, incl. commutativity/associativity property tests); typed conflict flags as today; kill mid-sync → no loss, cursors resume; clock-skew banner at >120 s; version-skew refusal works; perf budget §5.9 row 4 |
| **5 Pen-to-text & export** | F-PENTEXT (v1 part), F-EXPORT, F-WIDGET | 1–2 wk | Handwritten paragraph → correct text offline; PDF/PNG export golden files |
| **6 Later** | Ink search (§6.5 gate), self-hosted endpoint (§8) | — | — |

*Own estimates, solo dev + AI tooling. Phases 2 and 4 carry the highest uncertainty (native-surface embedding; Android background/network edge cases).

## 10. Risks (updated post-review)
| Risk | Sev. | Mitigation |
|---|---|---|
| LocalKeyring misses a crypto call-site still gated on `db.user` → runtime throw or, worse, silent plaintext | **High** | Exhaustive grep list in §5.1; integration test that runs collector+attachment+vault flows with no user object; I2 `strings` audit |
| RN ↔ native ink surface embedding (touch ownership, front-buffer compositing) | **High** | Mandatory week-1 spike; [GATE] fallback to full-screen native Activity (§6.4) |
| D4 merge yShift edge cases (annotating above earlier writing after a device switch) | Med | Property-based tests: commutativity, associativity, idempotence, no-overlap invariant; per-device running-shift rule (§5.3.3) preserves an author's own layout |
| Android background sync flakiness (Doze/FGS/NSD) | Med-High | Foreground-initiated model, `connectedDevice` FGS windows, WorkManager periodic; Syncthing-folder Plan B stays documented |
| `androidx.ink` youth (stable Dec 2025) | Med | Pin 1.0.x; mvink is ours — renderer swap can never lose data |
| Clock skew corrupts LWW/D4 ordering | Med | 120 s banner (§5.4.7); no NTP offline — user-visible, not silent |
| Fork drift from upstream security fixes | Med | Changes are additive behind seams (LocalKeyring, `collectSince`, content type, vault predicate); pin fork point; cherry-pick |
| ML Kit model unobtainable offline | Low (post-v1) | [GATE] §6.5: bundle → asset-sideload → drop, in that order |

---
*Provenance: architecture and all file references verified against the Notesnook clone (core v8.1.3) on 2026-07-12; corrections C1/C2 verified in `collector.ts`, `user-manager.ts`, `sql-collection.ts`; ecosystem facts (androidx.ink 1.0.0 stable 2025-12-17; graphics-core 1.0.4; input-motionprediction 1.0.0; react-native-zeroconf 0.14.0; react-native-tcp-socket 6.4.1; cr-sqlite unmaintained since 2024-10; Syncthing-Fork active v2.1.2.0; ML Kit Digital Ink current, no personalization; Samsung S Pen SDK discontinued except Remote SDK; notesnook-sync-server alpha, SMTP mandatory) verified via web on 2026-07-12. Own estimates: all effort figures, the 10–25 ms latency projection, storage-per-page figure. The mvink format, merge algorithm, and mvsync protocol are original normative specifications of this document.*
