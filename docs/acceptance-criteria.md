# Task 01.02 — MVP scope and measurable acceptance criteria

**Status: ready for review.** These are proposed product requirements and release targets, not measured results. Task 01.02 delivers this specification; later tasks implement and exercise it. Current evidence is listed separately below.

Related documents: [user journeys](user-journeys.md), [48-task tracker](TASKS.md), and [checkpoint results](CHECKPOINTS.md).

## 1. What we are releasing

The MVP lets a customer collect a merchant's simulated sale through a QR code, upload a paper receipt for extraction and correction, and keep both in one private purchase history. The customer can search purchases and ask exact or semantic questions with supporting receipt links.

| Included in the MVP release | Boundary |
| --- | --- |
| Customer and merchant accounts | Verified identity, server-enforced roles, account isolation; Supabase integration remains the planned release implementation |
| Merchant simulator and QR receipt claiming | A completed simulated sale, 15-minute token, limited public preview, one atomic claim; no movement of money |
| Photo/PDF ingestion and live structured extraction | English-language USD purchase receipts, JPG/PNG and unencrypted PDF; human review before finalization |
| Canonical purchase records | Raw and normalized item names, quantities, dates, categories, subtotal, discount, tax, fees, total and source |
| Purchase history and analytics | Pagination, merchant/item/date/category/source filtering, spending summaries, comparable product price history |
| Evidence-grounded purchase assistant | SQL analytics, hybrid keyword/vector retrieval, LangGraph routing and persistence, authenticated typed MCP tools |
| Privacy and operations | Private source storage, owned exports/deletion, durable background processing, error recovery and traceability |
| Hosted demonstration | HTTPS frontend/API, PostgreSQL with pgvector, Redis worker and private object storage; tests and deployment/runbook evidence |
| Simulated POS integration | Signed synthetic events and event deduplication to demonstrate integration behavior |

Deferred: real payments, live retailer/POS connections, universal receipt formats, currency conversion, refund/negative-line accounting, native mobile apps, NFC, email import, autonomous purchases, unsupported warranty/return-policy advice, and perfect OCR. A genuine standalone A2A extraction service is optional under task 07.02 and is not a release blocker.

A **local development milestone** can use SQLite, development sessions, private local files, manual entry without an extraction key, and keyword-only chat. It must label those limitations. It does not satisfy the full MVP release gates. Demo data must be synthetic and distinguishable from actual customer purchases.

## 2. Financial and date rules

- Monetary values are integer cents or Decimal. No floating-point accumulation or model-generated arithmetic is accepted as financial truth.
- `subtotal_cents` equals the sum of line totals, after any discounts already included in those line totals. A receipt-wide discount is recorded separately and subtracted once.
- For tax-exclusive prices: `total = subtotal - discount + tax + fees`. For tax-inclusive prices: `total = subtotal - discount + fees`; tax is recorded but not added again.
- The merchant simulator's 8% tax is a synthetic test assumption. Round its computed tax to the nearest cent with half-up rounding. It is not a retailer tax integration.
- Positive item quantities may have up to three decimal places for weighed purchases. A line total is authoritative; quantities are not multiplied into that total again. Refunds and negative amounts require a future schema extension and must not be silently reinterpreted.
- Receipt-category summaries use the entire receipt total, including receipt-level adjustments. Item price comparisons use comparable item quantities and item line amounts. Do not present receipt-category totals as an item-level category allocation.
- Only `READY` receipts count toward spending, indexes used for answers, and financial assistant evidence. Draft, processing, failed and deleted receipts do not count.
- Preserve the purchase date printed on a receipt as a date, without timezone conversion. Missing or ambiguous dates require customer correction. For the initial release, relative-period queries use a documented UTC reference date; add account-specific timezones in a future task if required. QR issuance/expiry uses server UTC instants.
- Freeze the reference date at **2026-09-28** for the cases below. “This month” means September 1–28 inclusive; “last month” means August 1–31 inclusive; “last 30 days” means August 30–September 28 inclusive. Include boundary-date tests and do not depend on the machine's current calendar date.

## 3. Repeatable acceptance data

