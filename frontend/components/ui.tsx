"use client";

import Link from "next/link";
import {
  ArrowUpRight,
  Coffee,
  ShoppingBag,
  ShoppingBasket,
  TrainFront,
  HeartPulse,
  ReceiptText,
  QrCode,
  Image as ImageIcon,
  LoaderCircle,
} from "lucide-react";
import { formatDate, money, Receipt } from "@/lib/api";

export function CategoryIcon({
  category,
  size = 20,
}: {
  category: string;
  size?: number;
}) {
  const Icon =
    category === "Groceries"
      ? ShoppingBasket
      : category === "Food & drink"
        ? Coffee
        : category === "Shopping"
          ? ShoppingBag
          : category === "Transport"
            ? TrainFront
            : category === "Health"
              ? HeartPulse
              : ReceiptText;
  return <Icon size={size} strokeWidth={1.7} />;
}
export function MerchantIcon({
  receipt,
}: {
  receipt: Pick<Receipt, "category">;
}) {
  return (
    <span
      className={`merchant-icon cat-${receipt.category.split(" ")[0].toLowerCase()}`}
    >
      <CategoryIcon category={receipt.category} />
    </span>
  );
}
export function Loading({
  label = "Getting things ready…",
}: {
  label?: string;
}) {
  return (
    <div className="loading">
      <LoaderCircle className="spin" size={22} />
      <span>{label}</span>
    </div>
  );
}
export function ErrorBox({ message }: { message: string }) {
  return message ? (
    <div className="error-box" role="alert">
      {message}
    </div>
  ) : null;
}
export function ReceiptTable({
  receipts,
  compact = false,
}: {
  receipts: Receipt[];
  compact?: boolean;
}) {
  if (!receipts.length)
    return (
      <div className="empty-state">
        <ReceiptText size={36} />
        <h3>A fresh start.</h3>
        <p>Your receipts will appear here when you add one.</p>
        <Link className="button primary" href="/upload">
          Add your first receipt
        </Link>
      </div>
    );
  return (
    <div className="table-scroll">
      <table className="receipt-table">
        <thead>
          <tr>
            <th>Merchant</th>
            <th>Date</th>
            {!compact && <th>Category</th>}
            <th>Source</th>
            <th className="right">Amount</th>
            <th>
              <span className="sr-only">Open</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {receipts.map((receipt) => (
            <tr key={receipt.id}>
              <td>
                <Link
                  href={
                    receipt.status === "READY"
                      ? `/receipts/${receipt.id}`
                      : `/review/${receipt.id}`
                  }
                  className="merchant-cell"
                >
                  <MerchantIcon receipt={receipt} />
                  <span>
                    <strong>{receipt.merchant_name}</strong>
                    <small>
                      {receipt.status === "READY"
                        ? `${receipt.items.length} items`
                        : receipt.status.replaceAll("_", " ").toLowerCase()}
                    </small>
                  </span>
                </Link>
              </td>
              <td className="muted nowrap">
                {formatDate(receipt.purchased_at)}
              </td>
              {!compact && (
                <td>
                  <span className="category-pill">{receipt.category}</span>
                </td>
              )}
              <td>
                <span className="source-pill">
                  {receipt.source_type === "QR" ? (
                    <QrCode size={13} />
                  ) : (
                    <ImageIcon size={13} />
                  )}
                  <span>
                    {receipt.source_type === "QR" ? "QR scan" : "Upload"}
                  </span>
                </span>
              </td>
              <td className="right amount">{money(receipt.total_cents)}</td>
              <td>
                <Link
                  className="icon-button"
                  href={
                    receipt.status === "READY"
                      ? `/receipts/${receipt.id}`
                      : `/review/${receipt.id}`
                  }
                  aria-label={`Open ${receipt.merchant_name} receipt`}
                >
                  <ArrowUpRight size={16} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
