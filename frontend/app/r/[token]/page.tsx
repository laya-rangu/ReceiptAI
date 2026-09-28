"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Clock3,
  ReceiptText,
  ShieldCheck,
  Store,
} from "lucide-react";
import { api, formatDate, money, post, Receipt, User } from "@/lib/api";
import { ErrorBox, Loading } from "@/components/ui";

type Preview = {
  merchant_name: string;
  total_cents: number;
  item_count: number;
  purchased_at: string;
  expires_at: number;
};
export default function ClaimPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params),
    router = useRouter();
  const [preview, setPreview] = useState<Preview | null>(null),
    [user, setUser] = useState<User | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api<Preview>(`/public/receipts/${token}`)
      .then(setPreview)
      .catch((e) => setError(e.message));
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => {});
  }, [token]);
  async function claim() {
    setBusy(true);
    try {
      const receipt = await post<Receipt>("/receipts/claim", { token });
      router.push(`/receipts/${receipt.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="claim-page">
      <Link className="brand" href="/">
        <span className="brand-mark">
          <ReceiptText />
        </span>
        ReceiptAI
      </Link>
      <section className="claim-card">
        <ErrorBox message={error} />
        {preview ? (
          <>
            <span className="claim-store">
              <Store size={32} />
            </span>
            <span className="eyebrow">A LITTLE LESS PAPER</span>
            <h1>{preview.merchant_name}</h1>
            <p>Your purchase is ready to keep.</p>
            <div className="claim-amount">{money(preview.total_cents)}</div>
            <div className="claim-meta">
              <span>{preview.item_count} items</span>
              <span>{formatDate(preview.purchased_at)}</span>
            </div>
            <div className="receipt-dash" />
            <p>
              Save this receipt to your account to see all the item details.
            </p>
            {user ? (
              <>
                <button
                  className="button primary full"
                  disabled={busy || Boolean(error)}
                  onClick={claim}
                >
                  {busy ? "Saving receipt…" : "Save to my receipts"}
                  <ArrowRight size={17} />
                </button>
                <small>Saving to {user.email}</small>
              </>
            ) : (
              <Link
                className="button primary full"
                href={`/login?next=${encodeURIComponent(`/r/${token}`)}`}
              >
                Sign in to save <ArrowRight size={17} />
              </Link>
            )}
            <div className="claim-expiry">
              <Clock3 size={14} />
              This link is single-use and expires in 15 minutes from checkout.
            </div>
          </>
        ) : (
          !error && <Loading />
        )}
      </section>
      <span className="login-privacy">
        <ShieldCheck size={15} />
        Your purchases. Your private space.
      </span>
    </div>
  );
}
