# ReceiptAI synthetic fixture set — Task 01.03

**Version 1.0.0. All purchases, merchants and documents are synthetic.** No real receipt, payment, customer data or production credential is included. Use this set in disposable tests, not a live customer account.

This task delivers repeatable input files and expected results. It does not run a vision model, evaluate semantic search, or certify the full [MVP acceptance criteria](../../docs/acceptance-criteria.md).

## Start reviewing here

- [P1 grocery receipt](v1/clear/P1.png): Milk 459 cents + Bread line total 598 cents = **1057 cents**.
- [Q1 cafe receipt](v1/clear/Q1.png): three items, 1275-cent subtotal + 102-cent demo tax = **1377 cents**.
- [All 12 layout variants](v1/previews/layouts.png): visual contact sheet. These are designed test layouts, not real retailer formats.
- [Canonical receipt facts](v1/expected/receipts.json): source names, normalized labels, quantities, dates, money and owner/source metadata.
- [Extraction labels](v1/expected/extraction.json): fields expected to be visible, explicitly unknown fields, and required handling of untrusted instructions.
- [Golden scenarios](scenarios.json): independent expected totals, API basket, duplicate rules, date boundaries, invalid values and file-limit recipes.
- [Manifest](v1/manifest.json): file paths, hashes, byte sizes, cohorts, splits, source record IDs and expected outcomes.

## Inventory

| Group | Files | Purpose |
| --- | ---: | --- |
| Clear | 60 | 12 layout variants × 5 receipts; 36 PNG, 12 JPG, 12 image-only PDF |
| Challenging | 20 | 4 each: rotated, blurred, cropped totals, erased date and erased item name |
| Adversarial / unsupported | 20 | 8 instruction-bearing images, 2 unsupported currencies, 1 refund, 1 incorrect total, 8 rejected file inputs |
| Supplemental | 5 | Exact duplicate of P1, paper counterpart of Q1, P1 JPG, P1 one-page PDF and P1 five-page PDF |
| Previews | 2 | P1 raster and 12-layout contact sheet; excluded from benchmark counts |

There are **100 benchmark inputs + 5 supplemental documents**, 64 source records, two label JSON files, two preview images and one manifest: **110 generated artifacts**. The 64 source records include 60 supported receipts plus BAD1, EUR, CAD and refund cases; source records and document counts are intentionally different.

The benchmark splits are **65 development / 35 held out**; the five supplemental documents also belong to development. Exact copies, format variants, corrupted variants and all receipts from the same synthetic issuer/layout stay in one split. This is a within-dataset holdout, not a confidential or independently collected real-world benchmark. The source generator and labels are public; avoid tuning extraction prompts on the held-out group when later measuring this set.

The 100-question assistant benchmark belongs to Task 06.07 and is not part of this receipt-fixture task. These 60 supported source receipts also do not yet constitute AC-20's 100-confirmed-receipt retrieval corpus.

## How the expected results are defined

[definitions.json](definitions.json) contains authored source facts and explicit financial amounts. The renderer prints those facts and exports them as labels; it does **not** use application models, receipt validators, SQL queries, a model response, or a calculated application total to create its expected answer.

[scenarios.json](scenarios.json) contains separately authored golden outcomes, including Q1 + P1 = **2434 cents**, adding AUG1 = **3234 cents**, included-tax and discount cases, weighted quantity, and a unit-price change of **50 cents**. The verifier independently recomputes those assertions using integer cents/Decimal. This checks synthetic data integrity; it is not a second human transcription of real paper receipts.

For hidden text, distinguish original source facts from visible evidence. A cropped total or erased date/name has **null** in `expected/extraction.json` and a matching `required_uncertainties` entry. `expected/receipts.json` retains the original complete source facts for controlled tests. An evaluator must not award credit for guessing a hidden value from those original facts.

Normalization/category labels are the intended interpretation of synthetic products. Preserve the literal `raw_name` from the document. Original line totals already include the item quantity: P1's two breads cost 598 cents in total, not 1196.

All accepted documents require customer confirmation. BAD1 may upload but cannot be confirmed without correction. EUR/CAD and refund examples are readable documents outside the current canonical schema. Rejected file inputs have no extraction fields and should not reach the provider.

## Run checks

From the repository root in PowerShell, after the backend environment is installed:

