# Task 01.01 — User journeys and failure states

**Status: delivered; the user requested the next task.** This document defines required behavior. It does not certify that every behavior is implemented. The follow-on [acceptance criteria](acceptance-criteria.md) define measurable pass/fail checks.

The project has two actors: customers, who own receipts, and merchants, who issue receipts for simulated sales. Both acquisition methods produce the same customer-owned receipt record. Only confirmed receipts contribute to spending and assistant answers.

## A. Merchant checkout and QR collection

1. A merchant signs in to the merchant studio.
2. The merchant adds catalog items and quantities to a basket.
3. The server calculates subtotal, discounts, tax, fees, and total using integer cents or Decimal. Client totals are not trusted.
4. The merchant completes the simulated sale. No real payment is processed.
5. The server creates a random token, stores its hash, and displays a link encoded as a QR code. The claim expires after 15 minutes.
6. A customer scans the code with a phone camera, or opens the link in a browser.
7. The public preview shows the merchant, date, amount, and item count. Item details and customer information stay private.
8. The customer signs in, returns to the same preview, and chooses to save the receipt.
9. An atomic transaction claims the sale for that customer and writes a READY receipt with all line items.
10. The customer sees the receipt in history, spending totals, and eligible assistant evidence.

| Failure or edge case | Required behavior | Verification |
| --- | --- | --- |
| Customer attempts merchant action | Reject with 403 | Call sale creation as a customer |
| Unknown product or invalid quantity | Reject without creating a sale | Submit fabricated product ID and zero/negative quantities |
| Modified client price | Calculate from the server catalog | Submit unexpected price fields; verify rejection |
| Unknown QR token | Explain that the link is unavailable; return 404 | Open a random token |
| Expired QR token | Return 410 and ask for a new merchant link | Advance token expiry in a test |
| Token replay | Refuse a second claim | Claim the same sale twice |
| Two customers claim concurrently | Exactly one customer receives the receipt | Issue simultaneous claims from separate sessions |
| Merchant reissues an unclaimed QR | Invalidate the old token and keep one sale | Verify old link fails and replacement succeeds |
| Merchant reissues after claim | Refuse; never remove existing ownership | Attempt reissue after successful claim |
| Customer abandons login | Do not claim the receipt | Inspect unclaimed sale after leaving login |
| Search indexing fails | Receipt stays available through normal history and SQL | Simulate indexing failure once indexing exists |

## B. Photo or PDF upload

1. A signed-in customer chooses a JPG, PNG, or PDF, or uses a phone camera.
2. The API checks the actual content, size (10 MB maximum), and PDF limits (1–5 unencrypted pages).
3. The original is stored privately with a random object key and a file hash. The server creates a PROCESSING receipt.
4. Processing runs outside the upload request. With an extraction provider configured, it extracts typed merchant, date, line item, quantity, category, and amount fields.
5. Original item text is preserved alongside normalized names. Unknown facts remain unknown.
6. The validator checks item sums, subtotal, discounts, tax mode, fees, dates, and likely duplicates.
7. The receipt enters NEEDS_REVIEW. The customer compares the draft with the original and corrects fields.
8. Saving a draft persists corrections without including them in spending.
9. Confirmation revalidates amounts and requests explicit acknowledgment of a likely duplicate.
10. A valid, confirmed receipt enters READY and appears in the same history as QR receipts.

