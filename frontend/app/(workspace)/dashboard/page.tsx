"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Check,
  ChevronDown,
  Plus,
  QrCode,
  ReceiptText,
  Sparkles,
  Store,
  Wallet,
} from "lucide-react";
import { api, money, Receipt, Summary } from "@/lib/api";
import { useUser } from "@/components/shell";
import { ErrorBox, Loading, ReceiptTable } from "@/components/ui";

const colors = [
  "#34765b",
  "#94bca0",
  "#c9dca9",
  "#dfc48b",
  "#b9accd",
  "#dedfd8",
];
export default function Dashboard() {
  const user = useUser();
  const [summary, setSummary] = useState<Summary | null>(null),
    [receipts, setReceipts] = useState<Receipt[]>([]),
    [error, setError] = useState("");
  const [period, setPeriod] = useState("month");
  const today = new Date();
  const monthName = today.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });
  useEffect(() => {
    const now = new Date();
    const start = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
    const range = period === "month" ? `?start=${start}` : "";
    Promise.all([
      api<Summary>(`/me/spending${range}`),
      api<{ items: Receipt[] }>("/me/receipts?page_size=5"),
    ])
      .then(([s, r]) => {
        setSummary(s);
        setReceipts(r.items);
        setError("");
      })
      .catch((e) => setError(e.message));
  }, [period]);
  if (!summary && !error) return <Loading />;
  const weekly = Array.from(
    { length: 5 },
    (_, index) =>
      summary?.daily
        .filter(
          (day) =>
            Math.min(Math.floor((Number(day.date.slice(-2)) - 1) / 7), 4) ===
            index,
        )
        .reduce((s, day) => s + day.total_cents, 0) || 0,
  );
  const max = Math.max(...weekly, 1);
  const total = summary?.total_cents || 0;
  let percent = 0;
  const gradient =
    summary?.categories
      .map((cat, i) => {
        const begin = percent;
        percent += total ? (cat.total_cents / total) * 100 : 0;
        return `${colors[i % colors.length]} ${begin}% ${percent}%`;
      })
      .join(", ") || "#e9ece6 0% 100%";
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">YOUR MONEY, A LITTLE CLEARER</div>
          <h1>
            Hello, {user.name.split(" ")[0]}{" "}
            <span className="greeting-star">✳</span>
          </h1>
          <p>A little overview of your everyday spending.</p>
        </div>
        <div className="heading-actions">
          <a className="button secondary" href="/api/me/export">
            <ArrowDownToLine size={16} />
            Export
          </a>
          <Link className="button primary" href="/upload">
            <Plus size={18} />
            Add receipt
          </Link>
        </div>
      </div>
      <ErrorBox message={error} />
      <section className="welcome-banner">
        <div className="banner-copy">
          <span className="banner-tag">
            <span />
            EVERY LITTLE PURCHASE, TOGETHER
          </span>
          <h2>
            Your receipts.
            <br />
            Finally, in one place.
          </h2>
          <p>
            Scan a QR or upload a photo. We’ll keep the details
            <br className="desktop-only" /> organized, so you can focus on the
            bigger picture.
          </p>
          <Link href="/upload">
            Bring your next receipt <ArrowRight size={17} />
          </Link>
        </div>
        <div className="banner-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <span className="art-spark spark-one">✳</span>
          <span className="art-spark spark-two">✦</span>
          <div className="art-receipt back-receipt">
            <QrCode size={37} />
            <div className="art-line" />
            <div className="art-line short" />
          </div>
          <div className="art-receipt front-receipt">
            <span className="art-shop">
              <Store size={19} />
              THE EVERYDAY STORE
            </span>
            <div className="art-dotted" />
            <div className="art-row">
              <span>A little coffee</span>
              <span>5.50</span>
            </div>
            <div className="art-row">
              <span>Something sweet</span>
              <span>4.25</span>
            </div>
            <div className="art-dotted" />
            <div className="art-row art-total">
              <span>A good day</span>
              <span>✓</span>
            </div>
            <span className="art-barcode">|||| ||| || |||| ||| || ||||</span>
          </div>
          <div className="saved-bubble">
            <span>
              <Check size={14} />
            </span>
            One less thing to keep.
          </div>
        </div>
      </section>
      <div className="section-heading overview-heading">
        <h2>
          At a glance <span>{period === "month" ? monthName : "All time"}</span>
        </h2>
        <label className="period-select">
          <CalendarDays size={15} />
          <select
            aria-label="Spending period"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
          >
            <option value="month">This month</option>
            <option value="all">All time</option>
          </select>
          <ChevronDown size={13} />
        </label>
      </div>
      <div className="stats-grid">
        {[
          {
            label: "Total spending",
            value: money(total),
            icon: Wallet,
            note: "From your saved receipts",
            tone: "green",
          },
          {
            label: "Receipts collected",
            value: String(summary?.receipt_count || 0).padStart(2, "0"),
            icon: ReceiptText,
            note: `${receipts.filter((r) => r.source_type === "QR").length ? "QR scans & photo uploads" : "Every purchase has a home"}`,
            tone: "blue",
          },
          {
            label: "Places you shopped",
            value: String(summary?.merchant_count || 0).padStart(2, "0"),
            icon: Store,
            note: "A few familiar favorites",
            tone: "sand",
          },
        ].map(({ label, value, icon: Icon, note, tone }) => (
          <section className="stat-card" key={label}>
            <div>
              <span>{label}</span>
              <span className={`stat-icon ${tone}`}>
                <Icon size={19} />
              </span>
            </div>
            <strong>{value}</strong>
            <small>
              <span className="small-dot" />
              {note}
            </small>
          </section>
        ))}
      </div>
      <div className="insights-grid">
        <section className="panel spending-panel">
          <div className="section-heading">
            <div>
              <h2>Spending rhythm</h2>
              <p>
                {period === "month"
                  ? "The little things add up. Here’s your month."
                  : "All saved spending, grouped by day of the month."}
              </p>
            </div>
            <span className="chart-key">
              <span />
              Spending
            </span>
          </div>
          <div
            className="bar-chart"
            role="img"
            aria-label={`Spending by week: ${weekly.map((v, i) => `week ${i + 1} ${money(v)}`).join(", ")}`}
          >
            <div className="chart-y">
              <span>{money(max)}</span>
              <span>{money(Math.round(max / 2))}</span>
              <span>$0</span>
            </div>
            <div className="chart-bars">
              <div className="chart-gridline line-top" />
              <div className="chart-gridline line-middle" />
              <div className="chart-gridline line-bottom" />
              {weekly.map((value, index) => (
                <div className="bar-column" key={index}>
                  <div
                    className={`chart-bar ${value === max && value > 0 ? "highlight" : ""}`}
                    style={{ height: `${Math.max((value / max) * 145, 3)}px` }}
                  >
                    <span className="bar-value">{money(value)}</span>
                  </div>
                  <span className="bar-label">Week {index + 1}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
        <section className="panel category-panel">
          <div className="section-heading">
            <div>
              <h2>Where it went</h2>
              <p>Everyday spending, by category.</p>
            </div>
            <ArrowUpRight size={18} className="muted" />
          </div>
          <div className="category-chart">
            <div
              className="donut"
              style={{ background: `conic-gradient(${gradient})` }}
              role="img"
              aria-label="Spending by receipt category"
            >
              <div>
                <span>Total</span>
                <strong>{money(total)}</strong>
              </div>
            </div>
            <div className="category-legend">
              {summary?.categories.length ? (
                summary.categories.map((cat, i) => (
                  <div key={cat.name}>
                    <span
                      className="legend-dot"
                      style={{ background: colors[i % colors.length] }}
                    />
                    <span>{cat.name}</span>
                    <strong>
                      {Math.round((cat.total_cents / total) * 100)}%
                    </strong>
                  </div>
                ))
              ) : (
                <p className="muted">Add a receipt to see your categories.</p>
              )}
            </div>
          </div>
        </section>
      </div>
      <section className="panel recent-panel">
        <div className="section-heading">
          <div>
            <h2>Freshly filed</h2>
            <p>Your most recent receipts, all accounted for.</p>
          </div>
          <Link className="text-link" href="/receipts">
            View all receipts <ArrowRight size={15} />
          </Link>
        </div>
        <ReceiptTable receipts={receipts} />
      </section>
      {Boolean(summary?.pending_count) && (
        <Link href="/receipts" className="pending-banner">
          {summary?.pending_count} receipt(s) need your review before they count
          toward spending. <ArrowRight size={16} />
        </Link>
      )}
      <section className="assistant-strip">
        <span className="assistant-symbol">
          <Sparkles size={23} />
        </span>
        <div>
          <h3>Your receipts have answers.</h3>
          <p>
            “How much did I spend on groceries this month?” Start with a
            question.
          </p>
        </div>
        <Link className="button secondary" href="/chat">
          Ask your assistant <ArrowUpRight size={16} />
        </Link>
      </section>
    </>
  );
}
