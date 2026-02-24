import { useEffect, useState } from 'react';
import {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
} from '../../services/usersService';
import { BASE_ROLES, buildStationRoles, getRoleLabel } from '../../constants/roles';
import useMenuStore from '../../store/menuStore';
import CreateUserModal from '../../components/CreateUserModal';
import './Users.css';

function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingUserId, setEditingUserId] = useState(null);
  const [editingRole, setEditingRole] = useState('');
  const [resetPasswordModalOpen, setResetPasswordModalOpen] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const workstations = useMenuStore((state) => state.workstations);
  const loadWorkstations = useMenuStore((state) => state.loadWorkstations);

  // Load users on mount
  useEffect(() => {
    loadUsers();
  }, []);

  useEffect(() => {
    loadWorkstations();
  }, [loadWorkstations]);

  // Auto-clear messages after 5 seconds
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

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listUsers();
      setUsers(data);
    } catch (err) {
      console.error('[Users] Failed to load users:', err);
      setError(err.detail || err.message || 'Αποτυχία φόρτωσης χρηστών');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (formData) => {
    try {
      setIsSubmitting(true);
      setError(null);
      const newUser = await createUser({
        username: formData.username,
        password: formData.password,
        roles: formData.roles,
      });
      setUsers((prev) => [newUser, ...prev]);
      setSuccessMessage(`Ο χρήστης "${newUser.username}" δημιουργήθηκε`);
      setCreateModalOpen(false);
    } catch (err) {
      console.error('[Users] Failed to create user:', err);
      setError(err.detail || err.message || 'Αποτυχία δημιουργίας χρήστη');
      throw err; // Re-throw to let modal handle it
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartEditRoles = (user) => {
    setEditingUserId(user.id);
    setEditingRole((user.roles || [])[0] || '');
  };

  const handleRoleChange = (roleValue) => {
    setEditingRole(roleValue);
  };

  const handleSaveRoles = async (userId) => {
    if (!editingRole) {
      setError('Παρακαλώ επιλέξτε ρόλο');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      const updatedUser = await updateUser(userId, { roles: [editingRole] });
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? updatedUser : u))
      );
      setSuccessMessage('Ο ρόλος ενημερώθηκε');
      setEditingUserId(null);
    } catch (err) {
      console.error('[Users] Failed to update roles:', err);
      setError(err.detail || err.message || 'Αποτυχία ενημέρωσης ρόλου');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelEdit = () => {
    setEditingUserId(null);
    setEditingRole('');
  };

  const handleResetPasswordClick = (user) => {
    setResetPasswordModalOpen(user.id);
    setNewPassword('');
    setPasswordError(null);
  };

  const handleSaveNewPassword = async (userId) => {
    if (!newPassword.trim()) {
      setPasswordError('Ο κωδικός δεν μπορεί να είναι κενός');
      return;
    }
    if (newPassword.length < 4) {
      setPasswordError('Ο κωδικός πρέπει να έχει τουλάχιστον 4 χαρακτήρες');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      const user = users.find((u) => u.id === userId);
      const updatedUser = await updateUser(userId, { password: newPassword });
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? updatedUser : u))
      );
      setSuccessMessage(`Ο κωδικός για τον χρήστη "${user.username}" ενημερώθηκε`);
      setResetPasswordModalOpen(null);
      setNewPassword('');
    } catch (err) {
      console.error('[Users] Failed to reset password:', err);
      setPasswordError(err.detail || err.message || 'Αποτυχία ενημέρωσης κωδικού');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (!confirm(`Είστε σίγουροι ότι θέλετε να διαγράψετε τον χρήστη "${username}";`)) {
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await deleteUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      setSuccessMessage(`Ο χρήστης "${username}" διαγράφηκε`);
    } catch (err) {
      console.error('[Users] Failed to delete user:', err);
      setError(err.detail || err.message || 'Αποτυχία διαγραφής χρήστη');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    try {
      return new Date(dateString).toLocaleString('el-GR', { timeZone: 'Europe/Athens' });
    } catch {
      return dateString;
    }
  };

  const roleOptions = [...BASE_ROLES, ...buildStationRoles(workstations)];

  return (
    <div className="users-page">
      <div className="users-header">
        <h1>Διαχείριση Χρηστών</h1>
        <button
          className="btn btn-primary"
          onClick={() => setCreateModalOpen(true)}
          disabled={loading || isSubmitting}
        >
          + Δημιουργία Χρήστη
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {successMessage && <div className="alert alert-success">{successMessage}</div>}

      {loading ? (
        <div className="loading">Φόρτωση χρηστών...</div>
      ) : users.length === 0 ? (
        <div className="empty-state">
          <p>Δεν βρέθηκαν χρήστες. Δημιουργήστε έναν για να ξεκινήσετε.</p>
        </div>
      ) : (
        <div className="users-table-container">
          <table className="users-table">
            <thead>
              <tr>
                <th>Όνομα χρήστη</th>
                <th>Ρόλος</th>
                <th>Δημιουργήθηκε</th>
                <th>Ενέργειες</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td className="username-cell">{user.username}</td>
                  <td className="roles-cell">
                    {editingUserId === user.id ? (
                      <div className="roles-edit">
                        <select
                          className="role-select"
                          value={editingRole}
                          onChange={(e) => handleRoleChange(e.target.value)}
                          disabled={isSubmitting}
                        >
                          <option value="">Επιλέξτε ρόλο</option>
                          {roleOptions.map((role) => (
                            <option key={role.value} value={role.value}>
                              {role.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    ) : (
                      <div className="roles-display">
                        {(user.roles || []).length > 0 ? (
                          <span className="role-badge">
                            {getRoleLabel((user.roles || [])[0], workstations)}
                          </span>
                        ) : (
                          <span className="no-roles">Χωρίς ρόλο</span>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="date-cell">{formatDate(user.created_at)}</td>
                  <td className="actions-cell">
                    {editingUserId === user.id ? (
                      <div className="action-buttons">
                        <button
                          className="btn btn-small btn-primary"
                          onClick={() => handleSaveRoles(user.id)}
                          disabled={isSubmitting}
                        >
                          Αποθήκευση
                        </button>
                        <button
                          className="btn btn-small btn-cancel"
                          onClick={handleCancelEdit}
                          disabled={isSubmitting}
                        >
                          Ακύρωση
                        </button>
                      </div>
                    ) : (
                      <div className="action-buttons">
                        <button
                          className="btn btn-small"
                          onClick={() => handleStartEditRoles(user)}
                          title="Ρόλος"
                        >
                          Ρόλος
                        </button>
                        <button
                          className="btn btn-small"
                          onClick={() => handleResetPasswordClick(user)}
                          title="Κωδικός"
                        >
                          Κωδικός
                        </button>
                        <button
                          className="btn btn-small btn-danger"
                          onClick={() => handleDeleteUser(user.id, user.username)}
                          title="Διαγραφή"
                        >
                          Διαγραφή
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <CreateUserModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSubmit={handleCreateUser}
        isLoading={isSubmitting}
        roleOptions={roleOptions}
      />

      {/* Reset Password Modal */}
      {resetPasswordModalOpen !== null && (
        <div className="modal-overlay" onClick={() => setResetPasswordModalOpen(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Επαναφορά Κωδικού</h2>
              <button
                className="close-btn"
                onClick={() => setResetPasswordModalOpen(null)}
              >
                ×
              </button>
            </div>
            <div style={{ padding: '20px' }}>
              <div className="form-group">
                <label htmlFor="new-password">Νέος κωδικός</label>
                <input
                  type="password"
                  id="new-password"
                  value={newPassword}
                  onChange={(e) => {
                    setNewPassword(e.target.value);
                    setPasswordError(null);
                  }}
                  placeholder="Εισάγετε νέο κωδικό"
                  disabled={isSubmitting}
                />
                {passwordError && <span className="error">{passwordError}</span>}
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-cancel"
                onClick={() => setResetPasswordModalOpen(null)}
                disabled={isSubmitting}
              >
                Ακύρωση
              </button>
              <button
                className="btn btn-primary"
                onClick={() => handleSaveNewPassword(resetPasswordModalOpen)}
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Αποθήκευση...' : 'Αποθήκευση'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Users;
