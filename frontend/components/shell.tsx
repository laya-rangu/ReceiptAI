"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import {
  ArrowUpRight,
  ChevronDown,
  CircleHelp,
  LayoutDashboard,
  LogOut,
  Menu,
  Plus,
  ReceiptText,
  ShieldCheck,
  Sparkles,
  Store,
  X,
} from "lucide-react";
import { api, post, User } from "@/lib/api";
import { Loading } from "./ui";

const UserContext = createContext<User | null>(null);
export const useUser = () => useContext(UserContext)!;
const navigation = [
  { href: "/dashboard", name: "Overview", icon: LayoutDashboard },
  { href: "/receipts", name: "All receipts", icon: ReceiptText },
  { href: "/chat", name: "Your assistant", icon: Sparkles },
  { href: "/merchant", name: "Merchant studio", icon: Store },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch((e) => {
        if (e.status === 401)
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        else
          setError(
            "Cannot connect to the API. Make sure the backend is running on port 8000.",
          );
      });
  }, [router, pathname]);
  if (error) return <div className="loading">{error}</div>;
  if (!user) return <Loading />;
  const title =
    navigation.find((n) => pathname.startsWith(n.href))?.name ||
    (pathname.includes("review") ? "Review receipt" : "Add a receipt");
  return (
    <UserContext.Provider value={user}>
      <div className="app-shell">
        {open && (
          <button
            className="sidebar-overlay"
            onClick={() => setOpen(false)}
            aria-label="Close navigation"
          />
        )}
        <aside className={`sidebar ${open ? "is-open" : ""}`}>
          <Link className="brand" href="/dashboard">
            <span className="brand-mark">
              <ReceiptText size={23} />
            </span>
            Receipt<span className="brand-ai">AI</span>
            <span className="brand-dot" />
          </Link>
          <button
            className="workspace-switch"
            onClick={() => router.push("/settings")}
          >
            <span className="workspace-avatar">{user.name[0]}</span>
            <span>
              Personal workspace<small>Your everyday, organized</small>
            </span>
            <ChevronDown size={14} />
          </button>
          <div className="nav-label">WORKSPACE</div>
          <nav>
            {navigation.map(({ href, name, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={`nav-link ${pathname.startsWith(href) ? "active" : ""}`}
              >
                <Icon size={19} />
                {name}
                {name === "Your assistant" && (
                  <span className="new-label">BETA</span>
                )}
              </Link>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="sidebar-tip">
              <span className="tip-icon">
                <Sparkles size={18} />
              </span>
              <h4>Less paper. More clarity.</h4>
              <p>
                Give every purchase a place. Your future self will thank you.
              </p>
              <Link href="/upload">
                Add a receipt <ArrowUpRight size={15} />
              </Link>
            </div>
            <Link className="nav-link" href="/guide">
              <CircleHelp size={18} />
              Quick start guide
            </Link>
            <div className="privacy-note">
              <ShieldCheck size={14} />
              Your receipts belong to you.
            </div>
          </div>
        </aside>
        <div className="main-wrap">
          <header className="topbar">
            <div className="breadcrumb">
              <button
                className="icon-button mobile-menu"
                onClick={() => setOpen(!open)}
                aria-label="Open navigation"
              >
                {open ? <X /> : <Menu />}
              </button>
              <span>Workspace</span>
              <span className="slash">/</span>
              <strong>{title}</strong>
            </div>
            <div className="topbar-right">
              <span className="private-badge">
                <span />
                Private workspace
              </span>
              <Link
                className="user-avatar"
                href="/settings"
                aria-label="Account settings"
              >
                {user.name
                  .split(" ")
                  .map((n) => n[0])
                  .slice(0, 2)
                  .join("")}
              </Link>
              <button
                className="icon-button"
                title="Sign out"
                aria-label="Sign out"
                onClick={async () => {
                  await post("/auth/logout");
                  router.push("/login");
                }}
              >
                <LogOut size={16} />
              </button>
            </div>
          </header>
          <main className="page-content">{children}</main>
          <footer className="app-footer">
            <span>
              ReceiptAI <span className="footer-dot">·</span> A little more
              clarity.
            </span>
            <span>Made for your everyday.</span>
          </footer>
        </div>
        <Link className="mobile-add" href="/upload" aria-label="Add receipt">
          <Plus />
        </Link>
      </div>
    </UserContext.Provider>
  );
}
