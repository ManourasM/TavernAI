import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { LocalNotifications } from '@capacitor/local-notifications';
import { Preferences } from '@capacitor/preferences';

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
          const permission = await LocalNotifications.requestPermissions();
          if (permission.display === 'granted') {
            console.log('Notification permissions granted');
            return { success: true };
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
          await LocalNotifications.schedule({
            notifications: [
              {
                title,
                body,
                id: Date.now(),
                schedule: { at: new Date(Date.now() + 100) },
                sound: soundEnabled ? 'beep.wav' : undefined,
                attachments: undefined,
                actionTypeId: '',
                extra: data,
              },
            ],
          });

          // Add to notification history
          const notification = {
            id: Date.now(),
            title,
            body,
            timestamp: new Date().toISOString(),
            read: false,
          };

          set({ notifications: [notification, ...get().notifications] });

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
        
        await Preferences.set({
          key: 'notifications_muted',
          value: JSON.stringify(newMuted),
        });

        return { success: true, isMuted: newMuted };
      },

      // Toggle sound
      toggleSound: async () => {
        const newSound = !get().soundEnabled;
        set({ soundEnabled: newSound });
        
        await Preferences.set({
          key: 'notifications_sound',
          value: JSON.stringify(newSound),
        });

        return { success: true, soundEnabled: newSound };
      },

      // Toggle vibration
      toggleVibration: async () => {
        const newVibration = !get().vibrationEnabled;
        set({ vibrationEnabled: newVibration });
        
        await Preferences.set({
          key: 'notifications_vibration',
          value: JSON.stringify(newVibration),
        });

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

