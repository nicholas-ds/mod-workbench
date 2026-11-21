// The context meter label: shows how full the context window of the showing chat is.

import { DomBuilder } from "./dom_builder.js";

export class ContextMeterLabel {
  constructor() {
    this._node = DomBuilder.el("span", "context-meter");
    this.clear();
  }

  node() {
    return this._node;
  }

  show(percent) {
    if (percent === null || percent === undefined) return this.clear();
    this._node.textContent = `${Math.round(percent)}% context`;
    this._node.title = `${percent.toFixed(1)}% of the context window is in use`;
    this._node.hidden = false;
  }

  clear() {
    this._node.textContent = "";
    this._node.title = "";
    this._node.hidden = true;
  }
}
