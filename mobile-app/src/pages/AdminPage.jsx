import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import useMenuStore from '../store/menuStore';
import Users from './Admin/Users';
import RestaurantProfile from './Admin/RestaurantProfile';
import {
  listWorkstations,
  createWorkstation,
  updateWorkstation,
  deleteWorkstation,
} from '../services/workstationsService';
import './AdminPage.css';

function AdminPage() {
  const isAdmin = useAuthStore((state) => state.isAdmin);
  
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
          className={activeSection === 'restaurant' ? 'active' : ''}
          onClick={() => setActiveSection('restaurant')}
        >
          🏪 Προφίλ Ταβέρνας
        </button>
        <button
          className={activeSection === 'workstations' ? 'active' : ''}
          onClick={() => setActiveSection('workstations')}
        >
          🏪 Διαχείριση Σημείων
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
          className={activeSection === 'menu' ? 'active' : ''}
          onClick={() => setActiveSection('menu')}
        >
          📋 Μενού
        </button>
      </div>

      <div className="admin-content">
        {activeSection === 'users' && <Users />}
        {activeSection === 'restaurant' && <RestaurantProfile />}
        {activeSection === 'workstations' && (
          <WorkstationsSection 
            endpoints={endpoints}
          />
        )}
        {activeSection === 'menu' && (
          <MenuSection onResetMenu={handleResetMenu} />
        )}
      </div>
    </div>
  );
}