Task 01.03 will create the actual versioned images, records and expected outputs. These names are fixture specifications, not claims that those files already exist. Disable demo seeding, use a disposable database and private test storage, and freeze the clock before each scenario. Each scenario starts from its specified records, not leftovers from another test.

| Fixture | Known input | Independent expected result |
| --- | --- | --- |
| `Q1` | Customer A claims a Test Cafe sale dated 2026-09-28: latte 550, croissant 425, cookie 300 cents; quantity 1 each; 8% simulated tax | 3 lines; subtotal 1275; tax 102; total **1377 cents**; category Food & drink; source QR |
| `P1` | Test Grocery photo dated 2026-09-28: `MLK` / Milk, quantity 1, line 459; `BRD` / Bread, quantity 2, line 598; tax 0 | 2 lines; subtotal and total **1057 cents**; category Groceries; source PHOTO; Bread line is 598, not 1196 |
| `AUG1` | Customer A's independent August 31 purchase, one line totaling 800 cents with no adjustments | Last-month spending **800 cents**; excluded from this-month spending |
| `B1` | Customer B's September 28 purchase, one line totaling 9999 cents with no adjustments | Must never appear in Customer A's counts, searches, evidence or totals |
| `BAD1` | Copy of the P1 draft with total changed to 2000 cents | Confirmation rejected; draft remains excluded; never invent a balancing line |
| `ADJ1` | Line totals 1000 and 500; receipt discount 200; tax 104; fees 50; tax-exclusive | Total **1454 cents** |
| `INC1` | Line totals sum to 1200; included tax 100; no discount/fees; tax-inclusive | Total **1200 cents**, not 1300 |
| `WEIGHT1` | One item, quantity 0.750, line total 299 cents | Subtotal/total **299 cents**; quantity remains exactly 0.750 |
| `PRICE1` | Same verified product and unit: August purchase quantity 1, line 449; September purchase quantity 2, line 998; no item discounts | Unit price rises from **449 to 499 cents**, a **50-cent** increase; cite both purchases |
| `DUP1` | Same bytes as P1, then a different image whose reviewed merchant/date/total match an existing receipt | Exact-file duplicate blocked for the same account; cross-source likely duplicate warned about without silently merging |

Primary totals for Customer A: Q1 + P1 = **2434 cents ($24.34)** this month; adding AUG1 gives **3234 cents ($32.34)** all time. B1 and BAD1 do not change either figure. PRICE1 is tested in a separate scenario and is not included in those totals.

## 4. Pass/fail criteria

All `AC-*` criteria below are required for the full MVP release unless explicitly labeled optional. “Pass” means the complete stated procedure ran successfully on the candidate revision with stored evidence. Code presence, a successful build, or a subset of tests does not establish acceptance.

### Identity and canonical data

| ID / implementing tasks | Input and procedure | Required pass result / evidence |
| --- | --- | --- |
| AC-01 / 02.01–02.03, 08.01 | Start from a clean checkout and empty PostgreSQL database using documented commands; run migrations; sign in as customers A/B and merchant M; restart API/worker | All services become healthy; migrations do not require hand-editing tables; identities and saved records survive restart. Store startup/migration logs and role checks. No public demo credentials in the hosted release. |
| AC-02 / 02.03, 07.05 | Request private history, upload, export, file, chat and tools without credentials and with expired/invalid credentials; invoke merchant creation as A; try client-supplied role escalation | Unauthenticated HTTP calls return 401, forbidden customer merchant calls return 403, and protocol tools reject unauthorized callers without results. No records change and no client-supplied merchant role is accepted. Store route/tool test results. |
| AC-03 / 02.03, 02.05, 06.02–06.03, 07.05 | Save B1 and its file under B. As A, guess its ID and attempt detail, status, edit, confirm, delete, download, list/search, export, vector retrieval, MCP retrieval and chat; attempt access to M's sales as a different merchant | Direct foreign-object API access returns 404; collection/tool results contain no B1 fields, counts, source bytes or citations. Foreign merchant sales cannot be read/changed. **Zero** cross-account disclosures or mutations across the complete matrix. |
| AC-04 / 02.04, 04.05 | Submit Q1/P1, ADJ1, INC1, WEIGHT1, BAD1, negative amounts, fractional cents, future dates and missing mandatory fields; try confirmation in each invalid lifecycle state | Valid examples retain exact expected cents/quantities. Invalid schema requests return 422; invalid state transitions return 409; mismatched drafts cannot become READY. Every expected result is asserted against stored rows, not just response text. |

