# Review checkpoints

## Initial scaffold + Task 01.01

Repository: `https://github.com/laya-rangu/ReceiptAI`.

This checkpoint preserves the initial scaffold written before the user requested a task-by-task workflow. It also delivers the user journeys and failure-state document for Task 01.01. It does not mark the later feature tasks complete.

### What changed

- Created a project-local Git repository, isolated from the unrelated parent repository.
- Added FastAPI/SQLAlchemy receipt, sale, claim, session and chat models and API routes.
- Added Next.js screens for sign-in, overview, history, upload/review, merchant checkout, QR preview, and a basic assistant.
- Added local demo data, local private-file storage, optional extraction adapter and manual review fallback.
- Added a 48-task tracker, user journeys, setup instructions, and the review/push working agreement.
- Added focused API regression tests with an isolated temporary database.

### Checks performed

| Check | Result |
| --- | --- |
| Python source compilation | Passed |
| Ruff check of backend source and tests | Passed |
| TypeScript type check | Passed |
| Frontend formatting check | Passed; source formatted for easier review |
| Next.js production build | Passed; all application routes compiled |
| pytest API tests | 8 passed |
| Test database cleanup on Windows | Fixed a locked connection issue; rerun completed without cleanup error |
| Full browser or real-phone acceptance | Not performed in this checkpoint |
| Live vision extraction | Not performed; no credential configured for verification |
| PostgreSQL, Redis, S3 or Supabase integration | Not verified |
| Deployment | Not performed |

The test run emits an upstream Starlette/httpx deprecation warning. The frontend build warns about ignoring a lockfile outside this project. Neither prevented the checks from passing.

The eight tests cover: unauthenticated data access, customer/merchant authorization, invalid login and cross-origin mutation, manual upload/review/confirmation and spending, amount mismatch rejection, content validation and exact-file duplicates, cross-account receipt/file isolation, and a QR sale/claim/replay flow.

### How to review

1. Read [Task 01.01 user journeys](user-journeys.md), especially the failure-state tables and review checklist.
2. Inspect [the task tracker](TASKS.md) to confirm the staged order and planned technologies.
3. Run the application using the [README](../README.md). The customer demo has synthetic receipts; the empty account is useful for testing uploads without sample purchases.
4. To inspect the code, start with `backend/app/schemas.py`, `backend/app/receipts.py`, `backend/app/main.py`, and `frontend/app/(workspace)/dashboard/page.tsx`.
5. Report a correction against a task ID, for example: “01.01: use a shorter QR expiry” or “02.03: prioritize Supabase login”.

### Known gaps before a usable release

- Existing screens are scaffold code; complete UI behavior and accessibility need browser review.
- Local password/session authentication is provisional. Production auth hardening and Supabase remain planned.
- The upload worker's in-process mode is not durable. Redis operation and retry behavior require dedicated tests.
- Concurrency, QR expiry/reissue races, extraction failure recovery, and likely cross-source duplicate confirmation need broader coverage.
- Exact-file deduplication currently checks for existing rows; a concurrent duplicate-upload race is not yet protected by a database uniqueness constraint.
- Extraction must be evaluated with live calls and realistic images. Partial extraction recovery, refunds, and unusual receipt layouts need further work.
- Chat uses a bounded deterministic implementation. Semantic RAG, MCP, LangGraph, A2A, and comprehensive financial-query parsing are not complete.
- Receipt and chat deletion consistency under concurrent requests, session rate limiting, and account deletion/export completeness need dedicated privacy/security review.
- Migrations, Docker, CI/CD, observability, backups and public hosting are not yet implemented.

**Next task at that checkpoint: 01.02 — measurable MVP acceptance criteria.** The user subsequently requested the next step.

## Task 01.02 — Scope and measurable acceptance criteria

**Status: ready for review.** This is a documentation checkpoint. It defines future product acceptance; it does not certify the scaffold as a completed MVP.

### What changed

- Added [acceptance-criteria.md](acceptance-criteria.md), defining local milestone versus full release scope, deferred features, financial/date semantics, and 29 numbered acceptance criteria.
- Specified independent synthetic fixture expectations for Task 01.03: a three-item QR sale totaling 1377 cents, a photo receipt totaling 1057 cents, their combined 2434-cent total, and boundary/duplicate/price cases.
- Connected every criterion to the implementation task IDs that will deliver it, with inputs/procedures, exact pass results and required evidence.
- Defined proposed extraction, retrieval, financial-answer, latency and recovery targets with dataset sizes and scoring rules. Targets are requirements, not measured performance.
- Documented a repeatable two-device release demonstration and PASS / FAIL / BLOCKED / NOT RUN evidence records.
- Mapped the eight existing tests to their partial coverage and explicitly left all 29 full release criteria unpassed.
- Updated the README, task tracker and journey links to make this the current review checkpoint. Task 01.01 is delivered; 01.03 has not started.

Skills used: requirements engineering, acceptance-test design, financial invariant specification, traceability and technical writing. No application behavior, dependency, provider setting or deployment changed.

### Checks performed

| Check | Result |
| --- | --- |
| Acceptance IDs and row structure | Passed: AC-01 through AC-29, unique, ordered, each with a procedure and pass/evidence cell |
| Roadmap consistency | Passed: all 48 original task IDs retained; referenced implementation tasks exist |
| Local documentation links | Passed: links in the changed documents resolve to existing files |
| Numerical examples | Passed: independent Decimal/integer calculations confirm tax, totals, adjustments, unit-price change and byte limit |
| Dataset counts and thresholds | Passed: 100 extraction documents and 100 assistant questions; 57/60 equals 95% |
| UTF-8 text and Git whitespace checks | Passed |
| Existing test coverage | Inspected test names/assertions; no additional behavior claimed |
| App builds, API tests, browser/device tests and live benchmarks | Not rerun; this task changes documentation only |

