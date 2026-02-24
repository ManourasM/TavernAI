import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  createMenuVersion,
  formatDateTime,
  getMenuByVersion,
  getMenuVersions,
  getCurrentMenu,
} from '../../services/menuService';
import useMenuStore from '../../store/menuStore';
import './MenuEditor.css';

const emptyItem = {
  id: '',
  name: '',
  price: 0,
  category: 'kitchen',
  metadata: {},
};

function cloneMenu(menu) {
  return JSON.parse(JSON.stringify(menu || {}));
}

function generateItemId(section) {
  const safeSection = String(section || 'item').toLowerCase().replace(/\s+/g, '_');
  return `${safeSection}_${Date.now()}`;
}

function normalizePrice(value) {
  const parsed = parseFloat(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

/**
 * Remove metadata fields (like available_categories) from menu before saving.
 * API adds these for display, but they shouldn't be saved back.
 */
function cleanMenuForSave(menu) {
  const clean = JSON.parse(JSON.stringify(menu || {}));
  // Remove non-menu fields that API adds
  delete clean.available_categories;
  return clean;
}

function MenuEditor() {
  const navigate = useNavigate();
  const refreshMenu = useMenuStore((state) => state.refreshMenu);
  const workstations = useMenuStore((state) => state.workstations);
  const loadWorkstations = useMenuStore((state) => state.loadWorkstations);
  const [versions, setVersions] = useState([]);
  const [selectedVersionId, setSelectedVersionId] = useState(null);
  const [menuData, setMenuData] = useState(null);
  const [menuDraft, setMenuDraft] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [editingSection, setEditingSection] = useState('');
  const [addSection, setAddSection] = useState('');
  const [addName, setAddName] = useState('');
  const [addPrice, setAddPrice] = useState('');
  const [addCategory, setAddCategory] = useState('kitchen');
  const [addMetadata, setAddMetadata] = useState('');

  const latestVersionId = versions.length > 0 ? versions[0].id : null;
  const isReadOnly = latestVersionId !== null && selectedVersionId !== latestVersionId;

  // Build dynamic category options from workstations
  const categoryOptions = useMemo(() => {
    if (!workstations || workstations.length === 0) {
      // Fallback to defaults if workstations not loaded
      return [
        { value: 'kitchen', label: 'Κουζινα', active: true },
        { value: 'grill', label: 'Ψησταρια', active: true },
        { value: 'drinks', label: 'Ποτα', active: true },
      ];
    }
    return workstations
      .filter((ws) => ws.slug && ws.slug !== 'waiter')
      .map((ws) => ({
        value: ws.slug,
        label: ws.active ? ws.name || ws.slug : `${ws.name || ws.slug} (Inactive)`,
        active: ws.active !== false,
      }));
  }, [workstations]);

  useEffect(() => {
    loadWorkstations();
  }, [loadWorkstations]);

  useEffect(() => {
    loadVersionsAndMenu();
  }, []);

  const sections = useMemo(() => {
    const draft = menuDraft || {};
    return Object.keys(draft);
  }, [menuDraft]);

  const loadVersionsAndMenu = async () => {
    setLoading(true);
    setError(null);

    try {
      const versionList = await getMenuVersions();
      setVersions(Array.isArray(versionList) ? versionList : []);

      if (Array.isArray(versionList) && versionList.length > 0) {
        const latest = versionList[0];
        setSelectedVersionId(latest.id);
        const menu = await getMenuByVersion(latest.id);
        setMenuData(menu);
        setMenuDraft(cloneMenu(menu));
      } else {
        const menu = await getCurrentMenu();
        setMenuData(menu);
        setMenuDraft(cloneMenu(menu));
      }
    } catch (err) {
      console.error('[MenuEditor] Load error:', err);
      setError(err?.message || 'Αποτυχια φορτωσης μενου');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectVersion = async (versionId) => {
    setSelectedVersionId(versionId);
    setLoading(true);
    setError(null);

    try {
      const menu = await getMenuByVersion(versionId);
      setMenuData(menu);
      setMenuDraft(cloneMenu(menu));
    } catch (err) {
      console.error('[MenuEditor] Load version error:', err);
      setError(err?.message || 'Αποτυχια φορτωσης εκδοσης');
    } finally {
      setLoading(false);
    }
  };

  const buildDraftWithItem = (draft, sectionName, updatedItem) => {
    const next = cloneMenu(draft);
    const itemId = updatedItem.id;

    Object.keys(next).forEach((section) => {
      next[section] = next[section].filter((item) => item.id !== itemId);
    });

    if (!next[sectionName]) {
      next[sectionName] = [];
    }
    next[sectionName].push(updatedItem);

    return next;
  };

  const buildDraftWithoutItem = (draft, itemId) => {
    const next = cloneMenu(draft);
    Object.keys(next).forEach((section) => {
      next[section] = next[section].filter((item) => item.id !== itemId);
    });
    return next;
  };

  const refreshAfterSave = async () => {
    const versionList = await getMenuVersions();
    setVersions(Array.isArray(versionList) ? versionList : []);

    if (Array.isArray(versionList) && versionList.length > 0) {
      const latest = versionList[0];
      setSelectedVersionId(latest.id);
      const menu = await getMenuByVersion(latest.id);
      setMenuData(menu);
      setMenuDraft(cloneMenu(menu));
    }

    await refreshMenu();
  };

  const handleEditItem = (item, section) => {
    setEditingItem(item);
    setEditingSection(section);
    setModalOpen(true);
  };

  const handleToggleHidden = async (item, sectionName) => {
    setSaving(true);
    setError(null);

    try {
      const updatedItem = {
        ...item,
        hidden: !item.hidden,
      };
      const nextDraft = buildDraftWithItem(menuDraft, sectionName, updatedItem);
      setMenuDraft(nextDraft);
      await createMenuVersion(cleanMenuForSave(nextDraft));
      await refreshAfterSave();
    } catch (err) {
      console.error('[MenuEditor] Toggle hidden error:', err);
      setError(err?.message || 'Αποτυχια ενημερωσης');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveItem = async (updatedItem, sectionName) => {
    setSaving(true);
    setError(null);

    try {
      const nextDraft = buildDraftWithItem(menuDraft, sectionName, updatedItem);
      setMenuDraft(nextDraft);
      await createMenuVersion(cleanMenuForSave(nextDraft));
      await refreshAfterSave();
      setModalOpen(false);
    } catch (err) {
      console.error('[MenuEditor] Save item error:', err);
      setError(err?.message || 'Αποτυχια αποθηκευσης');
    } finally {
      setSaving(false);
    }
  };

  const handleSoftDelete = async (itemId) => {
    const itemEntry = findItemById(itemId);
    if (!itemEntry) return;

    const promptText = itemEntry.item.hidden
      ? 'Θελετε να εμφανισετε ξανα αυτο το ειδος;'
      : 'Θελετε να αποκρυψετε αυτο το ειδος;';

    if (!confirm(promptText)) return;

    await handleToggleHidden(itemEntry.item, itemEntry.sectionName);
  };

  const handlePermanentDelete = async (itemId) => {
    const itemEntry = findItemById(itemId);
    if (!itemEntry) return;

    if (!confirm('Θελετε να διαγραψετε για παντα αυτο το ειδος; Δεν μπορει να αναιρεθει.')) return;

    setSaving(true);
    setError(null);

    try {
      const nextDraft = buildDraftWithoutItem(menuDraft, itemId);
      setMenuDraft(nextDraft);
      await createMenuVersion(cleanMenuForSave(nextDraft));
      await refreshAfterSave();
    } catch (err) {
      console.error('[MenuEditor] Permanent delete error:', err);
      setError(err?.message || 'Αποτυχια διαγραφης');
    } finally {
      setSaving(false);
    }
  };

  const handleAddItem = async (event) => {
    event.preventDefault();

    const sectionName = addSection.trim();
    const itemName = addName.trim();
    if (!sectionName || !itemName) {
      setError('Συμπληρωστε τμημα και ονομα');
      return;
    }

    let metadata = {};
    if (addMetadata.trim()) {
      try {
        metadata = JSON.parse(addMetadata);
      } catch {
        setError('Μη εγκυρο JSON στα μεταδεδομενα');
        return;
      }
    }

    const newItem = {
      ...emptyItem,
      id: generateItemId(sectionName),
      name: itemName,
      price: normalizePrice(addPrice),
      category: addCategory,
      metadata,
    };

    setSaving(true);
    setError(null);

    try {
      const draft = cloneMenu(menuDraft);
      if (!draft[sectionName]) {
        draft[sectionName] = [];
      }
      draft[sectionName].push(newItem);
      setMenuDraft(draft);

      await createMenuVersion(cleanMenuForSave(draft));
      await refreshAfterSave();

      setAddSection('');
      setAddName('');
      setAddPrice('');
      setAddCategory('kitchen');
      setAddMetadata('');
    } catch (err) {
      console.error('[MenuEditor] Add item error:', err);
      setError(err?.message || 'Αποτυχια προσθηκης');
    } finally {
      setSaving(false);
    }
  };

  const findItemById = (itemId) => {
    const draft = menuDraft || {};
    for (const sectionName of Object.keys(draft)) {
      const match = (draft[sectionName] || []).find((entry) => entry.id === itemId);
      if (match) {
        return { item: match, sectionName };
      }
    }
    return null;
  };

  if (loading) {
    return (
      <div className="menu-editor">
        <div className="menu-editor-header">
          <button onClick={() => navigate('/admin')} className="back-button">
            ← Πισω
          </button>
          <h1>Επεξεργασια Μενού</h1>
        </div>
        <div className="menu-editor-loading">Φορτωση εκδοσεων...</div>
      </div>
    );
  }

  return (
    <div className="menu-editor">
      <div className="menu-editor-header">
        <button onClick={() => navigate('/admin')} className="back-button">
          ← Πισω
        </button>
        <div>
          <h1>Επεξεργασια Μενού</h1>
          <p>Διαχειριση εκδοσεων και ειδων μενου</p>
        </div>
      </div>

      {error && <div className="menu-editor-error">❌ {error}</div>}

      <div className="menu-editor-body">
        <VersionList
          versions={versions}
          selectedVersionId={selectedVersionId}
          onSelectVersion={handleSelectVersion}
        />

        <div className="menu-editor-panel">
          {isReadOnly && (
            <div className="menu-editor-info">
              Προβολη ιστορικης εκδοσης. Επιλεξτε την πιο προσφατη εκδοση για επεξεργασια.
            </div>
          )}

          <form className="menu-add-form" onSubmit={handleAddItem}>
            <h2>Προσθηκη Ειδους</h2>
            <div className="menu-form-grid">
              <input
                type="text"
                placeholder="Τμημα (π.χ. Salads)"
                value={addSection}
                onChange={(e) => setAddSection(e.target.value)}
                disabled={isReadOnly || saving}
              />
              <input
                type="text"
                placeholder="Ονομα ειδους"
                value={addName}
                onChange={(e) => setAddName(e.target.value)}
                disabled={isReadOnly || saving}
              />
              <input
                type="number"
                step="0.1"
                placeholder="Τιμη"
                value={addPrice}
                onChange={(e) => setAddPrice(e.target.value)}
                disabled={isReadOnly || saving}
              />
              <select
                value={addCategory}
                onChange={(e) => setAddCategory(e.target.value)}
                disabled={isReadOnly || saving}
              >
                {categoryOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder='Μεταδεδομενα (JSON, προαιρετικο)'
                value={addMetadata}
                onChange={(e) => setAddMetadata(e.target.value)}
                disabled={isReadOnly || saving}
              />
            </div>
            <button type="submit" className="primary-button" disabled={isReadOnly || saving}>
              Προσθηκη και Νεα Εκδοση
            </button>
          </form>

          <div className="menu-sections">
            {sections.length === 0 && <p>Δεν βρεθηκαν ειδη.</p>}
            {sections.map((section) => (
              <MenuSection
                key={section}
                sectionName={section}
                items={menuDraft?.[section] || []}
                onEdit={handleEditItem}
                onToggleHidden={handleSoftDelete}
                onPermanentDelete={handlePermanentDelete}
                isReadOnly={isReadOnly || saving}
              />
            ))}
          </div>
        </div>
      </div>

      {modalOpen && (
        <ItemEditorModal
          item={editingItem}
          section={editingSection}
          onClose={() => setModalOpen(false)}
          onSave={handleSaveItem}
          saving={saving}
          readOnly={isReadOnly}
          categoryOptions={categoryOptions}
        />
      )}
    </div>
  );
}

function VersionList({ versions, selectedVersionId, onSelectVersion }) {
  return (
    <div className="menu-editor-sidebar">
      <h2>Εκδοσεις</h2>
      {versions.length === 0 ? (
        <p>Δεν υπαρχουν εκδοσεις.</p>
      ) : (
        <ul>
          {versions.map((version) => (
            <li key={version.id}>
              <button
                className={version.id === selectedVersionId ? 'active' : ''}
                onClick={() => onSelectVersion(version.id)}
              >
                <span>Εκδοση #{version.id}</span>
                <small>{formatDateTime(version.created_at)}</small>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MenuSection({ sectionName, items, onEdit, onToggleHidden, onPermanentDelete, isReadOnly }) {
  return (
    <div className="menu-section">
      <h3>{sectionName}</h3>
      {items.length === 0 ? (
        <p className="menu-section-empty">Δεν υπαρχουν ειδη.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Ονομα</th>
              <th>Τιμη</th>
              <th>Σταθμος</th>
              <th>Ενεργειες</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className={item.hidden ? 'menu-item-hidden' : ''}>
                <td>{item.name}</td>
                <td>€{Number(item.price || 0).toFixed(2)}</td>
                <td>{item.category}</td>
                <td>
                  <button
                    className="ghost-button"
                    onClick={() => onEdit(item, sectionName)}
                    disabled={isReadOnly}
                  >
                    Επεξεργασια
                  </button>
                  <button
                    className="danger-button"
                    onClick={() => onToggleHidden(item.id)}
                    disabled={isReadOnly}
                  >
                    {item.hidden ? 'Εμφανιση' : 'Αποκρυψη'}
                  </button>
                  {item.hidden && (
                    <button
                      className="danger-button delete-button"
                      onClick={() => onPermanentDelete(item.id)}
                      disabled={isReadOnly}
                    >
                      Διαγραφη για παντα
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ItemEditorModal({ item, section, onSave, onClose, saving, readOnly, categoryOptions }) {
  const [name, setName] = useState(item?.name || '');
  const [price, setPrice] = useState(String(item?.price ?? ''));
  const [category, setCategory] = useState(item?.category || 'kitchen');
  const [sectionName, setSectionName] = useState(section || '');
  const [metadata, setMetadata] = useState(item?.metadata ? JSON.stringify(item.metadata) : '');
  const [error, setError] = useState(null);

  const handleSave = async () => {
    let parsedMetadata = {};
    if (metadata.trim()) {
      try {
        parsedMetadata = JSON.parse(metadata);
      } catch {
        setError('Μη εγκυρο JSON στα μεταδεδομενα');
        return;
      }
    }

    const updatedItem = {
      ...item,
      name: name.trim(),
      price: normalizePrice(price),
      category,
      metadata: parsedMetadata,
      extra_data: parsedMetadata,
      station: category,
      hidden: Boolean(item?.hidden),
    };

    await onSave(updatedItem, sectionName.trim());
  };

  return (
    <div className="menu-modal-backdrop">
      <div className="menu-modal">
        <h2>Επεξεργασια Ειδους</h2>
        {error && <div className="menu-editor-error">❌ {error}</div>}
        <label>
          Ονομα
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={readOnly || saving}
          />
        </label>
        <label>
          Τιμη
          <input
            type="number"
            step="0.1"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            disabled={readOnly || saving}
          />
        </label>
        <label>
          Σταθμος
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            disabled={readOnly || saving}
          >
            {categoryOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Τμημα
          <input
            value={sectionName}
            onChange={(e) => setSectionName(e.target.value)}
            disabled={readOnly || saving}
          />
        </label>
        <label>
          Μεταδεδομενα (JSON)
          <textarea
            value={metadata}
            onChange={(e) => setMetadata(e.target.value)}
            disabled={readOnly || saving}
          />
        </label>
        <div className="menu-modal-actions">
          <button className="ghost-button" onClick={onClose} disabled={saving}>
            Ακυρωση
          </button>
          <button className="primary-button" onClick={handleSave} disabled={readOnly || saving}>
            Αποθηκευση
          </button>
        </div>
      </div>
    </div>
  );
}

export default MenuEditor;