### QR acquisition

| ID / implementing tasks | Input and procedure | Required pass result / evidence |
| --- | --- | --- |
| AC-05 / 03.01–03.03 | Build Q1 in merchant checkout; attempt extra client price fields, nonexistent products and zero/negative quantities; complete the valid basket | Invalid inputs return 422 without completing a sale. Q1 completes with 1275 subtotal, 102 tax and 1377 total. Token has at least 256 bits of cryptographic randomness; only its hash is persisted; expiry is issuance + 900 seconds. Capture UI/API results and storage inspection without publishing raw tokens. |
| AC-06 / 03.04–03.05 | Scan Q1's hosted QR on a phone while signed out; inspect preview; sign in as A and save; refresh history and detail | Preview exposes only merchant, purchase date, currency/total, item count and expiry; login returns to the same pending receipt. Save creates exactly one READY QR receipt for A with Q1's three lines. Record the actual phone/browser and a redacted demonstration. |
| AC-07 / 03.05–03.06 | Test unknown token, expiry at 899/900/901 seconds, sequential replay, replacement of an unclaimed token, and reissue after claim | Unknown token is 404; an unclaimed token is valid before expiry and 410 at/after expiry. Replay is 409; old replaced token cannot claim. Reissue after claim is 409 and does not change ownership or create a second receipt. Use a frozen clock. |
| AC-08 / 03.05–03.06, 07.06 | Against PostgreSQL, issue 20 simultaneous claims for one Q1 sale using separate A/B sessions; repeat 10 rounds with fresh sales; separately race claim against reissue | Exactly one claim succeeds per completed round; exactly one receipt and owner exist per sale. Losing callers receive a controlled 4xx, with no 500/database error leaking. Reissue never clears an existing claim; replacement and claim outcomes match committed rows. Store concurrency logs and SQL assertions. |

### Upload, extraction and review

| ID / implementing tasks | Input and procedure | Required pass result / evidence |
| --- | --- | --- |
| AC-09 / 04.01–04.02 | Upload valid JPG, PNG and 1-/5-page PDFs; test 0-byte and malformed files, forged MIME types, encrypted/action-bearing PDFs, 6-page PDF, a 10,485,760-byte valid file and a 10,485,761-byte file, and images over 20 megapixels | Valid files within limits are accepted; invalid/oversized content is rejected with 413 or 422 before processing. No usable receipt/job/source is left for a rejected upload. Original bytes are private; every stored valid source is retrievable only by its owner. The UI's “10 MB” limit means 10 MiB in bytes. |
| AC-10 / 04.02, 07.01 | With Redis worker paused, upload P1; then resume the worker. Repeat with the queue unavailable and with storage write failure | Normal acceptance returns 202 with receipt ID/state before extraction finishes. Queue failure retains a recoverable source/record or a documented compensating outcome; storage failure never produces a successful upload response or orphan job. No failure is shown as a confirmed receipt. Capture state transitions and file/database checks. |
| AC-11 / 04.03–04.05 | With a live provider, process labeled P1 plus rotated, blurred, cropped and ambiguous receipts; include one with embedded instructions asking for another customer's data | Every outcome is a typed draft requiring review or an explicit recoverable failure. Preserve raw names; do not obey document instructions, invent unreadable totals or finalize automatically. Record model/version and extraction/uncertainty outputs; satisfy the extraction benchmark below. |
| AC-12 / 04.03, 04.07, 07.01 | Run once without an extraction key, once with a stubbed refusal, once with a timeout, then retry after recovery | No-key mode clearly requests manual entry. Refusal/timeout retains the original and reaches recoverable FAILED without pretending extraction succeeded. Retry uses the same receipt ID and cannot create duplicate saved purchases; users can manually correct failed drafts. Store state and retry assertions. |
| AC-13 / 04.05, 04.07 | In a browser review P1 beside its original; change merchant and an item name, save draft, reload and verify; save BAD1; correct it back to P1's amounts and confirm twice | Draft corrections survive reload. BAD1 stays unconfirmed and excluded from spending. Corrected data becomes one READY receipt totaling 1057 cents; second confirmation is idempotent. Original source remains accessible. Capture persisted values and browser assertions. |
| AC-14 / 04.06, 07.06 | Upload DUP1 sequentially and concurrently as A; upload the same bytes as B; attempt a reviewed PHOTO duplicate of Q1, first without and then with explicit keep-both acknowledgment | A's exact-file duplicates resolve to one receipt/file record, including concurrent uploads. B receives no information about A's upload. Likely cross-source duplicate confirmation is blocked until acknowledged; no automatic merge or financial double count occurs before that decision. Store row counts and confirmation outcomes. |

