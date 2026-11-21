// Shared chat transcript store: per-orchestrator items and running flag, with listeners.

const DEFAULT_TEXT = "";
const DEFAULT_DETAIL = "";
const DEFAULT_SETTLED = "";
const PERMISSION_KIND = "permission";

export class ChatTranscripts {
  constructor() {
    this._items = new Map();
    this._running = new Map();
    this._listeners = new Set();
  }

  items(name) {
    return [...this._itemsFor(name)];
  }

  add(name, item) {
    this._itemsFor(name).push({
      kind: item.kind,
      text: item.text ?? DEFAULT_TEXT,
      detail: item.detail ?? DEFAULT_DETAIL,
      settled: item.settled ?? DEFAULT_SETTLED,
    });
    this._notify(name);
  }

  settle(name, requestId, outcome) {
    const item = this._itemsFor(name)
      .find((item) => item.kind === PERMISSION_KIND && item.detail === requestId);
    if (!item) return;
    item.settled = outcome;
    this._notify(name);
  }

  clear(name) {
    this._items.set(name, []);
    this._notify(name);
  }

  drop(name) {
    this._items.delete(name);
    this._running.delete(name);
    this._notify(name);
  }

  dropAfterLastUser(name) {
    const items = this._itemsFor(name);
    const last = items.map((item) => item.kind).lastIndexOf("user");
    if (last === -1) return;
    this._items.set(name, items.slice(0, last + 1));
    this._notify(name);
  }

  isRunning(name) {
    return this._running.get(name) ?? false;
  }

  runningNames() {
    return [...this._running].filter(([, running]) => running).map(([name]) => name);
  }

  setRunning(name, running) {
    this._running.set(name, running);
    this._notify(name);
  }

  subscribe(listener) {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  _itemsFor(name) {
    if (!this._items.has(name)) this._items.set(name, []);
    return this._items.get(name);
  }

  _notify(name) {
    for (const listener of this._listeners) listener(name);
  }
}
