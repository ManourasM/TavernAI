// src/App.jsx
import React, { useEffect, useMemo, useState, useRef } from "react";
import { createWS, getOrders, markDone } from "./api";
import { useSounds } from "./utils/sounds";

/**
 * Station UI (kitchen or grill).
 * To make grill UI set station = "grill".
 */
const station = "kitchen"; // change to "grill" in grill project

export default function App() {
  const [ordersMap, setOrdersMap] = useState({}); // { tableStr: { table, items: [...], meta } }
  const [checked, setChecked] = useState({});     // { itemId: true }
  const [debugEnabled, setDebugEnabled] = useState(false);

  // sounds
  const { muted, toggleMute, ensureAudio, playNewOrderSound, playDoneSound } = useSounds();
  useEffect(() => { ensureAudio(); }, [ensureAudio]);

  // --- Helpers ---
  function itemForThisStation(item) {
    if (!item) return false;
    if (station === "grill") return item.category === "grill";
    return item.category !== "grill";
  }

  function upsertItem(item) {
    if (!itemForThisStation(item)) return;
    setOrdersMap(prev => {
      const copy = { ...prev };
      const t = String(item.table);
      if (!copy[t]) copy[t] = { table: item.table, items: [], meta: { people: null, bread: false } };
      if (item.meta) copy[t].meta = item.meta;

      const idx = copy[t].items.findIndex(i => i.id === item.id);
      if (idx >= 0) copy[t].items[idx] = { ...copy[t].items[idx], ...item };
      else copy[t].items.push(item);

      copy[t].items.sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""));
      return copy;
    });
  }

  function removeItemById(itemId) {
    setOrdersMap(prev => {
      const copy = { ...prev };
      for (const k of Object.keys(copy)) {
        copy[k].items = (copy[k].items || []).filter(i => i.id !== itemId);
        if (!copy[k].items.length) delete copy[k];
      }
      return copy;
    });
    setChecked(prev => {
      if (!prev[itemId]) return prev;
      const cp = { ...prev }; delete cp[itemId]; return cp;
    });
  }

  // initial load
  useEffect(() => {
    getOrders().then(resp => {
      if (!resp || typeof resp !== "object") return;
      setOrdersMap(prev => {
        const copy = { ...prev };
        Object.keys(resp).forEach(table => {
          const arr = Array.isArray(resp[table]) ? resp[table] : [];
          const filtered = arr.filter(it => itemForThisStation(it));
          if (filtered.length > 0) {
            copy[String(table)] = { table: parseInt(table, 10), items: filtered.slice(), meta: (filtered[0] && filtered[0].meta) || { people: null, bread: false } };
            copy[String(table)].items.sort((a,b) => (a.created_at || "").localeCompare(b.created_at || ""));
          }
        });
        return copy;
      });
    }).catch(err => console.warn("getOrders failed", err));
  }, []);

  // websocket handler
  useEffect(() => {
    const ws = createWS(station, (msg) => {
      try {
        if (!msg || !msg.action) return;

        if (msg.action === "init" && Array.isArray(msg.items)) {
          if (msg.meta) msg.items.forEach(it => { if (it) it.meta = msg.meta; });
          msg.items.forEach(it => upsertItem(it));
          return;
        } else if (msg.action === "new" && msg.item) {
          // play new-order sound for this station
          try { playNewOrderSound(); } catch (e) {}
          if (msg.meta) msg.item.meta = msg.meta;
          upsertItem(msg.item);
          return;
        } else if (msg.action === "delete") {
          if (msg.item_id) removeItemById(msg.item_id);
          else if (msg.item && msg.item.id) removeItemById(msg.item.id);
          return;
        } else if (msg.action === "update" && msg.item) {
          if (msg.meta) msg.item.meta = msg.meta;
          if (msg.item.status === "done" || msg.item.status === "cancelled") {
            // removing completed items from station display
            removeItemById(msg.item.id);
          } else {
            upsertItem(msg.item);
          }
          return;
        } else if (msg.action === "meta_update" && msg.table !== undefined) {
          // Only update meta if the table already exists in this station UI (prevents empty frames)
          setOrdersMap(prev => {
            const copy = { ...prev };
            const t = String(msg.table);
            if (copy[t]) {
              copy[t].meta = msg.meta || { people: null, bread: false };
            }
            return copy;
          });
          return;
        } else if (msg.action === "table_finalized" && (msg.table !== undefined && msg.table !== null)) {
          const t = String(msg.table);
          setOrdersMap(prev => {
            const copy = { ...prev };
            if (copy[t]) delete copy[t];

            // cleanup checked items that no longer exist
            const validIds = new Set();
            Object.values(copy).forEach(tbl => {
              (tbl.items || []).forEach(it => { if (it && it.id) validIds.add(it.id); });
            });

            setChecked(prevChecked => {
              const cp = { ...prevChecked };
              Object.keys(cp).forEach(kid => { if (!validIds.has(kid)) delete cp[kid]; });
              return cp;
            });

            return copy;
          });
          return;
        }
      } catch (e) {
        console.warn("WS handler error", e, msg);
      }
    });
    return () => { try { ws.close(); } catch (e) {} };
  }, [station, playNewOrderSound]);

  // checkbox toggle
  function toggle(itemId) {
    setChecked(prev => {
      const cp = { ...prev };
      if (cp[itemId]) delete cp[itemId]; else cp[itemId] = true;
      return cp;
    });
  }

  // confirm all checked
  async function confirmAll() {
    const ids = Object.keys(checked);
    if (!ids.length) return;
    await Promise.all(ids.map(id => markDone(id).catch(()=>null)));
    ids.forEach(id => removeItemById(id));
    setChecked({});
    try { playDoneSound(); } catch (e) {}
  }

  // ----------------------------
  // Aggregation helpers (updated to separate kg vs portion)
  // ----------------------------
  function normalizeForDisplay(text) {
    if (!text) return "(άγνωστο)";
    let s = String(text).trim();
    s = s.replace(/\b(τεμ\.?|τεμ|x|χ)\b/gi, " ");
    s = s.replace(/\b\d+\b/g, " ");
    s = s.replace(/[,:·\-\(\)\[\]\.\/]/g, " ");
    s = s.replace(/\s+/g, " ").trim();
    if (!s) return "(άγνωστο)";
    return s;
  }

  function rootKey(text) {
    const N = 4;
    if (!text) return "__unknown__";
    // preserve only letters/numbers/space (unicode)
    try {
      const cleaned = String(text).replace(/[^\p{L}\p{N}\s]/gu, " ").trim();
      const words = cleaned.split(/\s+/).filter(Boolean);
      if (!words.length) return "__unknown__";
      const parts = words.map(w => w.normalize("NFC").slice(0, N).toLowerCase());
      return parts.join(" ");
    } catch (e) {
      const cleaned = String(text).replace(/[^\w\s]/g, " ").trim();
      const words = cleaned.split(/\s+/).filter(Boolean);
      if (!words.length) return "__unknown__";
      const parts = words.map(w => w.normalize("NFC").slice(0, N).toLowerCase());
      return parts.join(" ");
    }
  }

  const aggregated = useMemo(() => {
    const map = new Map();
    Object.keys(ordersMap).forEach(tableKey => {
      const tableObj = ordersMap[tableKey];
      if (!tableObj || !Array.isArray(tableObj.items)) return;
      tableObj.items.forEach(item => {
        if (!itemForThisStation(item)) return;
        if (item.status !== "pending") return;

        // Display normalization
        const raw = item.text || item.name || "";
        const display = normalizeForDisplay(raw);

        // decide if this item is a weight (kg) order based on server-provided weight_kg
        const isWeight = item.weight_kg != null;

        // aggregation key: rootKey + classification (kg/portion) + menu_id (if available) to avoid merging different-price items
        const baseKey = rootKey(display);
        const menuIdPart = item.menu_id ? `|${item.menu_id}` : "";
        const kind = isWeight ? "kg" : "portion";
        const key = `${baseKey}::${kind}${menuIdPart}`;

        const entry = map.get(key) || { key, displayName: display, qty: 0, tables: new Set(), isWeight };
        if (isWeight) {
          // for weight: sum weights (if server provided weight_kg we add it; otherwise fallback to parse numeric)
          const w = Number(item.weight_kg || 0);
          entry.qty += (Number.isFinite(w) ? w : 0);
        } else {
          // portion: use qty (server-provided qty preferred)
          const q = item.qty != null ? Number(item.qty) : (String(raw).match(/\d+/) ? Number(String(raw).match(/\d+/)[0]) : 1);
          entry.qty += (Number.isFinite(q) ? q : 1);
        }
        entry.tables.add(tableObj.table || parseInt(tableKey, 10));
        // prefer the shorter displayName? keep first seen as canonical (or try to prefer menu_name if present)
        if (!entry.displayName && display) entry.displayName = display;
        // keep menu info for debug if desired
        entry.menu_id = item.menu_id || entry.menu_id || null;

        map.set(key, entry);
      });
    });

    // Convert to array and sort: weight groups could be shown separately — sort by qty desc
    const arr = Array.from(map.values()).map(e => {
      // format qty for display: for weight groups show kilogram sum as integer/2-decimals?
      return e;
    });

    arr.sort((a, b) => {
      // compare numeric qty descending
      const aQty = a.qty || 0;
      const bQty = b.qty || 0;
      if (bQty !== aQty) return bQty - aQty;
      return (a.displayName || "").localeCompare(b.displayName || "");
    });

    return arr;
  }, [ordersMap]);

  // ----------------------------
  // Render
  // ----------------------------
  const tableEntries = Object.entries(ordersMap).map(([k, v]) => [parseInt(k,10), v]);
  tableEntries.sort(([, a], [, b]) => {
    const aMin = (a.items && a.items.length) ? a.items.reduce((m,i)=> (i.created_at && i.created_at < m ? i.created_at : m), a.items[0].created_at) : "9999-12-31T23:59:59Z";
    const bMin = (b.items && b.items.length) ? b.items.reduce((m,i)=> (i.created_at && i.created_at < m ? i.created_at : m), b.items[0].created_at) : "9999-12-31T23:59:59Z";
    return aMin.localeCompare(bMin);
  });

  const isNarrow = typeof window !== "undefined" && window.innerWidth < 700;

  const styles = {
    pageBg: "#0b0f14",
    cardBg: "#ffffff",
    lightCard: "#ffffff",
    text: "#000000",
    muted: "#666666",
    statusPending: "#c0392b",
    statusDone: "#2ecc71",
    confirm: "#b07a39"
  };

  return (
    <div style={{ padding: 16, fontFamily: "sans-serif", background: styles.pageBg, minHeight: "100vh" }}>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, alignItems: "center" }}>
        <label style={{ color: "#ddd", fontSize: 14 }}>
          Debug
          <input type="checkbox" checked={debugEnabled} onChange={e => setDebugEnabled(e.target.checked)} style={{ marginLeft: 6 }} />
        </label>
        <button onClick={toggleMute} style={{ padding: "6px 10px", borderRadius: 8, border: "none", cursor: "pointer" }}>
          {muted ? "🔇" : "🔊"}
        </button>
      </div>

      <h1 style={{ textAlign: "center", marginBottom: 12, color: "#fff" }}>{station === "grill" ? "ΨΗΣΤΑΡΙΑ" : "ΚΟΥΖΙΝΑ"}</h1>

      <div style={{
        display: "flex",
        gap: 16,
        alignItems: "flex-start",
        flexDirection: isNarrow ? "column" : "row"
      }}>
        <div style={{ flex: 1, minWidth: 320 }}>
          {tableEntries.length === 0 && <div style={{ textAlign: "center", padding: 18, color: "#ddd" }}>Δεν υπάρχουν ενεργές παραγγελίες</div>}

          {tableEntries.map(([tableNum, order]) => (
            <div key={tableNum} style={{ background: styles.cardBg, border: "1px solid #e6e2da", borderRadius: 8, padding: 12, marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <div style={{ fontWeight: 700, color: styles.text }}>Τραπέζι {tableNum}</div>
                <div style={{ fontSize: 12, color: styles.muted }}>
                  {order.meta && order.meta.people ? <>Άτομα: {order.meta.people}</> : null}
                  {order.meta && order.meta.bread ? <span style={{ marginLeft: 8 }}>• Ψωμί</span> : null}
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {order.items.map(item => {
                  const parsed = {
                    qty: (item.qty !== undefined ? item.qty : (String(item.text || item.name || "").match(/\d+/) ? Number(String(item.text || item.name || "").match(/\d+/)[0]) : 1)),
                    isWeight: item.weight_kg != null,
                    weight_kg: item.weight_kg ?? null,
                    unitRaw: null
                  };

                  return (
                    <label key={item.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: 8, borderRadius: 6, background: styles.lightCard }}>
                      <input type="checkbox" checked={!!checked[item.id]} onChange={() => toggle(item.id)} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 18, fontWeight: 600, color: styles.text }}>{item.text || item.name}</div>
                        <div style={{ fontSize: 12, color: styles.muted }}>{item.created_at ? new Date(item.created_at).toLocaleTimeString() : ""}</div>

                        {debugEnabled ? (
                          <div style={{ marginTop: 6, background: "#f6f6f6", padding: 6, borderRadius: 6, fontSize: 12, fontFamily: "monospace", color: "#222" }}>
                            <div><strong>Debug (server)</strong></div>
                            <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
{JSON.stringify({
  parsed,
  menu_id: item.menu_id ?? null,
  menu_name: item.menu_name ?? null,
  unit_price: item.unit_price ?? null,
  line_total: item.line_total ?? null,
  status: item.status
}, null, 2)}
                            </pre>
                          </div>
                        ) : null}
                      </div>
                      <div style={{ fontSize: 12, color: (item.status === "pending" ? styles.statusPending : styles.statusDone), minWidth: 86, textAlign: "right" }}>
                        {item.status === "pending" ? "εκκρεμεί" : (item.status === "done" ? "έτοιμο" : "ακυρωμένο")}
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <div style={{ width: 320, minWidth: 260 }}>
          <div style={{ fontWeight: 700, marginBottom: 10, color: "#fff" }}>ΣΥΝΟΛΙΚΑ — {aggregated.length} είδη</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {aggregated.length === 0 && <div style={{ color: "#ddd" }}>Δεν υπάρχουν πιάτα προς εκτέλεση</div>}
            {aggregated.map(entry => (
              <div key={entry.key} style={{ background: styles.cardBg, padding: 12, borderRadius: 8, boxShadow: "0 2px 6px rgba(0,0,0,0.08)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: styles.text }}>
                    {entry.isWeight ? `${entry.qty}kg × ${entry.displayName}` : `${entry.qty}× ${entry.displayName}`}
                  </div>
                  <div style={{ fontSize: 12, color: styles.muted }}>Τραπέζια: {Array.from(entry.tables).join(", ")}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ position: "fixed", right: 20, bottom: 20 }}>
        <button onClick={confirmAll} disabled={Object.keys(checked).length === 0} style={{
          padding: "12px 20px",
          background: Object.keys(checked).length === 0 ? "#666" : styles.confirm,
          color: "#fff", border: "none", borderRadius: 8, fontSize: 16, cursor: Object.keys(checked).length === 0 ? "not-allowed" : "pointer"
        }}>
          Επιβεβαίωση ({Object.keys(checked).length})
        </button>
      </div>
    </div>
  );
}
