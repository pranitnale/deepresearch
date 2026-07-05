# Gofrugal Purchase-Import Excel Formats — Field Spec (from live install)

**Source:** Screenshots of GOFRUGAL RetailEasy → *Purchase Entry → Excel Mapping & Importing*, store "RANJIT BAZAAR", GRN Type = **Direct**, FormulaID = 3. Captured by the store owner from their own installation → **primary, authoritative** (supersedes the earlier "CONFIRM"-tagged field guesses in `gofrugal-invoice-ocr-feasibility-research.md`).

**Original screenshots** (saved for future context) — in `screenshots/`:
- `gofrugal-purchase-import-01-standard.png`
- `gofrugal-purchase-import-02-serialized.png`
- `gofrugal-purchase-import-03-matrix.png`
- `gofrugal-purchase-import-04-kit.png`
- `gofrugal-purchase-import-05-non-matrix.png`

This is the **write-back format** for the agent: the agent's final output is an Excel file in one of these layouts, imported into a GRN/Purchase Entry.

---

## 1. The five item/GRN types

Gofrugal defines each item as a **type**, and the import layout changes with it:

| Type | What it's for | Relevance to a grocery store |
|---|---|---|
| **Standard** | Normal single item with batch/expiry | **Primary — ~all grocery items** |
| **Serialized** | Items tracked by serial number (electronics) | Rare / none |
| **Matrix** | Variant items (size × colour, apparel) | Rare / none |
| **Kit** | Bundle / combo of other items | Occasional (gift packs, combos) |
| **Non Matrix** | Superset layout (Standard + serials) | Fallback / mixed |

→ **For this project, "Standard" is the default output format.** The others are documented so the app can handle edge cases, but the grocery use-case is Standard.

---

## 2. Reading the columns

- **DataType → meaning of "Length":**
  - `Int` length 4 = 4-byte integer, `Money` length 8 = 8-byte currency, `Decimal` length 2 = 2 decimal places.
  - `Text`/`text` length N = **max N characters** — the agent must **truncate/validate** to these limits (e.g. ItemName ≤100, ItemAlias ≤100, Batch No ≤30, ManualBarcode ≤60). `[interpretation — confirm]`
- **`Map Excel Field` column** is filled **interactively in this screen**: you browse your Excel file, then map each Gofrugal field to one of your Excel columns. So the Excel column *headers* can be anything, but → **recommendation: name our headers identically to the "Field Description" values** so mapping is 1:1 and can be saved as a reusable mapping template.

---

## 3. Field matrix (which field appears in which type)

Order within each type is top-to-bottom as shown in the UI. ✓ = present.

| # | Field Description | DataType | Len | Standard | Serialized | Matrix | Kit | Non Matrix |
|---|---|---|---|:--:|:--:|:--:|:--:|:--:|
| 1 | ItemCode | Int | 4 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2 | ItemName | Text | 100 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 3 | ItemAlias | Text | 100 | ✓ | ✓ | — | ✓ | ✓ |
| 4 | EanCode | Text | 20* | ✓ | — | ✓* | ✓ | ✓ |
| 5 | QTY | Int | 4 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 6 | FreeQTY | Int | 4 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 7 | PurchasePrice | Money | 8 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 8 | SellingPrice | Money | 8 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 9 | MRP | Money | 8 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 10 | ItemDiscPerc | Decimal | 2 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 11 | MeterQty | Int | 4 | ✓ | — | ✓ | — | ✓ |
| 12 | HSN Code | text | 8 | ✓ | — | ✓ | — | ✓ |
| 13 | ManualBarcode / Manual Barcode | Text | 60 | ✓ | — | ✓ | — | ✓ |
| 14 | Min Selling | Money | 8 | ✓ | — | — | — | ✓ |
| 15 | Apply MinSelling fr Prev Batch (Yes/No) | Text | 3 | ✓ | — | — | — | ✓ |
| 16 | Cash Disc Perc | Decimal | 2 | ✓ | — | ✓ | — | ✓ |
| 17 | Batch No | Text | 30 | ✓ | — | ✓ | — | ✓ |
| 18 | Expiry Date | Text | 30 | ✓ | — | — | — | ✓ |
| 19 | SerialNo1 | Text | 25 | — | ✓ | — | — | ✓ |
| 20 | SerialNo2 | Text | 25 | — | ✓ | — | — | ✓ |
| 21 | SerialNo3 | Text | 25 | — | ✓ | — | — | ✓ |
| 22 | SerialNo4 | Text | 25 | — | ✓ | — | — | ✓ |
| 23 | SerialNo5 | Text | 25 | — | ✓ | — | — | ✓ |
| 24 | CATEGORY1 | Text | 100 | — | — | ✓ | — | — |
| 25 | CATEGORY2 | Text | 100 | — | — | ✓ | — | — |
| 26 | CATEGORY3 | Text | 100 | — | — | ✓ | — | — |

