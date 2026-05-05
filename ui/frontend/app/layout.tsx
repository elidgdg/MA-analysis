import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "M&A Analogue Dashboard",
  description: "Pending deal analogue and comparison dashboard",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}