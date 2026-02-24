import { useState, useEffect } from 'react';
import useMenuStore from '../store/menuStore';
import { getConfig } from '../services/api';
import './MenuEditor.css';

function MenuEditor({ initialMenu, onSave, onBack, loading }) {
  const [menu, setMenu] = useState(initialMenu || []);
  const [editingItem, setEditingItem] = useState(null);
  const [availableCategories, setAvailableCategories] = useState([]);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [categoriesError, setCategoriesError] = useState(null);
  const endpoints = useMenuStore((state) => state.endpoints);
  const workstations = useMenuStore((state) => state.workstations);
  const loadWorkstations = useMenuStore((state) => state.loadWorkstations);

  // Load available categories from API on mount and when refreshed
  useEffect(() => {
    loadAvailableCategories();
    loadWorkstations();
  }, []);

  const loadAvailableCategories = async () => {
    try {
      setCategoriesLoading(true);
      setCategoriesError(null);
      const config = await getConfig();
      const base = config.backend_base || `${location.protocol}//${location.host}`;
      const url = `${base}/api/menu`;
      
      const res = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (!res.ok) {
        throw new Error(`Failed to load menu: HTTP ${res.status}`);
      }
      
      const data = await res.json();
      const categories = data.available_categories || [];
      console.log('[MenuEditor] Loaded available categories:', categories);
      setAvailableCategories(categories);
    } catch (err) {
      console.error('[MenuEditor] Failed to load available categories:', err);
      setCategoriesError(err.message);
      // Fallback to endpoints if available
      if (endpoints && endpoints.length > 0) {
        setAvailableCategories(endpoints.map(ep => ep.id));
      }
    } finally {
      setCategoriesLoading(false);
    }
  };

  const handleEditItem = (item) => {
    setEditingItem({ ...item });
  };

  const handleSaveEdit = () => {
    setMenu(menu.map(item => 
      item.id === editingItem.id ? editingItem : item
    ));
    setEditingItem(null);
  };

  const handleDeleteItem = (itemId) => {
    if (confirm('Delete this item?')) {
      setMenu(menu.filter(item => item.id !== itemId));
    }
  };

  const handleAddItem = () => {
    // Use first available category or default to 'kitchen'
    const defaultCategory = availableCategories.length > 0 
      ? availableCategories[0]
      : (endpoints[0]?.id || '');
    
    const newItem = {
      id: Date.now(),
      name: 'New Item',
      price: 0,
      category: defaultCategory,
      unit: 'portion',
      hidden: false,
    };
    setMenu([...menu, newItem]);
    setEditingItem(newItem);
  };

  const handleSaveMenu = () => {
    onSave(menu);
  };

  // Check if item's category is in available categories
  const isLegacyCategory = (category) => {
    return !availableCategories.some(cat => cat === category);
  };

  // Get category display name
  const getCategoryName = (slug) => {
    const ws = workstations.find((item) => item.slug === slug);
    return ws ? ws.name : slug;
  };

  return (
    <div className="menu-editor">
      <div className="editor-header">
        <button onClick={onBack} className="back-button">← Back</button>
        <h2>Edit Menu ({menu.length} items)</h2>
        <button onClick={handleAddItem} className="add-button">+ Add</button>
      </div>

      {categoriesError && (
        <div className="categories-warning">
          ⚠ Could not load workstations: {categoriesError}
        </div>
      )}

      <div className="menu-list">
        {menu.map((item) => {
          const hasLegacyCategory = isLegacyCategory(item.category);
          
          return (
            <div key={item.id} className={`menu-item-card ${item.hidden ? 'hidden-item' : ''} ${hasLegacyCategory ? 'legacy-category-item' : ''}`}>
              {editingItem?.id === item.id ? (
                <div className="edit-form">
                  {hasLegacyCategory && (
                    <div className="legacy-warning">
                      ⚠ This item uses category "{item.category}" which is no longer available. Please select a new category or delete the item.
                    </div>
                  )}
                  <input
                    type="text"
                    value={editingItem.name}
                    onChange={(e) => setEditingItem({ ...editingItem, name: e.target.value })}
                    placeholder="Item name"
                  />
                  <input
                    type="number"
                    step="0.01"
                    value={editingItem.price}
                    onChange={(e) => setEditingItem({ ...editingItem, price: parseFloat(e.target.value) })}
                    placeholder="Price"
                  />
                  <select
                    value={editingItem.category}
                    onChange={(e) => setEditingItem({ ...editingItem, category: e.target.value })}
                  >
                    {/* Show legacy category if currently selected */}
                    {hasLegacyCategory && (
                      <option value={item.category} disabled={true}>
                        {item.category} (removed)
                      </option>
                    )}
                    {availableCategories.length > 0 ? (
                      availableCategories.map((slug) => (
                        <option key={slug} value={slug}>{getCategoryName(slug)}</option>
                      ))
                    ) : (
                      endpoints && endpoints.map((ep) => (
                        <option key={ep.id} value={ep.id}>{ep.name}</option>
                      ))
                    )}
                  </select>
                  <select
                    value={editingItem.unit}
                    onChange={(e) => setEditingItem({ ...editingItem, unit: e.target.value })}
                  >
                    <option value="portion">Portion</option>
                    <option value="kg">Kilogram</option>
                    <option value="liter">Liter</option>
                    <option value="ml">Milliliter</option>
                  </select>
                  <label className="hidden-toggle">
                    <input
                      type="checkbox"
                      checked={editingItem.hidden || false}
                      onChange={(e) => setEditingItem({ ...editingItem, hidden: e.target.checked })}
                    />
                    Hidden (not available)
                  </label>
                  <div className="edit-actions">
                    <button onClick={handleSaveEdit} className="save-btn">✓ Save</button>
                    <button onClick={() => setEditingItem(null)} className="cancel-btn">✗ Cancel</button>
                  </div>
                </div>
              ) : (
                <div className={`item-display ${item.hidden ? 'hidden-display' : ''}`}>
                  {hasLegacyCategory && (
                    <div className="legacy-category-indicator">⚠ Legacy category</div>
                  )}
                  <div className="item-info">
                    <h3>{item.name}</h3>
                    <p className="item-details">
                      {item.price}€ • {getCategoryName(item.category)} • {item.unit}
                      {item.hidden && <span className="hidden-badge">🚫 Hidden</span>}
                    </p>
                  </div>
                  <div className="item-actions">
                    <button onClick={() => handleEditItem(item)} className="edit-btn">✎</button>
                    <button onClick={() => handleDeleteItem(item.id)} className="delete-btn">🗑</button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="editor-footer">
        <button onClick={onBack} className="secondary-button">
          Back
        </button>
        <button 
          onClick={handleSaveMenu} 
          className="primary-button"
          disabled={loading}
        >
          {loading ? 'Saving...' : `Save Menu (${menu.length} items)`}
        </button>
      </div>
    </div>
  );
}

export default MenuEditor;

