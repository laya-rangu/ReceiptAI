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

**Next task after review: 01.03 — build synthetic receipt fixtures and independently labeled expected outputs.**
