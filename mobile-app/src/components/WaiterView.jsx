import { useState, useEffect, useRef } from 'react';
import { postOrder, putOrder, getOrders, getTableMeta, createWS } from '../services/api';

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
    if (price === null || price === undefined) return '—';
    return `€${Number(price).toFixed(2)}`;
  };

  // Get current order items for selected table
  const currentOrderItems = selectedTable && tables[selectedTable] ? tables[selectedTable] : [];

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
    <div className="waiter-view">
      {!selectedTable ? (
        <>
          <h1 style={{ textAlign: 'center' }}>ΤΡΑΠΕΖΙΑ</h1>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center' }}>
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
                <div
                  key={num}
                  style={{
                    width: 80,
                    height: 80,
                    margin: 8,
                    fontSize: 20,
                    backgroundColor: color,
                    color: '#fff',
                    borderRadius: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                  }}
                  onClick={() => handleSelectTable(tableNum)}
                >
                  {num}
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div style={{ padding: 16 }}>
          <h2>ΤΡΑΠΕΖΙ {selectedTable}</h2>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 8 }}>
            <label>
              Αριθμός ατόμων:
              <input
                type="number"
                min="1"
                value={people}
                onChange={(e) => setPeople(e.target.value)}
                style={{ width: 80, marginLeft: 8 }}
              />
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input type="checkbox" checked={bread} onChange={(e) => setBread(e.target.checked)} />
              Θέλουν ψωμί
            </label>
          </div>

          {/* Display current order items */}
          <div style={{ marginBottom: 12 }}>
            {currentOrderItems.length === 0 ? (
              <div style={{ color: '#666' }}>Δεν υπάρχουν παραγγελίες</div>
            ) : (
              currentOrderItems.map((item) => {
                const qty = item && item.qty ? item.qty : 1;
                const displayName = item && item.name ? item.name : item && item.text ? item.text : '(άγνωστο)';
                const isStruck = item && (item.status === 'done' || item.status === 'cancelled');
                return (
                  <div
                    key={item.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: 6,
                      borderBottom: '1px dashed #eee',
                    }}
                  >
                    <div style={{ textDecoration: isStruck ? 'line-through' : 'none', fontSize: 18 }}>
                      {qty > 1 ? `${qty}× ` : ''}
                      {displayName}
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: '#666',
                        minWidth: 120,
                        textAlign: 'right',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'flex-end',
                      }}
                    >
                      <div>{item.status === 'pending' ? 'εκκρεμεί' : item.status === 'done' ? 'έτοιμο' : 'ακυρωμένο'}</div>
                      <div style={{ marginTop: 4 }}>
                        {item && item.unit_price !== null && item.unit_price !== undefined && item.line_total !== null && item.line_total !== undefined ? (
                          <div style={{ fontSize: 12 }}>
                            {qty}× {formatPrice(item.unit_price)} = {formatPrice(item.line_total)}
                          </div>
                        ) : (
                          <div style={{ fontSize: 12, color: '#999' }}>—</div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <textarea
            value={orderText}
            onChange={(e) => setOrderText(e.target.value)}
            rows={10}
            style={{ width: '100%', fontSize: 18, padding: 12 }}
            placeholder="Γράψτε την παραγγελία — κάθε πιάτο σε νέα γραμμή"
          />

          <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
            <button
              onClick={handleSubmitOrder}
              disabled={loading}
              style={{
                padding: '12px 24px',
                fontSize: 18,
                backgroundColor: '#007bff',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'ΑΠΟΣΤΟΛΗ...' : tables[selectedTable] && tables[selectedTable].length > 0 ? 'ΕΠΕΞΕΡΓΑΣΙΑ' : 'ΑΠΟΣΤΟΛΗ'}
            </button>

            {tables[selectedTable] && tables[selectedTable].length > 0 && tables[selectedTable].every((it) => it && (it.status === 'done' || it.status === 'cancelled')) && (
              <button
                onClick={handleFinalizeTable}
                style={{
                  padding: '12px 24px',
                  fontSize: 18,
                  backgroundColor: '#4a90e2',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 8,
                  cursor: 'pointer',
                }}
              >
                ΟΛΟΚΛΗΡΩΣΗ ΤΡΑΠΕΖΙΟΥ
              </button>
            )}

            <button
              onClick={() => {
                setSelectedTable(null);
                setOrderText('');
                setPeople('');
                setBread(false);
              }}
              style={{ padding: '12px 24px', fontSize: 18 }}
            >
              ΑΚΥΡΟ
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default WaiterView;

