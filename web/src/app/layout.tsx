import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'LiveRecall',
  description: 'AI-powered screen recall with semantic search',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background antialiased">
        {children}
      </body>
    </html>
  );
}
