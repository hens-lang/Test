import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'LINK. Outreach',
  description: 'E-mailcampagneplatform van LINK.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="nl">
      <body>{children}</body>
    </html>
  );
}
