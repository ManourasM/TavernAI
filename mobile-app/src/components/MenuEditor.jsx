import { useState } from 'react';
import useMenuStore from '../store/menuStore';
import './MenuEditor.css';

function MenuEditor({ initialMenu, onSave, onBack, loading }) {
  const [menu, setMenu] = useState(initialMenu || []);
  const [editingItem, setEditingItem] = useState(null);
  const endpoints = useMenuStore((state) => state.endpoints);

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
    const newItem = {
      id: Date.now(),
      name: 'New Item',
      price: 0,
      category: 'kitchen',
      unit: 'portion',
      hidden: false,
    };
    setMenu([...menu, newItem]);
    setEditingItem(newItem);
  };

  const handleSaveMenu = () => {
    onSave(menu);
  };

  return (
    <div className="menu-editor">
      <div className="editor-header">
        <button onClick={onBack} className="back-button">← Back</button>
        <h2>Edit Menu ({menu.length} items)</h2>
        <button onClick={handleAddItem} className="add-button">+ Add</button>
      </div>

      <div className="menu-list">
        {menu.map((item) => (
          <div key={item.id} className={`menu-item-card ${item.hidden ? 'hidden-item' : ''}`}>
            {editingItem?.id === item.id ? (
              <div className="edit-form">
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
                  {endpoints.map((ep) => (
                    <option key={ep.id} value={ep.id}>{ep.name}</option>
                  ))}
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
                <div className="item-info">
                  <h3>{item.name}</h3>
                  <p className="item-details">
                    {item.price}€ • {item.category} • {item.unit}
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
        ))}
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

