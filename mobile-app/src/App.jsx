import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import useAuthStore from './store/authStore';
import useMenuStore from './store/menuStore';
import useNotificationStore from './store/notificationStore';
import { AdminRoute, ProtectedRoute, SetupRoute } from './components/RouteGuards';

// Pages
import LoginPage from './pages/LoginPage';
import SetupPage from './pages/SetupPage';
import HomePage from './pages/HomePage';
import AdminPage from './pages/AdminPage';
import MenuEditor from './pages/Admin/MenuEditor';
import NLPReview from './pages/Admin/NLPReview';
import OrdersHistory from './pages/OrdersHistory';
import ReceiptView from './pages/ReceiptView';

function App() {
  const loadMenu = useMenuStore((state) => state.loadMenu);
  const initializeNotifications = useNotificationStore((state) => state.initialize);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isMenuSetup = useMenuStore((state) => state.isMenuSetup);

  useEffect(() => {
    // Initialize PWA
    const initializeApp = async () => {
      // Load menu
      await loadMenu();

      // Initialize notifications
      await initializeNotifications();
    };

    initializeApp();
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
            <AdminRoute>
              <AdminPage />
            </AdminRoute>
          }
        />

        <Route
          path="/admin/menu"
          element={
            <AdminRoute>
              <MenuEditor />
            </AdminRoute>
          }
        />

        <Route
          path="/admin/nlp"
          element={
            <AdminRoute>
              <NLPReview />
            </AdminRoute>
          }
        />

        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <OrdersHistory />
            </ProtectedRoute>
          }
        />

        <Route
          path="/receipt/:receiptId"
          element={
            <ProtectedRoute>
              <ReceiptView />
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

