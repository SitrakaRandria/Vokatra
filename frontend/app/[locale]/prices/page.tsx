import { getPriceHistory } from '@/lib/api/prices';
import PriceChart from '@/components/prices/PriceChart';

export default async function PriceHistoryPage({ params: { locale } }: { params: { locale: string } }) {
  const history = await getPriceHistory({ months: 12 });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Historique des prix</h1>
      <div className="bg-white p-4 rounded-lg shadow">
        <PriceChart data={history} />
      </div>
    </div>
  );
}
