// Pinning of notes on whiteboard items: a click opens a note box at that spot
// and posts it to the notes route.

import { DomBuilder } from "./dom_builder.js";
import { FlashMessage } from "./flash_message.js";

export class NotePinner {
  constructor(api, mod, id) {
    this._api = api;
    this._mod = mod;
    this._id = id;
    this._box = null;
  }

  attach(element, item, onSave) {
    element.addEventListener("click", (event) => this._start(element, item, onSave, event));
  }

  _start(element, item, onSave, event) {
    this._dismiss();
    const spot = this._spot(element, event);
    this._box = this._noteBox(item, spot, onSave);
    element.appendChild(this._box);
    this._box.querySelector("textarea").focus();
  }

  _spot(element, event) {
    const bounds = element.getBoundingClientRect();
    return {
      left: `${event.clientX - bounds.left}px`,
      top: `${event.clientY - bounds.top}px`,
      x: (event.clientX - bounds.left) / bounds.width,
      y: (event.clientY - bounds.top) / bounds.height,
    };
  }

  _noteBox(item, spot, onSave) {
    const box = DomBuilder.el("div", "clay-small note-box");
    box.style.left = spot.left;
    box.style.top = spot.top;
    box.addEventListener("click", (event) => event.stopPropagation());
    const field = document.createElement("textarea");
    field.className = "clay-field";
    field.placeholder = "note";
    field.rows = 3;
    field.addEventListener("keydown", (event) => {
      if (event.key === "Escape") this._dismiss();
    });
    box.appendChild(field);
    box.appendChild(this._actions(field, item, spot, onSave));
    return box;
  }

  _actions(field, item, spot, onSave) {
    const row = DomBuilder.el("div", "note-actions");
    row.appendChild(this._action("save", "clay-button clay-action", () => {
      this._save(field, item, spot, onSave);
    }));
    row.appendChild(this._action("cancel", "clay-button clay-quiet", () => this._dismiss()));
    return row;
  }

  _action(label, className, onClick) {
    const button = DomBuilder.el("button", className, label);
    button.type = "button";
    button.addEventListener("click", onClick);
    return button;
  }

  async _save(field, item, spot, onSave) {
    const text = field.value.trim();
    if (!text) return this._dismiss();
    try {
      const result = await this._api.note(this._mod, this._id, { item: item.file, x: spot.x, y: spot.y, text });
      this._dismiss();
      onSave();
      this._flashResult(result);
    } catch (error) {
      this._report(String(error));
    }
  }

  _flashResult(result) {
    if (result.notified) {
      FlashMessage.shared().confirm("Note sent. The agent was told.");
    } else {
      FlashMessage.shared().fail("Note saved, but the agent was not told. No pane is registered for it.");
    }
  }

  _report(message) {
    if (!this._box) return;
    const line = DomBuilder.el("span", "note-error", message);
    this._box.appendChild(line);
  }

  _dismiss() {
    if (!this._box) return;
    this._box.remove();
    this._box = null;
  }
}
