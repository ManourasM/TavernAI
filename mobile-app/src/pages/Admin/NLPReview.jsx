import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useMenuStore from '../../store/menuStore';
import { getNlpRules, updateNlpRule, deleteNlpRule } from '../../services/api';
import './NLPReview.css';

function NLPReview() {
  const navigate = useNavigate();
  const menu = useMenuStore((state) => state.menu);
  const loadMenu = useMenuStore((state) => state.loadMenu);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [error, setError] = useState(null);

  const flatMenuItems = useMemo(() => {
    const items = [];
    if (menu && typeof menu === 'object') {
      Object.values(menu).forEach((section) => {
        if (Array.isArray(section)) {
          section.forEach((item) => {
            if (item && item.id && item.name) {
              items.push(item);
            }
          });
        }
      });
    }
    return items;
  }, [menu]);

  useEffect(() => {
    loadMenu();
  }, [loadMenu]);

  const loadRules = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getNlpRules();
      setRules(data);
    } catch (err) {
      setError(err.message || 'Σφάλμα φόρτωσης κανόνων');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRules();
  }, []);

  const handleUpdateRule = async (ruleId, updates) => {
    setSavingId(ruleId);
    try {
      const updated = await updateNlpRule(ruleId, updates);
      setRules((prev) => prev.map((rule) => (rule.id === ruleId ? updated : rule)));
    } catch (err) {
      alert(err.message || 'Σφάλμα ενημέρωσης κανόνα');
    } finally {
      setSavingId(null);
    }
  };

  const handleDeleteRule = async (ruleId) => {
    if (!confirm('Είστε σίγουροι ότι θέλετε να διαγράψετε τον κανόνα;')) return;
    setSavingId(ruleId);
    try {
      await deleteNlpRule(ruleId);
      setRules((prev) => prev.filter((rule) => rule.id !== ruleId));
    } catch (err) {
      alert(err.message || 'Σφάλμα διαγραφής κανόνα');
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="nlp-review-page">
      <div className="nlp-review-header">
        <button onClick={() => navigate('/admin')} className="back-button">
          ← Επιστροφή
        </button>
        <h1>🧠 Κανόνες NLP</h1>
        <button onClick={loadRules} className="refresh-button" disabled={loading}>
          ↻ Ανανέωση
        </button>
      </div>

      {loading && <p className="info-text">Φόρτωση κανόνων...</p>}
      {error && <div className="error-text">❌ {error}</div>}

      {!loading && !error && rules.length === 0 && (
        <p className="info-text">Δεν υπάρχουν καταχωρημένοι κανόνες.</p>
      )}

      {!loading && rules.length > 0 && (
        <div className="rules-table-wrapper">
          <table className="rules-table">
            <thead>
              <tr>
                <th>Freetext</th>
                <th>Σωστό είδος</th>
                <th>Τελευταία ενημέρωση</th>
                <th>Ενέργειες</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <RuleRow
                  key={rule.id}
                  rule={rule}
                  menuItems={flatMenuItems}
                  saving={savingId === rule.id}
                  onSave={handleUpdateRule}
                  onDelete={handleDeleteRule}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RuleRow({ rule, menuItems, saving, onSave, onDelete }) {
  const [rawText, setRawText] = useState(rule.raw_text || '');
  const [correctedId, setCorrectedId] = useState(rule.corrected_item_id || '');

  useEffect(() => {
    setRawText(rule.raw_text || '');
    setCorrectedId(rule.corrected_item_id || '');
  }, [rule]);

  const hasChanges = rawText !== rule.raw_text || correctedId !== (rule.corrected_item_id || '');

  return (
    <tr>
      <td>
        <input
          className="rule-input"
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          disabled={saving}
        />
      </td>
      <td>
        <select
          className="rule-select"
          value={correctedId}
          onChange={(e) => setCorrectedId(e.target.value)}
          disabled={saving}
        >
          <option value="">-- Επιλέξτε είδος --</option>
          {menuItems.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </td>
      <td>{new Date(rule.created_at).toLocaleString('el-GR')}</td>
      <td className="rule-actions">
        <button
          className="btn-save"
          onClick={() => onSave(rule.id, { raw_text: rawText, corrected_item_id: correctedId })}
          disabled={!hasChanges || saving || !rawText.trim()}
        >
          Αποθήκευση
        </button>
        <button
          className="btn-delete"
          onClick={() => onDelete(rule.id)}
          disabled={saving}
        >
          Διαγραφή
        </button>
      </td>
    </tr>
  );
}

export default NLPReview;