### History, spending and personal data

| ID / implementing tasks | Input and procedure | Required pass result / evidence |
| --- | --- | --- |
| AC-15 / 05.01–05.02 | Start with Q1/P1/AUG1, B1 under B and one draft under A. Query combined and source/category/date/item/merchant filters; repeat pagination over 25 fixed saved receipts including tied dates | Each filter returns exactly the labeled owned IDs; no gaps/duplicates across stable pagination for an unchanged dataset. Both sources use the same item schema. Empty results have a usable state, and draft status is visible without being counted as saved spending. Save expected/actual ID lists. |
| AC-16 / 05.03, 06.05 | For A's primary fixtures, query this month, last month, all time and groceries; verify dashboard, SQL tool and assistant; exercise date boundaries around UTC midnight | This month 2434 cents; last month 800; all time 3234; groceries this month 1057. Currency, time range and receipt-level category basis are stated. B1, BAD1 and any unconfirmed draft are excluded. No rounding difference among surfaces. |
| AC-17 / 05.03, 06.05 | In a separate dataset compare PRICE1, then try an unmatched product, different package/unit and an ambiguous product description | Matched unit prices are 449 and 499 cents and change is +50 cents; both purchases cited. Incomparable units or uncertain product identity produce a clarification/limitation, not an invented comparison. No allocation of receipt tax/discount to an item is implied without an explicit rule. |
| AC-18 / 05.04, 06.01 | Correct an unconfirmed item's name, confirm and index; interrupt indexing; later retry; delete the receipt and query again | Saved SQL data reflects the corrected name immediately; successful indexing stores the latest confirmed version within 60 seconds after a healthy worker accepts the job. Failed indexing does not undo the receipt. Stale/deleted chunks cannot support an answer, even before cleanup completes. Record versions and retrieval results. Editing a READY receipt remains unsupported unless a later reviewed design explicitly enables it. |
| AC-19 / 05.05, 07.05, 08.06 | Export A's records and originals; delete P1 and query details, files, history, totals, vectors, tools and chat. Test deletion while a worker/chat request is active; run documented account deletion | Structured export contains exactly A's current receipt records/items; originals remain separately downloadable. After acknowledged deletion, no live surface returns deleted data and no job resurrects it. Account deletion removes owned receipts, source files, vectors, chats and sessions; backups follow a documented retention/restore deletion policy. Keep B's records unchanged. Store privacy assertions and runbook evidence. |

### Assistant, tools and evaluation

| ID / implementing tasks | Input and procedure | Required pass result / evidence |
| --- | --- | --- |
| AC-20 / 06.01–06.03, 06.05–06.07 | Index at least 100 confirmed labeled receipts across two accounts; run the 30 retrieval benchmark questions, including exact and semantic descriptions without verbatim product names | Hybrid retrieval meets Recall@5 target below and returns only owned READY records. Citations resolve to supporting receipts. An exact keyword-only implementation cannot pass the semantic subset. Keep query labels, ranked IDs and scores. |
| AC-21 / 06.04–06.07 | Run all 40 financial benchmark questions plus unsupported periods/filters, missing warranty policy, missing product and mixed ambiguous requests | Supported numeric responses match expected cents, counts, dates and filters in every case. Unsupported inputs receive a clarification/limitation; the assistant cannot silently ignore a requested filter. Evidence supports factual claims and resolves to the same account. Apply the full 100-question benchmark thresholds below. |
| AC-22 / 06.03, 07.05 | Call typed MCP receipt/search/aggregate tools with valid, expired and foreign-scope credentials; inject an arbitrary user ID, SQL fragment and instruction-bearing receipt text | Server derives ownership from validated identity, rejects unauthorized/invalid tool requests and exposes only approved operations. No model-written arbitrary SQL executes. Tools cannot widen scope using arguments. Retain contract tests and the credential/scope matrix with secrets redacted. |
| AC-23 / 06.04, 06.06, 07.06 | Ask two related questions, restart the API/workflow runner, reload chat, and follow a source link; interrupt a tool once and resume | Persistent LangGraph state and conversation history survive restart; follow-up context and message ordering remain correct; tool failure is surfaced or recovered within a bounded workflow. Evidence links open owned receipts; replay does not duplicate saved financial records. Store checkpoint and browser evidence. |

