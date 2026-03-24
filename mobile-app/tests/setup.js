// Test setup: polyfill browser APIs not available in jsdom

// ResizeObserver is used by recharts' ResponsiveContainer.
// Provide a mock that immediately fires with a fixed 600×300 rect so
// charts render their SVG content during tests.
global.ResizeObserver = class ResizeObserver {
  constructor(cb) {
    this.cb = cb;
  }
  observe(el) {
    this.cb([{ contentRect: { width: 600, height: 300 }, target: el }], this);
  }
  unobserve() {}
  disconnect() {}
};
