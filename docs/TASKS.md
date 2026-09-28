# ReceiptAI — 48-task implementation tracker

Source: the supplied five-page project plan. Stage order and task identifiers are preserved.

**Working method:** implement one numbered task, run relevant checks, record results, commit and push, then pause for review. Existing scaffold code is provisional until the related task meets its acceptance check. Estimates in the original plan are planning ranges, not promised completion dates.

Status: **Delivered** = task artifact/checkpoint delivered and the user requested the next task; **Review** = artifact prepared for user review; **Draft** = partial scaffold exists, acceptance not complete; **Planned** = not yet implemented or verified. Delivering a requirements document does not mean its product acceptance criteria have passed.

## Stage 1 — Requirements and test fixtures · 4 tasks

Outcome: agreed journeys, measurable criteria, labeled fixtures, architecture and threat model.

| ID | Implement / deliver | Technology or skill | Completion check | Status |
| --- | --- | --- | --- | --- |
| 01.01 | Customer and merchant journeys, success paths, failure states, receipt lifecycle | Product design, user stories, failure analysis | Review each actor's actions and recovery paths in [user-journeys.md](user-journeys.md) | Delivered |
| 01.02 | Scope boundaries and measurable MVP acceptance criteria | Requirements engineering, acceptance test design | Each criterion has inputs, expected result, and a reproducible check in [acceptance-criteria.md](acceptance-criteria.md) | Delivered |
| 01.03 | Versioned synthetic receipt images, sales, edge cases, expected JSON | Python fixture generation, test data design | Fixtures are labeled synthetic and have independently known totals; see [fixture guide](../evaluations/fixtures/README.md) | Review: 100 benchmark inputs, 5 supplemental documents; 136 backend tests pass |
| 01.04 | Architecture, trust boundaries, and threat model | System design, Mermaid, security modeling | Trace tokens, files, identities, and AI data across every boundary | Planned |

## Stage 2 — Backend, authentication and schema · 5 tasks

Outcome: a reproducible application foundation with verified account isolation.

| ID | Implement / deliver | Technology or skill | Completion check | Status |
| --- | --- | --- | --- | --- |
| 02.01 | Next.js/FastAPI monorepo, linting, local scripts, Docker Compose | React, TypeScript, Python, Docker | Fresh checkout starts all required services and builds successfully | Draft: app builds; Docker and scripts pending |
| 02.02 | Canonical database tables, constraints, indexes, Alembic migrations | PostgreSQL, SQLAlchemy, Alembic | Upgrade a blank database; verify constraints and migration behavior | Draft: SQLite models; migrations pending |
| 02.03 | Supabase login, verified identity, customer/merchant authorization | Supabase Auth, JWT validation, access control | Two users cannot read each other's data; customer cannot create sales | Draft: local sessions only |
| 02.04 | Strict receipt schemas, integer-cent amounts, explicit lifecycle | Pydantic, Decimal, domain modeling | Valid examples pass; malformed or inconsistent receipts fail correctly | Draft: core schemas and arithmetic checks |
| 02.05 | Private source storage and authorized file access | S3-compatible storage, scoped API access | Owner can download; anonymous and foreign users cannot | Draft: private local files only |

## Stage 3 — QR sale to scan to claim · 6 tasks

Outcome: a merchant can complete a simulated purchase and a customer can save it using a real phone.

| ID | Implement / deliver | Technology or skill | Completion check | Status |
| --- | --- | --- | --- | --- |
| 03.01 | Merchant catalog, quantity selection and basket UI | React, TypeScript, accessible checkout UX | Add/remove items; empty and invalid baskets cannot complete | Draft |
| 03.02 | Persist simulated sales; recalculate amounts on the server | FastAPI, SQLAlchemy, Decimal | Client price tampering cannot change the server total | Draft |
| 03.03 | Cryptographically random, hashed, expiring claim token and QR | Python secrets/hashlib, QR generation | Hash stored; clear token only returned to issuer; expiry enforced | Draft |
| 03.04 | Mobile guest preview with limited public purchase information | Next.js routes, responsive CSS | Real phone opens a reachable link; no private item details leak | Draft: mobile device acceptance pending |
| 03.05 | Atomic authenticated claim and owned canonical receipt | SQL conditional updates, transactions | Concurrent requests produce one owner and one receipt | Draft: sequential replay checked; concurrency pending |
| 03.06 | Expiry, replay, token replacement and reissue UI | State transitions, API error handling | Expired/replaced tokens fail; claimed sales cannot be reassigned | Draft |