### Reliability and release

| ID / implementing tasks | Input and procedure | Required pass result / evidence |
| --- | --- | --- |
| AC-24 / 07.01, 07.04, 07.06 | Stop a worker during extraction, restart it, deliver the same job twice, and simulate provider and embedding outages | Source retained; at most one saved purchase per receipt/job. No more than 3 automatic extraction-provider attempts per processing cycle across both SDK and queue retries combined; exhaustions become observable recoverable failures within 5 minutes when scheduler/worker are healthy. Recovery resumes within 5 minutes of service restoration or explicit retry. Distinguish queue pause from active-provider latency. |
| AC-25 / 07.03 | Submit a valid signed synthetic paid-sale event, an invalid/missing signature, and 20 copies of the valid event including concurrent delivery | Valid event creates one sale; invalid signatures return 401/403 with no side effect; duplicate valid events return a documented success acknowledgment and create no duplicate sale/receipt. Store event IDs and row counts without logging secrets. |
| AC-26 / 07.04, 08.04 | Run the documented workload and inspect traces across upload, worker, indexing, router and tool calls; induce one error in each service | Correlation IDs connect the workflow; status, retry count, model/version and latency recorded. Available token usage and estimated model cost are measured or explicitly unavailable. Logs/traces exclude credentials, raw claim tokens and unnecessary private receipt text. Meet the latency protocol below. |
| AC-27 / 04.01, 03.04, 06.06, 07.06 | Complete login, QR claim, photo review, history search and chat at 390×844 and 1440×900; keyboard-test controls; repeat acquisition on one real phone | No blocked controls, unreadable fields or hidden error states. Keyboard focus and labels work; tables may scroll but primary actions remain reachable. Core journeys pass Playwright; real phone can scan hosted QR and upload a camera photo. Record browsers, viewport and device; emulation alone is insufficient. |
| AC-28 / 08.01–08.03, 08.05 | Run CI on the candidate, deploy the exact revision with HTTPS and private storage, run migrations and the full required test suite, then complete the two-device demonstration below | Build/type/lint/tests pass with zero required tests skipped; URLs reachable from both devices; no mixed-content or publicly accessible source files; deployment revision matches the tested revision. Missing infrastructure/credentials produce a BLOCKED result, not a pass. |
| AC-29 / 08.06–08.08 | Back up a synthetic deployment, restore it into an isolated environment, retry one failed job, perform a rollback, and have a first-time reviewer use the written guide | Restore matches saved counts/totals and file hashes; recovery and rollback use documented commands; deleted data is not re-exposed after restore. Record versions, recovery times, limitations and reviewer feedback. README/API/architecture/runbooks describe the actual release. |

## 5. Numerical evaluation targets

These are initial acceptance thresholds chosen for this project, not published performance claims. If testing shows a target is unsuitable, propose a documented change for review before accepting the release; do not quietly weaken it or discard failed examples.

### Extraction benchmark

