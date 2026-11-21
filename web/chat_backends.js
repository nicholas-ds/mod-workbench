// Backend choices of the chat: the traits come from the server, so no code here names a backend.

import { DomBuilder } from "./dom_builder.js";

export class ChatBackends {
  constructor(onFlip) {
    this._onFlip = onFlip;
    this._buttons = new Map();
    this._active = null;
    this._tray = DomBuilder.el("div", "backend-toggle");
  }

  node() {
    return this._tray;
  }

  async load() {
    const response = await fetch("/api/chat/backends");
    if (!response.ok) return;
    const { backends } = await response.json();
    this._tray.replaceChildren();
    this._buttons.clear();
    for (const traits of backends) this._addButton(traits);
    this.setActive(this._active);
  }

  setActive(key) {
    this._active = key;
    for (const [buttonKey, button] of this._buttons) {
      const active = buttonKey === key;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    }
  }

  active() {
    return this._active;
  }

  _addButton(traits) {
    const button = DomBuilder.el("button", "backend-seg", traits.label);
    button.type = "button";
    button.addEventListener("click", () => this._onFlip(traits.key));
    this._buttons.set(traits.key, button);
    this._tray.appendChild(button);
  }
}
