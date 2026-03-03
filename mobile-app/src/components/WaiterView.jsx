import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { postOrder, putOrder, getOrders, getTableMeta, createWS, captureNlpSample, previewOrder } from '../services/api';
import useMenuStore from '../store/menuStore';
import CorrectionModal from './CorrectionModal';
import { useSounds } from '../utils/sounds';
import './WaiterView.css';

// Global guard to prevent duplicate receipt tabs across all instances
const openedReceipts = new Map(); // Map receipt ID to timestamp
const RECEIPT_GUARD_TIMEOUT = 5000; // 5 seconds

// Clean up old entries periodically
setInterval(() => {
  const now = Date.now();
  for (const [key, timestamp] of openedReceipts.entries()) {
    if (now - timestamp > RECEIPT_GUARD_TIMEOUT) {
      openedReceipts.delete(key);
    }
  }
}, 1000);

// Helper to calculate table color based on items
const getTableColor = (tableOrders) => {
  if (!tableOrders || tableOrders.length === 0) return '#5cb85c'; // Green: empty
  const hasPending = tableOrders.some((it) => it && it.status === 'pending');
  const allDone = tableOrders.every((it) => it && (it.status === 'done' || it.status === 'cancelled'));
  
  if (allDone) return '#4a90e2'; // Blue: all done
  if (hasPending) return '#d9534f'; // Red: has pending
  return '#5cb85c'; // Green: default
};

