// The versions chip in the page header: counts pending tool updates and lists them in a small panel.

import { DomBuilder } from "./dom_builder.js";

const ARROW = "\u2192";

export class VersionsChip {
  constructor(beforeButton) {
    this._beforeButton = beforeButton;
    this._entries = [];
    this._chip = null;
    this._panel = null;
    this._watchOutside = null;
  }

  async start() {
    try {
      const data = await this._send("GET", "/api/versions");
      this._applyEntries(data.versions);
    } catch {
      // A missing or failing route means no chip; that is fine.
    }
  }

  async _checkAgain() {
    try {
      const data = await this._send("POST", "/api/versions/refresh");
      this._applyEntries(data.versions);
    } catch {
      // Keep the current rows and chip on a failed refresh.
    }
  }

  async _send(method, url) {
    const response = await fetch(url, { method });
    if (!response.ok) throw new Error(`${response.status} ${url}`);
    return response.json();
  }

  _applyEntries(entries) {
    this._entries = entries;
    this._refreshChip();
    if (this._panel) this._fillRows();
  }

  _refreshChip() {
    const count = this._entries.filter((entry) => entry.update_available).length;
    if (count === 0) {
      this._removeChip();
      return;
    }
    if (!this._chip) {
      this._chip = DomBuilder.el("button", "clay-button clay-quiet versions-chip");
      this._chip.type = "button";
      this._chip.addEventListener("click", () => this._togglePanel());
      this._beforeButton.before(this._chip);
    }
    this._chip.textContent = `updates: ${count}`;
  }

  _removeChip() {
    if (!this._chip) return;
    this._chip.remove();
    this._chip = null;
    this._closePanel();
  }

  _togglePanel() {
    if (this._panel) this._closePanel();
    else this._openPanel();
  }

  _openPanel() {
    this._panel = DomBuilder.el("div", "versions-panel clay-small");
    this._fillRows();
    document.body.appendChild(this._panel);
    this._watchOutside = (event) => {
      if (!this._panel.contains(event.target) && !this._chip.contains(event.target)) this._closePanel();
    };
    document.addEventListener("pointerdown", this._watchOutside);
  }

  _closePanel() {
    if (!this._panel) return;
    this._panel.remove();
    this._panel = null;
    document.removeEventListener("pointerdown", this._watchOutside);
    this._watchOutside = null;
  }

  _fillRows() {
    this._panel.textContent = "";
    for (const entry of this._entries) this._panel.appendChild(this._row(entry));
    const check = DomBuilder.el("button", "clay-button clay-quiet", "check again");
    check.type = "button";
    check.addEventListener("click", () => this._checkAgain());
    this._panel.appendChild(check);
  }

  _row(entry) {
    const row = DomBuilder.el("div", "versions-row");
    if (entry.update_available) row.classList.add("is-update");
    row.appendChild(DomBuilder.el("span", "versions-name", entry.name));
    row.appendChild(DomBuilder.el("span", "versions-installed", entry.installed));
    row.appendChild(DomBuilder.el("span", "versions-arrow", ARROW));
    row.appendChild(DomBuilder.el("span", "versions-latest", entry.latest));
    if (entry.note) row.appendChild(DomBuilder.el("span", "versions-note", entry.note));
    return row;
  }
}
