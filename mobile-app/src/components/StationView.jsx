// src/components/StationView.jsx
import { useEffect, useMemo, useState } from "react";
import { createWS, getOrders, markDone } from "../services/api";
import { useSounds } from "../utils/sounds";

export default function StationView({ station, stationName, stationColor }) {
  const [ordersMap, setOrdersMap] = useState({}); // { tableStr: { table, items: [...], meta } }
  const [checked, setChecked] = useState({});     // { itemId: true }

  // sounds
  const { muted, toggleMute, ensureAudio, playNewOrderSound, playDoneSound } = useSounds();
  useEffect(() => { ensureAudio(); }, [ensureAudio]);

  // --- Helpers ---
  function itemForThisStation(item) {
    if (!item) return false;
    return item.category === station;
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

  const syncState = async () => {
    const resp = await getOrders();
    if (!resp || typeof resp !== "object") return;
    const next = {};
    Object.keys(resp).forEach(table => {
      const arr = Array.isArray(resp[table]) ? resp[table] : [];
      const filtered = arr.filter(it => itemForThisStation(it));
      if (filtered.length > 0) {
        next[String(table)] = { table: parseInt(table, 10), items: filtered.slice(), meta: (filtered[0] && filtered[0].meta) || { people: null, bread: false } };
        next[String(table)].items.sort((a,b) => (a.created_at || "").localeCompare(b.created_at || ""));
      }
    });
    setOrdersMap(next);
  };

  // initial load
  useEffect(() => {
    syncState().catch(err => console.warn("getOrders failed", err));
  }, [station]);

  // websocket handler
  useEffect(() => {
    const ws = createWS(
      station,
      (msg) => {
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
      },
      null,
      {
        onSync: async () => {
          await syncState();
        }
      }
    );
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
  // Aggregation helpers
  // ----------------------------
  function parseQuantity(text) {
    if (!text) return 1;
    const m = String(text).match(/\d+/);
    if (m && m[0]) {
      const n = parseInt(m[0], 10);
      return Number.isFinite(n) && n > 0 ? n : 1;
    }
    return 1;
  }

  function normalizeForDisplay(text) {
    if (!text) return "(άγνωστο)";
    let s = String(text).trim();
    // Remove parentheses content for aggregate display
    s = s.replace(/\s*\([^)]*\)\s*/g, " ");
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

    // keep only letters/numbers/whitespace
    const cleaned = String(text).replace(/[^\p{L}\p{N}\s]/gu, " ").trim();
    const words = cleaned.split(/\s+/).filter(Boolean);
    if (!words.length) return "__unknown__";

    const parts = words.map(w => {
      // Normalize to NFD so diacritics are separate combining marks,
      // then strip all combining marks (Unicode category M) to remove accents.
      let base = w.normalize("NFD").replace(/\p{M}/gu, "");
      // normalize final sigma (ς) to standard sigma (σ) to reduce differences
      base = base.replace(/ς/g, "σ");
      // slice first N characters and lowercase
      return base.slice(0, N).toLowerCase();
    });

    return parts.join(" ");
  }

  const aggregated = useMemo(() => {
    const map = new Map();
    Object.keys(ordersMap).forEach(table => {
      const tableObj = ordersMap[table];
      if (!tableObj || !Array.isArray(tableObj.items)) return;
      tableObj.items.forEach(item => {
        if (!itemForThisStation(item)) return;
        if (item.status !== "pending") return;

        // Use menu_name for display if available (matched items), otherwise use text
        const displayText = item.menu_name || item.text || item.name || "";
        // Use item.qty if available (from backend), otherwise parse from text
        const qty = (item.qty !== null && item.qty !== undefined) ? item.qty : parseQuantity(item.text || item.name || "");

        const display = normalizeForDisplay(displayText);
        const key = rootKey(display);
        const entry = map.get(key) || { key, displayName: display, qty: 0, tables: new Set() };
        entry.qty += qty;
        entry.tables.add(tableObj.table || parseInt(table,10));
        if ((display.length < (entry.displayName || "").length) || !entry.displayName) {
          entry.displayName = display;
        }
        map.set(key, entry);
      });
    });
    return Array.from(map.values()).sort((a,b) => b.qty - a.qty || a.displayName.localeCompare(b.displayName));
  }, [ordersMap, station]);

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

  const hexToRgb = (hex) => {
    const normalized = String(hex || '').replace('#', '');
    if (normalized.length !== 6) return { r: 102, g: 126, b: 234 };
    const r = parseInt(normalized.slice(0, 2), 16);
    const g = parseInt(normalized.slice(2, 4), 16);
    const b = parseInt(normalized.slice(4, 6), 16);
    return { r, g, b };
  };

  const rgbToHex = (r, g, b) => {
    const clamp = (v) => Math.max(0, Math.min(255, v));
    return `#${[r, g, b].map((v) => clamp(v).toString(16).padStart(2, '0')).join('')}`;
  };

  const mixWith = (hex, mix, weight) => {
    const base = hexToRgb(hex);
    const target = hexToRgb(mix);
    const w = Math.max(0, Math.min(1, weight));
    const r = Math.round(base.r * (1 - w) + target.r * w);
    const g = Math.round(base.g * (1 - w) + target.g * w);
    const b = Math.round(base.b * (1 - w) + target.b * w);
    return rgbToHex(r, g, b);
  };

  const baseColor = stationColor || '#667eea';
  const colors = {
    primary: baseColor,
    secondary: mixWith(baseColor, '#ffffff', 0.35),
    bg: mixWith(baseColor, '#ffffff', 0.85),
    dark: mixWith(baseColor, '#000000', 0.25),
  };

  const styles = {
    pageBg: "#f5f6f8",
    cardBg: "#ffffff",
    lightCard: "#f8f9fa",
    text: "#2c3e50",
    muted: "#7f8c8d",
    statusPending: "#e74c3c",
    statusDone: "#27ae60",
    confirm: colors.primary,
    shadow: "0 4px 6px rgba(0,0,0,0.1)",
    shadowHover: "0 8px 12px rgba(0,0,0,0.15)"
  };

  const stationTitle = (stationName || station || '').toUpperCase();

  return (
    <div style={{
      padding: 0,
      fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
      background: styles.pageBg,
      minHeight: "100vh"
    }}>
      {/* Header */}
      <div style={{
        background: colors.primary,
        padding: "20px 24px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
        position: "sticky",
        top: 0,
        zIndex: 100
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", maxWidth: 1400, margin: "0 auto" }}>
          <h1 style={{
            margin: 0,
            color: "#fff",
            fontSize: 32,
            fontWeight: 700,
            letterSpacing: "0.5px",
            textShadow: "0 2px 4px rgba(0,0,0,0.2)"
          }}>
            {stationTitle}
          </h1>
          <button
            onClick={toggleMute}
            style={{
              padding: "10px 16px",
              borderRadius: 12,
              border: "2px solid rgba(255,255,255,0.3)",
              background: "rgba(255,255,255,0.2)",
              color: "#fff",
              fontSize: 20,
              cursor: "pointer",
              transition: "all 0.2s",
              backdropFilter: "blur(10px)"
            }}
            onMouseEnter={(e) => e.target.style.background = "rgba(255,255,255,0.3)"}
            onMouseLeave={(e) => e.target.style.background = "rgba(255,255,255,0.2)"}
          >
            {muted ? "🔇" : "🔊"}
          </button>
        </div>
      </div>

      <div style={{ padding: "24px", maxWidth: 1400, margin: "0 auto" }}>

      <div style={{
        display: "flex",
        gap: 16,
        alignItems: "flex-start",
        flexDirection: isNarrow ? "column" : "row"
      }}>
        <div style={{ flex: 1, minWidth: 320 }}>
          {tableEntries.length === 0 && (
            <div style={{
              textAlign: "center",
              padding: 48,
              background: "rgba(255,255,255,0.9)",
              borderRadius: 16,
              boxShadow: styles.shadow,
              color: styles.muted,
              fontSize: 18
            }}>
              ✓ Δεν υπάρχουν ενεργές παραγγελίες
            </div>
          )}

          {tableEntries.map(([tableNum, order]) => (
            <div key={tableNum} style={{
              background: styles.cardBg,
              borderRadius: 16,
              padding: 20,
              marginBottom: 16,
              boxShadow: styles.shadow,
              transition: "all 0.3s",
              border: `3px solid ${colors.secondary}`,
              borderLeft: `8px solid ${colors.primary}`
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div style={{
                  fontSize: 24,
                  fontWeight: 700,
                  color: colors.dark,
                  display: "flex",
                  alignItems: "center",
                  gap: 8
                }}>
                  <span style={{
                    background: colors.primary,
                    color: "#fff",
                    width: 40,
                    height: 40,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 18,
                    fontWeight: 700
                  }}>
                    {tableNum}
                  </span>
                  Τραπέζι
                </div>
                <div style={{
                  fontSize: 13,
                  color: styles.muted,
                  background: styles.lightCard,
                  padding: "6px 12px",
                  borderRadius: 8,
                  fontWeight: 600
                }}>
                  {order.meta && order.meta.people ? <>👥 {order.meta.people}</> : null}
                  {order.meta && order.meta.bread ? <span style={{ marginLeft: 8 }}>🍞</span> : null}
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {order.items.map(item => (
                  <label key={item.id} style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: 14,
                    borderRadius: 12,
                    background: styles.lightCard,
                    cursor: "pointer",
                    transition: "all 0.2s",
                    border: "2px solid transparent"
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = colors.bg;
                    e.currentTarget.style.borderColor = colors.secondary;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = styles.lightCard;
                    e.currentTarget.style.borderColor = "transparent";
                  }}
                  >
                    <input
                      type="checkbox"
                      checked={!!checked[item.id]}
                      onChange={() => toggle(item.id)}
                      style={{
                        width: 20,
                        height: 20,
                        cursor: "pointer",
                        accentColor: colors.primary
                      }}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 18, fontWeight: 600, color: styles.text, marginBottom: 4 }}>
                        {item.text || item.name}
                      </div>
                      <div style={{ fontSize: 12, color: styles.muted }}>
                        🕐 {item.created_at ? new Date(item.created_at).toLocaleTimeString('el-GR', { timeZone: 'Europe/Athens' }) : ""}
                      </div>
                    </div>
                    <div style={{
                      fontSize: 13,
                      color: "#fff",
                      background: item.status === "pending" ? styles.statusPending : styles.statusDone,
                      padding: "6px 12px",
                      borderRadius: 8,
                      minWidth: 90,
                      textAlign: "center",
                      fontWeight: 600
                    }}>
                      {item.status === "pending" ? "⏳ εκκρεμεί" : (item.status === "done" ? "✓ έτοιμο" : "✗ ακυρωμένο")}
                    </div>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div style={{ width: isNarrow ? "100%" : 360, minWidth: 260 }}>
          <div style={{
            background: "rgba(255,255,255,0.95)",
            borderRadius: 16,
            padding: 20,
            boxShadow: styles.shadow,
            position: isNarrow ? "relative" : "sticky",
            top: isNarrow ? 0 : 100
          }}>
            <div style={{
              fontSize: 20,
              fontWeight: 700,
              marginBottom: 16,
              color: colors.dark,
              display: "flex",
              alignItems: "center",
              gap: 10,
              paddingBottom: 12,
              borderBottom: `3px solid ${colors.primary}`
            }}>
              <span style={{ fontSize: 24 }}>📊</span>
              ΣΥΝΟΛΙΚΑ
              <span style={{
                background: colors.primary,
                color: "#fff",
                padding: "4px 12px",
                borderRadius: 20,
                fontSize: 16,
                marginLeft: "auto"
              }}>
                {aggregated.length}
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 12, maxHeight: isNarrow ? "auto" : "calc(100vh - 250px)", overflowY: "auto", paddingRight: 4 }}>
              {aggregated.length === 0 && (
                <div style={{
                  color: styles.muted,
                  textAlign: "center",
                  padding: 24,
                  fontSize: 15
                }}>
                  Δεν υπάρχουν πιάτα προς εκτέλεση
                </div>
              )}
              {aggregated.map(entry => (
                <div key={entry.key} style={{
                  background: colors.bg,
                  padding: 16,
                  borderRadius: 12,
                  boxShadow: "0 2px 4px rgba(0,0,0,0.06)",
                  border: `2px solid ${colors.secondary}`,
                  transition: "all 0.2s"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = styles.shadowHover;
                  e.currentTarget.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = "0 2px 4px rgba(0,0,0,0.06)";
                  e.currentTarget.style.transform = "translateY(0)";
                }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                    <div style={{
                      background: colors.primary,
                      color: "#fff",
                      fontSize: 20,
                      fontWeight: 700,
                      width: 48,
                      height: 48,
                      borderRadius: 12,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 2px 6px rgba(0,0,0,0.15)"
                    }}>
                      {entry.qty}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 17, fontWeight: 700, color: styles.text, lineHeight: 1.3 }}>
                        {entry.displayName}
                      </div>
                    </div>
                  </div>
                  <div style={{
                    fontSize: 13,
                    color: styles.muted,
                    background: "rgba(255,255,255,0.7)",
                    padding: "6px 10px",
                    borderRadius: 8,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6
                  }}>
                    <span>🍽️</span>
                    Τραπέζια: {Array.from(entry.tables).sort((a,b) => a-b).join(", ")}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Floating Confirm Button */}
      {Object.keys(checked).length > 0 && (
        <div style={{
          position: "fixed",
          right: 24,
          bottom: 24,
          zIndex: 1000
        }}>
          <button
            onClick={confirmAll}
            style={{
              padding: "16px 32px",
              background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.dark} 100%)`,
              color: "#fff",
              border: "none",
              borderRadius: 16,
              fontSize: 18,
              fontWeight: 700,
              cursor: "pointer",
              boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
              transition: "all 0.3s",
              display: "flex",
              alignItems: "center",
              gap: 12,
              letterSpacing: "0.5px"
            }}
            onMouseEnter={(e) => {
              e.target.style.transform = "translateY(-4px) scale(1.05)";
              e.target.style.boxShadow = "0 12px 32px rgba(0,0,0,0.35)";
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = "translateY(0) scale(1)";
              e.target.style.boxShadow = "0 8px 24px rgba(0,0,0,0.25)";
            }}
          >
            <span style={{ fontSize: 24 }}>✓</span>
            Επιβεβαίωση
            <span style={{
              background: "rgba(255,255,255,0.3)",
              padding: "4px 12px",
              borderRadius: 12,
              fontSize: 16
            }}>
              {Object.keys(checked).length}
            </span>
          </button>
        </div>
      )}
      </div>
    </div>
  );
}

