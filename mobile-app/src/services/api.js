// src/api.js
// Robust API client that:
//  - autodiscovers backend via /config (if available)
//  - builds HTTP endpoints from discovered backend_base
//  - builds WS endpoints from discovered ws_base
//  - provides resilient WebSocket client with auto-reconnect + send queue
//
// Improvements:
//  - if /config returns localhost/127.0.0.1 but the page is loaded from a LAN IP,
//    replace the host with location.hostname so phones can reach backend.
//  - extra debug logging and a refreshConfig() helper.

let _configCache = null;
let _configPromise = null;

/**
 * Try to fetch /config from the same origin first, then fallback to common places.
 * Returns { backend_base, ws_base, backend_port } (strings)
 */
export async function refreshConfig() {
  _configCache = null;
  _configPromise = null;
  return await getConfig();
}

async function getConfig() {
  console.log("[getConfig] called, cache exists?", !!_configCache, "promise exists?", !!_configPromise);
  if (_configCache) {
    console.log("[getConfig] returning cached config:", _configCache);
    return _configCache;
  }
  if (_configPromise) {
    console.log("[getConfig] returning existing promise");
    return _configPromise;
  }

  _configPromise = (async () => {
    const tries = [
      // relative (works when frontends are proxied by vite to backend)
      "/config",
      // common dev fallback: try page host with backend port 8000
      `${location.protocol}//${location.hostname}:8000/config`
    ];

    for (const url of tries) {
      try {
        console.log("[config] trying", url);
        const res = await fetch(url, { cache: "no-store" });
        console.log("[config] response from", url, "status:", res.status);
        if (res.ok) {
          const j = await res.json();
          console.log("[config] got config:", j);
          const raw_backend_base = j.backend_base || "";
          const raw_ws_base = j.ws_base || null;
          const port = j.backend_port || (raw_backend_base ? (new URL(raw_backend_base)).port : 8000);

          // normalize fields
          let backend_base = raw_backend_base.replace(/\/+$/, "");
          let ws_base = raw_ws_base ? raw_ws_base.replace(/\/+$/, "") : null;

          // Heuristic: if backend_base host is localhost/127.0.0.1 but the UI is accessed
          // via a different hostname (e.g. 192.168.x.y), replace the host so frontends can reach backend.
          try {
            if (backend_base) {
              const parsed = new URL(backend_base);
              const hostIsLocal = ["localhost", "127.0.0.1", ""].includes(parsed.hostname);
              const pageHost = location.hostname;
              const pageIsLAN = pageHost && pageHost !== "localhost" && pageHost !== "127.0.0.1";
              if (hostIsLocal && pageIsLAN) {
                console.debug("[config] replacing localhost in backend_base with page host:", pageHost);
                parsed.hostname = pageHost;
                // keep port from parsed (if any) or fallback to original port
                if (!parsed.port) parsed.port = String(port || 8000);
                backend_base = parsed.toString().replace(/\/+$/, "");
              }
            }
            if (ws_base) {
              const parsedWs = new URL(ws_base);
              const wsHostIsLocal = ["localhost", "127.0.0.1", ""].includes(parsedWs.hostname);
              const pageHost = location.hostname;
              const pageIsLAN = pageHost && pageHost !== "localhost" && pageHost !== "127.0.0.1";
              if (wsHostIsLocal && pageIsLAN) {
                console.debug("[config] replacing localhost in ws_base with page host:", pageHost);
                parsedWs.hostname = pageHost;
                if (!parsedWs.port) parsedWs.port = String(port || 8000);
                ws_base = parsedWs.toString().replace(/\/+$/, "");
              }
            }
          } catch (e) {
            console.warn("[config] host replace heuristic failed, keeping raw values", e);
          }

          _configCache = {
            backend_base: backend_base || `${location.protocol}//${location.host}`,
            ws_base: ws_base || `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}`,
            backend_port: port || (location.port ? Number(location.port) : 8000)
          };
          console.log("[config] ✅ resolved:", _configCache);
          return _configCache;
        } else {
          console.log("[config] ❌ not ok:", url, res.status);
        }
      } catch (e) {
        console.log("[config] ❌ fetch failed for", url, e.message);
      }
    }

    // final fallback: use page origin (relative)
    const fallback = {
      backend_base: `${location.protocol}//${location.host}`,
      ws_base: `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}`,
      backend_port: location.port ? Number(location.port) : 80
    };
    console.log("[config] ⚠️ falling back to page origin:", fallback);
    _configCache = fallback;
    return _configCache;
  })();

  try {
    const result = await _configPromise;
    console.log("[config] final result:", result);
    return result;
  } catch (e) {
    console.error("[config] ERROR:", e);
    // Return a basic fallback even if promise fails
    const emergencyFallback = {
      backend_base: `${location.protocol}//${location.host}`,
      ws_base: `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}`,
      backend_port: location.port ? Number(location.port) : 80
    };
    _configCache = emergencyFallback;
    return emergencyFallback;
  }
}

