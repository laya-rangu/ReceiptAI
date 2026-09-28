import Link from "next/link";
import { ArrowRight, Camera, MessageCircle, QrCode } from "lucide-react";
export default function Guide() {
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">START SMALL. FIND CLARITY.</div>
          <h1>A quick little guide.</h1>
          <p>Two ways to collect. One place to remember.</p>
        </div>
      </div>
      <div className="guide-grid">
        {[
          {
            icon: Camera,
            title: "1. Save a paper receipt",
            text: "Upload a JPG, PNG or PDF. Review the original, enter or correct the details, and confirm. The amounts must add up before the receipt is saved.",
            href: "/upload",
            action: "Upload a receipt",
          },
          {
            icon: QrCode,
            title: "2. Try a digital receipt",
            text: "Sign in to the merchant demo, build a basket, and complete the simulated sale. Copy the QR link, switch to a customer account, and open it to claim the receipt.",
            href: "/merchant",
            action: "Visit merchant studio",
          },
          {
            icon: MessageCircle,
            title: "3. Find a little insight",
            text: "Ask for this month’s spending or search for a product by name. Answers link back to your saved receipts. Unconfirmed drafts are excluded from calculations.",
            href: "/chat",
            action: "Ask your assistant",
          },
        ].map(({ icon: Icon, ...step }) => (
          <section key={step.title} className="panel guide-card">
            <Icon size={30} />
            <h2>{step.title}</h2>
            <p>{step.text}</p>
            <Link className="text-link" href={step.href}>
              {step.action}
              <ArrowRight size={16} />
            </Link>
          </section>
        ))}
      </div>
    </>
  );
}
