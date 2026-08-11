'use client';

import { useEffect } from 'react';
import { useNotifications } from '@/hooks/useNotifications';
import { useAuth } from '@/hooks/useAuth';
import Button from '@/components/ui/Button';

export default function NotificationManager() {
  const { user } = useAuth();
  const {
    isSupported,
    permission,
    subscribeToPush,
    unsubscribeFromPush
  } = useNotifications(user?.id);

  useEffect(() => {
    // Enregistrer le service worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then(registration => {
          console.log('Service Worker enregistré:', registration);
        })
        .catch(error => {
          console.error('Erreur Service Worker:', error);
        });
    }
  }, []);

  if (!isSupported) {
    return null;
  }

  if (permission === 'denied') {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
        <p className="text-sm">
          Les notifications sont bloquées. Veuillez les autoriser dans les paramètres de votre navigateur.
        </p>
      </div>
    );
  }

  if (permission === 'default') {
    return (
      <Button
        onClick={subscribeToPush}
        variant="primary"
        size="sm"
      >
        Activer les notifications
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-4">
      <span className="text-sm text-green-600">
        🔔 Notifications activées
      </span>
      <Button
        onClick={unsubscribeFromPush}
        variant="secondary"
        size="sm"
      >
        Désactiver
      </Button>
    </div>
  );
}
