'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useTranslation } from '@/lib/i18n/useTranslation';
import { Menu, X, Globe, User, LogIn } from 'lucide-react';
import Button from '@/components/ui/Button';

interface HeaderProps {
  locale: string;
}

export default function Header({ locale }: HeaderProps) {
  const { t } = useTranslation('common');
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isLangMenuOpen, setIsLangMenuOpen] = useState(false);

  // Pour simplifier, on suppose un utilisateur non connecté
  const isAuthenticated = false;

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen);
  const toggleLang = () => setIsLangMenuOpen(!isLangMenuOpen);

  const changeLanguage = (lng: string) => {
    // Changer la locale via Next.js (redirection)
    window.location.href = `/${lng}${window.location.pathname.slice(3)}`;
  };

  return (
    <header className="sticky top-0 z-50 bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4 md:px-6">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href={`/${locale}`} className="flex items-center space-x-2">
            <span className="text-2xl font-bold text-green-700">Vokatra</span>
          </Link>

          {/* Navigation Desktop */}
          <nav className="hidden md:flex items-center space-x-6">
            <Link href={`/${locale}/listings`} className="text-gray-700 hover:text-green-600 transition">
              {t('nav.listings')}
            </Link>
            <Link href={`/${locale}/transporters`} className="text-gray-700 hover:text-green-600 transition">
              {t('nav.transporters')}
            </Link>
            {isAuthenticated ? (
              <>
                <Link href={`/${locale}/offers`} className="text-gray-700 hover:text-green-600 transition">
                  {t('nav.offers')}
                </Link>
                <Link href={`/${locale}/profile`} className="text-gray-700 hover:text-green-600 transition">
                  <User size={20} />
                </Link>
              </>
            ) : (
              <Link href={`/${locale}/login`}>
                <Button variant="primary" size="sm">
                  <LogIn size={16} className="mr-2" />
                  {t('auth.login')}
                </Button>
              </Link>
            )}
          </nav>

          {/* Actions mobiles et bureau */}
          <div className="flex items-center space-x-4">
            {/* Sélecteur de langue */}
            <div className="relative">
              <button
                onClick={toggleLang}
                className="p-2 rounded-full hover:bg-gray-100 transition"
                aria-label="Changer la langue"
              >
                <Globe size={20} />
              </button>
              {isLangMenuOpen && (
                <div className="absolute right-0 mt-2 w-32 bg-white rounded-md shadow-lg border border-gray-200 py-1 z-50">
                  <button
                    onClick={() => changeLanguage('fr')}
                    className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                  >
                    Français
                  </button>
                  <button
                    onClick={() => changeLanguage('mg')}
                    className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                  >
                    Malagasy
                  </button>
                </div>
              )}
            </div>

            {/* Bouton menu mobile */}
            <button
              className="md:hidden p-2 rounded-full hover:bg-gray-100 transition"
              onClick={toggleMenu}
              aria-label="Menu"
            >
              {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* Navigation Mobile */}
        {isMenuOpen && (
          <nav className="md:hidden py-4 border-t border-gray-200 space-y-3">
            <Link
              href={`/${locale}/listings`}
              className="block px-3 py-2 rounded-md hover:bg-gray-100 transition"
              onClick={toggleMenu}
            >
              {t('nav.listings')}
            </Link>
            <Link
              href={`/${locale}/transporters`}
              className="block px-3 py-2 rounded-md hover:bg-gray-100 transition"
              onClick={toggleMenu}
            >
              {t('nav.transporters')}
            </Link>
            {isAuthenticated ? (
              <>
                <Link
                  href={`/${locale}/offers`}
                  className="block px-3 py-2 rounded-md hover:bg-gray-100 transition"
                  onClick={toggleMenu}
                >
                  {t('nav.offers')}
                </Link>
                <Link
                  href={`/${locale}/profile`}
                  className="block px-3 py-2 rounded-md hover:bg-gray-100 transition"
                  onClick={toggleMenu}
                >
                  {t('nav.profile')}
                </Link>
              </>
            ) : (
              <Link
                href={`/${locale}/login`}
                className="block px-3 py-2 rounded-md hover:bg-gray-100 transition"
                onClick={toggleMenu}
              >
                {t('auth.login')}
              </Link>
            )}
          </nav>
        )}
      </div>
    </header>
  );
}