| Failure or edge case | Required behavior | Verification |
| --- | --- | --- |
| User is signed out | Require authentication before accepting files | Upload without a session |
| Wrong file extension or forged MIME type | Inspect contents and reject unsupported files | Rename a non-image to `.png` |
| Empty, oversized, malformed or encrypted file | Explain the limit; do not create a usable receipt | Exercise each invalid fixture |
| Identical file already uploaded by the same user | Show the existing receipt rather than creating a duplicate | Upload the same bytes twice |
| Same bytes uploaded by another user | Do not reveal the other user's receipt | Repeat across two isolated accounts |
| No extraction provider configured | Open manual review and explain why | Start without a key and upload a valid file |
| Provider timeout or refusal | Keep the original and expose a recoverable FAILED state | Stub provider failure |
| Partial or illegible extraction | Require correction; never invent missing financial data | Use a fixture with obscured text |
| Totals disagree | Save draft if requested; reject final confirmation | Use line items totaling $10.57 and a stated total of $20.00 |
| Tax included in displayed prices | Avoid adding that tax a second time | Confirm a tax-inclusive fixture |
| QR/photo likely duplicate | Warn before confirmation; let the user keep both explicitly | Match merchant, date, and total across sources |
| Receipt contains instructions to the AI | Treat them as untrusted document text | Add an adversarial fixture to extraction evaluations |
| Worker interruption | Keep source and expose a recovery path | Verify durable job recovery in Stage 7; current local runner does not provide this |

## C. History and receipt management

1. The customer opens an overview of saved spending and recent receipts.
2. The customer searches merchant/product names and filters history by source, date, or category.
3. A receipt detail page shows exact item amounts and the original source when available.
4. Unconfirmed uploads show their status and link back to review. They do not increase financial totals.
5. The customer can export structured data and download original files.
6. Deleting a receipt removes it and its source from the account. The current scaffold also clears that customer's assistant history to avoid retaining deleted purchase details.

Required failure behavior: unknown or foreign receipt IDs return 404; expired sessions return 401; other accounts cannot search, export, download, edit, or delete the receipt. Drafts, failed uploads, and deleted data must not inflate totals. Empty accounts must have usable empty states.

## D. Purchase assistant

1. The customer asks a question.
2. A router selects an approved spending calculation, receipt search, or clarification.
3. SQL handles exact monetary calculations. Hybrid retrieval will handle semantic questions once Stage 6 is implemented.
4. Every tool derives account scope from authenticated identity; the model cannot choose an arbitrary user ID.
5. The response verifier checks evidence ownership and financial outputs.
6. The answer links to supporting receipts and clearly states missing information.

| Question | Intended behavior | Current scaffold |
| --- | --- | --- |
| How much did I spend this month? | SQL sum of confirmed purchases for the period | Implemented; covered by a focused API test |
| Total groceries spending last month | Period and receipt-category filter, with source links | Implemented; broader regression coverage pending |
| Find headphones | Search items and receipts owned by the customer | Keyword implementation; semantic search pending |
| Find the thing I bought for listening to music | Semantic retrieval with citations | Not implemented |
| How much more did I pay for milk? | Matched product history and deterministic comparison | Not implemented; must not fabricate a comparison |
| Is this returnable? | Use applicable policy evidence, or explain it is missing | Explains missing policy information |
| Show another customer's receipts | Deny access in tools and the database | Owner-scoped queries; broader adversarial testing pending |

Financial answers must not silently discard requested filters or time ranges. Unsupported queries should ask for a supported formulation rather than return a plausible but unrelated total.

## State definitions

| State | Meaning | Can count toward spending? |
| --- | --- | --- |
| PROCESSING | Source accepted; extraction pending/in progress | No |
| NEEDS_REVIEW | Manual or extracted draft awaiting confirmation | No |
| FAILED | Recoverable processing failure; original retained | No |
| READY | Validated purchase saved to the customer account | Yes |
| Deleted | No longer available to the customer or assistant | No |

QR receipts go directly to READY after a valid claim. Uploaded receipts pass through review. The current scaffold performs hard deletion; a full retention/audit design remains future work. Index status must remain independent from financial readiness.

## Review checklist

- [ ] Merchant and customer roles match the intended product.
- [ ] QR preview exposes the right amount of information.
- [ ] Upload limits, correction behavior, and duplicate handling are acceptable.
- [ ] Only confirmed receipts should affect spending and answers.
- [ ] USD-only positive purchases are an acceptable starting scope.
- [ ] Failure states explain what the user can do next.

Follow-on task: **01.02 — [measurable MVP acceptance criteria](acceptance-criteria.md)**. See the [task tracker](TASKS.md) for the current review checkpoint; no product feature is declared accepted by this document.
