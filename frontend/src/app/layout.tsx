import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "온라인 교무실 (Online Faculty Hub)",
  description: "학교 업무 허브 및 올인원 교직원 포털",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="antialiased min-h-screen bg-slate-100">{children}</body>
    </html>
  );
}
