import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { App as CapacitorApp } from '@capacitor/app';
import { StatusBar, Style } from '@capacitor/status-bar';
import useAuthStore from './store/authStore';
import useMenuStore from './store/menuStore';
import useNotificationStore from './store/notificationStore';

// Pages
import LoginPage from './pages/LoginPage';
import SetupPage from './pages/SetupPage';
import HomePage from './pages/HomePage';
import AdminPage from './pages/AdminPage';

// Protected Route Component
function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
}

// Setup Route Component (requires auth + checks if menu is setup)
function SetupRoute({ children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isMenuSetup = useMenuStore((state) => state.isMenuSetup);
  const user = useAuthStore((state) => state.user);
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  // Only admin can access setup
  if (user?.role !== 'admin') {
    return <Navigate to="/home" replace />;
  }
  
  return children;
}

function App() {
  const loadMenu = useMenuStore((state) => state.loadMenu);
  const initializeNotifications = useNotificationStore((state) => state.initialize);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isMenuSetup = useMenuStore((state) => state.isMenuSetup);

  useEffect(() => {
    // Initialize Capacitor plugins
    const initializeApp = async () => {
      try {
        // Set status bar style
        await StatusBar.setStyle({ style: Style.Light });
        await StatusBar.setBackgroundColor({ color: '#ffffff' });
      } catch (error) {
        console.log('StatusBar not available (web mode)');
      }

      // Load menu
      await loadMenu();

      // Initialize notifications
      await initializeNotifications();

      // Handle back button on Android
      CapacitorApp.addListener('backButton', ({ canGoBack }) => {
        if (!canGoBack) {
          CapacitorApp.exitApp();
        } else {
          window.history.back();
        }
      });
    };

    initializeApp();

    return () => {
      CapacitorApp.removeAllListeners();
    };
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Routes */}
        <Route
          path="/setup"
          element={
            <SetupRoute>
              <SetupPage />
            </SetupRoute>
          }
        />

        <Route
          path="/home"
          element={
            <ProtectedRoute>
              <HomePage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminPage />
            </ProtectedRoute>
          }
        />

        {/* Default Route */}
        <Route
          path="/"
          element={
            isAuthenticated ? (
              isMenuSetup ? (
                <Navigate to="/home" replace />
              ) : (
                <Navigate to="/setup" replace />
              )
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />

        {/* 404 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

