"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUp,
  ArrowUpRight,
  ReceiptText,
  Search,
  ShieldCheck,
  Sparkles,
  Wallet,
} from "lucide-react";
import { api, Message, money, post } from "@/lib/api";
import { ErrorBox } from "@/components/ui";

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]),
    [text, setText] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    api<Message[]>("/chat/history")
      .then(setMessages)
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);
  async function send(question = text) {
    if (!question.trim() || busy) return;
    setText("");
    setError("");
    setBusy(true);
    setMessages((previous) => [
      ...previous,
      { id: String(Date.now()), role: "user", content: question, evidence: [] },
    ]);
    try {
      const result = await post<Message>("/chat", { message: question });
      setMessages((previous) => [...previous, result]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">A CONVERSATION WITH YOUR EVERYDAY</div>
          <h1>Your purchase companion.</h1>
          <p>Less searching through receipts. More finding answers.</p>
        </div>
        <span className="mode-badge">
          <span />
          Exact search & spending
        </span>
      </div>
      <section className="panel chat-panel">
        {!messages.length && (
          <div className="chat-welcome">
            <div className="chat-orb">
              <Sparkles size={34} strokeWidth={1.3} />
            </div>
            <h2>Your receipts have a lot to say.</h2>
            <p>
              Ask about your spending, find that one purchase,
              <br />
              or revisit the little details. Start here.
            </p>
            <div className="prompt-grid">
              {[
                { icon: Wallet, text: "How much did I spend this month?" },
                { icon: Search, text: "Find headphones" },
                {
                  icon: ReceiptText,
                  text: "Total groceries spending last month",
                },
              ].map(({ icon: Icon, text: prompt }) => (
                <button key={prompt} onClick={() => send(prompt)}>
                  <Icon size={19} />
                  <span>{prompt}</span>
                  <ArrowRight size={16} />
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="chat-messages">
          {messages.map((message) => (
            <div className={`chat-message ${message.role}`} key={message.id}>
              {message.role === "assistant" && (
                <span className="message-icon">
                  <Sparkles size={18} />
                </span>
              )}
              <div>
                <div className="message-content">{message.content}</div>
                {message.evidence.length > 0 && (
                  <div className="evidence-list">
                    <span className="evidence-heading">FROM YOUR RECEIPTS</span>
                    {message.evidence.map((source) => (
                      <Link key={source.id} href={`/receipts/${source.id}`}>
                        <ReceiptText size={17} />
                        <span>
                          {source.merchant_name}
                          <small>
                            {money(source.total_cents)} · {source.purchased_at}
                          </small>
                        </span>
                        <ArrowUpRight size={16} />
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {busy && (
            <div className="chat-message assistant">
              <span className="message-icon">
                <Sparkles size={18} />
              </span>
              <div className="message-content muted">
                Checking your saved receipts…
              </div>
            </div>
          )}
          <div ref={bottom} />
        </div>
        <ErrorBox message={error} />
        <div className="chat-composer-wrap">
          <form
            className="chat-composer"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <input
              aria-label="Ask your assistant"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Ask something about your receipts…"
              maxLength={1000}
            />
            <button aria-label="Send message" disabled={busy || !text.trim()}>
              <ArrowUp size={20} />
            </button>
          </form>
          <p>
            <ShieldCheck size={12} />
            Answers use your saved receipts. Semantic AI search is coming in a
            later milestone.
          </p>
        </div>
      </section>
    </>
  );
}
