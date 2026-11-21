// The handoff chip in the page header: counts waiting research handoff items and lists them in a small panel.

import { DomBuilder } from "./dom_builder.js";
import { FlashMessage } from "./flash_message.js";

const RELOAD_MS = 30000;

export class HandoffChip {
  constructor(api, beforeButton) {
    this._api = api;
    this._beforeButton = beforeButton;
    this._rows = [];
    this._total = 0;
    this._chip = null;
    this._panel = null;
    this._watchOutside = null;
    this._watchKeys = null;
  }

  async start() {
    await this._reload();
    this._timer = setInterval(() => this._reload(), RELOAD_MS);
  }

  async _reload() {
    try {
      const data = await this._api.handoff();
      this._applyRows(data.rows, data.total);
    } catch {
      // A failed load keeps the old state: the chip stays as it is.
    }
  }

  _applyRows(rows, total) {
    this._rows = rows;
    this._total = total;
    this._refreshChip();
    if (this._panel) this._fillRows();
  }

  _refreshChip() {
    if (this._total === 0) {
      this._removeChip();
      return;
    }
    if (!this._chip) {
      this._chip = DomBuilder.el("button", "clay-button clay-quiet handoff-chip", "handoff 0");
      this._chip.type = "button";
      this._chip.setAttribute("aria-haspopup", "true");
      this._chip.addEventListener("click", () => this._togglePanel());
      this._beforeButton.before(this._chip);
    }
    this._chip.textContent = `handoff ${this._total}`;
    this._chip.setAttribute("aria-expanded", this._panel ? "true" : "false");
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
    this._panel = DomBuilder.el("div", "handoff-panel clay-small");
    this._fillRows();
    document.body.appendChild(this._panel);
    this._watchOutside = (event) => {
      if (!this._panel.contains(event.target) && !this._chip.contains(event.target)) this._closePanel();
    };
    this._watchKeys = (event) => {
      if (event.key === "Escape") this._closePanel();
    };
    document.addEventListener("pointerdown", this._watchOutside);
    document.addEventListener("keydown", this._watchKeys);
    this._chip.setAttribute("aria-expanded", "true");
  }

  _closePanel() {
    if (!this._panel) return;
    this._panel.remove();
    this._panel = null;
    document.removeEventListener("pointerdown", this._watchOutside);
    document.removeEventListener("keydown", this._watchKeys);
    this._watchOutside = null;
    this._watchKeys = null;
    if (this._chip) this._chip.setAttribute("aria-expanded", "false");
  }

  _fillRows() {
    this._panel.textContent = "";
    this._panel.appendChild(DomBuilder.el("h3", "panel-title", "Research handoff"));
    for (const row of this._rows) this._panel.appendChild(this._row(row));
  }

  _row(row) {
    const node = DomBuilder.el("div", "handoff-row");
    node.appendChild(DomBuilder.el("span", "handoff-label", row.label));
    node.appendChild(DomBuilder.el("span", "handoff-count", this._countText(row)));
    const ask = DomBuilder.el("button", "clay-button handoff-ask", `Ask ${row.label}`);
    ask.type = "button";
    ask.addEventListener("click", () => this._ask(row, ask));
    node.appendChild(ask);
    const items = DomBuilder.el("ul", "handoff-items");
    for (const item of row.items) items.appendChild(DomBuilder.el("li", "", item));
    node.appendChild(items);
    return node;
  }

  _countText(row) {
    const n = row.items.length;
    const plural = n === 1 ? "" : "s";
    if (row.kind === "files") return `${n} file${plural} not picked up`;
    return `${n} open request${plural}`;
  }

  async _ask(row, ask) {
    ask.disabled = true;
    try {
      await this._api.nudgeHandoff(row.kind, row.target);
      FlashMessage.shared().confirm(`Asked ${row.label}.`);
    } catch (error) {
      FlashMessage.shared().fail(`Ask failed: ${error.message}`);
    } finally {
      ask.disabled = false;
    }
  }
}
