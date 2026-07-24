import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "LAoN Visitor Camera",
  description:
    "Take a photo of a sculpture in a gallery or temple and find possible catalog matches. Research aid only.",
  appleWebApp: {
    capable: true,
    title: "LAoN Camera",
    statusBarStyle: "black-translucent",
  },
};

/** Minimal chrome so the phone feels like a camera app, not a website. */
export default function VisitLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="visit-shell">
      <header className="visit-topbar">
        <Link href="/" className="visit-brand">
          LAoN
        </Link>
        <span className="visit-topbar-title">Visitor camera</span>
        <Link href="/catalog" className="visit-top-link">
          Catalog
        </Link>
      </header>
      <div className="visit-body">{children}</div>
      <p className="visit-legal">
        Possible visual match — not a legal ownership claim.
      </p>
    </div>
  );
}
