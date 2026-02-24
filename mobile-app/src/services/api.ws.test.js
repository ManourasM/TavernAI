import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createWS } from './api';

class MockWebSocket {
  static instances = [];

  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    this.onopen = null;
    this.onmessage = null;
    this.onclose = null;
    this.onerror = null;
    MockWebSocket.instances.push(this);
  }

  send() {}

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose({ reason: 'closed' });
    }
  }

  triggerOpen() {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) this.onopen({});
  }

  triggerClose() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) this.onclose({ reason: 'test-close' });
  }
}
MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSED = 3;

function mockFetchWithConfig(extraHandler = null) {
  global.fetch = vi.fn(async (url) => {
    const u = String(url);
    if (u.includes('/config')) {
      return {
        ok: true,
        json: async () => ({
          backend_base: 'http://localhost:8000',
          ws_base: 'ws://localhost:8000',
          backend_port: 8000
        })
      };
    }
    if (extraHandler) {
      return extraHandler(u);
    }
    return { ok: true, json: async () => ({}) };
  });
}

describe('createWS reconnect sync', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    global.WebSocket = MockWebSocket;
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('calls onSync on open and reconnect', async () => {
    mockFetchWithConfig();

    const onSync = vi.fn();
    const ws = createWS('waiter', () => {}, () => {}, { onSync });

    expect(MockWebSocket.instances.length).toBe(1);
    MockWebSocket.instances[0].triggerOpen();

    await Promise.resolve();
    expect(onSync).toHaveBeenCalledTimes(1);
    expect(onSync.mock.calls[0][0]).toMatchObject({ station: 'waiter', isReconnect: false });

    MockWebSocket.instances[0].triggerClose();
    vi.advanceTimersByTime(1600);

    expect(MockWebSocket.instances.length).toBe(2);
    MockWebSocket.instances[1].triggerOpen();

    await Promise.resolve();
    expect(onSync).toHaveBeenCalledTimes(2);
    expect(onSync.mock.calls[1][0]).toMatchObject({ station: 'waiter', isReconnect: true });

    ws.close();
  });

  it('refreshes local state from server after reconnect', async () => {
    const responses = [
      { '1': [{ id: 'a', table: 1 }] },
      { '2': [{ id: 'b', table: 2 }] }
    ];

    mockFetchWithConfig((url) => {
      if (url.includes('/orders/')) {
        const data = responses.shift() || {};
        return { ok: true, json: async () => data };
      }
      return { ok: true, json: async () => ({}) };
    });

    let state = null;
    const onSync = async () => {
      const res = await fetch('/orders/');
      state = await res.json();
    };

    const ws = createWS('waiter', () => {}, () => {}, { onSync });

    MockWebSocket.instances[0].triggerOpen();
    await Promise.resolve();
    expect(state).toEqual({ '1': [{ id: 'a', table: 1 }] });

    MockWebSocket.instances[0].triggerClose();
    vi.advanceTimersByTime(1600);
    MockWebSocket.instances[1].triggerOpen();
    await Promise.resolve();

    expect(state).toEqual({ '2': [{ id: 'b', table: 2 }] });

    ws.close();
  });
});