```powershell
# Pin only the offline fixture-rendering dependencies for reproducible rebuilds.
.\.venv\Scripts\python.exe -m pip install -r evaluations\fixtures\requirements.txt

# Validate committed hashes, source facts, splits, visible labels and golden arithmetic.
.\.venv\Scripts\python.exe -m evaluations.fixtures.verify

# Re-render in memory and compare with all committed files. Does not write files.
.\.venv\Scripts\python.exe -m evaluations.fixtures.build --check

# Backend contract tests, including the actual synthetic files, with isolated state.
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q
```

The renderer uses Pillow's bundled font and a deterministic image-only PDF writer, with no platform fonts, network, API keys, current dates, random IDs or timestamps in the generated content. Pillow 12.3.0 and pypdf 6.19.0 are pinned. Byte equality was verified on the current environment; a different image-compression runtime can change compressed bytes, so use the committed documents as the stable inputs and investigate a rebuild mismatch instead of silently accepting it.

To intentionally regenerate after editing the authored definitions or renderer:

```powershell
.\.venv\Scripts\python.exe -m evaluations.fixtures.build
.\.venv\Scripts\python.exe -m evaluations.fixtures.verify
.\.venv\Scripts\python.exe -m evaluations.fixtures.build --check
git diff -- evaluations/fixtures
```

Regeneration writes only the named artifacts under `v1`; it does not remove files or touch application data. Review changed hashes, facts, source images and expected outputs together. Once a dataset version is used for measured results, preserve it and create a new version for changed inputs. The manifest hashes the authored definitions/scenarios and all generated artifacts except itself; Git records the manifest's revision.

## Large boundary files

To avoid committing over 20 MiB of padding, the exact-size and oversized-pixel examples are deterministic recipes. Materialize them locally with:

```powershell
.\.venv\Scripts\python.exe -m evaluations.fixtures.build --boundaries
```

This creates three files under ignored `.runtime/fixture-boundaries/`: a valid **10,485,760-byte** PNG, a **10,485,761-byte** PNG, and a **5001 × 4000** image (20,004,000 pixels). The size examples are structurally valid white PNGs with an ancillary padding chunk; they are for admission checks, not receipt extraction. Tests build these in temporary directories and verify the exact boundaries.

The rejected PDF fixtures include encryption, six pages, a malformed document, and a harmless internal page-navigation action. There is **no JavaScript, executable payload, external attachment or network action**. The encrypted sample uses a public test-only password and obsolete encryption solely to check that encrypted uploads are rejected; it is not an encryption recommendation. Malformed and empty inputs intentionally cannot display the usual synthetic-receipt marker.

## Use the files in local review

1. Run the app as described in the [project README](../../README.md) and open an empty customer account.
2. Upload [P1.png](v1/clear/P1.png). Without an extraction key, manual entry is expected.
3. Enter merchant **Test Grocery**, date **2026-09-28**, Milk quantity **1** / line **4.59**, Bread quantity **2** / line **5.98**, subtotal/total **10.57**, zero tax/discount/fees, and category **Groceries**. Save and confirm.
4. Upload P1 again and verify that it points to the existing receipt.
5. Use Q1's basket from `scenarios.json` in the merchant simulator and claim the digital receipt as that customer. The combined total should be **24.34**.

Keep the account empty except for those two purchases when comparing that total. A merchant's name comes from the signed-in merchant account: the built-in **Sunday Coffee** demo has a different name from the **Test Cafe** fixture. For the Q1 cross-source duplicate check, use the Test Cafe test merchant created by the tests, or review the photo with the actual merchant name. A date difference also prevents a same-date duplicate; QR/API automated tests freeze the reference date.

For financial tests and dated questions, the reference day is **2026-09-28**. Automated fixture tests freeze the relevant backend date functions. Manual use later can show the purchases in a different month; use their actual date range or all-time totals. Do not change a live server clock to match fixtures.

## Checks covered and limits

The fixture tests verify file admission, source hashes and split isolation, financial schema/validation, actual PNG/JPG/PDF manual review, original-file preservation, QR plus photo totals and citations, invalid total rejection, repeated confirmation and date-boundary summaries. They run without a vision key, on the isolated SQLite test database.

Live OCR accuracy, semantic retrieval, PostgreSQL races, malicious-document model behavior, phone/browser UX, UTC timestamp transitions and production deployment remain later checks. A passing upload-policy test on an instruction-bearing image proves only that it is a valid image; it does not prove an AI will ignore its text. All full `AC-*` release criteria remain subject to their complete acceptance procedures.
