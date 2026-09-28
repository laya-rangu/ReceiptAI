# ReceiptAI

QR receipts, photo uploads, and a personal purchase assistant, built around one shared receipt model.

**Status: development scaffold; Task 01.03 synthetic fixtures ready for review.** The code is not a completed or deployed product. Development proceeds one task at a time, with a commit, relevant checks, and user review at each checkpoint.

- [48-task implementation plan](docs/TASKS.md)
- [Task 01.01: user journeys and failure states](docs/user-journeys.md)
- [Task 01.02: MVP scope and measurable acceptance criteria](docs/acceptance-criteria.md)
- [Task 01.03: synthetic receipts, expected results and reproduction guide](evaluations/fixtures/README.md)
- [Checkpoint results and known limitations](docs/CHECKPOINTS.md)
- [Original five-page plan](ReceiptAI_5_Page_Project_Plan.pdf)

## Current scaffold

- Next.js / React / TypeScript web interface: sign-in, overview, receipts, upload/review, merchant checkout, QR preview, and chat.
- FastAPI / Pydantic / SQLAlchemy API with a SQLite development database.
- Local password authentication and server-side sessions. This is a temporary development implementation; Supabase integration remains a planned task.
- Merchant checkout with server-calculated amounts and hashed, expiring, single-use QR claim tokens.
- Private local file storage, upload validation, manual review, integer-cent arithmetic, and duplicate-file detection.
- Optional OpenAI receipt extraction adapter. Without a key, uploads require manual entry; no extraction result is fabricated.
- SQL spending calculations and a limited keyword assistant with receipt links. LangGraph, semantic RAG, MCP, and A2A are not implemented.

Demo purchases are synthetic. Seeded photo receipts do not have real source images.

## Run locally on Windows

Requirements: Python 3.10+ and Node.js 20.9+. Commands below assume PowerShell, starting in the repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open a second terminal in the repository root:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). API documentation is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

On the sign-in page, use **Open customer demo**, **Merchant demo**, or **Empty account demo**. Demo passwords are intentionally public, and demo seeding is restricted to development.

| Account | Email | Password |
| --- | --- | --- |
| Customer with synthetic receipts | `alex@receiptai.demo` | `ReceiptAI-demo-2026` |
| Empty customer account | `jamie@receiptai.demo` | `ReceiptAI-demo-2026` |
| Merchant checkout | `merchant@receiptai.demo` | `ReceiptAI-demo-2026` |

Do not use these development accounts for real personal data or expose the development server to the public internet.

## Optional extraction

Set `OPENAI_API_KEY` in your local `backend/.env`, then restart the API. Never commit the key. `EXTRACTION_MODEL` is configurable. An upload with extraction enabled sends the document to the configured API provider. The customer must review the result before saving.

The adapter uses the OpenAI Responses API with typed output. References: [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [image inputs](https://developers.openai.com/api/docs/guides/images-vision), and [file inputs](https://developers.openai.com/api/docs/guides/file-inputs). Live model calls have not been verified in this checkpoint.

## Validation

From the repository root:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m ruff check app tests
Set-Location ..\frontend
npm run typecheck
npm run format:check
npm run build
```

The test suite uses a separate temporary database and temporary files. It does not modify the local demo database. It now includes actual synthetic receipt files, fixed-date financial cases and the combined QR/photo flow. See the [fixture guide](evaluations/fixtures/README.md) for the versioned inputs, expected outputs, rendering dependency pins and independent integrity checks.

## Deployment status

Nothing has been deployed. PostgreSQL migrations, Docker Compose, Redis worker operations, Supabase, S3 storage, production authentication hardening, and cloud deployment remain in the task plan. The current local background-task runner is not durable across process restarts. The PostgreSQL connection option and RQ code path do not constitute a verified deployment.

The initial supported currency is USD, and the receipt schema currently covers positive purchases. Refunds, arbitrary receipt formats, and live payments are not yet supported. A phone cannot reach a QR URL pointing to your computer's `localhost`; hosted or explicitly configured LAN testing is a later acceptance check.
