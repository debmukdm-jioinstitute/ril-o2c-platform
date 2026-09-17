import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RIL O2C AI Decision Intelligence Platform",
  description:
    "Probabilistic digital twin for petrochemical economics, market forecasting and capacity expansion.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