## Stage 4 — Photo/PDF extraction and review · 7 tasks

Outcome: a photographed receipt becomes a reviewed purchase in the same schema as a QR receipt.

| ID | Implement / deliver | Technology or skill | Completion check | Status |
| --- | --- | --- | --- | --- |
| 04.01 | Camera capture, file picker, drop zone and source preview | React, browser file controls, responsive UX | Valid JPG/PNG/PDF works on desktop and phone | Draft |
| 04.02 | Validate actual file content, private storage and queued processing | Pillow, pypdf, Redis/RQ, storage | Invalid files rejected; request returns before expensive extraction | Draft: local background runner verified; RQ pending |
| 04.03 | Image orientation/size processing and typed vision extraction | Vision API, Pydantic, document processing | Live extraction evaluated against labeled receipts | Draft: adapter written; live provider unverified |
| 04.04 | Preserve original product names, normalize clear abbreviations and categories | Structured extraction, product taxonomy | Source names remain recoverable; uncertainty is explicit | Draft |
| 04.05 | Validate sums, taxes, discounts, fees, dates and missing fields | Integer arithmetic, Decimal, deterministic validation | Edge-case fixtures pass or request the correct correction | Draft: basic mismatch test passes |
| 04.06 | Exact-file and likely cross-source duplicate detection | SHA-256, owner-scoped database matching | Same-file duplicate blocked; QR/photo duplicate requires review | Draft: exact-file test passes |
| 04.07 | Side-by-side correction, saved drafts and final confirmation | React forms, FastAPI, validation UX | Corrections survive refresh and only confirmed data affects totals | Draft: API path passes; browser flow pending |

## Stage 5 — Unified dashboard · 5 tasks

Outcome: searchable purchase history and exact, reproducible financial metrics.

| ID | Implement / deliver | Technology or skill | Completion check | Status |
| --- | --- | --- | --- | --- |
| 05.01 | Paginated history mixing QR and photo records | React state, SQL pagination | Both sources appear in stable order with usable empty states | Draft |
| 05.02 | Merchant, date, category and item filters | Parameterized SQL, query UX | Filters return only matching owned records | Draft |
| 05.03 | Spending summaries and product price history | SQL aggregation, Decimal, charts | Fixture totals and comparisons match independent calculations | Draft: summaries only; price history pending |
| 05.04 | Refresh views and invalidate/rebuild search indexes after correction | Cache/index lifecycle, background jobs | Edited data replaces stale searchable and displayed values | Planned |
| 05.05 | Original download, structured export and deletion | Authorization, file lifecycle, privacy UX | Deleted data disappears from history, files and assistant evidence | Draft |

## Stage 6 — RAG, chatbot, MCP and agents · 7 tasks

Outcome: grounded answers across exact financial and semantic questions, with verified source links.

| ID | Implement / deliver | Technology or skill | Completion check | Status |
| --- | --- | --- | --- | --- |
| 06.01 | Index confirmed receipt/item summaries with account metadata | Embeddings, PostgreSQL/pgvector, workers | New or corrected receipts get owned, current embeddings | Planned |
| 06.02 | Hybrid keyword/vector retrieval with owner filters | LangChain, SQL full-text search, pgvector | Relevant sources retrieved; foreign-account matches excluded | Planned: keyword-only scaffold exists |
| 06.03 | Typed MCP search, retrieval and analytics tools | MCP SDK, caller authentication, schemas | Tool contracts and independent authorization tests pass | Planned |
| 06.04 | LangGraph supervisor and persistent conversation state | LangGraph, checkpointing, intent routing | Conversations resume and failures route to useful responses | Planned |
| 06.05 | Research and SQL spending specialist responsibilities | Retrieval pipelines, bounded tools, SQL | Numeric results come from deterministic tools and match fixtures | Draft: local deterministic assistant only |
| 06.06 | Answer verifier, citations and mobile chat interface | Evidence verification, React chat UX | Every cited receipt belongs to caller; unsupported claims rejected | Draft: basic evidence links; full verifier pending |
| 06.07 | 100-question mixed-source evaluation set | Retrieval/answer evaluation design | Expected outputs are labeled and measured results reproducible | Planned |

