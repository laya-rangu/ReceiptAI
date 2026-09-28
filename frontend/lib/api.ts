export type User = {
  id: string;
  name: string;
  email: string;
  role: "customer" | "merchant";
};
export type Item = {
  raw_name: string;
  normalized_name: string;
  quantity: string;
  line_total_cents: number;
  category: string;
};
export type Receipt = {
  id: string;
  merchant_name: string;
  purchased_at: string | null;
  source_type: "QR" | "PHOTO";
  status: "PROCESSING" | "NEEDS_REVIEW" | "READY" | "FAILED";
  currency: string;
  subtotal_cents: number;
  discount_cents: number;
  tax_cents: number;
  fees_cents: number;
  total_cents: number;
  tax_included: boolean;
  category: string;
  notes: string;
  validation_errors: string[];
  created_at: number;
  items: Item[];
  has_file: boolean;
  possible_duplicates?: { id: string; merchant_name: string }[];
};
export type Summary = {
  total_cents: number;
  receipt_count: number;
  merchant_count: number;
  pending_count: number;
  categories: { name: string; total_cents: number }[];
  daily: { date: string; total_cents: number }[];
};
export type Evidence = {
  id: string;
  merchant_name: string;
  total_cents: number;
  purchased_at: string;
};
export type Message = {
  id: string;
  role: string;
  content: string;
  evidence: Evidence[];
};
export const categories = [
  "Groceries",
  "Food & drink",
  "Shopping",
  "Transport",
  "Health",
  "Other",
];
export const money = (cents: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    cents / 100,
  );
export const formatDate = (day: string | null) =>
  day
    ? new Date(day + "T12:00:00").toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Date to review";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: Record<string, unknown>,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(!(options.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: "Something went wrong. Please try again." }));
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg: string }) => d.msg).join("; ")
          : detail?.message || "Something went wrong. Please try again.";
    throw new ApiError(message, response.status, detail);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const post = <T>(path: string, body: unknown = {}) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
