import { getTranslations } from '@/lib/i18n/getTranslations';
import ListingGrid from '@/components/listings/ListingGrid';
import { getListings } from '@/lib/api/listings';

interface HomePageProps {
  params: { locale: string };
}

export default async function HomePage({ params: { locale } }: HomePageProps) {
  const t = await getTranslations(locale, 'common');
  // Récupération des annonces récentes (côté serveur)
  const listings = await getListings({ limit: 8, sort_by: 'created_at', sort_order: 'desc' });

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <section className="text-center py-12 bg-gradient-to-r from-green-50 to-emerald-50 rounded-2xl">
        <h1 className="text-4xl md:text-5xl font-bold text-green-800 mb-4">
          {t('hero.title')}
        </h1>
        <p className="text-lg md:text-xl text-gray-700 max-w-2xl mx-auto">
          {t('hero.subtitle')}
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-4">
          <a href={`/${locale}/listings`} className="inline-block px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition">
            {t('hero.cta.browse')}
          </a>
          <a href={`/${locale}/register`} className="inline-block px-6 py-3 bg-white text-green-700 border border-green-600 rounded-lg hover:bg-green-50 transition">
            {t('hero.cta.sell')}
          </a>
        </div>
      </section>

      {/* Dernières annonces */}
      <section>
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">
          {t('home.recent_listings')}
        </h2>
        <ListingGrid listings={listings} />
      </section>
    </div>
  );
}
