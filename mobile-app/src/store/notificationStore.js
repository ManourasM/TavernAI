import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const useNotificationStore = create(
  persist(
    (set, get) => ({
      isMuted: false,
      soundEnabled: true,
      vibrationEnabled: true,
      notifications: [],

      // Initialize notifications (request permissions)
      initialize: async () => {
        try {
          if (!('Notification' in window)) {
            console.log('This browser does not support notifications');
            return { success: false, error: 'Notifications not supported' };
          }

          if (Notification.permission === 'granted') {
            console.log('Notification permissions already granted');
            return { success: true };
          }

          if (Notification.permission !== 'denied') {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
              console.log('Notification permissions granted');
              return { success: true };
            }
          }

          return { success: false, error: 'Notification permissions denied' };
        } catch (error) {
          console.error('Failed to request notification permissions:', error);
          return { success: false, error: error.message };
        }
      },

      // Send notification
      sendNotification: async (title, body, data = {}) => {
        const { isMuted, soundEnabled } = get();

        if (isMuted) {
          console.log('Notifications are muted');
          return { success: false, muted: true };
        }

        try {
          // Check if notifications are supported and permitted
          if (!('Notification' in window)) {
            console.log('Notifications not supported');
            return { success: false, error: 'Notifications not supported' };
          }

          if (Notification.permission !== 'granted') {
            console.log('Notification permission not granted');
            return { success: false, error: 'Permission not granted' };
          }

          // Create notification
          const notification = new Notification(title, {
            body,
            icon: '/pwa-192x192.png',
            badge: '/pwa-192x192.png',
            tag: `tavern-${Date.now()}`,
            requireInteraction: false,
            silent: !soundEnabled,
            data,
          });

          // Add to notification history
          const historyItem = {
            id: Date.now(),
            title,
            body,
            timestamp: new Date().toLocaleString('el-GR', { timeZone: 'Europe/Athens' }),
            read: false,
          };

          set({ notifications: [historyItem, ...get().notifications] });

          // Optional: Play sound if enabled
          if (soundEnabled) {
            try {
              const audio = new Audio('/notification.mp3');
              audio.play().catch(e => console.log('Could not play sound:', e));
            } catch (e) {
              console.log('Audio not available');
            }
          }

          return { success: true };
        } catch (error) {
          console.error('Failed to send notification:', error);
          return { success: false, error: error.message };
        }
      },

      // Toggle mute
      toggleMute: async () => {
        const newMuted = !get().isMuted;
        set({ isMuted: newMuted });
        return { success: true, isMuted: newMuted };
      },

      // Toggle sound
      toggleSound: async () => {
        const newSound = !get().soundEnabled;
        set({ soundEnabled: newSound });
        return { success: true, soundEnabled: newSound };
      },

      // Toggle vibration
      toggleVibration: async () => {
        const newVibration = !get().vibrationEnabled;
        set({ vibrationEnabled: newVibration });

        // Use Vibration API if available
        if (newVibration && 'vibrate' in navigator) {
          navigator.vibrate(200);
        }

        return { success: true, vibrationEnabled: newVibration };
      },

      // Mark notification as read
      markAsRead: (notificationId) => {
        const notifications = get().notifications.map((n) =>
          n.id === notificationId ? { ...n, read: true } : n
        );
        set({ notifications });
        return { success: true };
      },

      // Clear all notifications
      clearAll: () => {
        set({ notifications: [] });
        return { success: true };
      },

      // Get unread count
      getUnreadCount: () => {
        return get().notifications.filter((n) => !n.read).length;
      },
    }),
    {
      name: 'tavern-notification-storage',
    }
  )
);

export default useNotificationStore;