function WorkstationsSection({ endpoints = [] }) {
  const workstations = useMenuStore((state) => state.workstations);
  const loadWorkstations = useMenuStore((state) => state.loadWorkstations);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingWorkstationId, setEditingWorkstationId] = useState(null);
  const [editingData, setEditingData] = useState({});
  const [newWorkstationData, setNewWorkstationData] = useState({ name: '', slug: '', color: '#667eea' });
  const [createError, setCreateError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        await loadWorkstations();
        setError(null);
      } catch (err) {
        console.error('[Workstations] Failed to load workstations:', err);
        setError('Αποτυχία φόρτωσης σημείων');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [loadWorkstations]);

  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  useEffect(() => {
    if (createError) {
      const timer = setTimeout(() => setCreateError(''), 5000);
      return () => clearTimeout(timer);
    }
  }, [createError]);

  const handleCreateWorkstation = async (e) => {
    e.preventDefault();
    setCreateError('');

    if (!newWorkstationData.name.trim()) {
      setCreateError('Το όνομα είναι απαραίτητο');
      return;
    }

    if (!newWorkstationData.slug.trim()) {
      setCreateError('Το slug είναι απαραίτητο');
      return;
    }

    try {
      setIsSubmitting(true);
      const newWorkstation = await createWorkstation({
        name: newWorkstationData.name,
        slug: newWorkstationData.slug.toLowerCase().trim(),
        color: newWorkstationData.color,
      });
      setNewWorkstationData({ name: '', slug: '', color: '#667eea' });
      await loadWorkstations();
      setShowCreateModal(false);
      setSuccessMessage(`Σημείο "${newWorkstation.name}" δημιουργήθηκε με επιτυχία`);
    } catch (err) {
      console.error('[Workstations] Failed to create workstation:', err);
      setCreateError(err.detail || err.message || 'Αποτυχία δημιουργίας σημείου');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartEditColor = (workstation) => {
    setEditingWorkstationId(workstation.id);
    setEditingData({ name: workstation.name, slug: workstation.slug, color: workstation.color });
  };

  const handleSaveColor = async (workstationId) => {
    try {
      setIsSubmitting(true);
      setError(null);
      const updatedWorkstation = await updateWorkstation(workstationId, {
        name: editingData.name,
        slug: editingData.slug,
        color: editingData.color,
      });
      await loadWorkstations();
      setSuccessMessage('Σημείο ενημερώθηκε επιτυχώς');
      setEditingWorkstationId(null);
    } catch (err) {
      console.error('[Workstations] Failed to update:', err);
      setError(err.detail || err.message || 'Αποτυχία ενημέρωσης');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelEdit = () => {
    setEditingWorkstationId(null);
    setEditingData({});
  };

  const handleToggleActive = async (workstation) => {
    try {
      setIsSubmitting(true);
      setError(null);
      const updatedWorkstation = await updateWorkstation(workstation.id, {
        active: !workstation.active,
      });
      await loadWorkstations();
      const action = updatedWorkstation.active ? 'ενεργοποιήθηκε' : 'απενεργοποιήθηκε';
      setSuccessMessage(`Σημείο "${workstation.name}" ${action}`);
    } catch (err) {
      console.error('[Workstations] Failed to toggle active:', err);
      setError(err.detail || err.message || 'Αποτυχία ενημέρωσης');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteWorkstation = async (workstation) => {
    if (
      !confirm(
        `Είστε σίγουροι ότι θέλετε να διαγράψετε το σημείο "${workstation.name}"; Τα στοιχεία που χρησιμοποιούν αυτή την κατηγορία θα πρέπει να ανατεθούν ξανά.`
      )
    ) {
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await deleteWorkstation(workstation.id);
      await loadWorkstations();
      setSuccessMessage(`Σημείο "${workstation.name}" διαγράφηκε`);
    } catch (err) {
      console.error('[Workstations] Failed to delete workstation:', err);
      setError(err.detail || err.message || 'Αποτυχία διαγραφής');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Διαχείριση Σημείων Εξυπηρέτησης</h2>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreateModal(true)}
          disabled={loading || isSubmitting}
        >
          + Προσθήκη
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {successMessage && <div className="alert alert-success">{successMessage}</div>}

      {loading ? (
        <p className="info-text">Φόρτωση σημείων...</p>
      ) : workstations.length === 0 ? (
        <p className="info-text">Δεν βρέθηκαν σημεία εξυπηρέτησης.</p>
      ) : (
        <div className="endpoint-list">
          {workstations.map((workstation) => (
            <div key={workstation.id} className="endpoint-card">
              {editingWorkstationId === workstation.id ? (
                <>
                  <div className="endpoint-color-edit">
                    <input
                      type="color"
                      value={editingData.color || workstation.color || '#667eea'}
                      onChange={(e) =>
                        setEditingData((prev) => ({ ...prev, color: e.target.value }))
                      }
                      disabled={isSubmitting}
                    />
                  </div>
                  <div className="endpoint-info">
                    <div className="form-group">
                      <input
                        type="text"
                        value={editingData.name}
                        onChange={(e) =>
                          setEditingData((prev) => ({ ...prev, name: e.target.value }))
                        }
                        disabled={isSubmitting}
                        placeholder="Όνομα"
                      />
                    </div>
                    <div className="form-group">
                      <input
                        type="text"
                        value={editingData.slug}
                        onChange={(e) =>
                          setEditingData((prev) => ({ ...prev, slug: e.target.value }))
                        }
                        disabled={isSubmitting}
                        placeholder="Slug"
                      />
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      className="btn btn-small btn-primary"
                      onClick={() => handleSaveColor(workstation.id)}
                      disabled={isSubmitting}
                    >
                      ✓
                    </button>
                    <button
                      className="btn btn-small btn-cancel"
                      onClick={handleCancelEdit}
                      disabled={isSubmitting}
                    >
                      ✗
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div
                    className="endpoint-color"
                    style={{ backgroundColor: workstation.color || '#667eea' }}
                    title="Κλικ για επεξεργασία"
                  />
                  <div className="endpoint-info">
                    <h3>{workstation.name}</h3>
                    <p>{workstation.slug}</p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      className="btn btn-small"
                      onClick={() => handleStartEditColor(workstation)}
                      title="Επεξεργασία"
                    >
                      ✎
                    </button>
                    <button
                      className={`btn btn-small ${workstation.active ? 'btn-danger' : 'btn-success'}`}
                      onClick={() => handleToggleActive(workstation)}
                      disabled={isSubmitting}
                      title={workstation.active ? 'Απενεργοποίηση' : 'Ενεργοποίηση'}
                    >
                      {workstation.active ? '⊘' : '✓'}
                    </button>
                    <button
                      className="delete-btn"
                      onClick={() => handleDeleteWorkstation(workstation)}
                      disabled={isSubmitting}
                      title="Διαγραφή"
                    >
                      🗑
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Workstation Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Προσθήκη Νέου Σημείου</h2>
              <button
                className="close-btn"
                onClick={() => setShowCreateModal(false)}
              >
                ×
              </button>
            </div>
            <form onSubmit={handleCreateWorkstation}>
              <div style={{ padding: '20px' }}>
                {createError && <div className="alert alert-error" style={{ marginBottom: '15px' }}>{createError}</div>}
                
                <div className="form-group">
                  <label htmlFor="ws-name">Όνομα *</label>
                  <input
                    type="text"
                    id="ws-name"
                    value={newWorkstationData.name}
                    onChange={(e) =>
                      setNewWorkstationData((prev) => ({
                        ...prev,
                        name: e.target.value,
                      }))
                    }
                    placeholder="π.χ., Ψησταριά"
                    disabled={isSubmitting}
                    autoFocus
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="ws-slug">Slug *</label>
                  <input
                    type="text"
                    id="ws-slug"
                    value={newWorkstationData.slug}
                    onChange={(e) =>
                      setNewWorkstationData((prev) => ({
                        ...prev,
                        slug: e.target.value,
                      }))
                    }
                    placeholder="π.χ., grill (χωρίς κενά)"
                    disabled={isSubmitting}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="ws-color">Χρώμα</label>
                  <input
                    type="color"
                    id="ws-color"
                    value={newWorkstationData.color}
                    onChange={(e) =>
                      setNewWorkstationData((prev) => ({
                        ...prev,
                        color: e.target.value,
                      }))
                    }
                    disabled={isSubmitting}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-cancel"
                  onClick={() => setShowCreateModal(false)}
                  disabled={isSubmitting}
                >
                  Ακύρωση
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Δημιουργία...' : 'Δημιουργία'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
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
  const workstations = useMenuStore((state) => state.workstations);
  const loadWorkstations = useMenuStore((state) => state.loadWorkstations);

  useEffect(() => {
    loadMenu().finally(() => setLoading(false));
  }, [loadMenu]);

  useEffect(() => {
    loadWorkstations();
  }, [loadWorkstations]);

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

  const getCategoryLabel = (slug) => {
    const ws = workstations.find((item) => item.slug === slug);
    return ws?.name || slug;
  };

  const getCategoryColor = (slug) => {
    const ws = workstations.find((item) => item.slug === slug);
    return ws?.color || '#667eea';
  };

  const formatPrice = (price) => {
    const numericPrice = Number(price);
    if (Number.isFinite(numericPrice)) {
      return `€${numericPrice.toFixed(2)}`;
    }
    return '—';
  };

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
                <td style={{ padding: 12 }}>{formatPrice(item.price)}</td>
                <td style={{ padding: 12 }}>
                  <span style={{
                    padding: '4px 8px',
                    borderRadius: 4,
                    backgroundColor: getCategoryColor(item.category),
                    color: '#fff',
                    fontSize: 12,
                  }}>
                    {getCategoryLabel(item.category)}
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

