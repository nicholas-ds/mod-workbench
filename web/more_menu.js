// The "more" menu in the page header: one button whose panel holds the design button,
// the versions chip and the all-tasks tab. Items keep their own behavior.

import { DomBuilder } from "./dom_builder.js";

export class MoreMenu {
  constructor(parent) {
    this._parent = parent;
    this._button = null;
    this._panel = null;
    this._watchOutside = null;
    this._watchKeys = null;
  }

  start() {
    this._button = DomBuilder.el("button", "clay-button clay-quiet more-button", "more");
    this._button.type = "button";
    this._button.setAttribute("aria-haspopup", "true");
    this._button.setAttribute("aria-expanded", "false");
    this._button.addEventListener("click", () => this._toggle());
    this._panel = DomBuilder.el("div", "more-panel clay-small");
    this._panel.hidden = true;
    this._panel.addEventListener("click", () => this._close());
    document.body.appendChild(this._panel);
    this._parent.appendChild(this._button);
  }

  // Where the menu items live; app.js moves them in.
  host() { return this._panel; }

  // Header chips and pills anchor themselves before the menu button.
  button() { return this._button; }

  _toggle() {
    if (this._panel.hidden) this._open();
    else this._close();
  }

  _open() {
    this._panel.hidden = false;
    this._button.setAttribute("aria-expanded", "true");
    this._watchOutside = (event) => {
      if (!this._panel.contains(event.target) && !this._button.contains(event.target)) this._close();
    };
    this._watchKeys = (event) => {
      if (event.key === "Escape") this._close();
    };
    document.addEventListener("pointerdown", this._watchOutside);
    document.addEventListener("keydown", this._watchKeys);
  }

  _close() {
    if (this._panel.hidden) return;
    this._panel.hidden = true;
    this._button.setAttribute("aria-expanded", "false");
    document.removeEventListener("pointerdown", this._watchOutside);
    document.removeEventListener("keydown", this._watchKeys);
    this._watchOutside = null;
    this._watchKeys = null;
  }
}
