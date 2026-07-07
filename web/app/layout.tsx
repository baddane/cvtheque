import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CVthèque",
  description: "Recherche de CV par ville, diplôme, compétences.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