function WaiterView() {
  const navigate = useNavigate();
  const [tables, setTables] = useState({});
  const [selectedTable, setSelectedTable] = useState(null);
  const [orderText, setOrderText] = useState('');
  const [people, setPeople] = useState('');
  const [bread, setBread] = useState(false);
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [hiddenItemsPopup, setHiddenItemsPopup] = useState(null);
  const [unclassifiedItemsPopup, setUnclassifiedItemsPopup] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewItems, setPreviewItems] = useState([]);
  const [previewHidden, setPreviewHidden] = useState([]);
  const [previewUnclassified, setPreviewUnclassified] = useState([]);
  const [selectedItemForCorrection, setSelectedItemForCorrection] = useState(null);
  const [correctionLoading, setCorrectionLoading] = useState(false);
  const [notifications, setNotifications] = useState([]); // {id, text}
  const wsRef = useRef(null);
  const updateQueueRef = useRef([]); // Queue rapid updates
  const processingQueueRef = useRef(false);
  const recentNotifsRef = useRef(new Map()); // Track recent notifications to prevent duplicates
  const notifTimersRef = useRef({}); // Track notification timers
  
  const { playDoneSound } = useSounds();
  const menu = useMenuStore((state) => state.menu);

  // Notification helpers (similar to legacy waiter UI)
  const pushNotification = useCallback((text, opts = {}) => {
    if (!text) return;
    const serverId = opts.id || null;
    const ttl = opts.ttl ?? 15000; // 15 seconds default
    
    const now = Date.now();
    
    // Prevent duplicate notifications
    if (serverId) {
      if (recentNotifsRef.current.has(serverId)) return;
      recentNotifsRef.current.set(serverId, now + ttl);
    } else {
      const key = String(text).trim();
      const existingExpiry = recentNotifsRef.current.get(key);
      if (existingExpiry && existingExpiry > now) {
        return;
      }
      recentNotifsRef.current.set(key, now + Math.max(ttl, 6000));
    }
    
    const id = `notif-${Date.now()}-${Math.random()}`;
    const message = String(text);
    setNotifications((prev) => {
      const next = [{ id, text: message }, ...prev].slice(0, 6); // Max 6 notifications
      return next;
    });
    
    // Auto-dismiss after TTL
    const timer = setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      const now2 = Date.now();
      for (const [k, expiry] of recentNotifsRef.current.entries()) {
        if (expiry <= now2) recentNotifsRef.current.delete(k);
      }
      delete notifTimersRef.current[id];
    }, ttl);
    notifTimersRef.current[id] = timer;
  }, []);

  const dismissNotification = useCallback((id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    if (notifTimersRef.current[id]) {
      clearTimeout(notifTimersRef.current[id]);
      delete notifTimersRef.current[id];
    }
  }, []);

  // Helper function to format price
  const formatPrice = (price) => {
    if (price === null || price === undefined || Number.isNaN(price)) return '—';
    try {
      return `${Number(price).toFixed(2)} €`;
    } catch {
      return '—';
    }
  };

  const findMenuItemById = (menuData, itemId) => {
    if (!menuData || !itemId) return null;
    const idStr = String(itemId);
    for (const section of Object.values(menuData)) {
      if (!Array.isArray(section)) continue;
      const found = section.find((entry) => entry && String(entry.id) === idStr);
      if (found) return found;
    }
    return null;
  };

  const normalizeRuleKey = (text) => {
    if (!text) return '';
    const strippedParens = text.replace(/\s*\([^)]*\)\s*/g, ' ').replace(/\s+/g, ' ').trim();
    const strippedQty = strippedParens.replace(/^\d+(?:\.\d+)?(λτ|λ|lt|l|kg|κιλα|κιλο|κ|ml)?\s+/i, '');
    return strippedQty
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^\p{L}\p{N}\s]/gu, '')
      .replace(/\s+/g, ' ')
      .trim();
  };

  const applyLocalCorrection = (orderItemId, correctedItemId) => {
    if (!selectedTable) return;
    const correctedItem = findMenuItemById(menu, correctedItemId);
    if (!correctedItem) return;

    setTables((prev) => {
      const tableItems = prev[selectedTable] || [];
      const updatedItems = tableItems.map((it) => {
        if (!it || it.id !== orderItemId) return it;
        const qty = typeof it.qty === 'number' ? it.qty : 1;
        const unitPrice = correctedItem.price ?? it.unit_price;
        const lineTotal = unitPrice !== null && unitPrice !== undefined ? qty * Number(unitPrice) : it.line_total;
        return {
          ...it,
          menu_id: correctedItem.id,
          menu_name: correctedItem.name,
          name: correctedItem.name,
          unit_price: unitPrice,
          line_total: lineTotal
        };
      });
      return { ...prev, [selectedTable]: updatedItems };
    });
  };

  const recomputePreviewUnclassified = (items) => {
    const missing = items
      .filter((it) => !it.menu_name)
      .map((it) => it.text);
    setPreviewUnclassified(missing);
  };

  const applyPreviewCorrection = (previewId, correctedItemId) => {
    const correctedItem = findMenuItemById(menu, correctedItemId);
    if (!correctedItem) return;

    setPreviewItems((prev) => {
      const target = prev.find((it) => it && it.preview_id === previewId);
      const targetKey = target ? normalizeRuleKey(target.text) : null;
      const updated = prev.map((it) => {
        if (!it) return it;
        if (targetKey && normalizeRuleKey(it.text) !== targetKey) return it;
        return {
          ...it,
          menu_id: correctedItem.id,
          menu_name: correctedItem.name,
          price: correctedItem.price,
          category: correctedItem.category || it.category
        };
      });
      recomputePreviewUnclassified(updated);
      return updated;
    });
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

  // Memoize table colors and data for efficient rendering
  const tableDataMemo = useMemo(() => {
    const tableNums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17];
    return tableNums.map((num) => {
      const tableNum = String(num);
      const tableOrders = tables[tableNum] || [];
      return {
        num,
        tableNum,
        color: getTableColor(tableOrders),
        itemCount: tableOrders.length
      };
    });
  }, [tables]);

  // Load initial orders
  useEffect(() => {
    loadOrders();
  }, []);

  // Continuous fallback polling to keep table colors updated in real-time
  // Polls every 2.5 seconds to sync table status (pending/done indicators)
  useEffect(() => {
    const refreshInterval = setInterval(async () => {
      console.log('[WaiterView] Continuous poll: refreshing table data');
      try {
        const orders = await getOrders(true);
        setTables(orders);
      } catch (error) {
        console.warn('[WaiterView] Continuous poll failed:', error);
      }
    }, 2500); // Poll every 2.5 seconds for smooth table color updates
    
    return () => clearInterval(refreshInterval);
  }, []); // Empty dependency - runs continuously


  // Setup WebSocket connection
  useEffect(() => {
    console.log('[WaiterView] Setting up WebSocket connection');
    
    // Close any existing connection first
    if (wsRef.current) {
      console.log('[WaiterView] Closing existing WebSocket before creating new one');
      try {
        wsRef.current.close();
      } catch (e) {
        console.error('[WaiterView] Error closing old WebSocket:', e);
      }
    }
    
    wsRef.current = createWS(
      'waiter',
      (msg) => {
        handleWebSocketMessage(msg);
      },
      () => {
        console.log('[WaiterView] WebSocket connected');
        setConnected(true);
      },
      {
        onSync: async () => {
          await loadOrders();
        }
      }
    );

    return () => {
      console.log('[WaiterView] Cleaning up WebSocket');
      try {
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
      } catch (e) {
        console.error('[WaiterView] Error closing WebSocket:', e);
      }
    };
  }, []); // Empty dependency array - only run once on mount

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
      // New item added - process immediately (not frequent)
      const tableNum = String(data.item.table);
      console.log('[WaiterView] New item for table', tableNum, ':', data.item);
      setTables((prev) => ({
        ...prev,
        [tableNum]: [...(prev[tableNum] || []), data.item],
      }));
    } else if (data.action === 'update' && data.item) {
      // Item updated - queue for batch processing
      const tableNum = String(data.item.table);
      console.log('[WaiterView] Update for table', tableNum, 'item', data.item.id, 'status:', data.item.status);
      updateQueueRef.current.push(data.item);
      
      // Process queue if not already processing
      if (!processingQueueRef.current) {
        processingQueueRef.current = true;
        // Use small timeout to batch rapid updates
        setTimeout(() => {
          const toProcess = updateQueueRef.current.splice(0);
          processingQueueRef.current = false;
          
          console.log('[WaiterView] Processing batch update with', toProcess.length, 'items');
          
          if (toProcess.length === 0) return;
          
          setTables((prev) => {
            let updated = { ...prev };
            for (const item of toProcess) {
              const tableNum = String(item.table);
              const tableItems = updated[tableNum] || [];
              updated[tableNum] = tableItems.map((it) =>
                it.id === item.id ? item : it
              );
            }
            return updated;
          });
        }, 50); // 50ms batch window
      }
    } else if (data.action === 'delete' && data.item_id) {
      // Item deleted
      const tableNum = String(data.table);
      setTables((prev) => ({
        ...prev,
        [tableNum]: (prev[tableNum] || []).filter((item) => item.id !== data.item_id),
      }));
    } else if (data.action === 'table_finalized' && data.table !== undefined) {
      // Table finalized successfully (shared cleanup event for all clients)
      const tableNum = String(data.table);
      console.log('[WaiterView] Table finalized successfully:', tableNum);
      
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

      // Return to the tables overview after finalizing
      setSelectedTable(null);
      setOrderText('');
      setPeople('');
      setBread(false);
    } else if (data.action === 'receipt_ready' && data.receipt_id) {
      // Waiter-only event used to open/print receipt
      const receiptId = data.receipt_id;
      const receiptKey = `receipt-${receiptId}`;
      const now = Date.now();
      const lastOpened = openedReceipts.get(receiptKey);

      if (!lastOpened || (now - lastOpened) > RECEIPT_GUARD_TIMEOUT) {
        console.log('[WaiterView] Opening receipt tab for:', receiptId);
        openedReceipts.set(receiptKey, now);
        window.open(`/receipt/${receiptId}`, '_blank');
      } else {
        console.log('[WaiterView] Receipt already opened (blocked duplicate):', receiptId, 'ms ago:', now - lastOpened);
      }
    } else if (data.action === 'finalized_ok' && data.table !== undefined) {
      // Finalization confirmed
      console.log('[WaiterView] Finalization confirmed for table:', data.table);
    } else if (data.action === 'finalize_failed' && data.table !== undefined) {
      // Finalization failed
      console.error('[WaiterView] Finalization failed:', data);
      const reason = data.reason || 'unknown';
      const pending = data.pending || 0;
      
      if (reason === 'items_pending') {
        alert(`Δεν μπορεί να ολοκληρωθεί το τραπέζι ${data.table}.\nΥπάρχουν ακόμα ${pending} εκκρεμή είδη.`);
      } else if (reason === 'table_not_found') {
        alert(`Το τραπέζι ${data.table} δεν βρέθηκε.`);
      } else {
        alert(`Αποτυχία ολοκλήρωσης τραπεζιού ${data.table}: ${reason}`);
      }
    } else if (data.action === 'notify') {
      // Notification from kitchen/grill/drinks (item ready)
      if (data.message) {
        console.log('[WaiterView] Notification:', data.message);
        // Play done sound
        try { playDoneSound(); } catch (e) { console.warn('Failed to play done sound:', e); }
        // Show notification toast
        pushNotification(data.message, { id: data.id });
      }
    }
  };

  const handleSelectTable = useCallback(async (tableNum) => {
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
  }, [tables]);

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
      console.log('[handleSubmitOrder] previewing order...', { payloadTable, payloadText, payloadPeople, payloadBread });
      const preview = await previewOrder(payloadTable, payloadText, payloadPeople, payloadBread);
      const previewList = (preview.classified || []).map((item, idx) => ({
        ...item,
        preview_id: `${payloadTable}-${idx}`
      }));

      setPreviewItems(previewList);
      setPreviewHidden(preview.hidden_items || []);
      setPreviewUnclassified(preview.unclassified_items || []);
      setPreviewOpen(true);
    } catch (error) {
      console.error('[handleSubmitOrder] failed', error);
      console.error('[handleSubmitOrder] error details:', {
        status: error.status,
        data: error.data,
        message: error.message
      });
      
      // Check if error is about hidden items
      // FastAPI returns: { detail: { error: "...", hidden_items: [...] } }
      const hiddenItems = error.data?.detail?.hidden_items || error.data?.hidden_items;
      if (error.status === 400 && hiddenItems && hiddenItems.length > 0) {
        console.log('[handleSubmitOrder] Found hidden items:', hiddenItems);
        setHiddenItemsPopup({ items: hiddenItems, table: selectedTable });
      } 
      // Check if error is about unclassified items
      else {
        const unclassifiedItems = error.data?.detail?.unclassified_items || error.data?.unclassified_items;
        if (error.status === 400 && unclassifiedItems && unclassifiedItems.length > 0) {
          console.log('[handleSubmitOrder] Found unclassified items:', unclassifiedItems);
          setUnclassifiedItemsPopup({ items: unclassifiedItems, table: selectedTable });
        } else {
          alert('Σφάλμα κατά την αποστολή της παραγγελίας: ' + error.message);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFinalizeTable = () => {
    if (!selectedTable) return;

    // Show confirmation dialog in Greek
    const confirmed = window.confirm(
      `Είστε σίγουροι ότι θέλετε να ολοκληρώσετε το τραπέζι ${selectedTable};\n\nΘα εμφανιστεί η απόδειξη για εκτύπωση.`
    );

    if (!confirmed) {
      console.log('[handleFinalizeTable] Finalization cancelled by user');
      return;
    }

    console.log('[handleFinalizeTable] Attempting to finalize table:', selectedTable);
    console.log('[handleFinalizeTable] Current items:', tables[selectedTable]);

    try {
      if (wsRef.current && wsRef.current.send) {
        const message = { action: 'finalize_table', table: parseInt(selectedTable) };
        console.log('[handleFinalizeTable] Sending WebSocket message:', message);
        wsRef.current.send(message);
      } else {
        console.warn('[handleFinalizeTable] No websocket available to finalize table. Try reloading or check backend.');
        alert('Δεν υπάρχει σύνδεση WebSocket. Παρακαλώ ανανεώστε τη σελίδα.');
      }
    } catch (e) {
      console.error('[handleFinalizeTable] Error:', e);
      alert('Σφάλμα κατά την ολοκλήρωση του τραπεζιού: ' + e.message);
    }
  }

  const handleConfirmOrder = async () => {
    if (!selectedTable) return;
    if (previewHidden.length > 0) {
      alert('Υπάρχουν είδη που δεν είναι διαθέσιμα. Αφαιρέστε τα πριν την αποστολή.');
      return;
    }
    if (previewUnclassified.length > 0) {
      alert('Υπάρχουν είδη χωρίς αντιστοίχιση. Διορθώστε τα πριν την αποστολή.');
      return;
    }

    const payloadTable = parseInt(selectedTable);
    const payloadText = orderText;
    const payloadPeople = people ? parseInt(people, 10) : null;
    const payloadBread = !!bread;

    setLoading(true);
    try {
      const hasExistingOrders = tables[selectedTable] && tables[selectedTable].length > 0;
      if (hasExistingOrders) {
        await putOrder(payloadTable, payloadText, payloadPeople, payloadBread);
      } else {
        await postOrder(payloadTable, payloadText, payloadPeople, payloadBread);
      }

      await loadOrders();

      setPreviewOpen(false);
      setPreviewItems([]);
      setPreviewHidden([]);
      setPreviewUnclassified([]);

      setSelectedTable(null);
      setOrderText('');
      setPeople('');
      setBread(false);
    } catch (error) {
      console.error('[handleConfirmOrder] failed', error);
      const hiddenItems = error.data?.detail?.hidden_items || error.data?.hidden_items;
      if (error.status === 400 && hiddenItems && hiddenItems.length > 0) {
        setHiddenItemsPopup({ items: hiddenItems, table: selectedTable });
      } else {
        const unclassifiedItems = error.data?.detail?.unclassified_items || error.data?.unclassified_items;
        if (error.status === 400 && unclassifiedItems && unclassifiedItems.length > 0) {
          setUnclassifiedItemsPopup({ items: unclassifiedItems, table: selectedTable });
        } else {
          alert('Σφάλμα κατά την αποστολή της παραγγελίας: ' + error.message);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCancelPreview = () => {
    setPreviewOpen(false);
    setPreviewItems([]);
    setPreviewHidden([]);
    setPreviewUnclassified([]);
  };

  const handleOpenCorrection = (item, source = 'existing') => {
    if (source === 'preview') {
      setPreviewOpen(false);
    }
    setSelectedItemForCorrection({ ...item, source });
  };

  const handleCloseCorrection = () => {
    setSelectedItemForCorrection(null);
  };

  const handleSubmitCorrection = async (correctionData) => {
    setCorrectionLoading(true);
    try {
      await captureNlpSample(correctionData);

      console.log('[handleSubmitCorrection] Correction submitted successfully');
      if (selectedItemForCorrection) {
        if (selectedItemForCorrection.source === 'preview') {
          applyPreviewCorrection(selectedItemForCorrection.preview_id, correctionData.corrected_item_id);
        } else {
          applyLocalCorrection(selectedItemForCorrection.id, correctionData.corrected_item_id);
        }
      }
      alert('Η διόρθωση καταχωρήθηκε. Ευχαριστούμε!');
      setSelectedItemForCorrection(null);
    } catch (error) {
      console.error('[handleSubmitCorrection] Error:', error);
      alert('Σφάλμα κατά την υποβολή της διόρθωσης: ' + error.message);
    } finally {
      setCorrectionLoading(false);
    }
  }

  return (
    <div className="waiter-container">
      {/* Notifications - Item Ready Toasts */}
      <div style={{
        position: 'fixed',
        top: 100,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        maxWidth: '90vw',
        maxHeight: '60vh',
        overflowY: 'auto'
      }}>
        {notifications.map((notif) => (
          <div
            key={notif.id}
            onClick={() => dismissNotification(notif.id)}
            style={{
              background: 'linear-gradient(135deg, #4CAF50 0%, #45a049 100%)',
              color: '#fff',
              padding: '16px 24px',
              borderRadius: 12,
              boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
              fontSize: 18,
              fontWeight: 600,
              textAlign: 'center',
              cursor: 'pointer',
              lineHeight: '1.15',
              minWidth: 240,
              animation: 'slideInUp 0.3s ease-out',
              whiteSpace: 'normal',
              wordWrap: 'break-word'
            }}
          >
            {notif.text}
          </div>
        ))}
      </div>

      {/* Hidden Items Popup Modal */}
      {hiddenItemsPopup && hiddenItemsPopup.items && hiddenItemsPopup.items.length > 0 && (
        <div className="waiter-modal-overlay">
          <div className="waiter-modal">
            <div className="waiter-modal-header">
              <h2>⚠️ Ειδη χωρις διαθεσιμοτητα</h2>
            </div>
            <div className="waiter-modal-content">
              <p>Τραπέζι {hiddenItemsPopup.table}: Τα παρακατω ειδη δεν υπαρχουν πλεον στο μενου:</p>
              <ul className="hidden-items-list">
                {hiddenItemsPopup.items.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
              <p style={{ marginTop: '16px', color: '#666' }}>
                Παρακαλω αφαιρεστε τα ειδη και δοκιμαστε παλι.
              </p>
            </div>
            <div className="waiter-modal-actions">
              <button 
                className="primary-button"
                onClick={() => setHiddenItemsPopup(null)}
              >
                Κλεισιμο
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Unclassified Items Popup Modal */}
      {unclassifiedItemsPopup && unclassifiedItemsPopup.items && unclassifiedItemsPopup.items.length > 0 && (
        <div className="waiter-modal-overlay">
          <div className="waiter-modal">
            <div className="waiter-modal-header">
              <h2>❓ Αναγνωριση ειδων</h2>
            </div>
            <div className="waiter-modal-content">
              <p>Τραπέζι {unclassifiedItemsPopup.table}: Τα παρακατω ειδη δεν ηταν δυνατον να αναγνωριστουν στο μενου:</p>
              <ul className="hidden-items-list">
                {unclassifiedItemsPopup.items.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
              <p style={{ marginTop: '16px', color: '#666' }}>
                Παρακαλω διευκρινιστε τα ειδη ή προσθεστε τα στο μενου και δοκιμαστε παλι.
              </p>
            </div>
            <div className="waiter-modal-actions">
              <button 
                className="primary-button"
                onClick={() => setUnclassifiedItemsPopup(null)}
              >
                Κλεισιμο
              </button>
            </div>
          </div>
        </div>
      )}

      {previewOpen && (
        <div className="waiter-modal-overlay">
          <div className="waiter-modal preview-modal">
            <div className="waiter-modal-header">
              <h2>🧾 Επιβεβαίωση Παραγγελίας</h2>
            </div>
            <div className="waiter-modal-content">
              <p>Ελέγξτε την κατάταξη των ειδών πριν αποσταλεί η παραγγελία.</p>

              <div className="preview-list">
                {previewItems.map((item) => (
                  <div key={item.preview_id} className="preview-item">
                    <div className="preview-item-main">
                      <div className="preview-item-text">{item.text}</div>
                      <div className="preview-item-match">
                        {item.menu_name ? `→ ${item.menu_name}` : '— Δεν υπάρχει αντιστοίχιση'}
                      </div>
                    </div>
                    <button
                      className="correction-link"
                      onClick={() => handleOpenCorrection(item, 'preview')}
                    >
                      ❌ Λάθος;
                    </button>
                  </div>
                ))}
              </div>

              {previewHidden.length > 0 && (
                <div className="preview-warning">
                  ⚠️ Περιέχονται είδη που δεν είναι διαθέσιμα: {previewHidden.join(', ')}
                </div>
              )}

              {previewUnclassified.length > 0 && (
                <div className="preview-warning">
                  ❓ Υπάρχουν είδη χωρίς αντιστοίχιση: {previewUnclassified.join(', ')}
                </div>
              )}

              <div className="preview-actions">
                <button className="btn btn-secondary" onClick={handleCancelPreview}>
                  Ακύρωση
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleConfirmOrder}
                  disabled={previewHidden.length > 0 || previewUnclassified.length > 0 || loading}
                >
                  {loading ? '⏳ Αποστολή...' : '✅ Επιβεβαίωση & Αποστολή'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
            {tableDataMemo.map(({ num, tableNum, color }) => (
              <button
                key={num}
                className="table-button"
                style={{ backgroundColor: color }}
                onClick={() => handleSelectTable(tableNum)}
              >
                {num}
              </button>
            ))}
          </div>
        </>
      ) : (
        <div className="order-form">
          <div className="form-header">
            <div className="table-badge">{selectedTable}</div>
            ΤΡΑΠΕΖΙ {selectedTable}
          </div>

          {/* Menu Display - Hidden/Unavailable Items Only */}
          {menu && Object.values(menu).flat().some(item => item?.hidden === true) && (
            <div className="menu-reference">
              <h3>⚠️ Τα παρακατω ειδη δεν ειναι διαθεσιμα</h3>
              <div className="hidden-items-display">
                {Object.entries(menu)
                  .flatMap(([, items]) => Array.isArray(items) ? items.filter(item => item?.hidden === true) : [])
                  .map((item) => (
                    <div key={item.id} className="hidden-item-tag">
                      {item.name}
                    </div>
                  ))}
              </div>
            </div>
          )}

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
                      {item.status === 'pending' && (
                        <button
                          className="correction-link"
                          onClick={() => handleOpenCorrection(item, 'existing')}
                          title="Διόρθωση κατάταξης"
                        >
                          ❌ Λάθος;
                        </button>
                      )}
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
      
      {/* NLP Correction Modal */}
      {selectedItemForCorrection && (
        <CorrectionModal
          item={selectedItemForCorrection}
          menu={menu}
          onSubmit={handleSubmitCorrection}
          onCancel={handleCloseCorrection}
          loading={correctionLoading}
        />
      )}
    </div>
  );
}

export default WaiterView;

