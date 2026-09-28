"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  Download,
  FileText,
  Plus,
  RotateCw,
  Save,
  Trash2,
} from "lucide-react";
import { api, categories, formatDate, money, post, Receipt } from "@/lib/api";
import { ErrorBox, Loading, MerchantIcon } from "./ui";

type EditItem = {
  raw_name: string;
  normalized_name: string;
  quantity: string;
  amount: string;
  category: string;
};
const decimal = (cents: number) => (cents / 100).toFixed(2);
function cents(value: string) {
  if (!/^\d+(\.\d{1,2})?$/.test(value))
    throw new Error(
      "Enter non-negative amounts with at most two decimal places.",
    );
  const [whole, part = ""] = value.split(".");
  return Number(whole) * 100 + Number(part.padEnd(2, "0"));
}

export default function ReceiptDetail({ id }: { id: string }) {
  const router = useRouter();
  const [receipt, setReceipt] = useState<Receipt | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const [merchant, setMerchant] = useState(""),
    [day, setDay] = useState(""),
    [category, setCategory] = useState("Other"),
    [taxIncluded, setTaxIncluded] = useState(false);
  const [items, setItems] = useState<EditItem[]>([]),
    [amounts, setAmounts] = useState({
      subtotal: "0.00",
      discount: "0.00",
      tax: "0.00",
      fees: "0.00",
      total: "0.00",
    });
  const [acknowledge, setAcknowledge] = useState(false),
    [deleting, setDeleting] = useState(false);
  function populate(r: Receipt) {
    setReceipt(r);
    setMerchant(r.merchant_name === "Untitled receipt" ? "" : r.merchant_name);
    setDay(r.purchased_at || "");
    setCategory(r.category);
    setTaxIncluded(r.tax_included);
    setItems(
      r.items.length
        ? r.items.map((i) => ({ ...i, amount: decimal(i.line_total_cents) }))
        : [
            {
              raw_name: "",
              normalized_name: "",
              quantity: "1",
              amount: "",
              category: "Other",
            },
          ],
    );
    setAmounts({
      subtotal: decimal(r.subtotal_cents),
      discount: decimal(r.discount_cents),
      tax: decimal(r.tax_cents),
      fees: decimal(r.fees_cents),
      total: decimal(r.total_cents),
    });
  }
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const r = await api<Receipt>(`/me/receipts/${id}`);
        if (!alive) return;
        populate(r);
        if (r.status === "PROCESSING") timer = setTimeout(load, 2000);
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    }
    void load();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [id]);
  async function save(confirm: boolean) {
    if (!receipt) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const body = {
        merchant_name: merchant,
        purchased_at: day,
        category,
        currency: "USD",
        items: items.map((item) => ({
          raw_name: item.raw_name || item.normalized_name,
          normalized_name: item.normalized_name,
          quantity: item.quantity,
          line_total_cents: cents(item.amount),
          category: item.category,
        })),
        subtotal_cents: cents(amounts.subtotal),
        discount_cents: cents(amounts.discount),
        tax_cents: cents(amounts.tax),
        fees_cents: cents(amounts.fees),
        total_cents: cents(amounts.total),
        tax_included: taxIncluded,
        notes: receipt.notes,
      };
      const updated = await api<Receipt>(`/receipts/${id}/draft`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setReceipt(updated);
      if (confirm) {
        const saved = await post<Receipt>(`/receipts/${id}/confirm`, {
          acknowledge_duplicate: acknowledge,
        });
        populate(saved);
        router.replace(`/receipts/${id}`);
        setNotice("Receipt saved. It’s now part of your spending history.");
      } else {
        setNotice("Draft saved. Your changes will be here when you return.");
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    setBusy(true);
    try {
      await api(`/me/receipts/${id}`, { method: "DELETE" });
      router.push("/receipts");
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  async function retry() {
    setBusy(true);
    try {
      await post(`/receipts/${id}/retry`);
      window.location.reload();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  if (!receipt) return error ? <ErrorBox message={error} /> : <Loading />;
  const editable =
    receipt.status === "NEEDS_REVIEW" || receipt.status === "FAILED";
  return (
    <>
      <Link className="back-link" href="/receipts">
        <ArrowLeft size={15} />
        Back to receipts
      </Link>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            {editable ? "A QUICK SECOND LOOK" : "THE DETAILS, SAFELY FILED"}
          </div>
          <h1>
            {editable ? "Make sure it all adds up." : receipt.merchant_name}
          </h1>
          <p>
            {editable
              ? "Check the original, correct the details, and make it yours."
              : `${formatDate(receipt.purchased_at)} · ${receipt.source_type === "QR" ? "Collected by QR" : "Uploaded receipt"}`}
          </p>
        </div>
        <div className="heading-actions">
          {receipt.has_file && (
            <a
              href={`/api/me/receipts/${id}/file`}
              target="_blank"
              rel="noreferrer"
              className="button secondary"
            >
              <Download size={16} />
              Original file
            </a>
          )}
          <button
            className="icon-button delete-button"
            aria-label="Delete receipt"
            onClick={() => setDeleting(true)}
            disabled={receipt.status === "PROCESSING"}
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>
      <ErrorBox message={error} />
      {notice && (
        <div className="success-note" role="status">
          {notice}
        </div>
      )}
      {deleting && (
        <div className="delete-confirm">
          <strong>Delete this receipt and its original file?</strong>
          <p>
            Your assistant history will also be cleared so it does not retain
            details from this purchase.
          </p>
          <button className="button danger" disabled={busy} onClick={remove}>
            Delete receipt
          </button>
          <button
            className="button secondary"
            onClick={() => setDeleting(false)}
          >
            Keep receipt
          </button>
        </div>
      )}
      {receipt.status === "PROCESSING" ? (
        <section className="panel">
          <Loading label="Reading your receipt. This may take a moment…" />
        </section>
      ) : (
        <div className={`detail-layout ${!editable ? "read-only" : ""}`}>
          <section className="panel receipt-paper">
            <div className="paper-heading">
              <MerchantIcon receipt={receipt} />
              <h2>{receipt.merchant_name}</h2>
              <span>{formatDate(receipt.purchased_at)}</span>
              <span className="paper-status">
                {receipt.status === "READY"
                  ? "SAVED TO YOUR WORKSPACE"
                  : "ORIGINAL RECEIPT"}
              </span>
            </div>
            {receipt.has_file ? (
              <div className="source-preview">
                <a
                  href={`/api/me/receipts/${id}/file`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <img
                    src={`/api/me/receipts/${id}/file`}
                    alt="Original uploaded receipt"
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                  />
                  <span className="source-fallback">
                    <FileText size={17} />
                    Open original image or PDF <ArrowUpRight size={15} />
                  </span>
                </a>
              </div>
            ) : (
              <>
                <div className="paper-items">
                  {receipt.items.map((item, index) => (
                    <div key={index}>
                      <span>
                        {item.normalized_name}
                        <small>
                          Qty {Number(item.quantity)}
                          {item.raw_name !== item.normalized_name
                            ? ` · ${item.raw_name}`
                            : ""}
                        </small>
                      </span>
                      <strong>{money(item.line_total_cents)}</strong>
                    </div>
                  ))}
                </div>
                <div className="basket-totals">
                  <div>
                    <span>Subtotal</span>
                    <span>{money(receipt.subtotal_cents)}</span>
                  </div>
                  {receipt.discount_cents > 0 && (
                    <div>
                      <span>Discount</span>
                      <span>−{money(receipt.discount_cents)}</span>
                    </div>
                  )}
                  <div>
                    <span>Tax{receipt.tax_included ? " (included)" : ""}</span>
                    <span>{money(receipt.tax_cents)}</span>
                  </div>
                  {receipt.fees_cents > 0 && (
                    <div>
                      <span>Fees</span>
                      <span>{money(receipt.fees_cents)}</span>
                    </div>
                  )}
                  <div className="total">
                    <strong>Total</strong>
                    <strong>{money(receipt.total_cents)}</strong>
                  </div>
                </div>
                <p className="tiny centered">{receipt.notes}</p>
              </>
            )}
            <div className="paper-footer">
              A LITTLE LESS PAPER. A LITTLE MORE CLARITY.
            </div>
          </section>
          {editable ? (
            <section className="panel review-panel">
              <h2>Review the details</h2>
              {receipt.validation_errors.length > 0 && (
                <div className="validation-note">
                  {receipt.validation_errors.map((issue, i) => (
                    <p key={i}>{issue}</p>
                  ))}
                </div>
              )}
              {receipt.status === "FAILED" && (
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={retry}
                >
                  <RotateCw size={15} />
                  Retry extraction
                </button>
              )}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void save(true);
                }}
              >
                <label>
                  Merchant
                  <input
                    required
                    value={merchant}
                    onChange={(e) => setMerchant(e.target.value)}
                    placeholder="Name on the receipt"
                    maxLength={200}
                  />
                </label>
                <div className="form-two">
                  <label>
                    Purchase date
                    <input
                      type="date"
                      required
                      value={day}
                      onChange={(e) => setDay(e.target.value)}
                    />
                  </label>
                  <label>
                    Receipt category
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                    >
                      {categories.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className="review-items-heading">
                  <h3>Line items</h3>
                  <span>USD</span>
                </div>
                {items.map((item, index) => (
                  <div className="review-item" key={index}>
                    <label>
                      Item {index + 1}
                      <input
                        required
                        value={item.normalized_name}
                        onChange={(e) =>
                          setItems(
                            items.map((it, i) =>
                              i === index
                                ? { ...it, normalized_name: e.target.value }
                                : it,
                            ),
                          )
                        }
                        placeholder="Item name"
                      />
                    </label>
                    <label>
                      Qty
                      <input
                        required
                        inputMode="decimal"
                        value={item.quantity}
                        onChange={(e) =>
                          setItems(
                            items.map((it, i) =>
                              i === index
                                ? { ...it, quantity: e.target.value }
                                : it,
                            ),
                          )
                        }
                      />
                    </label>
                    <label>
                      Line total
                      <input
                        required
                        inputMode="decimal"
                        value={item.amount}
                        onChange={(e) =>
                          setItems(
                            items.map((it, i) =>
                              i === index
                                ? { ...it, amount: e.target.value }
                                : it,
                            ),
                          )
                        }
                        placeholder="0.00"
                      />
                    </label>
                    <button
                      type="button"
                      className="icon-button"
                      aria-label={`Remove item ${index + 1}`}
                      disabled={items.length === 1}
                      onClick={() =>
                        setItems(items.filter((_, i) => i !== index))
                      }
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className="text-link add-item"
                  onClick={() =>
                    setItems([
                      ...items,
                      {
                        raw_name: "",
                        normalized_name: "",
                        quantity: "1",
                        amount: "",
                        category,
                      },
                    ])
                  }
                >
                  <Plus size={15} />
                  Add line item
                </button>
                <div className="form-two">
                  {Object.entries(amounts).map(([key, value]) => (
                    <label key={key} className="capitalize">
                      {key} (USD)
                      <input
                        aria-label={`${key} amount`}
                        required
                        inputMode="decimal"
                        value={value}
                        onChange={(e) =>
                          setAmounts({ ...amounts, [key]: e.target.value })
                        }
                      />
                    </label>
                  ))}
                </div>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={taxIncluded}
                    onChange={(e) => setTaxIncluded(e.target.checked)}
                  />
                  Tax is already included in the subtotal
                </label>
                {Boolean(receipt.possible_duplicates?.length) && (
                  <div className="validation-note">
                    <p>
                      This purchase looks like another receipt in your account.
                    </p>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={acknowledge}
                        onChange={(e) => setAcknowledge(e.target.checked)}
                      />
                      I checked and want to keep both receipts
                    </label>
                  </div>
                )}
                <div className="review-actions">
                  <button
                    type="button"
                    className="button secondary"
                    disabled={busy}
                    onClick={() => save(false)}
                  >
                    Save draft
                  </button>
                  <button className="button primary" disabled={busy}>
                    <Save size={16} />
                    {busy ? "Saving…" : "Confirm & save receipt"}
                  </button>
                </div>
                <p className="tiny">
                  Only confirmed receipts count toward your spending totals.
                </p>
              </form>
            </section>
          ) : (
            receipt.has_file && (
              <section className="panel saved-details">
                <h2>Saved purchase details</h2>
                <div className="paper-items">
                  {receipt.items.map((item, i) => (
                    <div key={i}>
                      <span>
                        {item.normalized_name}
                        <small>Qty {Number(item.quantity)}</small>
                      </span>
                      <strong>{money(item.line_total_cents)}</strong>
                    </div>
                  ))}
                </div>
                <div className="basket-totals">
                  <div>
                    <span>Subtotal</span>
                    <span>{money(receipt.subtotal_cents)}</span>
                  </div>
                  <div>
                    <span>Discount</span>
                    <span>−{money(receipt.discount_cents)}</span>
                  </div>
                  <div>
                    <span>Tax{receipt.tax_included ? " (included)" : ""}</span>
                    <span>{money(receipt.tax_cents)}</span>
                  </div>
                  <div>
                    <span>Fees</span>
                    <span>{money(receipt.fees_cents)}</span>
                  </div>
                  <div className="total">
                    <strong>Total</strong>
                    <strong>{money(receipt.total_cents)}</strong>
                  </div>
                </div>
                <p className="tiny">Category: {receipt.category}</p>
              </section>
            )
          )}
        </div>
      )}
    </>
  );
}
