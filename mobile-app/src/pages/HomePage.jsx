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
  const getAccessibleEndpoints = useAuthStore((state) => state.getAccessibleEndpoints);
  const endpoints = useMenuStore((state) => state.endpoints);
  const isMuted = useNotificationStore((state) => state.isMuted);
  const toggleMute = useNotificationStore((state) => state.toggleMute);
  
  const [activeTab, setActiveTab] = useState('waiter');
  const navigate = useNavigate();

  const accessibleEndpoints = getAccessibleEndpoints();

  useEffect(() => {
    // Set initial tab based on user role
    if (user?.role && user.role !== 'admin') {
      setActiveTab(user.role);
    }
  }, [user]);

  const handleLogout = async () => {
    if (confirm('Είστε σίγουροι ότι θέλετε να αποσυνδεθείτε;')) {
      await logout();
      navigate('/login');
    }
  };

  const handleAdminPanel = () => {
    navigate('/admin');
  };

  return (
    <div className="home-page">
      {/* Header */}
      <div className="app-header">
        <div className="header-left">
          <h1>🍽️ Tavern</h1>
          <span className="user-badge">{user?.name}</span>
        </div>
        <div className="header-right">
          <button
            onClick={toggleMute}
            className="icon-button"
            title={isMuted ? 'Ενεργοποίηση ειδοποιήσεων' : 'Απενεργοποίηση ειδοποιήσεων'}
          >
            {isMuted ? '🔕' : '🔔'}
          </button>
          {user?.role === 'admin' && (
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
            if (!endpoint) return null;
            
            return (
              <button
                key={endpointId}
                className={`tab ${activeTab === endpointId ? 'active' : ''}`}
                onClick={() => setActiveTab(endpointId)}
                style={{
                  borderBottomColor: activeTab === endpointId ? endpoint.color : 'transparent'
                }}
              >
                {endpoint.name}
              </button>
            );
          })}
        </div>
      )}

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'waiter' && <WaiterView />}
        {activeTab === 'kitchen' && <StationView station="kitchen" />}
        {activeTab === 'grill' && <StationView station="grill" />}
        {activeTab === 'drinks' && <StationView station="drinks" />}
      </div>
    </div>
  );
}

export default HomePage;

