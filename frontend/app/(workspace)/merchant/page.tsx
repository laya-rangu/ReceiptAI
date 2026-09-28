"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Check,
  Coffee,
  Cookie,
  Copy,
  Croissant,
  Minus,
  Plus,
  QrCode,
  Sandwich,
  Store,
} from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { api, money, post } from "@/lib/api";
import { useUser } from "@/components/shell";
import { ErrorBox } from "@/components/ui";

type Product = { id: string; name: string; price_cents: number; icon: string };
type Claim = {
  claim_url: string;
  expires_at: number;
  total_cents: number;
  sale_id: string;
};
export default function Merchant() {
  const user = useUser();
  const [products, setProducts] = useState<Product[]>([]),
    [basket, setBasket] = useState<Record<string, number>>({}),
    [claim, setClaim] = useState<Claim | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [copied, setCopied] = useState(false);
  useEffect(() => {
    if (user.role === "merchant")
      api<Product[]>("/merchant/products")
        .then(setProducts)
        .catch((e) => setError(e.message));
  }, [user.role]);
  const subtotal = products.reduce(
    (sum, product) => sum + product.price_cents * (basket[product.id] || 0),
    0,
  );
  const tax = Math.round((subtotal * 8) / 100);
  function change(id: string, amount: number) {
    setBasket({
      ...basket,
      [id]: Math.max(0, Math.min(100, (basket[id] || 0) + amount)),
    });
  }
  async function checkout() {
    setBusy(true);
    setError("");
    try {
      const sale = await post<{ id: string }>("/merchant/sales", {
        items: Object.entries(basket)
          .filter(([, quantity]) => quantity > 0)
          .map(([product_id, quantity]) => ({ product_id, quantity })),
      });
      const result = await post<Claim>(`/merchant/sales/${sale.id}/complete`);
      setClaim(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function reissue() {
    if (!claim) return;
    setBusy(true);
    try {
      setClaim(await post<Claim>(`/merchant/sales/${claim.sale_id}/complete`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (user.role !== "merchant")
    return (
      <>
        <div className="page-heading">
          <div>
            <div className="eyebrow">ON THE OTHER SIDE OF THE COUNTER</div>
            <h1>Merchant studio.</h1>
            <p>A simple checkout that gives paper receipts a day off.</p>
          </div>
        </div>
        <section className="panel empty-state">
          <Store size={42} />
          <h2>This space is for merchants.</h2>
          <p>
            Sign in with the merchant demo account to create a simulated sale
            and QR receipt.
          </p>
          <button
            className="button primary"
            onClick={async () => {
              await post("/auth/logout");
              window.location.href = "/login";
            }}
          >
            Switch account <ArrowRight size={16} />
          </button>
        </section>
      </>
    );
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">MERCHANT STUDIO · SIMULATED CHECKOUT</div>
          <h1>A good day at {user.name}.</h1>
          <p>Create a basket. Complete a sale. Share a little less paper.</p>
        </div>
        <span className="mode-badge">Demo · No real payments</span>
      </div>
      <ErrorBox message={error} />
      <div className="merchant-layout">
        <section>
          <div className="section-heading">
            <h2>On the menu</h2>
            <span className="muted">Made for everyday moments</span>
          </div>
          <div className="product-grid">
            {products.map((product) => {
              const Icon =
                product.icon === "croissant"
                  ? Croissant
                  : product.icon === "sandwich"
                    ? Sandwich
                    : product.icon === "cookie"
                      ? Cookie
                      : Coffee;
              return (
                <button
                  className="product-card"
                  key={product.id}
                  disabled={Boolean(claim)}
                  onClick={() => change(product.id, 1)}
                >
                  <span className={`product-art product-${product.icon}`}>
                    <Icon size={43} strokeWidth={1.1} />
                  </span>
                  <span className="product-details">
                    <strong>{product.name}</strong>
                    <span>
                      {money(product.price_cents)}
                      <span className="product-plus">
                        <Plus size={16} />
                      </span>
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </section>
        <section className="panel basket-panel">
          {claim ? (
            <div className="claim-generated">
              <span className="success-symbol">
                <Check size={24} />
              </span>
              <h2>A receipt, ready to go.</h2>
              <p>The customer can scan this QR code and save their purchase.</p>
              <div className="qr-code">
                <QRCodeSVG
                  value={claim.claim_url}
                  size={190}
                  level="M"
                  marginSize={2}
                />
              </div>
              <strong className="qr-total">{money(claim.total_cents)}</strong>
              <small>
                Valid until{" "}
                {new Date(claim.expires_at * 1000).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}{" "}
                · Single use
              </small>
              <Link
                className="button primary full"
                href={new URL(claim.claim_url).pathname}
              >
                Preview receipt <ArrowRight size={16} />
              </Link>
              <button
                className="button secondary full"
                onClick={async () => {
                  await navigator.clipboard.writeText(claim.claim_url);
                  setCopied(true);
                }}
              >
                <Copy size={15} />
                {copied ? "Link copied" : "Copy receipt link"}
              </button>
              <button className="text-button" disabled={busy} onClick={reissue}>
                Reissue QR link
              </button>
              <button
                className="text-button"
                onClick={() => {
                  setClaim(null);
                  setBasket({});
                  setError("");
                  setCopied(false);
                }}
              >
                Start a new sale
              </button>
              <p className="tiny">
                For a phone scan, FRONTEND_URL must point to a reachable host.
                See the setup guide.
              </p>
            </div>
          ) : (
            <>
              <div className="section-heading">
                <h2>Current basket</h2>
                <span className="basket-count">
                  {Object.values(basket).reduce((sum, n) => sum + n, 0)}
                </span>
              </div>
              <div className="basket-items">
                {!subtotal && (
                  <div className="basket-empty">
                    <Coffee size={32} />
                    <p>
                      A little something to start?
                      <br />
                      Choose an item from the menu.
                    </p>
                  </div>
                )}
                {products
                  .filter((p) => basket[p.id])
                  .map((product) => (
                    <div className="basket-item" key={product.id}>
                      <div>
                        <strong>{product.name}</strong>
                        <span>
                          {money(product.price_cents * basket[product.id])}
                        </span>
                      </div>
                      <div className="quantity-stepper">
                        <button
                          aria-label={`Remove one ${product.name}`}
                          onClick={() => change(product.id, -1)}
                        >
                          <Minus size={13} />
                        </button>
                        <span>{basket[product.id]}</span>
                        <button
                          aria-label={`Add one ${product.name}`}
                          onClick={() => change(product.id, 1)}
                        >
                          <Plus size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
              <div className="basket-totals">
                <div>
                  <span>Subtotal</span>
                  <span>{money(subtotal)}</span>
                </div>
                <div>
                  <span>Demo tax (8%)</span>
                  <span>{money(tax)}</span>
                </div>
                <div className="total">
                  <strong>Total</strong>
                  <strong>{money(subtotal + tax)}</strong>
                </div>
              </div>
              <button
                className="button primary full"
                disabled={!subtotal || busy}
                onClick={checkout}
              >
                <QrCode size={17} />
                {busy ? "Creating receipt…" : "Complete sale & create QR"}
              </button>
              <p className="tiny centered">
                This simulates a completed payment. No money is charged.
              </p>
            </>
          )}
        </section>
      </div>
    </>
  );
}
