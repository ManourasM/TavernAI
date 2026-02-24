import { useState } from 'react';
import './CreateUserModal.css';

function CreateUserModal({ isOpen, onClose, onSubmit, isLoading, roleOptions = [] }) {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    role: '',
  });
  const [errors, setErrors] = useState({});

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear error for this field
    if (errors[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: null,
      }));
    }
  };

  const handleRoleSelect = (roleValue) => {
    setFormData((prev) => ({
      ...prev,
      role: roleValue,
    }));
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.username.trim()) {
      newErrors.username = 'Απαιτείται όνομα χρήστη';
    }

    if (!formData.password.trim()) {
      newErrors.password = 'Απαιτείται κωδικός';
    } else if (formData.password.length < 4) {
      newErrors.password = 'Ο κωδικός πρέπει να έχει τουλάχιστον 4 χαρακτήρες';
    }

    if (!formData.role) {
      newErrors.role = 'Επιλέξτε έναν ρόλο';
    }

    return newErrors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const formErrors = validateForm();
    if (Object.keys(formErrors).length > 0) {
      setErrors(formErrors);
      return;
    }

    try {
      await onSubmit({
        username: formData.username,
        password: formData.password,
        roles: formData.role ? [formData.role] : [],
      });
      // Reset form on success
      setFormData({
        username: '',
        password: '',
        role: '',
      });
      setErrors({});
      onClose();
    } catch (error) {
      // Error is handled by parent component
      console.error('[CreateUserModal] Submit error:', error);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Δημιουργία Χρήστη</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="create-user-form">
          <div className="form-group">
            <label htmlFor="username">Όνομα χρήστη</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleInputChange}
              placeholder="Εισάγετε όνομα χρήστη"
              disabled={isLoading}
            />
            {errors.username && <span className="error">{errors.username}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="password">Κωδικός</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleInputChange}
              placeholder="Εισάγετε κωδικό"
              disabled={isLoading}
            />
            {errors.password && <span className="error">{errors.password}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="role">Ρόλος</label>
            <select
              id="role"
              name="role"
              className="role-select"
              value={formData.role}
              onChange={(e) => handleRoleSelect(e.target.value)}
              disabled={isLoading}
            >
              <option value="">Επιλέξτε ρόλο</option>
              {roleOptions.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
            {errors.role && <span className="error">{errors.role}</span>}
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-cancel"
              onClick={onClose}
              disabled={isLoading}
            >
              Ακύρωση
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading}
            >
              {isLoading ? 'Δημιουργία...' : 'Δημιουργία'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreateUserModal;
