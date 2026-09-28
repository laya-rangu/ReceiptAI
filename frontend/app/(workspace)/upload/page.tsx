"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Camera,
  Check,
  FileImage,
  ImagePlus,
  QrCode,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { ErrorBox } from "@/components/ui";

export default function UploadPage() {
  const router = useRouter(),
    input = useRef<HTMLInputElement>(null),
    camera = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [drag, setDrag] = useState(false),
    [configured, setConfigured] = useState(false),
    [claim, setClaim] = useState("");
  useEffect(() => {
    api<{ extraction_configured: boolean }>("/health")
      .then((h) => setConfigured(h.extraction_configured))
      .catch(() => {});
  }, []);
  async function upload(file?: File) {
    if (!file || busy) return;
    if (file.size > 10 * 1024 * 1024) {
      setError("Please choose a file smaller than 10 MB.");
      return;
    }
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await api<{ receipt_id: string }>("/receipts/upload", {
        method: "POST",
        body: form,
      });
      router.push(`/review/${result.receipt_id}`);
    } catch (e) {
      const err = e as ApiError;
      setError(err.message);
      if (err.detail?.receipt_id)
        router.push(`/review/${err.detail.receipt_id}`);
    } finally {
      setBusy(false);
    }
  }
  function openClaim() {
    try {
      const url = new URL(claim, window.location.origin);
      const match = url.pathname.match(/^\/r\/([A-Za-z0-9_-]+)$/);
      if (!match) throw new Error();
      router.push(`/r/${match[1]}`);
    } catch {
      setError("Paste a valid ReceiptAI receipt link ending in /r/your-token.");
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">A NEW PLACE FOR YOUR PAPER TRAIL</div>
          <h1>Keep the good details.</h1>
          <p>A quick upload now. One less thing to find later.</p>
        </div>
      </div>
      <ErrorBox message={error} />
      <div className="upload-layout">
        <section className="panel upload-panel">
          <div className="section-heading">
            <div>
              <h2>Upload a receipt</h2>
              <p>We’ll keep the original alongside your purchase.</p>
            </div>
            <FileImage size={22} className="muted" />
          </div>
          <div
            className={`dropzone ${drag ? "dragging" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              void upload(e.dataTransfer.files[0]);
            }}
          >
            <span className="upload-symbol">
              <ImagePlus size={34} strokeWidth={1.4} />
            </span>
            <h3>
              {busy
                ? "Making room for your receipt…"
                : "Drop your receipt right here"}
            </h3>
            <p>or choose a photo or PDF from your device</p>
            <button
              className="button primary"
              disabled={busy}
              onClick={() => input.current?.click()}
            >
              <Upload size={17} />
              {busy ? "Uploading…" : "Choose a file"}
            </button>
            <small>JPG, PNG or PDF · Up to 10 MB · PDFs up to 5 pages</small>
            <input
              ref={input}
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              className="sr-only"
              aria-label="Receipt file"
              onChange={(e) => upload(e.target.files?.[0])}
            />
          </div>
          <button
            className="button secondary full camera-button"
            disabled={busy}
            onClick={() => camera.current?.click()}
          >
            <Camera size={18} />
            Take a photo instead
          </button>
          <input
            ref={camera}
            className="sr-only"
            type="file"
            accept="image/jpeg,image/png"
            capture="environment"
            aria-label="Receipt camera"
            onChange={(e) => upload(e.target.files?.[0])}
          />
          <div className="info-note">
            <ShieldCheck size={18} />
            <span>
              {configured
                ? "Receipt extraction is enabled. Your document is sent to the configured AI provider for processing; you review every detail before saving."
                : "Automatic extraction is not configured yet. Upload your receipt, then enter its details in the review form."}
            </span>
          </div>
        </section>
        <div>
          <section className="panel photo-tips">
            <span className="eyebrow">A CLEAR PHOTO GOES A LONG WAY</span>
            <h2>
              Little tips.
              <br />
              Better receipts.
            </h2>
            {[
              "Lay your receipt on a flat surface.",
              "Use natural light, without a flash.",
              "Keep all four corners in the frame.",
              "Make sure the text is in focus.",
            ].map((tip) => (
              <p key={tip}>
                <Check size={16} />
                {tip}
              </p>
            ))}
          </section>
          <section className="panel qr-link-panel">
            <QrCode size={25} />
            <h3>Have a merchant QR code?</h3>
            <p>
              Scan it with your phone’s camera, or paste your receipt link here.
            </p>
            <input
              aria-label="Receipt claim link"
              placeholder="https://…/r/…"
              value={claim}
              onChange={(e) => setClaim(e.target.value)}
            />
            <button className="text-link" onClick={openClaim} disabled={!claim}>
              Open receipt <ArrowRight size={16} />
            </button>
          </section>
        </div>
      </div>
    </>
  );
}
