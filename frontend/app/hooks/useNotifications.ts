import { useEffect, useState } from 'react';
import apiClient from '@/lib/api/client';

export function useNotifications(userId?: number) {
  const [isSupported, setIsSupported] = useState(false);
  const [permission, setPermission] = useState<NotificationPermission>('default');
  const [subscription, setSubscription] = useState<PushSubscription | null>(null);

  useEffect(() => {
    // Vérifier le support des notifications
    if ('Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window) {
      setIsSupported(true);
      setPermission(Notification.permission);
      
      // Demander la permission si pas encore accordée
      if (Notification.permission === 'default') {
        Notification.requestPermission().then(setPermission);
      }
    }
  }, []);

  // S'abonner aux notifications push
  const subscribeToPush = async () => {
    if (!isSupported || Notification.permission !== 'granted') {
      console.warn('Notifications non supportées ou refusées');
      return;
    }

    try {
      // Récupérer le service worker
      const registration = await navigator.serviceWorker.ready;
      
      // S'abonner
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY
      });
      
      setSubscription(subscription);
      
      // Envoyer le token au backend
      await apiClient.post('/notifications/register-token', {
        token: JSON.stringify(subscription),
        device_type: 'web'
      });
      
      console.log('Abonnement push réussi');
      return subscription;
      
    } catch (error) {
      console.error('Erreur d\'abonnement push:', error);
      throw error;
    }
  };

  // Se désabonner
  const unsubscribeFromPush = async () => {
    try {
      if (subscription) {
        await subscription.unsubscribe();
        await apiClient.delete('/notifications/unregister-token', {
          params: { token: JSON.stringify(subscription) }
        });
        setSubscription(null);
        console.log('Désabonnement push réussi');
      }
    } catch (error) {
      console.error('Erreur de désabonnement:', error);
    }
  };

  return {
    isSupported,
    permission,
    subscription,
    subscribeToPush,
    unsubscribeFromPush
  };
}
