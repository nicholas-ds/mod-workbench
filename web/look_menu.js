// One header button ("design") that opens a small panel: pick the theme (classic or calm) and switch greyscale on or off.

import { DomBuilder } from "./dom_builder.js";

const THEME_KEY = "wb-theme";
const GREY_KEY = "wb-grey";
const THEMES = ["classic", "calm"];

export class LookMenu {
  constructor(button) {
    this._button = button;
    this._panel = null;
    this._watchOutside = null;
  }

  start() {
    this._applyTheme(this._storedTheme());
    this._applyGrey(localStorage.getItem(GREY_KEY) === "1");
    this._button.setAttribute("aria-haspopup", "true");
    this._button.addEventListener("click", () => (this._panel ? this._close() : this._open()));
  }

  _storedTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    return THEMES.includes(saved) ? saved : THEMES[0];
  }

  _applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }

  _applyGrey(on) {
    document.documentElement.dataset.grey = on ? "1" : "0";
    if (on) localStorage.setItem(GREY_KEY, "1");
    else localStorage.removeItem(GREY_KEY);
  }

  _open() {
    this._panel = DomBuilder.el("div", "look-panel clay-small");
    this._fill();
    document.body.appendChild(this._panel);
    this._button.setAttribute("aria-expanded", "true");
    this._watchOutside = (event) => {
      if (!this._panel.contains(event.target) && !this._button.contains(event.target)) this._close();
    };
    document.addEventListener("pointerdown", this._watchOutside);
  }

  _close() {
    document.removeEventListener("pointerdown", this._watchOutside);
    this._panel.remove();
    this._panel = null;
    this._button.setAttribute("aria-expanded", "false");
  }

  _fill() {
    const theme = document.documentElement.dataset.theme;
    const grey = document.documentElement.dataset.grey === "1";
    const options = THEMES.map((name) => this._option(name, name === theme, () => this._applyTheme(name)));
    options.push(this._option("greyscale", grey, () => this._applyGrey(!grey)));
    this._panel.replaceChildren(...options);
  }

  _option(label, pressed, onChoose) {
    const option = DomBuilder.el("button", "clay-button clay-quiet", label);
    option.type = "button";
    option.setAttribute("aria-pressed", pressed ? "true" : "false");
    option.addEventListener("click", () => { onChoose(); this._fill(); });
    return option;
  }
}