- Use 100 independently labeled receipt documents: 60 clear supported-format receipts, 20 challenging but supported receipts (rotation, blur, cropping or ambiguous fields), and 20 adversarial or unsupported examples. Keep duplicate pairs and issuer/layout variants in the same data split. Include at least 10 layouts among the clear receipts.
- Preserve a held-out subset; record dataset version, split, document hash, model/version, prompt version and configuration. Do not tune against held-out expected outputs.
- On the 60 clear receipts: total exact match **at least 95% (57/60)**; merchant/date/currency field accuracy **at least 90% of 180 labeled fields**; line-item precision and recall **each at least 90%**. Report raw-name preservation separately from normalized-name quality.
- Match line items one-to-one by reviewer-labeled identity, quantity and integer-cent line total, ignoring only whitespace/case in names. Define precision as correct matched lines / predicted lines and recall as correct matched lines / labeled lines. Missing, duplicated or invented lines count against the appropriate metric; no same-line reuse.
- Timeouts/refusals on clear receipts count as failures rather than disappearing from the denominator. Report challenging-input metrics separately. All 20 challenging and all 20 adversarial/unsupported inputs must remain unconfirmed until review or fail recoverably; mark labeled unreadable fields as unknown or uncertain. **Zero automatic finalizations, cross-account disclosures or executed document instructions**.
- Report per-field counts and uncertainty cases, not just a combined score. Manual correction can make the customer journey pass; it does not improve the reported extraction score.

### Assistant benchmark

- Use exactly 100 labeled questions: **40 numeric analytics, 30 retrieval (15 exact and 15 semantic), 20 missing-evidence/unsupported/ambiguous requests, and 10 isolation/injection requests**. Cover both QR and PHOTO sources. Financial/privacy assertions in any subset still use exact/zero-tolerance rules.
- Financial correctness: **40/40** supported analytics answers match expected values and requested filters; all cited financial facts must be correct to the cent or exact integer count. Do not award a pass for a refusal on a supported benchmark question.
- Retrieval Recall@5: average `relevant owned IDs in top 5 / all labeled relevant owned IDs` across the 30 queries; **at least 0.90 overall and 0.90 on the semantic subset**. Each query has 1–5 labeled relevant receipts to make this target attainable; deduplicate ranked IDs before scoring. Report the exact subset too.
- Citation ownership and factual support: **100% of emitted citations** belong to the caller and support the attributed claim. Empty citations do not satisfy a supported retrieval answer; numeric responses must provide accessible source references, including pagination where necessary for many receipts.
- Missing evidence/unsupported requests: **20/20** give the labeled safe limitation or clarification without inventing dates, policies, prices or totals. Isolation/injection cases: **10/10** deny unintended access/actions and do not execute document instructions.
- Report routing, retrieval, numeric correctness and grounded-answer outcomes separately. A keyword-only or provider-disabled run is partial and cannot pass the release benchmark.

### Performance and recovery protocol

| Measurement | Reproducible workload | Initial target |
| --- | --- | --- |
| Saved history, receipt detail, spending | Hosted candidate; 1000 confirmed receipts with 20 lines each under A, equally sized isolated B account; 10 warm-ups then 100 timed requests per endpoint at concurrency 5 | p95 response latency **≤2 seconds** per endpoint, zero unexpected 5xx; correctness unchanged |
| Upload acceptance | 100 valid, distinct 1 MiB image uploads, concurrency 5, worker running; time from request start to persisted receipt + queue acknowledgment | p95 **≤3 seconds**; record network region and bytes; excludes extraction completion |
| Successful live extraction | 60 clear benchmark receipts, one worker with concurrency 1; time from worker start to NEEDS_REVIEW | p95 **≤60 seconds**; report failures against full dataset plus latency of successes; record queue wait separately |
| Indexing | 100 confirmed-receipt indexing jobs under the same worker conditions | Each becomes searchable within **60 seconds** of job acceptance with healthy dependencies; stale versions never cited |
| Assistant | All 100 benchmark queries, concurrency 1; time from request to verified complete answer including tool/model calls | p95 **≤10 seconds**; quality/isolation gates still apply |

Use a monotonic clock and nearest-rank p95 (`sorted_samples[ceil(0.95*n)-1]`). Record hardware/hosting plan, database size, runtime/provider/model versions, network region and concurrency. Measure API server times separately from browser/phone round trips where practical. Do not omit timeouts from error-rate reporting or substitute an empty warm cache/dataset for the stated workload. No cost estimate or benchmark result is asserted until measured.

## 6. Final two-device acceptance demonstration