\* **EanCode inconsistency:** Standard/Kit/Non-Matrix show length **20**; Matrix shows "Eancode" length **25**. Serialized has no EanCode column. Minor — validate to the tighter limit (20) to be safe.

**Structural notes:**
- **Non Matrix = Standard + SerialNo1-5** (the union layout, minus CATEGORY).
- **Serialized** drops batch/expiry/HSN/barcode/discount extras and adds SerialNo1-5.
- **Matrix** adds CATEGORY1-3 (the variant dimensions) and drops ItemAlias, Expiry Date, Min Selling.
- **Kit** is the minimal core (10 columns).
- The **10 core columns** (ItemCode, ItemName, QTY, FreeQTY, PurchasePrice, SellingPrice, MRP, ItemDiscPerc — plus ItemAlias & EanCode in most) exist in every type.

---

## 4. Canonical agent output — STANDARD template

The app's default deliverable. Exact column order:

```
ItemCode | ItemName | ItemAlias | EanCode | QTY | FreeQTY | PurchasePrice |
SellingPrice | MRP | ItemDiscPerc | MeterQty | HSN Code | ManualBarcode |
Min Selling | Apply MinSelling fr Prev Batch (Yes/No) | Cash Disc Perc |
Batch No | Expiry Date
```

### How each column is filled from a supplier invoice

| Column | Source | Notes |
|---|---|---|
| **ItemCode** | Matching engine → store's item master | Blank/flagged if new product (see Q1) |
| **ItemName** | Store's canonical name (from master, or proposed for new) | ≤100 chars |
| **ItemAlias** | **Raw supplier text from the invoice** | ⭐ **This is the self-learning anchor** — writing the supplier's spelling here means Gofrugal itself matches it next time |
| **EanCode** | Invoice barcode, if printed | else blank |
| **QTY** | Billed quantity | |
| **FreeQTY** | Scheme / free quantity | often 0 |
| **PurchasePrice** | Invoice rate (per unit, pre-tax or as per Formula) | confirm tax treatment vs FormulaID |
| **SellingPrice** | From master, or derived | store policy |
| **MRP** | Invoice MRP | grocery invoices usually print MRP |
| **ItemDiscPerc** | Invoice line discount % | |
| **MeterQty** | Loose/weighed qty | usually blank for packaged goods |
| **HSN Code** | Invoice HSN | ≤8 chars |
| **ManualBarcode** | Store barcode if used | else blank |
| **Min Selling / Apply MinSelling** | Store policy | usually blank/default |
| **Cash Disc Perc** | Invoice cash discount | |
| **Batch No** | Invoice batch | ≤30 chars |
| **Expiry Date** | Invoice expiry | Text(30) — **confirm exact format**, likely dd/mm/yyyy |

---

## 5. Open questions to confirm with Gofrugal (blockers for the write flow)

1. **Does the import CREATE a new item** when ItemCode is blank/new, or only add stock to an **existing** item? → Decides how the "new product detected" flow ends.
2. **What is the match key on import** — ItemCode, ItemAlias, or EanCode? Can we import with only **ItemAlias/EanCode** and let Gofrugal resolve ItemCode? → If yes, the agent can lean on Gofrugal's own matching + our Alias table.
3. **Which columns are mandatory** vs optional, per type?
4. **Expiry Date format** expected in the Text(30) field.
5. **GRN Type "Direct" and FormulaID 3** — what do these control (tax formula, price basis), and must they be chosen per import?
6. **ItemCode** — store-assigned or system-generated? (It's Int → likely system-generated; leave blank for new items?)
7. **Can the field-mapping be saved as a template** so the map step isn't repeated every import? (The UI implies a manual map each time.)

---

## 6. Implications for the app (to expand in the PRD)

- The agent's core job = **produce a valid Standard-layout Excel row per invoice line**, with **ItemCode resolved by matching** and **ItemAlias = the raw supplier text** (the learning loop's persistent memory).
- Because Gofrugal has its own Item Mapping + Alias, the self-learning corrections we capture can be pushed *into Gofrugal* (as aliases), not just kept locally — so accuracy improves on both sides.
- Grocery = Standard only, which keeps v1 simple; Kit/Matrix/Serialized are post-v1.
- The human-in-the-loop review screen should show, per line: matched ItemCode+Name, confidence, the raw invoice text (→ alias), and a "new product?" flag — then export the approved rows as the Standard Excel.
