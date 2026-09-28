"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowDownToLine,
  ChevronLeft,
  ChevronRight,
  Plus,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { api, categories, Receipt } from "@/lib/api";
import { ErrorBox, Loading, ReceiptTable } from "@/components/ui";

export default function Receipts() {
  const [search, setSearch] = useState(""),
    [category, setCategory] = useState(""),
    [source, setSource] = useState(""),
    [page, setPage] = useState(1);
  const [start, setStart] = useState(""),
    [end, setEnd] = useState("");
  const [data, setData] = useState<{ items: Receipt[]; total: number } | null>(
      null,
    ),
    [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    const timer = setTimeout(() => {
      const params = new URLSearchParams({
        search,
        page: String(page),
        page_size: "10",
      });
      if (category) params.set("category", category);
      if (source) params.set("source", source);
      if (start) params.set("start", start);
      if (end) params.set("end", end);
      api<{ items: Receipt[]; total: number }>(`/me/receipts?${params}`)
        .then((d) => {
          if (alive) {
            setData(d);
            setError("");
          }
        })
        .catch((e) => {
          if (alive) setError(e.message);
        });
    }, 180);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [search, category, source, page, start, end]);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">EVERY PURCHASE HAS A PLACE</div>
          <h1>All your receipts.</h1>
          <p>From morning coffee to something worth keeping.</p>
        </div>
        <div className="heading-actions">
          <a href="/api/me/export" className="button secondary">
            <ArrowDownToLine size={16} />
            Export
          </a>
          <Link href="/upload" className="button primary">
            <Plus size={17} />
            Add receipt
          </Link>
        </div>
      </div>
      <ErrorBox message={error} />
      <section className="panel">
        <div className="receipt-filters">
          <label className="search-field">
            <Search size={18} />
            <input
              aria-label="Search receipts"
              placeholder="Search a merchant or item…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <SlidersHorizontal size={17} className="muted" />
          <select
            aria-label="Category filter"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <select
            aria-label="Source filter"
            value={source}
            onChange={(e) => {
              setSource(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All sources</option>
            <option value="QR">QR scans</option>
            <option value="PHOTO">Photo uploads</option>
          </select>
        </div>
        <div className="date-filters">
          <label>
            From{" "}
            <input
              type="date"
              aria-label="Start date"
              value={start}
              onChange={(e) => {
                setStart(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label>
            To{" "}
            <input
              type="date"
              aria-label="End date"
              value={end}
              onChange={(e) => {
                setEnd(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <span>{data?.total || 0} receipts in your workspace</span>
        </div>
        {data ? <ReceiptTable receipts={data.items} /> : <Loading />}
        <div className="pagination">
          <span>
            Page {page} of {Math.max(1, Math.ceil((data?.total || 0) / 10))}
          </span>
          <div>
            <button
              className="icon-button"
              aria-label="Previous page"
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              <ChevronLeft size={18} />
            </button>
            <button
              className="icon-button"
              aria-label="Next page"
              disabled={page * 10 >= (data?.total || 0)}
              onClick={() => setPage(page + 1)}
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </section>
    </>
  );
}