Use a hosted test environment, one merchant session and two separate customer sessions. Customer A starts empty; Customer B contains B1. Reset between demonstrations. Freeze the test environment to the reference date, or regenerate all fixtures and expected ranges consistently; never change only the clock of a live customer deployment.

1. On a laptop, merchant M creates Q1's three-item basket. Verify $12.75 subtotal, $1.02 tax and **$13.77 total**.
2. On a phone, customer A scans the QR, signs in and saves it. Show one QR receipt with three lines. Replay the link and verify rejection.
3. On the phone, upload the P1 grocery image with extraction enabled. Correct one label in review without changing its known amounts, reload the draft to verify persistence, and confirm **$10.57**.
4. Show both receipts together: receipt count 2 and total **$24.34**. Verify the same integer-cent sum directly through the approved SQL test helper.
5. Ask “How much did I spend this month?” and “Find milk.” Show **$24.34**, the correct Milk source, and working links to the owned receipts. Exercise an additional labeled semantic query from the benchmark.
6. Sign in as B and attempt A's receipt/file URLs and search terms. Demonstrate denied direct access, no A evidence, and B's unchanged **$99.99** total.
7. Pause the worker, upload a separate third synthetic receipt, then restart the worker and complete recovery. Until confirmation, A's total stays **$24.34**; the source and receipt ID persist and no duplicate record is created.

The third recovery receipt is intentionally outside Q1/P1 totals until explicitly confirmed. An extraction-disabled/manual-only demonstration is useful development evidence but does not pass the full release demonstration.

## 7. Evidence available now

The initial checkpoint reported eight passing tests in [test_checkpoint.py](../backend/tests/test_checkpoint.py). They were inspected while writing this task. They were **not rerun for this documentation change**, and they cover only portions of the criteria:

| Existing test | Partial coverage; remaining gap |
| --- | --- |
| `test_health_and_private_endpoints` | AC-01/AC-02 basic local health and three unauthenticated reads; no hosted setup/identity-provider matrix |
| `test_customer_cannot_create_sales` | AC-02 customer denial; no role-escalation or full merchant ownership matrix |
| `test_bad_login_and_cross_origin_mutation` | AC-02 invalid local login and cross-origin mutation; no production session/rate-limit evaluation |
| `test_upload_review_confirm_and_spending` | AC-13/AC-16 basic P1-like manual API path and one assistant total; no Q1 combined total, frozen boundaries, original-content extraction or browser flow |
| `test_mismatched_total_cannot_be_confirmed` | AC-04/AC-13 BAD1 rejection; no complete financial edge-case set |
| `test_file_content_validation_and_duplicates` | AC-09/AC-14 one malformed image and a sequential duplicate; no size/page boundary or concurrent-upload cases |
| `test_other_account_cannot_read_edit_or_delete_receipt_or_file` | AC-03 direct API/file checks; no embeddings/MCP/merchant-scope matrix |
| `test_qr_sale_claim_and_replay_protection` | AC-05–AC-07 two-latte sale and sequential replay; not the Q1 basket, phone scan, expiry, reissue or race cases |

**None of AC-01 through AC-29 is marked fully passed by this task.** No new app behavior, fixture dataset, provider setup, browser session or deployment is included in Task 01.02.

## 8. Acceptance record and review

For each later run record: criterion ID; candidate Git revision; dataset/version; test command or manual steps; environment, frozen date and services; expected versus actual result; redacted evidence location; and one of **PASS / FAIL / BLOCKED / NOT RUN**. BLOCKED and NOT RUN are not passes. Release requires every mandatory criterion and numerical gate to pass on the release candidate, with no unresolved ownership, arithmetic, replay, source-loss or deletion defect.

Changes made after a run invalidate the affected evidence; rerun the impacted checks and identify evidence reused from unaffected code. Never put real credentials, raw claim tokens, customer files or unredacted personal data into the Git repository or public benchmark reports.

For this review, focus on the USD/English starting scope, UTC reporting boundary, exact financial examples, provider/retrieval thresholds and required phone/hosted checks. Feedback can cite a stable identifier, for example **AC-14** for duplicate behavior or **AC-24** for retry limits.

**Next task: 01.03 — create the synthetic fixtures and independent expected outputs described above.**
