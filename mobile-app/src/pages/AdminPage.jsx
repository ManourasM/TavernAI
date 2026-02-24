import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore, { ROLES } from '../store/authStore';
import useMenuStore from '../store/menuStore';
import './AdminPage.css';

function AdminPage() {
  const user = useAuthStore((state) => state.user);
  const isAdmin = useAuthStore((state) => state.isAdmin);
  const users = useAuthStore((state) => state.users);
  const addUser = useAuthStore((state) => state.addUser);
  const deleteUser = useAuthStore((state) => state.deleteUser);
  
  const endpoints = useMenuStore((state) => state.endpoints);
  const addEndpoint = useMenuStore((state) => state.addEndpoint);
  const deleteEndpoint = useMenuStore((state) => state.deleteEndpoint);
  const resetMenu = useMenuStore((state) => state.resetMenu);
  
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState('users');

  // Redirect if not admin
  if (!isAdmin()) {
    navigate('/home');
    return null;
  }

  const handleResetMenu = async () => {
    if (confirm('Είστε σίγουροι ότι θέλετε να επαναφέρετε το μενού; Αυτό θα διαγράψει όλα τα δεδομένα μενού.')) {
      await resetMenu();
      navigate('/setup');
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-header">
        <button onClick={() => navigate('/home')} className="back-button">
          ← Επιστροφή
        </button>
        <h1>⚙️ Πίνακας Διαχείρισης</h1>
      </div>

      <div className="admin-navigation">
        <button
          className={activeSection === 'users' ? 'active' : ''}
          onClick={() => setActiveSection('users')}
        >
          👥 Χρήστες
        </button>
        <button
          className={activeSection === 'menu-editor' ? 'active' : ''}
          onClick={() => navigate('/admin/menu')}
        >
          🧾 Επεξεργασία Μενού
        </button>
        <button
          className={activeSection === 'nlp-rules' ? 'active' : ''}
          onClick={() => navigate('/admin/nlp')}
        >
          🧠 Κανόνες
        </button>
        <button
          className={activeSection === 'endpoints' ? 'active' : ''}
          onClick={() => setActiveSection('endpoints')}
        >
          📍 Σημεία Εξυπηρέτησης
        </button>
        <button
          className={activeSection === 'menu' ? 'active' : ''}
          onClick={() => setActiveSection('menu')}
        >
          📋 Μενού
        </button>
      </div>

      <div className="admin-content">
        {activeSection === 'users' && (
          <UsersSection users={users} addUser={addUser} deleteUser={deleteUser} />
        )}
        {activeSection === 'endpoints' && (
          <EndpointsSection 
            endpoints={endpoints} 
            addEndpoint={addEndpoint} 
            deleteEndpoint={deleteEndpoint} 
          />
        )}
        {activeSection === 'menu' && (
          <MenuSection onResetMenu={handleResetMenu} />
        )}
      </div>
    </div>
  );
}

function UsersSection({ users = [], addUser, deleteUser }) {
  return (
    <div className="section">
      <h2>Διαχείριση Χρηστών</h2>
      {users.length === 0 ? (
        <p className="info-text">Δεν υπάρχουν χρήστες ακόμα. Η διαχείριση χρηστών θα προστεθεί σύντομα.</p>
      ) : (
        <div className="user-list">
          {users.map((user) => (
            <div key={user.id} className="user-card">
              <div className="user-info">
                <h3>{user.name}</h3>
                <p>@{user.username} • {user.role}</p>
              </div>
              <button 
                onClick={() => deleteUser(user.id)} 
                className="delete-btn"
                disabled={user.role === ROLES.ADMIN}
              >
                Διαγραφή
              </button>
            </div>
          ))}
        </div>
      )}
      <p className="info-text" style={{marginTop: '20px'}}>
        Η δημιουργία νέων χρηστών θα προστεθεί σύντομα.
      </p>
    </div>
  );
}

function EndpointsSection({ endpoints = [], addEndpoint, deleteEndpoint }) {
  return (
    <div className="section">
      <h2>Διαχείριση Σημείων Εξυπηρέτησης</h2>
      {endpoints.length === 0 ? (
        <p className="info-text">Δεν υπάρχουν σημεία εξυπηρέτησης. Η διαχείριση σημείων θα προστεθεί σύντομα.</p>
      ) : (
        <div className="endpoint-list">
          {endpoints.map((endpoint) => (
            <div key={endpoint.id} className="endpoint-card">
              <div 
                className="endpoint-color" 
                style={{ backgroundColor: endpoint.color }}
              />
              <div className="endpoint-info">
                <h3>{endpoint.name}</h3>
                <p>{endpoint.id}</p>
              </div>
              <button 
                onClick={() => deleteEndpoint(endpoint.id)} 
                className="delete-btn"
              >
                Διαγραφή
              </button>
            </div>
          ))}
        </div>
      )}
      <p className="info-text" style={{marginTop: '20px'}}>
        Η δημιουργία νέων σημείων θα προστεθεί σύντομα.
      </p>
    </div>
  );
}

function MenuSection({ onResetMenu }) {
  const menu = useMenuStore((state) => state.menu);
  const [loading, setLoading] = useState(true);
  const loadMenu = useMenuStore((state) => state.loadMenu);

  useEffect(() => {
    loadMenu().finally(() => setLoading(false));
  }, [loadMenu]);

  if (loading) {
    return <div className="section"><p>Φόρτωση μενού...</p></div>;
  }

  if (!menu) {
    return (
      <div className="section">
        <h2>Διαχείριση Μενού</h2>
        <p>Δεν βρέθηκε μενού. Παρακαλώ ρυθμίστε το μενού πρώτα.</p>
      </div>
    );
  }

  // Flatten menu items from all sections
  const allItems = [];
  Object.entries(menu).forEach(([section, items]) => {
    if (Array.isArray(items)) {
      items.forEach(item => {
        allItems.push({ ...item, section });
      });
    }
  });

  return (
    <div className="section">
      <h2>Διαχείριση Μενού</h2>

      <div style={{ marginBottom: 20 }}>
        <p><strong>Σύνολο πιάτων:</strong> {allItems.length}</p>
      </div>

      <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#f5f5f5', position: 'sticky', top: 0 }}>
              <th style={{ padding: 12, textAlign: 'left', borderBottom: '2px solid #ddd' }}>Όνομα</th>
              <th style={{ padding: 12, textAlign: 'left', borderBottom: '2px solid #ddd' }}>Τιμή</th>
              <th style={{ padding: 12, textAlign: 'left', borderBottom: '2px solid #ddd' }}>Κατηγορία</th>
              <th style={{ padding: 12, textAlign: 'left', borderBottom: '2px solid #ddd' }}>Τμήμα</th>
            </tr>
          </thead>
          <tbody>
            {allItems.map((item) => (
              <tr key={item.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 12 }}>{item.name}</td>
                <td style={{ padding: 12 }}>€{item.price.toFixed(2)}</td>
                <td style={{ padding: 12 }}>
                  <span style={{
                    padding: '4px 8px',
                    borderRadius: 4,
                    backgroundColor: item.category === 'kitchen' ? '#4CAF50' : item.category === 'grill' ? '#FF5722' : '#2196F3',
                    color: '#fff',
                    fontSize: 12,
                  }}>
                    {item.category === 'kitchen' ? 'Κουζίνα' : item.category === 'grill' ? 'Ψησταριά' : 'Ποτά'}
                  </span>
                </td>
                <td style={{ padding: 12, fontSize: 14, color: '#666' }}>{item.section}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="menu-actions" style={{ marginTop: 20 }}>
        <button onClick={onResetMenu} className="danger-button">
          Επαναφορά Μενού
        </button>
        <p className="warning-text">
          Αυτό θα διαγράψει όλα τα δεδομένα μενού και θα επιστρέψει στην οθόνη ρύθμισης.
        </p>
      </div>
    </div>
  );
}

export default AdminPage;

