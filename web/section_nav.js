// The top-level menu in the page header: one button per section of the workbench.

import { DomBuilder } from "./dom_builder.js";

export class SectionNav {
  constructor(parent, sections, onSelect) {
    this._buttons = new Map();
    this._nav = DomBuilder.el("nav", "top-nav");
    this._nav.setAttribute("aria-label", "Sections");
    for (const [id, label] of sections) {
      const button = DomBuilder.el("button", "stage-tab", label);
      button.type = "button";
      button.addEventListener("click", () => onSelect(id));
      this._buttons.set(id, button);
      this._nav.appendChild(button);
    }
    parent.insertBefore(this._nav, parent.querySelector("button"));
  }

  select(id) {
    for (const [key, button] of this._buttons) {
      button.classList.toggle("is-selected", key === id);
      button.setAttribute("aria-current", key === id ? "page" : "false");
    }
  }
}