The previous checkpoint's eight API passes and production build remain historical evidence for that revision. This checkpoint adds no new product-test or benchmark result.

### How to review

1. Read sections 1–3 of [acceptance-criteria.md](acceptance-criteria.md) for the release boundary and exact receipt examples.
2. Review the criterion relevant to any concern: AC-08 for QR races, AC-14 for duplicates, AC-16 for totals, AC-19 for deletion, or AC-24 for retry limits.
3. Review section 5's proposed quality/performance targets and section 6's phone/laptop demonstration.
4. Report corrections by criterion ID. The initial USD/English scope and UTC reporting date are documented design choices that can be revised before implementation.

**Next task at that checkpoint: 01.03 — build synthetic receipt fixtures and independently labeled expected outputs.** The user subsequently requested that task.

## Task 01.03 — Versioned synthetic receipt fixtures

**Status: ready for review.** Delivered the [v1 fixture set and guide](../evaluations/fixtures/README.md), offline rendering/verification tools and fixture-backed API tests. No application endpoint or frontend behavior changed.

### What changed

- Created 100 benchmark inputs: 60 clear receipts across 12 designed layout variants, 20 challenging inputs and 20 adversarial/unsupported inputs; added five supplemental files for duplicate and format/page cases.
- Added authored definitions, independent golden scenarios, 64 source records, visible-field extraction labels, file hashes and byte counts. Explicitly hidden fields have null labels and required uncertainty markers.
- Kept issuer/layout families and their duplicates/variants in one split: 65 development / 35 held-out benchmark inputs, plus five development supplements. The holdout is synthetic and public, not a real-world accuracy result.
- Added an offline Pillow renderer and deterministic raster PDF writer. Pinned rendering dependencies and verified repeatable bytes. Images contain synthetic/not-a-purchase notices; malformed/empty inputs are documented exceptions.
- Added benign prompt-injection text as untrusted receipt content, unsupported currencies/refunds, mismatched totals, malformed images/PDFs, encryption, internal PDF navigation and page-limit cases. No executable or external-network PDF payloads are included.
- Added temporary exact-size PNG and pixel-limit recipes so large padding files stay out of Git.
- Added fixture-backed tests using a frozen 2026-09-28 reference date and the isolated test database. Broadened coverage without using an AI provider or touching local demo data.
- Added image binary attributes; updated README, roadmap and acceptance-document links. Task 01.02 is delivered; Task 01.04 has not started.

Technologies/skills: Python, Pillow, PDF construction/pypdf, JSON, SHA-256, Decimal, pytest, source-data design and visual verification. Expected amounts come from authored fixture facts and separate golden scenarios, not production calculations or model output.

### Checks performed

| Check | Result |
| --- | --- |
| Dataset integrity and golden scenarios | Passed: 100 benchmark + 5 supplemental files, 12 layouts, source/visible labels, hashes, file structure and arithmetic |
| Split integrity | Passed: no issuer/layout family or exact file hash crosses development/held-out splits |
| Deterministic regeneration | Passed: all 110 generated artifacts reproduce byte-for-byte in the pinned local environment |
| Backend test suite | **136 passed**, including the previous eight; one existing upstream Starlette/httpx deprecation warning |
| File admission matrix | Passed for all 105 source documents, including expected rejections |
| Large boundary recipes | Passed: exactly 10,485,760 bytes accepted; 10,485,761 bytes and 20,004,000-pixel image rejected |
| Financial/core API scenarios | Passed: BAD1 cannot confirm; Q1 + corrected P1 total 2434 cents with two citations; repeated confirmation is idempotent; valid adjustments, tax-inclusive/weighted and date-boundary cases pass |
| Real fixture upload/review | Passed for P1 PNG, JPG, one-page PDF and five-page PDF; original download matches uploaded bytes |
| Ruff source/test/tool lint and formatting | Passed |
| Visual inspection | Reviewed P1 at full size, the 12-layout contact sheet, cropped-total and erased-date examples, and an instruction-bearing receipt image |
| Live extraction, model prompt-injection resistance, semantic retrieval, PostgreSQL concurrency, real phone/browser and deployment | Not run; the fixture/SQLite checks do not establish these outcomes |

The 136 passing tests include many parameterized file/schema cases; they are not 136 end-to-end customer journeys or model-quality measurements. The 100-question assistant evaluation set remains Task 06.07, and the full AC-20 retrieval dataset still requires at least 100 confirmed receipts.

### How to review

1. Open the [P1 grocery](../evaluations/fixtures/v1/clear/P1.png) and [Q1 cafe](../evaluations/fixtures/v1/clear/Q1.png) files. Compare their visible amounts with [scenarios.json](../evaluations/fixtures/scenarios.json).
2. Inspect the [layout preview](../evaluations/fixtures/v1/previews/layouts.png) and [extraction labels](../evaluations/fixtures/v1/expected/extraction.json). Hidden dates/totals must be null in the visible labels.
3. Run the commands in the [fixture guide](../evaluations/fixtures/README.md) to verify file hashes, regeneration and the test suite.
4. Optionally upload P1 into an empty local demo account and manually review the two items. The guide explains the reference-date and merchant-name differences when trying the duplicate examples with today's demo checkout.

**Next task after review: 01.04 — architecture diagram, trust boundaries and threat model.**
