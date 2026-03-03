import { useState, useEffect } from 'react';
import { getProfile, updateProfile } from '../../services/restaurantService';
import './RestaurantProfile.css';

/**
 * Restaurant Profile Editor - Admin UI for managing restaurant info
 * 
 * Features:
 * - Display current restaurant profile (name, phone, address)
 * - Edit all fields with form validation
 * - Update profile on server
 * - Show last-updated timestamp
 * - Auto-clear success/error messages
 */
function RestaurantProfile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    address: '',
    extra_details: '',
  });

  // Load profile on mount
  useEffect(() => {
    loadProfile();
  }, []);

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

  const loadProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getProfile();
      setProfile(data);
      
      // Populate form with current profile data
      setFormData({
        name: data.name || '',
        phone: data.phone || '',
        address: data.address || '',
        extra_details: data.extra_details ? JSON.stringify(data.extra_details, null, 2) : '',
      });
    } catch (err) {
      console.error('[RestaurantProfile] Failed to load profile:', err);
      setError(err.message || 'Αποτυχία φόρτωσης προφίλ');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      // Validate form
      if (!formData.name.trim()) {
        throw new Error('Το όνομα της ταβέρνας είναι υποχρεωτικό');
      }

      // Parse extra_details if provided
      let extraDetails = null;
      if (formData.extra_details.trim()) {
        try {
          extraDetails = JSON.parse(formData.extra_details);
        } catch (parseErr) {
          throw new Error('Μη έγκυρο JSON στα επιπλέον στοιχεία');
        }
      }

      // Prepare payload
      const payload = {
        name: formData.name.trim(),
        phone: formData.phone.trim() || null,
        address: formData.address.trim() || null,
        extra_details: extraDetails,
      };

      // Submit update
      const updatedProfile = await updateProfile(payload);
      setProfile(updatedProfile);
      setSuccessMessage('✓ Το προφίλ ενημερώθηκε επιτυχώς');
    } catch (err) {
      console.error('[RestaurantProfile] Update failed:', err);
      setError(err.message || 'Αποτυχία ενημέρωσης προφίλ');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="restaurant-profile">
        <div className="profile-loading">Φόρτωση προφίλ ταβέρνας...</div>
      </div>
    );
  }

  return (
    <div className="restaurant-profile">
      <div className="profile-header">
        <h2>🏪 Προφίλ Ταβέρνας</h2>
        {profile && profile.updated_at && (
          <p className="last-updated">
            Τελευταία ενημέρωση: {new Date(profile.updated_at).toLocaleDateString('el-GR', {
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
              timeZone: 'Europe/Athens'
            })}
          </p>
        )}
      </div>

      {/* Messages */}
      {error && (
        <div className="alert alert-error">
          ❌ {error}
        </div>
      )}
      {successMessage && (
        <div className="alert alert-success">
          {successMessage}
        </div>
      )}

      {/* Profile Form */}
      <form onSubmit={handleSubmit} className="profile-form">
        <div className="form-group">
          <label htmlFor="name">
            Όνομα Ταβέρνας <span className="required">*</span>
          </label>
          <input
            id="name"
            type="text"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            placeholder="π.χ. Ταβέρνα Γιάννη"
            required
            disabled={isSubmitting}
            className="form-input"
          />
        </div>

        <div className="form-group">
          <label htmlFor="phone">Τηλέφωνο</label>
          <input
            id="phone"
            type="tel"
            name="phone"
            value={formData.phone}
            onChange={handleInputChange}
            placeholder="π.χ. +30 210 123 4567"
            disabled={isSubmitting}
            className="form-input"
          />
        </div>

        <div className="form-group">
          <label htmlFor="address">Διεύθυνση</label>
          <input
            id="address"
            type="text"
            name="address"
            value={formData.address}
            onChange={handleInputChange}
            placeholder="π.χ. Οδός Παναίας 42, Αθήνα"
            disabled={isSubmitting}
            className="form-input"
          />
        </div>

        <div className="form-group">
          <label htmlFor="extra_details">
            Επιπλέον Στοιχεία (JSON)
          </label>
          <textarea
            id="extra_details"
            name="extra_details"
            value={formData.extra_details}
            onChange={handleInputChange}
            placeholder={'{\n  "website": "https://taverna.gr",\n  "afm": "123456789"\n}'}
            disabled={isSubmitting}
            className="form-textarea"
            rows={6}
          />
          <small className="form-hint">
            Προαιρετικό. Δέχεται έγκυρο JSON format.
          </small>
        </div>

        <div className="form-actions">
          <button
            type="submit"
            disabled={isSubmitting}
            className="btn btn-primary"
          >
            {isSubmitting ? 'Αποθήκευση...' : '💾 Αποθήκευση'}
          </button>
          <button
            type="button"
            onClick={loadProfile}
            disabled={isSubmitting}
            className="btn btn-secondary"
          >
            ↻ Ακύρωση
          </button>
        </div>
      </form>

      {/* Current Profile Info */}
      {profile && (
        <div className="profile-preview">
          <h3>Τρέχοντα Στοιχεία</h3>
          <div className="preview-item">
            <span className="label">Όνομα:</span>
            <span className="value">{profile.name || '—'}</span>
          </div>
          <div className="preview-item">
            <span className="label">Τηλέφωνο:</span>
            <span className="value">{profile.phone || '—'}</span>
          </div>
          <div className="preview-item">
            <span className="label">Διεύθυνση:</span>
            <span className="value">{profile.address || '—'}</span>
          </div>
          {profile.extra_details && Object.keys(profile.extra_details).length > 0 && (
            <div className="preview-item">
              <span className="label">Επιπλέον:</span>
              <span className="value">
                <pre>{JSON.stringify(profile.extra_details, null, 2)}</pre>
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default RestaurantProfile;
