# Gofrugal Invoice-OCR & Auto-Inventory Agent — Feasibility & Architecture Research

**Prepared for:** Grocery store owner using Gofrugal Inventory Manager
**Date:** 2026-07-04
**Scope:** Feasibility of an OCR + AI agent that reads supplier invoices (incl. Marathi / other Indian languages, misspellings), matches product names against the Gofrugal item/stock master, flags new products for verification, writes corrected inventory back into Gofrugal, and learns from user corrections.

> **How to read confidence tags:** `[HIGH]` = supported by primary sources; `[MED]` = supported by official-vendor snippets that could not be fully opened; `[LOW / CONFIRM]` = partial/indirect evidence — verify with Gofrugal before building on it.

---

## 1. Bottom line (verdict)

1. **The AI half is clearly feasible.** OCR for Indian scripts, post-OCR correction for Marathi/Hindi, LLM/embedding-based product matching, and a human-in-the-loop self-learning loop are all backed by recent primary research with strong results. This is engineering, not a research gamble. `[HIGH]`

2. **Do not assume you must build the matching + write-back from scratch — Gofrugal already ships two features that overlap your idea:**
   - **Purchase Import** (import a supplier invoice as a purchase entry), and
   - **Item Mapping** (map a supplier's item name/code to *your* item, remembered per supplier via an **Alias / EAN** field).
   These are exactly the "the invoice name ≠ my name" and "write it into stock" problems. Your agent's highest-value role is to **feed and pre-fill these features automatically**, not to replace the ERP write path. `[MED]`

3. **Reading your stock/item master by API is realistic.** Gofrugal exposes a REST API (the "eCommerce/WebReporter API", header auth `X-Auth-Token`) with a documented **items endpoint (item + rate + stock)** and **sales-order endpoints**. `[MED]`

4. **The biggest open risk is the *write-back* API.** The publicly documented *writable* REST endpoint is **sales orders**, not purchase/GRN/item-creation. Pushing *new purchases/stock/items* programmatically most likely goes through **Purchase Import / CSV import / the Master Import (QuickStart) tool**, or a UI step — **not** a clean REST POST. This must be confirmed with Gofrugal for your exact edition before committing to a fully-automated write path. `[LOW / CONFIRM]`

**Recommended shape:** a "human-approves-then-imports" pipeline, not a silent auto-writer — which also happens to be the safest design for stock accuracy.

---

## 2. Part A — Technical feasibility of the OCR + matching + LLM pipeline

### A.1 OCR on Indian scripts is accurate, but engine choice matters per script `[HIGH]`
A 2025 benchmark (RANLP 2025, arXiv 2507.18264) tested six OCR engines (Google Cloud Vision, Google Document AI, Tesseract, Surya, EasyOCR, Subasa) zero-shot on Brahmic scripts. **Google Document AI reached CER ≈ 0.78% on Tamil**; for Sinhala, Surya was best (WER ≈ 2.61%). **No single engine won every script.**
→ *Implication:* benchmark 2-3 engines on *your own* Marathi/Devanagari invoices and pick per script; don't hard-commit to one vendor.

### A.2 Post-OCR correction for Marathi/Hindi works and training data exists `[HIGH]`
RoundTripOCR (ICON 2024, arXiv 2412.15248) frames OCR-error correction as machine translation and releases synthetic correction datasets for six Devanagari languages — **Marathi (1.58M sentences), Hindi (3.1M)**. Fine-tuned **mBART cut Marathi CER from 4.10%→2.46%** (WER 15.37%→9.89%) and **Hindi CER 2.25%→1.56%**.
→ This is precisely your "the invoice has wrong spellings / bad OCR, clean it up" step. Caveat: the datasets are general-domain, not invoice-specific — you'll get more from a small amount of your own labelled invoice text.

### A.3 LLM-based invoice extraction beats template OCR `[HIGH]`
"Automated Invoice Data Extraction: Using LLM and OCR" (arXiv 2511.05547, Nov 2025) and corroborating work (Nature s41598-025-15627-z) show template/rule OCR fails on varied layouts and handwriting, while LLMs add semantic understanding and contextual field relationships; Visual NER on the invoice image raises extraction accuracy. Reported field accuracy: template OCR ~85-95% vs. vision-LLM ~97-99%.
→ Use a **vision-capable LLM** (image → structured JSON of line items) rather than raw OCR + regex.

### A.4 Product matching by LLM/embeddings is feasible without labelled data `[HIGH]`
Cost-efficient prompt-engineering for unsupervised entity resolution (Springer Discover AI 2024, 10.1007/s44163-024-00159-8) achieves **>80% F1** on hard product-matching benchmarks (Amazon-Google) with simple prompting and no training data. Peeters & Bizer (arXiv 2305.03423): ChatGPT ~82% F1 zero-shot on product matching.
→ Matching "invoice line → your item master" is a solved-enough problem. **Caveat:** these benchmarks are English e-commerce; Marathi grocery invoices are an extrapolation, so expect to validate on your real data.

### A.5 The self-learning loop has a proven, cheap pattern `[HIGH]`
ALER (arXiv 2601.20664, Jan 2026) and the CIKM-2019 human-in-the-loop entity-resolution tutorial (10.1145/3357384.3360316) describe the right architecture: a **frozen bi-encoder** produces embeddings **once**, and a **lightweight classifier** is retrained iteratively on user feedback via **active learning** — you never retrain a heavy model. ALER reports F1 90-93% on benchmarks with ~3.8× lower latency.
→ This is exactly your "user corrected me, learn it for next time" requirement, and it runs cheaply.

**No turnkey template exists.** Public "LLM invoice OCR" repos (e.g. ShafqaatMalik/llm-based-invoice-ocr) do PDF→JSON extraction only — **no multilingual, misspelling, matching, or inventory logic**. You will assemble existing components, not fork one project. `[MED]`

---

## 3. Part B — Reading the Gofrugal item / stock master (API)

**Gofrugal exposes a REST API layer** (branded as the eCommerce / "WebReporter" API) available across editions (RetailEasy, ServeEasy; HQ for chains). `[MED]`

| Attribute | Detail (from official KB search snippets) | Confidence |
|---|---|---|
| Auth | HTTP header **`X-Auth-Token: <API-KEY>`** | `[MED]` |
| Base URL pattern | `http://<server-host>:<port>/WebReporter/api/v1/...` (docs show `localhost:8482`) | `[MED]` |
| **Read items** | **`GET /WebReporter/api/v1/items`** — "item master with rate and stock details", lists all items | `[MED]` |
| Sales orders (read) | `GET /WebReporter/api/v1/salesOrders`, plus "retrieve a sales order" | `[MED]` |

Key points:
- The items API returns **item + price + stock**, which is what you need to build the local matching catalogue (your "real stock list"). `[MED]`
- Marketing pages confirm the API is used for **auto-syncing warehouse-wise inventory and pricing** with e-commerce channels (Shopify, Unicommerce, etc.), i.e. it's a real, in-production integration surface. `[MED]`
- **Not verifiable from public sources:** the exact JSON field names of the items response, pagination/filter params, licensing tier required, and whether it runs on the local POS server vs. a cloud gateway for your specific plan. **Confirm with Gofrugal.** `[LOW / CONFIRM]`

> ⚠️ The official API pages on `community.gofrugal.com` could not be opened during this research — the network egress policy for this session blocks that host, so the details above come from search-engine snippets of those official pages, not the full pages. Treat endpoint/field specifics as "to be confirmed against the live API docs / a sandbox key."

---

## 4. Part C — Writing new inventory back into Gofrugal

This is the crux. There are **four candidate write paths**, in rough order of automation-friendliness:

### C.1 Purchase Import + Item Mapping (recommended primary path) `[MED]`
Gofrugal has **native features that mirror your project**:
- **"Map the items and import the invoice"** and **"Map the purchase invoice fields"** — import a supplier invoice as a purchase, mapping invoice columns to Gofrugal fields.
- **"Purchase Import"** procedure (+ FAQs) with **supplier-specific invoice templates** and **Excel import**; **items can be created directly from the purchase-invoice screen**.
- **Item Mapping** stores the link between the *supplier's* item name/code and *your* item — this is remembered, and items carry an **Alias** and **EAN** field usable for matching. (NetTrade/distribution flows literally call this "Item Mapping" between retailer and distributor codes.)
- **Master Import Tool / QuickStart** and a **Normalisation tool** (HQ) for bulk item migration and keeping codes uniform.

→ **Architectural consequence:** your agent's job becomes "produce a clean, correctly-mapped purchase-import file (Excel/CSV/API payload) using *my* item codes, and maintain the supplier-name → my-item alias table." Gofrugal's own Item Mapping + Alias becomes the persistent store for your self-learning corrections. This is a much smaller, safer build than a custom write API. **Confirm the exact import format and whether it's scriptable headlessly.** `[LOW / CONFIRM]`

### C.2 CSV / template item import `[MED]`
For creating **new items**, Gofrugal downloads an item template (e.g. `itemMigrations.csv`) and re-imports it. Confirmed ServQuick template columns: *Item name, Variant name, Cost price, Selling price, Tax value, Category, Tax inclusive, Service-tax applicable, Service-charge applicable, Packing amount, Status.* RPOS/RetailEasy templates add more (HSN, barcode, MRP, batch — see Part D). Import returns a status report + an **error-record sheet** for rejected rows.
→ Good fit for your "new product detected → after user verifies, create it" flow.

### C.3 Opening Stock Entry (manual UI) `[HIGH]`
Confirmed official feature (RetailEasy on-cloud): a UI screen to record stock **not** entering via a purchase invoice, supporting bulk and single entries. Item selected from the item list (Enter in the Code field, description auto-fills), quantity in the Qty field. Per-line fields captured: **Cost Price, Landing Cost, Sell Price, MRP, Disc% / Disc Amount, GST% / GST TaxAmt, Supplier, Scheme Disc%/Amt/Others, Net Amount, Qty.**
→ This is manual/UI, useful as a fallback and as ground truth for which fields a stock line needs, but **not** an automation target.

### C.4 REST write API `[LOW / CONFIRM]`
The only clearly-documented *writable* REST endpoint is **`POST .../salesOrders`** (create a sales order). **No public documentation confirms a REST endpoint to create a purchase/GRN or a new item.** GRN/purchase-inwards exists as a mobile app ("GoSure GRN") and UI/import, but not confirmed as an API POST.
→ **Do not assume a purchase/item write API exists.** This is the single most important thing to confirm with Gofrugal for your edition. If it doesn't exist, C.1/C.2 (import files) is your write path.

---

## 5. Part D — Standard parameters of a Gofrugal item / stock record

Consolidated from the confirmed Opening-Stock fields, the CSV import template, and item-master KB titles. Fields marked `[HIGH]` are confirmed; others are `[CONFIRM]` (typical for Indian grocery ERP but not verified in an openable source).

**Identity & naming**
- Item Name / Description `[HIGH]`
- Short Name `[CONFIRM]`
- Item Code / SKU `[HIGH]`
- **Alias** (supplier/alternate names) — *directly relevant to your matching problem* `[MED]`
- Barcode / **EAN** `[MED]`

**Classification**
- Category / Sub-category / Department `[CONFIRM]`
- Manufacturer / Brand `[CONFIRM]`
- **HSN code** (mentioned via "HSN Master in HQ") `[MED]`

**Tax & price**
- **MRP** `[HIGH]`
- Sell Price / Selling Price `[HIGH]`
- Cost Price / Purchase Price `[HIGH]`
- Landing Cost `[HIGH]`
- **GST % / Tax value / Tax inclusive flag** `[HIGH]`
- Discount % / Discount Amount, Scheme Disc/Amt `[HIGH]`

**Units & stock**
- **UOM** (unit of measure; UOM-to-ingredient mapping exists) `[MED]`
- Pack / conversion (bulk ↔ retail; "repack bulk items" feature) `[MED]`
- Quantity / Stock on hand `[HIGH]`
- **Batch** and **Expiry** (batch-tracked, critical for grocery) `[CONFIRM]`
- Item Serial No. (opening-stock migration keys on Item Name, Serial No., Alias, EAN) `[MED]`
- Reorder level / min-max `[CONFIRM]`
- Supplier link `[HIGH]`

> You said you'll supply the real data later — that's the right move. Treat the above as the *shape* to expect; the authoritative field list is whatever the item-master screen and the import template in *your* installation show.

---

## 6. Part E — The self-learning correction loop

Concrete design (maps ALER + human-in-the-loop pattern onto your workflow):

1. **Embed the catalogue once.** Run each Gofrugal item (name + alias + category) through a multilingual sentence-embedding model (frozen bi-encoder). Store vectors in a small vector index (e.g. FAISS / pgvector / SQLite-VSS). Re-embed only new/changed items.
2. **Match a new invoice line:** embed the (post-corrected) invoice text → nearest-neighbour top-k from the index → an LLM re-ranks/decides the best item **with a confidence score**.
3. **Route by confidence:**
   - High confidence → auto-map (still shown for review).
   - Low confidence / no good match → **flag as "possible new product — please verify."**
4. **Capture the correction.** When you accept/fix a mapping, store `(supplier, raw invoice text) → your item code` as a labelled pair. Two learning effects:
   - **Immediate & deterministic:** write the raw supplier text into Gofrugal's **Alias** field (or a local alias table) so the exact string matches next time — no model needed. This alone kills most repeat errors.
   - **Generalising:** periodically retrain the lightweight classifier / adjust matching thresholds on accumulated pairs (active learning). Frozen embeddings mean this is cheap.
5. **Never silently write.** New products and low-confidence maps always require your confirmation before anything is imported — this is what actually fixes your "software ≠ physical stock" problem.

The **Alias table is the heart of the self-learning system** and it doubles as data Gofrugal itself understands.

---

## 7. Part F — Recommended architecture & infrastructure

```
Supplier invoice (photo/PDF, Marathi/English, misspelled)
        │
        ▼
[1] Vision-LLM extraction  → structured JSON line items
        │   (optional: dedicated OCR engine per script + mBART post-correction
        │    if pure vision-LLM underperforms on your Marathi invoices)
        ▼
[2] Normalise / clean each line (language, units, qty, price)
        ▼
[3] Match against local Gofrugal catalogue
        │   embeddings (frozen bi-encoder) → top-k → LLM re-rank + confidence
        ▼
[4] Human review UI  ── matched (review) / low-confidence / NEW PRODUCT flag
        │        ▲
        │        └── your corrections → Alias table + labelled pairs (self-learning)
        ▼
[5] Write-back builder → Purchase Import file (Excel/CSV) OR API payload
        ▼
Gofrugal: Purchase Import / Item Mapping / CSV item import  (confirm exact channel)

Catalogue sync: GET /WebReporter/api/v1/items  → local DB + vector index (scheduled)
```

**Component choices**
- **Extraction:** a vision-capable LLM (JSON-structured output). Add a dedicated OCR engine (Document AI / Surya / Tesseract) + mBART post-correction *only if* the vision-LLM alone is weak on your Marathi invoices — decide with a benchmark on real invoices.
- **Matching:** multilingual embeddings + vector index + LLM re-rank.
- **Store:** one small relational DB (Postgres) for items cache, alias table, correction log, audit trail; a vector index alongside (pgvector keeps it in one place).
- **Review UI:** a lightweight web app — this is where the human-in-the-loop happens and is non-negotiable for stock accuracy.
- **Gofrugal I/O:** read via API on a schedule; write via the confirmed import channel.

**Infrastructure & cost (own estimate — validate against real volume):**
- A single small cloud VM or even the in-store PC can host the app + DB; this is low-throughput (tens–hundreds of invoices/month).
- **LLM/OCR is the main running cost** and it's roughly *per invoice*, not fixed. Order-of-magnitude only: a vision-LLM pass over an invoice image + matching a few dozen line items is typically a few cents to a few tens of cents per invoice at current API prices. At, say, 200 invoices/month that is plausibly single-digit dollars/month for the AI calls — but this depends entirely on your invoice volume, page count, and chosen model, so **treat it as a rough estimate to be re-costed once volume is known.** Self-hosting mBART/Tesseract trades API cost for a GPU/ops burden and is only worth it at high volume.

---

## 8. What to confirm with Gofrugal before building (highest-value questions)

1. For **my edition/version**, is there a REST API to **create a purchase entry / GRN and to create a new item**, or is the only supported programmatic write the **Purchase Import / CSV / Master-Import** file? (Determines whether write-back is API or file-based.)
2. Exact **items API** JSON schema, filter/pagination params, and the **licensing tier / API key** needed to enable it.
3. Full **item-master field list** and which fields are **mandatory** when creating an item via import/API (esp. HSN, GST, UOM, batch, barcode, MRP, category).
4. Whether **Item Mapping / Alias** can be read and written programmatically (so the self-learning loop can persist corrections into Gofrugal, not just locally).
5. Where the API is served (local POS server port `8482` vs. a cloud endpoint) for your deployment, and any rate limits.

---

## 9. Confidence, assumptions & gaps

- **Strongest evidence** (primary academic sources, `[HIGH]`): the entire AI pipeline — OCR on Indian scripts, Marathi/Hindi post-OCR correction, LLM/embedding product matching, and the active-learning self-learning loop.
- **Medium evidence** (`[MED]`): Gofrugal REST API existence, `X-Auth-Token` auth, `GET /items` and salesOrder endpoints, Purchase Import / Item Mapping / Alias / CSV import features. These come from **search-engine snippets of official Gofrugal KB pages**, because the network policy for this session **blocked direct access to `community.gofrugal.com`** (403 at the egress proxy) — the same block hit the research pipeline. Nothing here is fabricated, but the full pages were not read.
- **Weakest / must-confirm** (`[LOW / CONFIRM]`): existence of a purchase/GRN/item-creation **write API**, exact JSON field names, mandatory fields, licensing, and server location. Also: matching-accuracy figures are from **English e-commerce** benchmarks, and correction datasets are **general-domain**, so real Marathi-grocery-invoice accuracy is an extrapolation until tested on your data.
- **Assumption made:** low invoice throughput (grocery store scale). If you process thousands of invoices/month, the cost and self-hosting trade-offs change.

---

## 10. Sources

**Gofrugal (official — accessed via search snippets; pages blocked for direct fetch this session):**
- API Integration overview — https://community.gofrugal.com/portal/en/kb/articles/api-integration
- RetailEasy API Integration KB — https://community.gofrugal.com/portal/en/kb/gofrugalretaileasy/ecommerce-integration/api-integration
- List all items (API) — https://community.gofrugal.com/portal/en/kb/gofrugalretaileasy/ecommerce-integration/api-integration/articles/list-all-items
- API to create a sales order — https://community.gofrugal.com/portal/en/kb/articles/api-for-create-a-sales-order
- Which APIs for website integration — https://community.gofrugal.com/portal/en/kb/articles/what-is-api-integration-which-api-do-we-provide-for-website-integration
- Opening Stock Entry (RetailEasy on-cloud) — https://community.gofrugal.com/portal/en/kb/articles/how-to-make-an-opening-stock-entry-in-retaileasy-on-cloud
- Item Master — https://community.gofrugal.com/portal/en/kb/articles/item-master-19-8-2025
- Map items & import the invoice — https://community.gofrugal.com/portal/en/kb/articles/item-mapping-importing-the-invoice
- Map the purchase invoice fields — https://community.gofrugal.com/portal/en/kb/articles/mapping-the-purchase-invoice-fields
- Purchase Import procedure — https://community.gofrugal.com/portal/en/kb/articles/purchase-import
- Import items from CSV — https://community.gofrugal.com/portal/en/kb/articles/import-option
- Manage HSN Master in HQ — https://community.gofrugal.com/portal/en/kb/articles/learn-about-managing-hsn-master-in-hq
- Creating an item (ServQuick) — https://www.gofrugal.com/support/servquick/create-item.html
- HQ master data management — https://www.gofrugal.com/hq/master-data-management.html
- GoSure GRN — https://www.gofrugal.com/inventory-app/grn-goods-received-note.html
- POS/e-commerce integration — https://www.gofrugal.com/ecommerce-pos-integration.html

**Academic / technical (primary, verified):**
- OCR engine benchmark on Brahmic scripts (RANLP 2025) — https://arxiv.org/pdf/2507.18264
- RoundTripOCR: post-OCR correction for Devanagari incl. Marathi/Hindi (ICON 2024) — https://arxiv.org/pdf/2412.15248
- Automated Invoice Data Extraction: LLM + OCR (2025) — https://arxiv.org/abs/2511.05547
- Cost-efficient prompt engineering for unsupervised product matching (Springer 2024) — https://link.springer.com/article/10.1007/s44163-024-00159-8
- Peeters & Bizer, LLMs for product matching — https://arxiv.org/abs/2305.03423
- ALER: active-learning entity resolution with frozen embeddings (2026) — https://arxiv.org/pdf/2601.20664
- CIKM-2019 human-in-the-loop entity-resolution tutorial — https://dl.acm.org/doi/10.1145/3357384.3360316
- Reference repo (illustrates the gap, not a template) — https://github.com/ShafqaatMalik/llm-based-invoice-ocr
