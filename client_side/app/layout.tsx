import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Behördenbrief Assistant",
};

/**
 * Root layout that wraps every page of the app.
 *
 * @param props - Layout props from Next.js.
 * @param props.children - The page content to render inside the body.
 * @returns The HTML document with the page content.
 */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
