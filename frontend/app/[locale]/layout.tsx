import { ReactNode } from 'react';
import { notFound } from 'next/navigation';
import { i18n, type Locale } from '@/lib/i18n/config';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import '@/styles/globals.css';

interface LayoutProps {
  children: ReactNode;
  params: { locale: string };
}

export async function generateStaticParams() {
  return i18n.locales.map((locale) => ({ locale }));
}

export default async function RootLayout({ children, params }: LayoutProps) {
  const { locale } = params;
  // Vérifier si la locale est supportée
  if (!i18n.locales.includes(locale as Locale)) {
    notFound();
  }

  return (
    <html lang={locale} className="h-full">
      <body className="flex min-h-screen flex-col bg-gray-50 font-sans antialiased">
        <Header locale={locale} />
        <main className="flex-1 container mx-auto px-4 py-6 md:px-6 lg:px-8">
          {children}
        </main>
        <Footer locale={locale} />
      </body>
    </html>
  );
}
