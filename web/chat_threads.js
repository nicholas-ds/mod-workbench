// Per-name chat threads: one thread node per orchestrator name, one shown at a time.

import { AgentsPill } from "./agents_pill.js";
import { DomBuilder } from "./dom_builder.js";
import { WorkingPill } from "./working_pill.js";

export class ChatThreads {
  constructor(transcripts, renderer, agents) {
    this._transcripts = transcripts;
    this._renderer = renderer;
    this._agents = agents;
    this._holder = DomBuilder.el("div", "chat-holder");
    this._threads = new Map();
    this._drawn = new Map(); // chat name -> item count drawn last time
  }

  holder() {
    return this._holder;
  }

  show(name) {
    const thread = this._threadFor(name);
    this._fill(name, thread);
    this._drawn.set(name, this._transcripts.items(name).length);
    this._holder.replaceChildren(thread);
    return thread;
  }

  refresh(name) {
    if (!this._threads.has(name)) return;
    const thread = this._threads.get(name);
    const before = this._drawn.get(name);
    const count = this._transcripts.items(name).length;
    this._fill(name, thread);
    if (before !== undefined && count === before + 1) this._markNewest(thread);
    this._drawn.set(name, count);
    this._scrollToBottom(thread);
  }

  scrollToBottom(name) {
    if (!this._threads.has(name)) return;
    this._scrollToBottom(this._threads.get(name));
  }

  remove(name) {
    this._threads.delete(name);
    this._drawn.delete(name);
  }

  showError(node) {
    const thread = this._newThread();
    thread.appendChild(node);
    this._holder.replaceChildren(thread);
    return thread;
  }

  _fill(name, thread) {
    const messages = this._renderer.render(this._transcripts.items(name), name);
    const pill = WorkingPill.trailing(this._transcripts.isRunning(name), name);
    const agents = AgentsPill.trailing(this._agents.runningFor(name));
    thread.replaceChildren(...messages, ...pill, ...agents);
  }

  _markNewest(thread) {
    thread.lastElementChild?.classList.add("wobble-once");
  }

  _threadFor(name) {
    if (!this._threads.has(name)) this._threads.set(name, this._newThread());
    return this._threads.get(name);
  }

  _scrollToBottom(thread) {
    thread.scrollTop = thread.scrollHeight;
  }

  _newThread() {
    const thread = DomBuilder.el("div", "chat-thread");
    thread.setAttribute("role", "log");
    thread.setAttribute("aria-live", "polite");
    return thread;
  }
}
