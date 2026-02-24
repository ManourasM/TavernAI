import { useState } from 'react';
import './CorrectionModal.css';

function CorrectionModal({ item, menu, onSubmit, onCancel, loading }) {
  const [selectedItemId, setSelectedItemId] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    if (!selectedItemId) {
      setError('Παρακαλώ επιλέξτε το σωστό είδος');
      return;
    }

    try {
      await onSubmit({
        raw_text: item.text,
        predicted_item_id: item.menu_id ? String(item.menu_id) : null,
        corrected_item_id: String(selectedItemId)
      });
      
      // Reset form on success
      setSelectedItemId('');
      setError(null);
    } catch (err) {
      setError(err.message || 'Σφάλμα κατά την αποστολή διόρθωσης');
    }
  };

  // Flatten menu items for dropdown
  const flatMenuItems = [];
  if (menu && typeof menu === 'object') {
    Object.values(menu).forEach(section => {
      if (Array.isArray(section)) {
        section.forEach(item => {
          if (item && item.id && item.name) {
            flatMenuItems.push(item);
          }
        });
      }
    });
  }

  return (
    <div className="correction-modal-overlay">
      <div className="correction-modal">
        <div className="correction-modal-header">
          <h2>✏️ Διόρθωση Ταξινόμησης</h2>
          <button className="close-button" onClick={onCancel} disabled={loading}>
            ✕
          </button>
        </div>

        <div className="correction-modal-content">
          <div className="correction-item-info">
            <h3>Αρχικό είδος προς διόρθωση:</h3>
            <div className="original-text">{item.text}</div>
            {item.menu_name && (
              <p className="classified-as">
                <strong>Ταξινομήθηκε ως:</strong> {item.menu_name}
              </p>
            )}
          </div>

          <div className="correction-form">
            <label htmlFor="correction-select">
              <strong>Σωστό είδος:</strong>
              <select
                id="correction-select"
                value={selectedItemId}
                onChange={(e) => {
                  setSelectedItemId(e.target.value);
                  setError(null);
                }}
                disabled={loading}
              >
                <option value="">-- Επιλέξτε είδος --</option>
                {flatMenuItems.map(item => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>

            {error && <div className="correction-error">❌ {error}</div>}
          </div>
        </div>

        <div className="correction-modal-actions">
          <button
            className="secondary-button"
            onClick={onCancel}
            disabled={loading}
          >
            Ακύρωση
          </button>
          <button
            className="primary-button"
            onClick={handleSubmit}
            disabled={loading || !selectedItemId}
          >
            {loading ? 'Αποστολή...' : 'Αποστολή Διόρθωσης'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default CorrectionModal;
