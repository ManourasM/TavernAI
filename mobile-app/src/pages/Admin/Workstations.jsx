import { useEffect, useState } from 'react';
import {
  listWorkstations,
  createWorkstation,
  updateWorkstation,
  deleteWorkstation,
} from '../../services/workstationsService';
import './Workstations.css';

function CreateWorkstationModal({ isOpen, onClose, onSubmit, isSubmitting }) {
  const [formData, setFormData] = useState({ name: '', slug: '' });
  const [errors, setErrors] = useState({});

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const validateForm = () => {
    const newErrors = {};
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }
    if (!formData.slug.trim()) {
      newErrors.slug = 'Slug is required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;
    
    try {
      await onSubmit(formData);
      setFormData({ name: '', slug: '' });
      setErrors({});
      onClose();
    } catch (err) {
      console.error('[CreateWorkstationModal] Error:', err);
      // Error handled by parent
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create Workstation</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Name *</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g., Grill Station"
              disabled={isSubmitting}
              autoFocus
            />
            {errors.name && <span className="error-text">{errors.name}</span>}
          </div>

          <div className="form-group">
            <label>Slug *</label>
            <input
              type="text"
              name="slug"
              value={formData.slug}
              onChange={handleChange}
              placeholder="e.g., grill (lowercase, no spaces)"
              disabled={isSubmitting}
            />
            {errors.slug && <span className="error-text">{errors.slug}</span>}
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-cancel"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Workstations() {
  const [workstations, setWorkstations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingWorkstationId, setEditingWorkstationId] = useState(null);
  const [editingData, setEditingData] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load workstations on mount
  useEffect(() => {
    loadWorkstations();
  }, []);

  // Auto-clear messages
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

  const loadWorkstations = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listWorkstations();
      // Sort by created_at descending
      data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setWorkstations(data);
    } catch (err) {
      console.error('[Workstations] Failed to load workstations:', err);
      setError(err.detail || err.message || 'Failed to load workstations');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWorkstation = async (formData) => {
    try {
      setIsSubmitting(true);
      setError(null);
      const newWorkstation = await createWorkstation({
        name: formData.name,
        slug: formData.slug.toLowerCase().trim(),
      });
      setWorkstations((prev) => [newWorkstation, ...prev]);
      setSuccessMessage(`Workstation "${newWorkstation.name}" created successfully`);
      setCreateModalOpen(false);
    } catch (err) {
      console.error('[Workstations] Failed to create workstation:', err);
      setError(err.detail || err.message || 'Failed to create workstation');
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartEdit = (workstation) => {
    setEditingWorkstationId(workstation.id);
    setEditingData({ name: workstation.name, slug: workstation.slug });
  };

  const handleCancelEdit = () => {
    setEditingWorkstationId(null);
    setEditingData({});
  };

  const handleSaveEdit = async (workstationId) => {
    if (!editingData.name.trim() || !editingData.slug.trim()) {
      setError('Name and slug are required');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      const updatedWorkstation = await updateWorkstation(workstationId, {
        name: editingData.name,
        slug: editingData.slug.toLowerCase().trim(),
      });
      setWorkstations((prev) =>
        prev.map((w) => (w.id === workstationId ? updatedWorkstation : w))
      );
      setSuccessMessage('Workstation updated successfully');
      setEditingWorkstationId(null);
      setEditingData({});
    } catch (err) {
      console.error('[Workstations] Failed to update workstation:', err);
      setError(err.detail || err.message || 'Failed to update workstation');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleActive = async (workstation) => {
    try {
      setIsSubmitting(true);
      setError(null);
      const updatedWorkstation = await updateWorkstation(workstation.id, {
        active: !workstation.active,
      });
      setWorkstations((prev) =>
        prev.map((w) => (w.id === workstation.id ? updatedWorkstation : w))
      );
      const action = updatedWorkstation.active ? 'activated' : 'deactivated';
      setSuccessMessage(`Workstation "${workstation.name}" ${action}`);
    } catch (err) {
      console.error('[Workstations] Failed to toggle active status:', err);
      setError(err.detail || err.message || 'Failed to update workstation');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteWorkstation = async (workstationId, name) => {
    if (
      !confirm(
        `Are you sure you want to delete workstation "${name}"? Items using this category will need to be reassigned.`
      )
    ) {
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await deleteWorkstation(workstationId);
      setWorkstations((prev) => prev.filter((w) => w.id !== workstationId));
      setSuccessMessage(`Workstation "${name}" deleted successfully`);
    } catch (err) {
      console.error('[Workstations] Failed to delete workstation:', err);
      setError(err.detail || err.message || 'Failed to delete workstation');
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

  return (
    <div className="workstations-page">
      <div className="workstations-header">
        <h1>Workstations Management</h1>
        <button
          className="btn btn-primary"
          onClick={() => setCreateModalOpen(true)}
          disabled={loading || isSubmitting}
        >
          + Create Workstation
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {successMessage && <div className="alert alert-success">{successMessage}</div>}

      {loading ? (
        <div className="loading">Loading workstations...</div>
      ) : workstations.length === 0 ? (
        <div className="empty-state">
          <p>No workstations found. Create one to get started.</p>
        </div>
      ) : (
        <div className="workstations-table-container">
          <table className="workstations-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Slug</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {workstations.map((workstation) => (
                <tr key={workstation.id} className={!workstation.active ? 'inactive-row' : ''}>
                  <td className="name-cell">
                    {editingWorkstationId === workstation.id ? (
                      <input
                        type="text"
                        value={editingData.name}
                        onChange={(e) =>
                          setEditingData((prev) => ({ ...prev, name: e.target.value }))
                        }
                        disabled={isSubmitting}
                        className="edit-input"
                      />
                    ) : (
                      workstation.name
                    )}
                  </td>
                  <td className="slug-cell">
                    {editingWorkstationId === workstation.id ? (
                      <input
                        type="text"
                        value={editingData.slug}
                        onChange={(e) =>
                          setEditingData((prev) => ({ ...prev, slug: e.target.value }))
                        }
                        disabled={isSubmitting}
                        className="edit-input"
                      />
                    ) : (
                      <code>{workstation.slug}</code>
                    )}
                  </td>
                  <td className="status-cell">
                    <span className={`status-badge ${workstation.active ? 'active' : 'inactive'}`}>
                      {workstation.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="date-cell">{formatDate(workstation.created_at)}</td>
                  <td className="actions-cell">
                    {editingWorkstationId === workstation.id ? (
                      <div className="action-buttons">
                        <button
                          className="btn btn-small btn-primary"
                          onClick={() => handleSaveEdit(workstation.id)}
                          disabled={isSubmitting}
                        >
                          Save
                        </button>
                        <button
                          className="btn btn-small btn-cancel"
                          onClick={handleCancelEdit}
                          disabled={isSubmitting}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div className="action-buttons">
                        <button
                          className="btn btn-small"
                          onClick={() => handleStartEdit(workstation)}
                          title="Edit Workstation"
                        >
                          Edit
                        </button>
                        <button
                          className={`btn btn-small btn-toggle ${workstation.active ? 'btn-danger' : 'btn-success'}`}
                          onClick={() => handleToggleActive(workstation)}
                          title={workstation.active ? 'Deactivate' : 'Activate'}
                        >
                          {workstation.active ? 'Deactivate' : 'Activate'}
                        </button>
                        <button
                          className="btn btn-small btn-danger"
                          onClick={() => handleDeleteWorkstation(workstation.id, workstation.name)}
                          title="Delete Workstation"
                        >
                          Delete
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

      <CreateWorkstationModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSubmit={handleCreateWorkstation}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}

export default Workstations;
