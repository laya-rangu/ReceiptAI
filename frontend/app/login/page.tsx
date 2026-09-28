"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Check, ReceiptText, ShieldCheck } from "lucide-react";
import { api, post, User } from "@/lib/api";
import { ErrorBox } from "@/components/ui";

export default function Login() {
  const [register, setRegister] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [name, setName] = useState("");
  const [demo, setDemo] = useState(false);
  const router = useRouter();
  useEffect(() => {
    api<{ demo_mode: boolean }>("/health")
      .then((h) => setDemo(h.demo_mode))
      .catch(() =>
        setError("The API is offline. Start the backend on port 8000."),
      );
  }, []);
  async function signIn(demoEmail?: string) {
    setBusy(true);
    setError("");
    try {
      await post<User>(
        register && !demoEmail ? "/auth/register" : "/auth/login",
        demoEmail
          ? { email: demoEmail, password: "ReceiptAI-demo-2026" }
          : { email, password, ...(register ? { name } : {}) },
      );
      const next = new URLSearchParams(window.location.search).get("next");
      router.push(
        next?.startsWith("/") && !next.startsWith("//") && !next.includes("\\")
          ? next
          : demoEmail?.startsWith("merchant")
            ? "/merchant"
            : "/dashboard",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-page">
      <div className="login-story">
        <div className="brand">
          <span className="brand-mark">
            <ReceiptText />
          </span>
          ReceiptAI
        </div>
        <div>
          <span className="eyebrow">A LITTLE MORE CLARITY</span>
          <h1>
            Life happens.
            <br />
            Keep the receipts.
          </h1>
          <p>
            One quiet place for your purchases, your spending, and all those
            “where did I put it?” moments.
          </p>
          <div className="story-receipt">
            <span className="mini-star">✳</span>
            <strong>Your everyday, organized.</strong>
            <div>
              <Check size={17} />
              Scan it. Save it. Find it.
            </div>
            <div>
              <Check size={17} />
              Know where your money goes.
            </div>
            <div>
              <Check size={17} />
              Ask your purchase history.
            </div>
            <div className="receipt-dash" />
            <small>LESS PAPER. MORE PEACE OF MIND.</small>
          </div>
        </div>
        <span className="story-foot">
          Every purchase has a story. Keep yours.
        </span>
      </div>
      <div className="login-form-wrap">
        <div className="login-form">
          <span className="eyebrow">YOUR PERSONAL RECEIPT SPACE</span>
          <h2>{register ? "Make room for clarity." : "Welcome back."}</h2>
          <p>
            {register
              ? "Create your private workspace in a moment."
              : "Your receipts are right where you left them."}
          </p>
          <ErrorBox message={error} />
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void signIn();
            }}
          >
            {register && (
              <label>
                Your name
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                />
              </label>
            )}
            <label>
              Email address
              <input
                type="email"
                placeholder="you@example.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                placeholder={
                  register ? "At least 10 characters" : "Your password"
                }
                minLength={register ? 10 : 1}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={register ? "new-password" : "current-password"}
              />
            </label>
            <button className="button primary full" disabled={busy}>
              {busy
                ? "Just a moment…"
                : register
                  ? "Create account"
                  : "Sign in"}
              <ArrowRight size={17} />
            </button>
          </form>
          <button
            className="text-button login-toggle"
            onClick={() => setRegister(!register)}
          >
            {register
              ? "Already have an account? Sign in"
              : "New here? Create an account"}
          </button>
          {demo && (
            <div className="demo-login">
              <span>EXPLORE WITH SYNTHETIC DATA</span>
              <button
                className="button secondary full"
                disabled={busy}
                onClick={() => signIn("alex@receiptai.demo")}
              >
                Open customer demo <ArrowRight size={16} />
              </button>
              <div className="demo-links">
                <button
                  onClick={() => signIn("merchant@receiptai.demo")}
                  disabled={busy}
                >
                  Merchant demo
                </button>
                <span>·</span>
                <button
                  onClick={() => signIn("jamie@receiptai.demo")}
                  disabled={busy}
                >
                  Empty account demo
                </button>
              </div>
            </div>
          )}
          <div className="login-privacy">
            <ShieldCheck size={15} />
            Your receipts stay in your account.
          </div>
        </div>
      </div>
    </div>
  );
}
