import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const futura = localFont({
  src: "./fonts/Futura-Medium.woff",
  variable: "--font-futura",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Alarm Control Panel",
  description: "Control Panel for the Bobik alarm system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${futura.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
