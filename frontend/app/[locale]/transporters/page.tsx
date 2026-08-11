import { getTranslations } from '@/lib/i18n/getTranslations';
import { getTransporters } from '@/lib/api/transporters';
import TransporterCard from '@/components/transporters/TransporterCard';

export default async function TransportersPage({ params: { locale } }: { params: { locale: string } }) {
  const t = await getTranslations(locale, 'common');
  const transporters = await getTransporters({ is_available: true });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{t('transporters.title')}</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {transporters.map(transporter => (
          <TransporterCard key={transporter.id} transporter={transporter} />
        ))}
      </div>
    </div>
  );
}