function ensureLeadingSlash(path) {
  if (!path) return "/";
  return path.startsWith("/") ? path : "/" + path;
}

async function buildHttpUrl(path) {
  console.log("[buildHttpUrl] getting config for path:", path);
  console.log("[buildHttpUrl] about to call getConfig()");
  const cfg = await getConfig();
  console.log("[buildHttpUrl] getConfig() returned:", cfg);
  const base = (cfg && cfg.backend_base) ? String(cfg.backend_base).replace(/\/$/, "") : "";
  console.log("[buildHttpUrl] base:", base);
  const url = `${base}${ensureLeadingSlash(path)}`;
  console.log("[buildHttpUrl] built URL:", url);
  return url;
}

async function buildWsUrl(station) {
  const cfg = await getConfig();
  if (cfg && cfg.ws_base) {
    return `${String(cfg.ws_base).replace(/\/$/, "")}/ws/${station}`;
  }
  // fallback to same-origin
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}/ws/${station}`;
}

/* ---------------------------
   HTTP API helpers (async)
   ---------------------------*/

export async function postOrder(table, orderText, people = null, bread = false) {
  console.log("[api.postOrder] START", { table, orderText, people, bread });
  const payload = { table, order_text: orderText };
  if (people !== null) payload.people = people;
  payload.bread = !!bread;
  console.log("[api.postOrder] payload created:", payload);

  console.log("[api.postOrder] calling buildHttpUrl...");
  const url = await buildHttpUrl("/order/");
  console.log("[api.postOrder] got URL:", url);

  console.log("[api] POST", url, payload);
  console.log("[api.postOrder] calling fetch...");
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  console.log("[api.postOrder] fetch completed");
  console.log("[api] POST response status:", res.status, res.statusText);
  if (!res.ok) {
    const errorText = await res.text();
    console.error("[api] POST failed:", res.status, errorText);
    throw new Error(`HTTP ${res.status}: ${errorText}`);
  }
  const result = await res.json();
  console.log("[api] POST result:", result);
  return result;
}

export async function putOrder(table, orderText, people = null, bread = false) {
  const payload = { table, order_text: orderText };
  if (people !== null) payload.people = people;
  payload.bread = !!bread;
  const url = await buildHttpUrl(`/order/${table}`);
  console.log("[api] PUT", url, payload);
  const res = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  console.log("[api] PUT response status:", res.status, res.statusText);
  if (!res.ok) {
    const errorText = await res.text();
    console.error("[api] PUT failed:", res.status, errorText);
    throw new Error(`HTTP ${res.status}: ${errorText}`);
  }
  const result = await res.json();
  console.log("[api] PUT result:", result);
  return result;
}

export async function getOrders(includeHistory = false) {
  const qs = includeHistory ? "?include_history=true" : "";
  const url = await buildHttpUrl(`/orders/${qs}`);
  console.debug("[api] GET", url);
  const res = await fetch(url);
  return await res.json();
}

export async function getTableMeta(table) {
  const url = await buildHttpUrl(`/table_meta/${table}`);
  console.debug("[api] GET meta", url);
  const res = await fetch(url);
  if (!res.ok) return { people: null, bread: false };
  return await res.json();
}

export async function markDone(itemId) {
  const url = await buildHttpUrl(`/item/${itemId}/done`);
  console.debug("[api] POST markDone", url);
  const res = await fetch(url, { method: "POST" });
  return await res.json();
}

/* ---------------------------
   Resilient WebSocket wrapper
   - auto-reconnect
   - outgoing queue while disconnected
   - onOpen/onMessage handlers
   ---------------------------*/

export function createWS(station, onMessage, onOpen) {
  let ws = null;
  let closedByUser = false;
  let isConnecting = false;
  const outgoingQueue = []; // buffered messages while not connected
  let reconnectTimer = null;

  async function resolveWsUrl() {
    try {
      return await buildWsUrl(station);
    } catch (e) {
      // fallback
      const proto = location.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${location.host}/ws/${station}`;
    }
  }

  async function flushQueue() {
    while (outgoingQueue.length > 0 && ws && ws.readyState === WebSocket.OPEN) {
      const msg = outgoingQueue.shift();
      try {
        ws.send(JSON.stringify(msg));
        console.debug("[WS] flushed msg", msg);
      } catch (e) {
        console.error("[WS] send during flush failed, pushing back to queue", e, msg);
        outgoingQueue.unshift(msg);
        break;
      }
    }
  }

  async function connect() {
    if (closedByUser) return;
    if (isConnecting) return;
    isConnecting = true;

    const wsUrl = await resolveWsUrl();
    console.debug("[WS] connecting to", wsUrl, "for station", station);
    try {
      ws = new WebSocket(wsUrl);
    } catch (e) {
      console.warn("[WS] WebSocket construction failed, scheduling reconnect", e, wsUrl);
      isConnecting = false;
      scheduleReconnect();
      return;
    }

    ws.onopen = (ev) => {
      console.debug("[WS] open", station, ev);
      isConnecting = false;
      if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
      try { if (onOpen) onOpen(ev); } catch (e) { console.error("[WS] onOpen handler error", e); }
      flushQueue();
    };

    ws.onmessage = (evt) => {
      let parsed = null;
      try {
        parsed = JSON.parse(evt.data);
      } catch (e) {
        console.warn("[WS] Failed to parse message", e, evt.data);
        return;
      }
      try { if (onMessage) onMessage(parsed); } catch (e) { console.error("[WS] onMessage handler error", e, parsed); }
    };

    ws.onclose = (ev) => {
      console.debug("[WS] closed", station, ev);
      isConnecting = false;
      ws = null;
      if (!closedByUser) scheduleReconnect();
      // inform onMessage optionally
      try { if (onMessage) onMessage({ action: "ws_closed", reason: ev.reason || null }); } catch (e) {}
    };

    ws.onerror = (err) => {
      console.warn("[WS] error", station, err);
      // onclose will follow — let it schedule reconnect
    };
  }

  function scheduleReconnect(delay = 1500) {
    if (closedByUser) return;
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, delay);
  }

  // start initial connect (no await)
  connect();

  return {
    send: (obj) => {
      try {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(obj));
          console.debug("[WS] sent", obj);
        } else {
          // buffer the message for later
          outgoingQueue.push(obj);
          console.warn("[WS] not open: buffering message", obj);
          // ensure we try to connect
          scheduleReconnect(500);
          // also kick off connect if we don't have an active ws or ongoing connect
          if (!ws && !isConnecting) connect();
        }
      } catch (e) {
        console.error("[WS] send failed", e, obj);
        outgoingQueue.push(obj);
        scheduleReconnect(500);
      }
    },
    close: () => {
      closedByUser = true;
      try { if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; } } catch (e) {}
      try { if (ws) ws.close(); } catch (e) {}
      ws = null;
    }
  };
}
