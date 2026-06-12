import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SchemeSathi Chatbot',
  description: 'Chatbot-first welfare scheme assistant for Indian users.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
