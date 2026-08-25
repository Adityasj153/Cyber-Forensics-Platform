import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cyber Forensics Platform",
  description: "AI-Based Log Investigation Framework for Digital Forensics",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-ink-950 text-fog-200 min-h-screen">
        {children}
      </body>
    </html>
  );
}
