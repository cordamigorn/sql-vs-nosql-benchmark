import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SQL vs NoSQL Benchmark",
  description: "Local PostgreSQL and MongoDB benchmarking platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
