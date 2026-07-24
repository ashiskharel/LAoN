import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "LAoN — Lost Ancient Arts of Nepal",
  description:
    "Visitor camera: photograph a Nepali sculpture and find possible matches in open museum records. Research aid only — not a legal claim tool.",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    title: "LAoN",
    statusBarStyle: "black-translucent",
  },
  icons: {
    icon: "/icons/icon.svg",
    apple: "/icons/icon.svg",
  },
};

export const viewport: Viewport = {
  themeColor: "#0f1410",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="banner">
          Possible visual match — not a determination of legal ownership. LAoN
          does not file claims.
        </div>
        <main>
          <header className="app-header">
            <div className="brand">
              <strong>
                <Link href="/" style={{ color: "inherit", textDecoration: "none" }}>
                  LAoN
                </Link>
              </strong>
              <span>Lost Ancient Arts of Nepal</span>
            </div>
            <nav>
              <Link href="/">Home</Link>
              <Link href="/visit">Visitor camera</Link>
              <Link href="/research">Research</Link>
              <Link href="/catalog">Catalog</Link>
              <Link href="/map">Map</Link>
              <Link href="/about">About</Link>
            </nav>
          </header>
          {children}
          <footer>
            Independent open-source project. Not affiliated with museums or
            recovery campaigns. Code MIT · image licenses per object.{" "}
            <Link href="/about">Ethics & sources</Link>
          </footer>
        </main>
        <nav className="mobile-dock" aria-label="Primary">
          <Link href="/">
            <span className="dock-icon" aria-hidden>
              ⌂
            </span>
            Home
          </Link>
          <Link href="/visit" className="dock-camera">
            <span className="dock-icon" aria-hidden>
              ◎
            </span>
            Camera
          </Link>
          <Link href="/research">
            <span className="dock-icon" aria-hidden>
              ✎
            </span>
            Research
          </Link>
          <Link href="/catalog">
            <span className="dock-icon" aria-hidden>
              ≡
            </span>
            Catalog
          </Link>
        </nav>
      </body>
    </html>
  );
}
