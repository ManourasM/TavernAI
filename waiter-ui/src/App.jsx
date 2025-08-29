// waiter-ui/src/App.jsx
import React, { useEffect, useRef, useState } from "react";
import { createWS, getOrders, postOrder, putOrder, getTableMeta } from "./api";
import { useSounds } from "./utils/sounds";

// small util to generate a short id for notifications
function nid() { return Math.random().toString(36).slice(2, 9); }

function TableButton({ n, color, onClick }) {
  const style = {
    width: 80, height: 80, margin: 8, fontSize: 20,
    backgroundColor: color || "#5cb85c",
    color: "#fff", borderRadius: 8, display: "flex",
    alignItems: "center", justifyContent: "center", cursor: "pointer"
  };
  return <div style={style} onClick={() => onClick(n)}>{n}</div>;
}

/**
 * Waiter UI
 * ordersMap shape: { "3": { items: [ {id,...}, ... ], meta: {people, bread} }, ... }
 */
export default function App() {
  const [ordersMap, setOrdersMap] = useState({}); // normalized shape
  const [selectedTable, setSelectedTable] = useState(null);
  const [text, setText] = useState("");
  const [people, setPeople] = useState("");
  const [bread, setBread] = useState(false);

  // debug panel toggle
  const [debugEnabled, setDebugEnabled] = useState(false);

  // notifications: newest first
  const [notifications, setNotifications] = useState([]); // {id, text}
  const timersRef = useRef({}); // map id -> timeoutId
  const recentNotifs = useRef(new Map()); // dedupe map
  const wsRef = useRef(null);

  // sounds
  const { muted, toggleMute, ensureAudio, playDoneSound } = useSounds();
  useEffect(() => { ensureAudio(); }, [ensureAudio]);

  // helper: ensure table entry exists with normalized shape
  function ensureTableEntry(copy, tableNum) {
    const k = String(tableNum);
    if (!copy[k]) copy[k] = { items: [], meta: { people: null, bread: false } };
    if (!Array.isArray(copy[k].items)) copy[k].items = [];
    if (!copy[k].meta) copy[k].meta = { people: null, bread: false };
    return copy[k];
  }

  // add or replace an item safely
  function addOrReplaceItem(item) {
    if (!item || !("table" in item) || !item.id) return;
    setOrdersMap(prev => {
      const copy = { ...prev };
      const tableEntry = ensureTableEntry(copy, item.table);
      const idx = tableEntry.items.findIndex(i => i.id === item.id);
      if (idx >= 0) tableEntry.items[idx] = { ...tableEntry.items[idx], ...item };
      else tableEntry.items.push(item);
      // sort by created_at if present
      tableEntry.items.sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""));
      // attach meta if item contains it
      if (item.meta) tableEntry.meta = item.meta;
      return copy;
    });
  }

  // replace entire table items (used cautiously)
  function setTableItems(tableNum, items, meta) {
    setOrdersMap(prev => {
      const copy = { ...prev };
      const k = String(tableNum);
      copy[k] = { items: Array.isArray(items) ? items.slice() : [], meta: meta || (copy[k] && copy[k].meta) || { people: null, bread: false } };
      return copy;
    });
  }

  // mark or update an item (status change)
  function updateItem(item) {
    if (!item || !item.id) return;
    setOrdersMap(prev => {
      const copy = { ...prev };
      const k = String(item.table);
      if (!copy[k] || !Array.isArray(copy[k].items)) {
        copy[k] = { items: [], meta: item.meta || { people: null, bread: false } };
      }
      const idx = copy[k].items.findIndex(i => i.id === item.id);
      if (idx >= 0) copy[k].items[idx] = { ...copy[k].items[idx], ...item };
      else copy[k].items.push(item);
      return copy;
    });
  }

  // remove a table completely (finalize)
  function removeTable(tableNum) {
    setOrdersMap(prev => {
      const copy = { ...prev };
      delete copy[String(tableNum)];
      return copy;
    });
  }

  // mark single item cancelled/done in-place (keep in history)
  function markItemStatus(tableNum, itemId, status) {
    setOrdersMap(prev => {
      const copy = { ...prev };
      const k = String(tableNum);
      if (!copy[k] || !Array.isArray(copy[k].items)) return prev;
      copy[k].items = copy[k].items.map(it => it.id === itemId ? { ...it, status } : it);
      return copy;
    });
  }

  // ---------- Notifications helpers ----------
  function pushNotification(text, opts = {}) {
    if (!text) return;
    const serverId = opts.id || null;
    const ttl = opts.ttl ?? 15000; // ms

    const now = Date.now();

    if (serverId) {
      if (recentNotifs.current.has(serverId)) return;
      recentNotifs.current.set(serverId, now + ttl);
    } else {
      const key = String(text).trim();
      const existingExpiry = recentNotifs.current.get(key);
      if (existingExpiry && existingExpiry > now) {
        return;
      }
      recentNotifs.current.set(key, now + Math.max(ttl, 6000));
    }

    const id = nid();
    const message = String(text);
    setNotifications(prev => {
      const next = [{ id, text: message }, ...prev].slice(0, 6);
      return next;
    });

    // auto-dismiss
    const to = setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
      const now2 = Date.now();
      for (const [k, expiry] of recentNotifs.current.entries()) {
        if (expiry <= now2) recentNotifs.current.delete(k);
      }
      delete timersRef.current[id];
    }, ttl);
    timersRef.current[id] = to;
  }

  function dismissNotification(id) {
    setNotifications(prev => prev.filter(n => n.id !== id));
    if (timersRef.current[id]) {
      clearTimeout(timersRef.current[id]);
      delete timersRef.current[id];
    }
  }

  useEffect(() => {
    return () => {
      Object.values(timersRef.current).forEach(tid => clearTimeout(tid));
      timersRef.current = {};
      recentNotifs.current.clear();
    };
  }, []);

  // Initial full-load (include_history=true)
  async function refresh() {
    try {
      const data = await getOrders(true);
      const normalized = {};
      if (data && typeof data === "object") {
        Object.keys(data).forEach(k => {
          const arr = Array.isArray(data[k]) ? data[k] : [];
          normalized[String(k)] = { items: arr.slice(), meta: { people: null, bread: false } };
        });
      }
      setOrdersMap(normalized);
    } catch (err) {
      console.error("refresh failed", err);
    }
  }

  useEffect(() => { refresh(); const id = setInterval(refresh, 5000); return () => clearInterval(id); }, []);

  // Setup waiter websocket
  useEffect(() => {
    wsRef.current = createWS("waiter", (msg) => {
      try {
        if (!msg || typeof msg !== "object") return;
        const action = msg.action || msg.type;

        if (action === "notify" && msg.message) {
          // play done sound for waiter notifications
          try { playDoneSound(); } catch (e) {}
          pushNotification(msg.message, { id: msg.id });
          return;
        }

        if (action === "item_ready") {
          const table = msg.table;
          const itemText = msg.item;
          const serverId = msg.id || msg.item_id || null;
          const noteText = `ετοιμα ${itemText} τραπέζι ${table}`;
          // play done sound
          try { playDoneSound(); } catch (e) {}
          pushNotification(noteText, { id: serverId });

          if (msg.item_id) {
            markItemStatus(table, msg.item_id, "done");
          } else if (itemText) {
            setOrdersMap(prev => {
              const copy = { ...prev };
              const k = String(table);
              if (!copy[k] || !Array.isArray(copy[k].items)) return prev;
              copy[k].items = copy[k].items.map(it => (it.text === itemText || it.name === itemText) ? { ...it, status: "done" } : it);
              return copy;
            });
          }
          return;
        }

        if (action === "meta_update") {
          const t = String(msg.table);
          setOrdersMap(prev => {
            const copy = { ...prev };
            if (!copy[t]) copy[t] = { items: [], meta: msg.meta || { people: null, bread: false } };
            else copy[t].meta = msg.meta || { people: null, bread: false };
            return copy;
          });
          return;
        }

        if (action === "init") {
          if (msg.orders && typeof msg.orders === "object") {
            setOrdersMap(prev => {
              const copy = { ...prev };
              Object.keys(msg.orders).forEach(k => {
                const arr = Array.isArray(msg.orders[k]) ? msg.orders[k] : [];
                copy[String(k)] = { items: arr.slice(), meta: (msg.meta && msg.meta[k]) ? msg.meta[k] : (copy[String(k)] ? copy[String(k)].meta : { people: null, bread: false }) };
              });
              return copy;
            });
            return;
          }
          return;
        }

        if (action === "new" && msg.item) {
          addOrReplaceItem(msg.item);
          return;
        }

        if (action === "update" && msg.item) {
          updateItem(msg.item);
          return;
        }

        if (action === "delete" && (msg.item_id || (msg.item && msg.item.id))) {
          const iid = msg.item_id || (msg.item && msg.item.id);
          const tab = msg.table || (msg.item && msg.item.table);
          if (tab) markItemStatus(tab, iid, "cancelled");
          return;
        }

        if (action === "table_finalized") {
          const t = msg.table;
          if (t !== undefined && t !== null) {
            removeTable(t);
            setSelectedTable(prev => {
              if (prev === t || String(prev) === String(t)) {
                setText(""); setPeople(""); setBread(false);
                return null;
              }
              return prev;
            });
          }
          return;
        }

      } catch (e) {
        console.error("[waiter WS handler] error", e, msg);
      }
    });

    return () => { try { wsRef.current && wsRef.current.close(); } catch (e) {} };
  }, [playDoneSound]);

  // open table: prefill ONLY pending lines (safely)
  async function openTable(n) {
    setSelectedTable(n);
    const tableObj = ordersMap[String(n)];
    const items = (tableObj && Array.isArray(tableObj.items)) ? tableObj.items : [];
    const pendingLines = items.filter(i => i && i.status === "pending");
    if (pendingLines.length) setText(pendingLines.map(i => (i.text ?? i.name ?? "")).join("\n"));
    else setText("");
    try {
      const meta = await getTableMeta(n);
      setPeople(meta.people ?? "");
      setBread(Boolean(meta.bread));
    } catch (err) {
      setPeople((tableObj && tableObj.meta && tableObj.meta.people) || "");
      setBread((tableObj && tableObj.meta && !!tableObj.meta.bread) || false);
    }
  }

  async function sendOrEdit() {
    if (!selectedTable) return;
    const payloadTable = selectedTable;
    const payloadText = text;
    const payloadPeople = people ? parseInt(people, 10) : null;
    const payloadBread = !!bread;
    try {
      if (!ordersMap[String(selectedTable)] || (ordersMap[String(selectedTable)].items || []).length === 0) {
        await postOrder(payloadTable, payloadText, payloadPeople, payloadBread);
      } else {
        await putOrder(payloadTable, payloadText, payloadPeople, payloadBread);
      }
      await refresh();
      setSelectedTable(null); setText(""); setPeople(""); setBread(false);
    } catch (err) {
      console.error("sendOrEdit failed", err);
    }
  }

  function closeTable() { setSelectedTable(null); setText(""); setPeople(""); setBread(false); }

  async function finalizeTable() {
    if (!selectedTable) return;
    try {
      if (wsRef.current && wsRef.current.send) {
        wsRef.current.send({ action: "finalize_table", table: selectedTable });
      } else {
        console.warn("No websocket available to finalize table. Try reloading or check backend.");
      }
    } catch (e) {
      console.error("finalizeTable error", e);
    }
  }

  // small price formatting helper
  function formatPrice(v) {
    if (v === null || v === undefined || Number.isNaN(v)) return "—";
    try {
      return `${Number(v).toFixed(2)} €`;
    } catch {
      return "—";
    }
  }

  // local lightweight parser for debug only
  function parseQuantityAndUnit(text) {
    if (!text) return { qty: 1, isWeight: false, weight_kg: null, unitRaw: null };
    const s = String(text).trim().toLowerCase();
    // immediate no-space unit
    let m = s.match(/^\s*([0-9]+(?:[.,][0-9]+)?)(kg|κ|κιλ|κιλό|g|γρ|gr)/i);
    if (m && m[1]) {
      const num = Number(String(m[1]).replace(",", "."));
      const unit = (m[2] || "").toLowerCase();
      if (unit === "kg" || unit === "κ" || unit === "κιλ" || unit === "κιλό") return { qty: 1, isWeight: true, weight_kg: num, unitRaw: unit };
      if (unit === "g" || unit === "γρ" || unit === "gr") return { qty: 1, isWeight: true, weight_kg: num / 1000, unitRaw: unit };
    }
    // grams anywhere
    m = s.match(/([0-9]+(?:[.,][0-9]+)?)\s*(g|γρ|gr)\b/i);
    if (m && m[1]) {
      const grams = Number(String(m[1]).replace(",", "."));
      return { qty: 1, isWeight: true, weight_kg: grams / 1000, unitRaw: m[2] };
    }
    // leading count
    m = s.match(/^\s*([0-9]+)(?:\b|\s+)/);
    if (m && m[1]) {
      const n = Number(m[1]);
      return { qty: Number.isFinite(n) ? n : 1, isWeight: false, weight_kg: null, unitRaw: null };
    }
    return { qty: 1, isWeight: false, weight_kg: null, unitRaw: null };
  }

  // compute subtotal of known line totals for non-cancelled items (trust server-provided if present)
  const currentEntry = selectedTable ? (ordersMap[String(selectedTable)] || { items: [], meta: { people: null, bread: false } }) : null;
  const currentOrderItems = currentEntry ? (Array.isArray(currentEntry.items) ? currentEntry.items : []) : [];

  const subtotalKnown = currentOrderItems.reduce((acc, it) => {
    if (!it) return acc;
    if (it.status === "cancelled") return acc;
    // prefer server-provided line_total
    if (typeof it.line_total === "number") return acc + it.line_total;
    return acc;
  }, 0);
  const hasUnknownPrices = currentOrderItems.some(it => {
    if (!it) return false;
    if (it.status === "cancelled") return false;
    if (typeof it.line_total === "number") return false;
    return true;
  });

  const isMobile = typeof window !== "undefined" && window.innerWidth < 700;

  return (
    <div style={{ padding: 16, fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, alignItems: "center" }}>
        <label style={{ color: "#666", fontSize: 14 }}>
          Debug
          <input type="checkbox" checked={debugEnabled} onChange={e => setDebugEnabled(e.target.checked)} style={{ marginLeft: 6 }} />
        </label>
        <button onClick={toggleMute} style={{ padding: "6px 10px", borderRadius: 8, border: "none", cursor: "pointer" }}>
          {muted ? "🔇" : "🔊"}
        </button>
      </div>

      {/* Notifications */}
      <div>
        {isMobile ? (
          <div style={{
            position: "fixed", left: 12, right: 12, bottom: 16, zIndex: 9999, display: "flex", flexDirection: "column", gap: 10, alignItems: "center",
            pointerEvents: "auto"
          }}>
            {notifications.map(n => (
              <div key={n.id} onClick={() => dismissNotification(n.id)} style={{
                width: "100%",
                maxWidth: 520,
                background: "#ffffff",
                color: "#000",
                padding: "14px 16px",
                borderRadius: 12,
                boxShadow: "0 6px 20px rgba(0,0,0,0.25)",
                fontSize: 18,
                fontWeight: 600,
                textAlign: "center",
                cursor: "pointer",
                lineHeight: "1.15"
              }}>
                {n.text}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ position: "fixed", top: 12, right: 12, zIndex: 9999, maxWidth: 360 }}>
            {notifications.map(n => (
              <div key={n.id} onClick={() => dismissNotification(n.id)} style={{
                background: "#ffffff",
                color: "#000",
                padding: 10,
                marginBottom: 8,
                borderRadius: 10,
                boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
                cursor: "pointer",
                fontSize: 15,
                fontWeight: 600
              }}>
                {n.text}
              </div>
            ))}
          </div>
        )}
      </div>

      {!selectedTable ? (
        <>
          <h1 style={{ textAlign: "center" }}>ΤΡΑΠΕΖΙΑ</h1>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center" }}>
            {Array.from({ length: 17 }).map((_, i) => i + 1).map(i => {
              const entry = ordersMap[String(i)] || { items: [], meta: { people: null, bread: false } };
              const items = Array.isArray(entry.items) ? entry.items : [];
              const hasPending = items.some(it => it && it.status === "pending");
              const hasAny = items.length > 0;
              const allDone = hasAny && items.every(it => it && (it.status === "done" || it.status === "cancelled"));
              let color = "#5cb85c";
              if (allDone) color = "#4a90e2";
              else if (hasPending) color = "#d9534f";
              return <TableButton key={i} n={i} color={color} onClick={openTable} />;
            })}
          </div>
        </>
      ) : (
        <div>
          <h2>ΤΡΑΠΕΖΙ {selectedTable}</h2>

          <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 8 }}>
            <label>
              Αριθμός ατόμων:
              <input type="number" min="1" value={people} onChange={e => setPeople(e.target.value)} style={{ width: 80, marginLeft: 8 }} />
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" checked={bread} onChange={(e) => setBread(e.target.checked)} />
              Θέλουν ψωμί
            </label>
          </div>

          <div style={{ marginBottom: 12 }}>
            {currentOrderItems.length === 0 ? (
              <div style={{ color: "#666" }}>Δεν υπάρχουν παραγγελίες</div>
            ) : (
              currentOrderItems.map(item => {
                const displayName = (item && item.name) ? item.name : (item && item.text) ? item.text : "(άγνωστο)";
                const isStruck = item && (item.status === "done" || item.status === "cancelled");

                // Prefer server-provided pricing/weight
                const serverUnitPrice = item.unit_price !== undefined ? item.unit_price : null;
                const serverLineTotal = item.line_total !== undefined ? item.line_total : null;
                const serverWeight = item.weight_kg !== undefined ? item.weight_kg : null;
                const serverQty = item.qty !== undefined ? item.qty : 1;

                let priceLine = null;
                if (serverLineTotal != null && serverUnitPrice != null) {
                  if (serverWeight != null) {
                    const weightLabel = (serverWeight < 1) ? `${Math.round(serverWeight * 1000)}g` : `${Number(serverWeight % 1 === 0 ? serverWeight : Number(serverWeight.toFixed(2)))}kg`;
                    priceLine = `${weightLabel} × ${Number(serverUnitPrice).toFixed(2)}€/kg = ${Number(serverLineTotal).toFixed(2)}€`;
                  } else {
                    priceLine = `${serverQty}× ${Number(serverUnitPrice).toFixed(2)}€ = ${Number(serverLineTotal).toFixed(2)}€`;
                  }
                } else if (serverLineTotal != null && serverUnitPrice == null) {
                  // server gave a line total but not unit price
                  priceLine = `= ${Number(serverLineTotal).toFixed(2)}€`;
                } else {
                  // fallback: compute nothing (server is authoritative)
                  priceLine = "—";
                }

                // local parse for debug comparison
                const parsedLocal = parseQuantityAndUnit(item.text || item.name || "");

                return (
                  <div key={item.id} style={{ marginBottom: 6 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", padding: 6, borderBottom: "1px dashed #eee" }}>
                      <div style={{ fontSize: 18 }}>
                        <div style={{ textDecoration: isStruck ? "line-through" : "none", fontSize: 18 }}>
                          {displayName}
                        </div>
                        <div style={{ fontSize: 13, color: priceLine && priceLine !== "—" ? "#444" : "#999", marginTop: 4 }}>
                          {priceLine}
                        </div>
                      </div>
                      <div style={{ fontSize: 12, color: "#666", minWidth: 120, textAlign: "right", display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
                        <div>
                          {item.status === "pending" ? "εκκρεμεί" : (item.status === "done" ? "έτοιμο" : "ακυρωμένο")}
                        </div>
                      </div>
                    </div>

                    {debugEnabled ? (
                      <div style={{ background: "#f6f6f6", padding: 8, fontSize: 12, fontFamily: "monospace", color: "#222", borderRadius: 6 }}>
                        <div><strong>Debug</strong></div>
                        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
{JSON.stringify({
  server: {
    menu_id: item.menu_id ?? null,
    menu_name: item.menu_name ?? null,
    unit_price: item.unit_price ?? null,
    line_total: item.line_total ?? null,
    qty: item.qty ?? null,
    weight_kg: item.weight_kg ?? null
  },
  parsed_local: parsedLocal
}, null, 2)}
                        </pre>
                      </div>
                    ) : null}
                  </div>
                );
              })
            )}
          </div>

          <textarea value={text} onChange={e => setText(e.target.value)} rows={10} style={{ width: "100%", fontSize: 18, padding: 12 }} placeholder="Γράψτε την παραγγελία — κάθε πιάτο σε νέα γραμμή" />

          <div style={{ display: "flex", gap: 12, marginTop: 12, alignItems: "center" }}>
            <button onClick={sendOrEdit} style={{ padding: "12px 24px", fontSize: 18, backgroundColor: "#007bff", color: "#fff", border: "none", borderRadius: 8 }}>
              {(currentOrderItems.length) ? "ΕΠΕΞΕΡΓΑΣΙΑ" : "ΑΠΟΣΤΟΛΗ"}
            </button>

            {currentOrderItems.length > 0 && currentOrderItems.every(it => it && (it.status === "done" || it.status === "cancelled")) ? (
              <>
                <div style={{ marginLeft: 8, fontSize: 18, fontWeight: 700, color: "#fff", background: "#4a90e2", padding: "8px 12px", borderRadius: 8 }}>
                  Σύνολο: {formatPrice(subtotalKnown)} {hasUnknownPrices ? <span style={{ fontSize: 12, color: "#f6f6f6", marginLeft: 8 }}>(κάποια είδη χωρίς τιμή)</span> : null}
                </div>

                <button onClick={finalizeTable} style={{ padding: "12px 24px", fontSize: 18, backgroundColor: "#4a90e2", color: "#fff", border: "none", borderRadius: 8 }}>
                  ΟΛΟΚΛΗΡΩΣΗ ΤΡΑΠΕΖΙΟΥ
                </button>
              </>
            ) : null }

            <button onClick={closeTable} style={{ padding: "12px 24px", fontSize: 18 }}>
              ΑΚΥΡΟ
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
