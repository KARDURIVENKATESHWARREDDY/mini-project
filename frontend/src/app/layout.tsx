import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: {
    default: "CARD-Net | Fraud Intelligence Platform",
    template: "%s | CARD-Net",
  },
  description:
    "CARD-Net — Credit Card Fraud Detection Research Platform. Advanced ML-powered fraud risk intelligence for Anurag University, Department of Artificial Intelligence.",
  keywords: ["fraud detection", "machine learning", "XGBoost", "credit card", "risk intelligence"],
  robots: "noindex, nofollow", // Research prototype — not for public indexing
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
