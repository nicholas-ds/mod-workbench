// One row of thread tabs for one orchestrator: the main chat plus one tab per thread.

import { DomBuilder } from "./dom_builder.js";

export class ThreadTabs {
  constructor(chatStream, onSelect, onClose = null) {
    this._chatStream = chatStream;
    this._onSelect = onSelect;
    this._onClose = onClose;
    this._orchestrator = null;
    this._threads = [];
    this._selected = null;
    this._row = DomBuilder.el("div", "thread-tabs");
  }

  node() {
    return this._row;
  }

  selectedName() {
    return this._selected;
  }

  async load(orchestrator) {
    this._orchestrator = orchestrator;
    await this._fetchThreads();
    this._select(this._initialName());
    this._rebuild();
  }

  async _fetchThreads() {
    try {
      this._threads = await this._chatStream.threads(this._orchestrator);
    } catch {
      this._threads = [];
    }
  }

  _initialName() {
    const valid = new Set([this._orchestrator, ...this._threads.map((thread) => thread.name)]);
    return [this._selected, this._storedName()].find((name) => name && valid.has(name)) ?? this._orchestrator;
  }

  _select(chatName) {
    this._selected = chatName;
    try { localStorage.setItem(`wb-chat-thread-${this._orchestrator}`, chatName); } catch {}
  }

  _storedName() {
    try { return localStorage.getItem(`wb-chat-thread-${this._orchestrator}`); } catch { return null; }
  }

  _rebuild() {
    this._row.replaceChildren(this._segment(this._orchestrator, "main"));
    for (const thread of this._threads) this._row.append(this._segment(thread.name, thread.label, thread));
    this._row.append(this._addButton());
  }

  _segment(chatName, text, thread = null) {
    const segment = DomBuilder.el("span", "thread-seg");
    segment.classList.toggle("is-selected", chatName === this._selected);
    segment.append(this._tab(chatName, text, thread));
    if (thread) segment.append(this._closeButton(thread));
    return segment;
  }

  _tab(chatName, text, thread = null) {
    const button = DomBuilder.el("button", "thread-tab", text);
    button.type = "button";
    if (thread?.mark) button.dataset.mark = thread.mark;
    if (chatName === this._selected) button.setAttribute("aria-current", "true");
    button.addEventListener("click", () => this._tabClicked(chatName));
    return button;
  }

  _closeButton(thread) {
    const button = DomBuilder.el("button", "thread-tab-close", "×");
    button.type = "button";
    button.title = "Close thread";
    button.setAttribute("aria-label", `Close ${thread.label}`);
    button.addEventListener("click", () => this._removeClicked(thread));
    return button;
  }

  _addButton() {
    const button = DomBuilder.el("button", "thread-tab-add", "+");
    button.type = "button";
    button.setAttribute("aria-label", "New thread");
    button.addEventListener("click", () => this._addClicked());
    return button;
  }

  _tabClicked(chatName) {
    this._select(chatName);
    this._rebuild();
    this._onSelect(chatName);
  }

  async _addClicked() {
    const thread = await this._chatStream.addThread(this._orchestrator);
    await this._fetchThreads();
    this._select(thread.name);
    this._rebuild();
    this._onSelect(this._selected);
  }

  async _removeClicked(thread) {
    const wasSelected = this._selected === thread.name;
    await this._chatStream.removeThread(this._orchestrator, thread.thread_id);
    if (this._onClose) this._onClose(thread.name);
    await this._fetchThreads();
    if (wasSelected) this._select(this._orchestrator);
    this._rebuild();
    if (wasSelected) this._onSelect(this._orchestrator);
  }
}
