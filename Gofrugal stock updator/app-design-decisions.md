# Gofrugal Stock Updator — App Design Decisions (running log)

Brainstorming log from the design session (2026-07-05). This captures decisions as they are made; it will be superseded by a full PRD.

## Product goal
Help the user fill products into Gofrugal inventory **as quickly and as accurately as possible** from supplier invoices. The app must let the user check everything before the Excel export. The app must be **self-learning end-to-end** with no developer maintenance for its judgment quality.

## Confirmed decisions

### Platform & devices
- **Phone** = capture-only device. PWA at a **static URL**, installed to home screen ("Add to Home Screen"), long-lived login (QR sign-in only for first-time setup). Tap icon → camera opens. The phone never shows forms.
- **PC (shop server, Microsoft Edge)** = review-only device. The PC never asks for photos.
- Photos taken with no open session land in a **capture inbox**, attachable to a session later.
- Real-time phone→PC sync (WebSocket) within a paired session.

### Architecture
- Cloud backend does all heavy work (OCR, LLM, matching, learning).
- **Tiny local connector** on the shop PC (single small binary, e.g. Go; single-digit MB RAM, near-zero CPU): (a) proxies the local Gofrugal API (localhost:8482 WebReporter) to the backend, (b) optionally drops exported Excel into a watched folder. **Outbound-only** connection — no inbound ports on the shop PC. Reason: the server PC is low-powered; also browsers can't call the local API cross-origin (no CORS on WebReporter — to verify).
- Gofrugal write path = **Excel import (Purchase Entry → Excel Mapping & Importing)**, per the field spec in `gofrugal-purchase-import-excel-formats.md`. User performs the import themselves (v1).
- Gofrugal read path = items API (X-Auth-Token; credentials being provisioned by the Gofrugal team — in progress).

### The 5-step flow ("capture first, review later")
1. **Snap the invoice** (phone, ~10s). Multi-page; blur warning; extraction runs in background.
2. **Product Pass** (phone). Per product, a card with chips: `Name | Batch/MFG | Expiry | Barcode`. User clicks photos in any order; AI **auto-classifies** each photo and lights the matching chip; one photo can light two chips. Big "Next product" button; auto-advance when chips complete. Chips are demand-driven (non-perishables show no Expiry chip).
3. **Check invoice** (PC). Split screen: invoice image ↔ extracted lines; click-to-highlight region; confidence colors; **gross-total reconciliation** (line sum vs printed invoice total) as the master sanity check.
4. **Matching Desk** (PC). Three buckets per line: 🟢 auto-matched (shown, not asked), 🟡 needs a look (top-3 candidates with pack photo alongside), 🔴 probably new (pre-filled create-product card: clean name from pack photo, MRP/HSN from invoice, barcode/batch/expiry from Product Pass). Agent runs **multiple rounds**: (1) text match vs master, (2) cross-check vs pack photos, (3) plausibility checks (e.g. MRP mismatch demotes to yellow). User corrections are one-click.
5. **Verify & Export** (PC). Full table; validation against field spec (lengths/formats); item **type** from master API decides the Excel layout (Standard default; Kit/Matrix split into own correctly-shaped files). Download Excel; batch marked "exported"; audit trail.

### Barcode — two distinct jobs (key clarification)
- **Barcodes change with every batch** (user-confirmed ground truth). Therefore a barcode scan does NOT identify the product against the master.
- **Identification** = front-of-pack photo + visual memory (+ invoice text + alias memory).
- **Data capture** = the new batch's barcode is **always captured, every delivery**, and written to the Excel.
- Capture modes: live scan in the PWA (camera preview, beep-on-decode — primary), still-photo decode (EAN-13/Code-128 libs, vision-LLM digit fallback), handheld USB scanner at the PC (keyboard-wedge listener) as fallback.

### Expiry & batch capture
- Photo of the date printing → OCR extracts expiry, batch, MFG in one shot.
- Handles "best before N months from manufacture": reads MFG + rule, computes expiry, **shows its working** ("MFG 03/26 + 24 mo → 03/2028") for trust.
- **Shelf-life memory** suggests expiry per product from history — always a visible suggestion to confirm, never a silent fill.
- Fast manual fallback with smart parsing (`0328` → `03/2028`); month-granular.
- Bulk-apply same expiry to multi-selected rows.
- "No expiry" is remembered per product (never asked again).

### Self-learning architecture (core requirement)
**Principle: every human touch anywhere is a feedback event — (context, AI proposal, human final value). No edit is just an edit.** One universal event log feeds per-step learners:

1. **Alias memory** — supplier's raw text → item code. Exact repeats auto-match forever. Also written into Gofrugal's `ItemAlias` column so Gofrugal itself learns.
2. **Visual memory** — image embeddings of confirmed pack photos per item. Front photo identifies the product instantly next time; continuously refreshed, so it tracks packaging redesigns.
3. **Shelf-life memory** — per-product typical shelf life → expiry suggestions.
4. **Correction memory** — (evidence → correct answer) pairs from every user override, weighted heavily in future matching.
5. **Supplier layout profiles** (step 1) — corrected OCR fields stored as (image crop, wrong, right); injected as few-shot examples per supplier; extraction self-improves per supplier.
6. **Behavioral defaults** (step 5) — repeated manual patterns (e.g. SellingPrice=MRP for a category, ItemDiscPerc always 0, batch format) detected after N repeats → pre-applied as visible, one-click-undo suggested defaults.
7. **Self-tuning thresholds** — green/yellow/red confidence cutoffs calibrate themselves from observed correction rates (greens never corrected → relax; a green gets corrected → tighten).
8. **Automatic retraining** — lightweight matcher (frozen embeddings + small classifier, ALER pattern) retrains on a schedule from the event log. No developer, no redeploy; all learning lives in data + small models, not code.
- App ships with a **self-monitoring dashboard**: accuracy trend, correction rate per step.
- Honest boundary (agreed): the app self-improves its judgments/defaults/thresholds, not its own feature set.

### UX rules
- One obvious primary path; manual entry is a quiet fallback behind each cell, not a parallel flow.
- Never ask for data the system already has; only surface lines missing something. Work-queue view (incomplete-only) with progress bar; full table one toggle away.
- Every answer the user gives should be the last time they're asked that question.
- Suggestions are always visible as suggestions; nothing fills silently.

## Open items
- Gofrugal API credentials — being provisioned by Gofrugal team (in progress, user-side).
- The 7 import-behavior questions in `gofrugal-purchase-import-excel-formats.md` §5 (esp.: does import create new items? what is the match key — ItemCode/ItemAlias/EanCode?).
- Validate early in build: (a) photo auto-classification accuracy (name vs date vs barcode shots); (b) date-OCR on Indian dot-matrix/embossed printing incl. "N months from MFG" arithmetic — spot-test ~20 real products; (c) whether WebReporter really lacks CORS (decides if connector is strictly required).
- PRD to be written next, consolidating this log + field spec + research.
