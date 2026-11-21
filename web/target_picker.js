// Clay drop-down that picks the pane the author messages. Replaces the native select, which cannot be styled.

import { DomBuilder } from "./dom_builder.js";

export class TargetPicker {
  constructor(onChange) {
    this._onChange = onChange;
    this._names = [];
    this._value = "";
    this.node = DomBuilder.el("button", "dock-target clay-button clay-quiet");
    this.node.type = "button";
    this.node.setAttribute("aria-haspopup", "listbox");
    this.node.setAttribute("aria-label", "Send to");
    this.node.addEventListener("click", () => this._toggleMenu());
    this._menu = DomBuilder.el("div", "target-menu clay-small");
    this._menu.setAttribute("role", "listbox");
    document.addEventListener("pointerdown", (event) => this._closeOnOutside(event));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") this._closeMenu();
    });
  }

  get value() {
    return this._value;
  }

  set value(name) {
    this._value = name;
    this.node.textContent = `to: ${name} ▾`;
  }

  setNames(names) {
    this._names = names;
  }

  _toggleMenu() {
    if (this._menu.isConnected) this._closeMenu();
    else this._openMenu();
  }

  _openMenu() {
    this._menu.replaceChildren(...this._names.map((name) => this._optionNode(name)));
    document.body.appendChild(this._menu);
    const rect = this.node.getBoundingClientRect();
    this._menu.style.left = `${rect.left}px`;
    this._menu.style.top = `${rect.bottom + 8}px`;
    this.node.setAttribute("aria-expanded", "true");
  }

  _closeMenu() {
    this._menu.remove();
    this.node.setAttribute("aria-expanded", "false");
  }

  _closeOnOutside(event) {
    if (!this._menu.isConnected) return;
    if (this._menu.contains(event.target) || this.node.contains(event.target)) return;
    this._closeMenu();
  }

  _optionNode(name) {
    const option = DomBuilder.el("button", "target-option clay-button", name);
    option.type = "button";
    option.setAttribute("role", "option");
    option.setAttribute("aria-pressed", name === this._value ? "true" : "false");
    option.addEventListener("click", () => {
      this.value = name;
      this._closeMenu();
      this._onChange(name);
    });
    return option;
  }
}