### Planned logical agent responsibilities

- **Extraction:** read the uploaded document into a typed draft. Uses vision input and Pydantic; has no authority to finalize amounts.
- **Normalization:** propose clear product names/categories while retaining source text and uncertainty.
- **Supervisor:** route the user's question and persist workflow state through LangGraph.
- **Research:** use owned keyword/vector retrieval to find relevant purchases and documents.
- **Spending analyst:** call predefined SQL tools for totals and comparisons; never execute arbitrary model-written SQL.
- **Verifier:** check calculations, source ownership, and evidential support before producing an answer.

These are application responsibilities, not autonomous developer agents. They can live in one backend initially. A separate A2A service is optional and does not replace actual authorization or deterministic validation.

## Stage 7 — Reliability, security and interoperability · 6 tasks

Outcome: observable workflows that recover safely and isolate customers.

| ID | Implement / deliver | Technology or skill | Completion check | Status |
| --- | --- | --- | --- | --- |
| 07.01 | Idempotent durable jobs, bounded retries, backoff and failure queue | Redis/RQ, transactions, resilience testing | Worker restart does not lose files or duplicate records | Planned |
| 07.02 | Optional independently deployed extraction agent and Agent Card | A2A protocol, service auth, deployment | A real remote task exchange works with controlled file access | Planned / optional |
| 07.03 | Signed simulated POS webhook and event deduplication | HMAC/webhook verification, idempotency | Forged events rejected; replay does not duplicate sales | Planned |
| 07.04 | Structured traces, model version, latency, failures and cost | OpenTelemetry, Langfuse, operational metrics | A workflow can be traced from upload through answer | Planned |
| 07.05 | Account isolation and prompt-injection tests across all surfaces | AppSec, pytest, adversarial fixtures | Database, files, vectors and MCP resist cross-account access | Draft: initial API/file isolation checks only |
| 07.06 | Integration and Playwright end-to-end failure scenarios | pytest, Playwright, failure injection | Both journeys and recovery cases pass in a browser | Planned |

## Stage 8 — Test, deploy and publish · 8 tasks

Outcome: a reproducible release, hosted demonstration, measured results, and operations documentation.

| ID | Implement / deliver | Technology or skill | Completion check | Status |
| --- | --- | --- | --- | --- |
| 08.01 | Frontend/API/worker images and migration commands | Docker, runtime configuration | Build and boot the complete stack from a clean environment | Planned |
| 08.02 | CI checks, build and deployment gates | GitHub Actions, linting, pytest, TypeScript | A deliberately broken change is prevented from releasing | Planned |
| 08.03 | HTTPS hosting, PostgreSQL, Redis and private object storage | Cloud operations, secrets, network configuration | Two-device hosted QR/upload/chat acceptance succeeds | Planned |
| 08.04 | Extraction, retrieval, financial and latency benchmarks | Labeled datasets, evaluations, metrics | Publish measured outcomes with reproducible commands | Planned |
| 08.05 | Release-blocking replay, isolation and adversarial suite | Security regression tests | All release gates pass against the deployment candidate | Planned |
| 08.06 | Backup/restore, deletion, recovery and rollback runbook | Operations documentation, recovery drills | Restore backup and recover failed jobs in a test environment | Planned |
| 08.07 | README, architecture/API documentation and recorded full-flow demo | Technical writing, diagrams, demo scripting | A new developer can run and explain the product | Draft: starter README only |
| 08.08 | Pilot feedback and documented limitations | Usability testing, issue triage | Findings are recorded and release limits stated accurately | Planned |

## Current review boundary

The initial code checkpoint preserves work written before the task-by-task workflow was requested. The user requested the next step after **01.02**. Task **01.03** is now presented for review; the next numbered task is **01.04** (architecture and threat model). Fixture and API checks add partial evidence without declaring any full product release gate complete.
