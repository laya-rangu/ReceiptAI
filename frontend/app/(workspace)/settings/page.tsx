"use client";
import { ArrowDownToLine, ShieldCheck } from "lucide-react";
import { useUser } from "@/components/shell";
export default function Settings() {
  const user = useUser();
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">YOUR LITTLE CORNER</div>
          <h1>Your workspace.</h1>
          <p>Personal by design.</p>
        </div>
      </div>
      <section className="panel settings-panel">
        <ShieldCheck size={30} />
        <h2>{user.name}</h2>
        <p>{user.email}</p>
        <span className="category-pill">{user.role}</span>
        <div className="receipt-dash" />
        <h3>Your data, to go.</h3>
        <p>
          Download your receipt records and line items as JSON. Original files
          can be downloaded from each receipt.
        </p>
        <a className="button secondary" href="/api/me/export">
          <ArrowDownToLine size={16} />
          Export my receipts
        </a>
        <div className="receipt-dash" />
        <h3>About this first release</h3>
        <p>
          This local MVP supports USD purchases, exact spending calculations,
          keyword search and receipt review. Supabase sign-in, semantic search,
          managed storage and cloud deployment are tracked as upcoming work.
        </p>
        <p>
          Remove an individual receipt from its detail page. Deletion also
          clears assistant history for your account.
        </p>
      </section>
    </>
  );
}
