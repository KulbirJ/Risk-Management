import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '../components/AuthProvider';
import { ThemeProvider } from '../components/ThemeProvider';
import { ToastProvider } from '../components/Toast';
import Layout from '../components/Layout';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: 'EdgeVision — Intelligent Analytics & Insights',
  description: 'Enterprise threat risk assessment and compliance management platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} ${inter.variable}`}>
        <ThemeProvider>
          <ToastProvider>
            <AuthProvider>
              <Layout>{children}</Layout>
            </AuthProvider>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
