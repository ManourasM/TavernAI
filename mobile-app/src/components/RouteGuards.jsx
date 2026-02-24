import { Navigate } from 'react-router-dom';
import useAuthStore, { ROLES } from '../store/authStore';

/**
 * AdminRoute - Protects routes that require admin role
 * Renders children only if user is authenticated and has admin role
 * Otherwise redirects to login
 */
export function AdminRoute({ children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isAdmin = useAuthStore((state) => state.isAdmin);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin()) {
    return <Navigate to="/home" replace />;
  }

  return children;
}

/**
 * StationRoute - Protects routes that require specific station role
 * Renders children only if user is authenticated and has the specified station role
 * Otherwise redirects to login
 */
export function StationRoute({ station, children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const hasRole = useAuthStore((state) => state.hasRole);
  const isAdmin = useAuthStore((state) => state.isAdmin);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Admin can access all stations
  if (isAdmin()) {
    return children;
  }

  // Check if user has the specific station role
  const stationRoleMap = {
    kitchen: ROLES.KITCHEN,
    grill: ROLES.GRILL,
    drinks: ROLES.DRINKS,
    waiter: ROLES.WAITER,
  };

  const requiredRole = stationRoleMap[station];
  if (!requiredRole || !hasRole(requiredRole)) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

/**
 * ProtectedRoute - Generic authentication guard
 * Renders children only if user is authenticated
 * Otherwise redirects to login
 */
export function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

/**
 * SetupRoute - Allows access only for admins during setup
 * Used when menu setup is required
 */
export function SetupRoute({ children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isAdmin = useAuthStore((state) => state.isAdmin);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin()) {
    return <Navigate to="/home" replace />;
  }

  return children;
}
