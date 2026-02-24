import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import useMenuStore from '../store/menuStore';
import useNotificationStore from '../store/notificationStore';
import WaiterView from '../components/WaiterView';
import StationView from '../components/StationView';
import './HomePage.css';

function HomePage() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const isAdmin = useAuthStore((state) => state.isAdmin);
  const endpoints = useMenuStore((state) => state.endpoints);
  const workstations = useMenuStore((state) => state.workstations);
  const loadWorkstations = useMenuStore((state) => state.loadWorkstations);
  const isMuted = useNotificationStore((state) => state.isMuted);
  const toggleMute = useNotificationStore((state) => state.toggleMute);
  
  const [activeTab, setActiveTab] = useState('waiter');
  const navigate = useNavigate();

  useEffect(() => {
    loadWorkstations();
  }, [loadWorkstations]);

  const stationSlugs = endpoints.map((ep) => ep.id);
  const roleStations = (user?.roles || [])
    .filter((role) => role.startsWith('station_'))
    .map((role) => role.replace('station_', ''))
    .filter((slug) => stationSlugs.includes(slug));

  const accessibleStations = isAdmin()
    ? stationSlugs
    : roleStations;

  const accessibleEndpoints = [
    ...(isAdmin() || user?.roles?.includes('waiter') ? ['waiter'] : []),
    ...accessibleStations,
  ];

  useEffect(() => {
    // Set initial tab based on accessible endpoints
    // If user can only access kitchen, grill, or drinks, default to their station
    if (accessibleEndpoints.length === 1 && accessibleEndpoints[0] !== 'waiter') {
      setActiveTab(accessibleEndpoints[0]);
    }
  }, [accessibleEndpoints]);

  const handleLogout = async () => {
    if (confirm('Είστε σίγουροι ότι θέλετε να αποσυνδεθείτε;')) {
      await logout();
      navigate('/login');
    }
  };

  const handleAdminPanel = () => {
    navigate('/admin');
  };

  const handleMenuEditor = () => {
    navigate('/admin/menu');
  };

  const handleHistory = () => {
    navigate('/history');
  };

  // Get role display name for badge
  const getRoleBadge = () => {
    if (!user) return '';
    
    const roles = user.roles || [];
    if (roles.includes('admin')) return 'Διαχειριστής';
    if (roles.includes('waiter')) return 'Σερβιτόρος';
    const stationRole = roles.find((role) => role.startsWith('station_'));
    if (stationRole) {
      const slug = stationRole.replace('station_', '');
      const ws = workstations.find((item) => item.slug === slug);
      return ws?.name || slug;
    }
    return '';
  };

  return (
    <div className="home-page">
      {/* Header */}
      <div className="app-header">
        <div className="header-left">
          <h1>🍽️ Tavern</h1>
          <div className="header-info">
            <span className="user-badge">{user?.name}</span>
            <span className="role-badge">{getRoleBadge()}</span>
          </div>
        </div>
        <div className="header-right">
          <button
            onClick={toggleMute}
            className="icon-button"
            title={isMuted ? 'Ενεργοποίηση ειδοποιήσεων' : 'Απενεργοποίηση ειδοποιήσεων'}
          >
            {isMuted ? '🔕' : '🔔'}
          </button>
          {(isAdmin() || user?.roles?.includes('waiter')) && (
            <button onClick={handleHistory} className="icon-button" title="Ιστορικό Παραγγελιών">
              📋
            </button>
          )}
          {isAdmin() && (
            <button onClick={handleMenuEditor} className="icon-button" title="Επεξεργασια Μενού">
              🧾
            </button>
          )}
          {isAdmin() && (
            <button onClick={handleAdminPanel} className="icon-button" title="Πίνακας Διαχείρισης">
              ⚙️
            </button>
          )}
          <button onClick={handleLogout} className="icon-button" title="Αποσύνδεση">
            🚪
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      {accessibleEndpoints.length > 1 && (
        <div className="tab-navigation">
          {accessibleEndpoints.map((endpointId) => {
            const endpoint = endpoints.find((ep) => ep.id === endpointId);
            if (endpointId !== 'waiter' && !endpoint) return null;
            
            return (
              <button
                key={endpointId}
                className={`tab ${activeTab === endpointId ? 'active' : ''}`}
                onClick={() => setActiveTab(endpointId)}
                style={{
                  borderBottomColor: activeTab === endpointId ? (endpoint?.color || '#667eea') : 'transparent'
                }}
              >
                {endpointId === 'waiter' ? 'Σερβιτόρος' : endpoint.name}
              </button>
            );
          })}
        </div>
      )}

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'waiter' && <WaiterView />}
        {activeTab !== 'waiter' && (
          <StationView
            station={activeTab}
            stationName={endpoints.find((ep) => ep.id === activeTab)?.name}
            stationColor={endpoints.find((ep) => ep.id === activeTab)?.color}
          />
        )}
      </div>
    </div>
  );
}

export default HomePage;

