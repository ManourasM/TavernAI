import { useState, useEffect, useRef } from 'react';
import { postOrder, putOrder, getOrders, getTableMeta, createWS } from '../services/api';
import './WaiterView.css';

function WaiterView() {
  const [tables, setTables] = useState({});
  const [selectedTable, setSelectedTable] = useState(null);
  const [orderText, setOrderText] = useState('');
  const [people, setPeople] = useState('');
  const [bread, setBread] = useState(false);
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  // Helper function to format price
  const formatPrice = (price) => {
    if (price === null || price === undefined || Number.isNaN(price)) return '—';
    try {
      return `${Number(price).toFixed(2)} €`;
    } catch {
      return '—';
    }
  };

  // Get current order items for selected table
  const currentOrderItems = selectedTable && tables[selectedTable] ? tables[selectedTable] : [];

  // Compute subtotal of known line totals for non-cancelled items
  const subtotalKnown = currentOrderItems.reduce((acc, it) => {
    if (!it) return acc;
    if (it.status === 'cancelled') return acc;
    if (typeof it.line_total === 'number') return acc + it.line_total;
    return acc;
  }, 0);
  const hasUnknownPrices = currentOrderItems.some(
    (it) => it && it.status !== 'cancelled' && (it.line_total === null || it.line_total === undefined)
  );

  // Load initial orders
  useEffect(() => {
    loadOrders();
  }, []);

  // Setup WebSocket connection
  useEffect(() => {
    wsRef.current = createWS('waiter', (msg) => {
      handleWebSocketMessage(msg);
    }, () => {
      console.log('[WaiterView] WebSocket connected');
      setConnected(true);
    });

    return () => {
      try {
        if (wsRef.current) wsRef.current.close();
      } catch (e) {
        console.error('Error closing WebSocket:', e);
      }
    };
  }, []);

  const loadOrders = async () => {
    try {
      const orders = await getOrders(true); // Include history
      setTables(orders);
    } catch (error) {
      console.error('Failed to load orders:', error);
    }
  };

  const handleWebSocketMessage = (data) => {
    console.log('[WaiterView] WebSocket message:', data);

    if (data.action === 'init') {
      // Initial data from server
      if (data.orders) {
        setTables(data.orders);
      }
    } else if (data.action === 'new' && data.item) {
      // New item added
      const tableNum = String(data.item.table);
      setTables((prev) => ({
        ...prev,
        [tableNum]: [...(prev[tableNum] || []), data.item],
      }));
    } else if (data.action === 'update' && data.item) {
      // Item updated
      const tableNum = String(data.item.table);
      setTables((prev) => ({
        ...prev,
        [tableNum]: (prev[tableNum] || []).map((item) =>
          item.id === data.item.id ? data.item : item
        ),
      }));
    } else if (data.action === 'delete' && data.item_id) {
      // Item deleted
      const tableNum = String(data.table);
      setTables((prev) => ({
        ...prev,
        [tableNum]: (prev[tableNum] || []).filter((item) => item.id !== data.item_id),
      }));
    } else if (data.action === 'table_finalized' && data.table !== undefined) {
      // Table finalized
      const tableNum = String(data.table);
      setTables((prev) => {
        const newTables = { ...prev };
        delete newTables[tableNum];
        return newTables;
      });

      // Clear selection if this table was selected
      if (selectedTable === tableNum) {
        setSelectedTable(null);
        setOrderText('');
        setPeople('');
        setBread(false);
      }
    } else if (data.action === 'notify') {
      // Notification from kitchen/grill/drinks
      console.log('[WaiterView] Notification:', data.message);
      // You can show a toast notification here
    }
  };

  const handleSelectTable = async (tableNum) => {
    setSelectedTable(tableNum);

    // Load existing order for this table
    const tableOrders = tables[tableNum] || [];
    const pendingItems = tableOrders.filter((item) => item.status === 'pending');
    const orderLines = pendingItems.map((item) => item.text).join('\n');
    setOrderText(orderLines);

    // Load table metadata
    try {
      const meta = await getTableMeta(parseInt(tableNum));
      setPeople(meta.people || '');
      setBread(meta.bread || false);
    } catch (error) {
      console.error('Failed to load table meta:', error);
    }
  };

  const handleSubmitOrder = async () => {
    console.log('[handleSubmitOrder] called', { selectedTable, orderText, people, bread });
    if (!selectedTable) {
      console.warn('[handleSubmitOrder] no table selected');
      return;
    }
    if (!orderText || !orderText.trim()) {
      console.warn('[handleSubmitOrder] no order text entered');
      alert('Παρακαλώ εισάγετε παραγγελία');
      return;
    }

    const payloadTable = parseInt(selectedTable);
    const payloadText = orderText;
    const payloadPeople = people ? parseInt(people, 10) : null;
    const payloadBread = !!bread;

    setLoading(true);

    try {
      console.log('[handleSubmitOrder] sending order...', { payloadTable, payloadText, payloadPeople, payloadBread });

      // Check if table already has orders
      const hasExistingOrders = tables[selectedTable] && tables[selectedTable].length > 0;

      if (hasExistingOrders) {
        console.log('[handleSubmitOrder] calling putOrder');
        await putOrder(payloadTable, payloadText, payloadPeople, payloadBread);
      } else {
        console.log('[handleSubmitOrder] calling postOrder');
        await postOrder(payloadTable, payloadText, payloadPeople, payloadBread);
      }

      console.log('[handleSubmitOrder] success, refreshing...');
      await loadOrders();

      // Clear form
      setSelectedTable(null);
      setOrderText('');
      setPeople('');
      setBread(false);
    } catch (error) {
      console.error('[handleSubmitOrder] failed', error);
      alert('Σφάλμα κατά την αποστολή της παραγγελίας: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFinalizeTable = () => {
    if (!selectedTable) return;

    try {
      if (wsRef.current && wsRef.current.send) {
        wsRef.current.send({ action: 'finalize_table', table: parseInt(selectedTable) });
      } else {
        console.warn('No websocket available to finalize table. Try reloading or check backend.');
      }
    } catch (e) {
      console.error('finalizeTable error', e);
    }
  };

  return (
    <div className="waiter-container">
      {/* Header */}
      <div className="waiter-header">
        <div className="waiter-header-content">
          <h1 className="waiter-title">ΣΕΡΒΙΤΟΡΟΣ</h1>
          <div className="connection-status">
            <div className={`status-dot ${connected ? 'status-connected' : 'status-disconnected'}`}></div>
            {connected ? 'Συνδεδεμένο' : 'Αποσυνδεδεμένο'}
          </div>
        </div>
      </div>

      {!selectedTable ? (
        <>
          <h1 style={{ textAlign: 'center', color: '#fff', fontSize: 36, margin: '32px 0', textShadow: '0 2px 4px rgba(0,0,0,0.2)' }}>ΤΡΑΠΕΖΙΑ</h1>
          <div className="tables-grid">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17].map((num) => {
              const tableNum = String(num);
              const tableOrders = tables[tableNum] || [];
              const hasPending = tableOrders.some((it) => it && it.status === 'pending');
              const hasAny = tableOrders.length > 0;
              const allDone = hasAny && tableOrders.every((it) => it && (it.status === 'done' || it.status === 'cancelled'));

              let color = '#5cb85c';
              if (allDone) color = '#4a90e2';
              else if (hasPending) color = '#d9534f';

              return (
                <button
                  key={num}
                  className="table-button"
                  style={{ backgroundColor: color }}
                  onClick={() => handleSelectTable(tableNum)}
                >
                  {num}
                </button>
              );
            })}
          </div>
        </>
      ) : (
        <div className="order-form">
          <div className="form-header">
            <div className="table-badge">{selectedTable}</div>
            ΤΡΑΠΕΖΙ {selectedTable}
          </div>

          <div className="meta-inputs">
            <div className="input-group">
              <label>
                👥 Αριθμός ατόμων:
                <input
                  type="number"
                  min="1"
                  value={people}
                  onChange={(e) => setPeople(e.target.value)}
                />
              </label>
            </div>

            <div className="input-group">
              <label>
                <input type="checkbox" checked={bread} onChange={(e) => setBread(e.target.checked)} />
                🍞 Θέλουν ψωμί
              </label>
            </div>
          </div>

          {/* Display current order items */}
          {currentOrderItems.length > 0 && (
            <div className="order-items-list">
              {currentOrderItems.map((item) => {
                const qty = item && item.qty ? item.qty : 1;
                const displayName = item && item.name ? item.name : item && item.text ? item.text : '(άγνωστο)';
                const isStruck = item && (item.status === 'done' || item.status === 'cancelled');
                const statusClass = item.status === 'pending' ? 'status-pending' : item.status === 'done' ? 'status-done' : 'status-cancelled';

                return (
                  <div key={item.id} className="order-item">
                    <div className={`item-name ${isStruck ? 'struck' : ''}`}>
                      {qty > 1 ? `${qty}× ` : ''}
                      {displayName}
                    </div>
                    <div className="item-details">
                      <div className={`item-status ${statusClass}`}>
                        {item.status === 'pending' ? '⏳ εκκρεμεί' : item.status === 'done' ? '✓ έτοιμο' : '✗ ακυρωμένο'}
                      </div>
                      {item && item.unit_price !== null && item.unit_price !== undefined && item.line_total !== null && item.line_total !== undefined ? (
                        <div className="item-price">
                          {qty}× {formatPrice(item.unit_price)} = {formatPrice(item.line_total)}
                        </div>
                      ) : (
                        <div className="item-price">—</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <textarea
            className="order-textarea"
            value={orderText}
            onChange={(e) => setOrderText(e.target.value)}
            rows={10}
            placeholder="Γράψτε την παραγγελία — κάθε πιάτο σε νέα γραμμή"
          />

          <div className="action-buttons">
            <button
              className="btn btn-primary"
              onClick={handleSubmitOrder}
              disabled={loading}
            >
              {loading ? '⏳ ΑΠΟΣΤΟΛΗ...' : tables[selectedTable] && tables[selectedTable].length > 0 ? '✏️ ΕΠΕΞΕΡΓΑΣΙΑ' : '📤 ΑΠΟΣΤΟΛΗ'}
            </button>

            {tables[selectedTable] && tables[selectedTable].length > 0 && tables[selectedTable].every((it) => it && (it.status === 'done' || it.status === 'cancelled')) && (
              <>
                <div className="total-badge">
                  💰 Σύνολο: {formatPrice(subtotalKnown)}
                  {hasUnknownPrices && (
                    <span className="total-note">(κάποια είδη χωρίς τιμή)</span>
                  )}
                </div>

                <button
                  className="btn btn-success"
                  onClick={handleFinalizeTable}
                >
                  ✓ ΟΛΟΚΛΗΡΩΣΗ ΤΡΑΠΕΖΙΟΥ
                </button>
              </>
            )}

            <button
              className="btn btn-secondary"
              onClick={() => {
                setSelectedTable(null);
                setOrderText('');
                setPeople('');
                setBread(false);
              }}
            >
              ← ΑΚΥΡΟ
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default WaiterView;

