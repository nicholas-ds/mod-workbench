// Delivery strip for one board: one chip per sent answer, polled from the server.

import { DomBuilder } from "./dom_builder.js";

const POLL_MS = 15000;
const MAX_ROWS = 5;

const NOTES = {
  delivered: "The agent got the answer in its pane or chat.",
  fresh_started:
    "The source chat was above 25% context. The server started a new session with the handoff and the answer file.",
  pending: "The pane is busy or not found yet. The server retries every 30 seconds.",
  failed: "Every retry failed. Press Retry. The answer stays safe in the inbox.",
  unknown_owner:
    "The board named an unknown owner. The server sent the answer to the mod orchestrator instead."
};

export class DeliveryChips {
  constructor(api, mod, boardId) {
    this._api = api;
    this._mod = mod;
    this._boardId = boardId;
    this._root = DomBuilder.el("section", "delivery-chips");
    this._root.setAttribute("hidden", "");
    this._timer = null;
  }

  render() {
    return this._root;
  }

  start() {
    this._reload();
    this._timer = setInterval(() => this._reload(), POLL_MS);
  }

  stop() {
    if (this._timer !== null) {
      clearInterval(this._timer);
      this._timer = null;
    }
  }

  async _reload() {
    try {
      const data = await this._api.notices(this._mod);
      this._draw(data.notices);
    } catch (error) {
      // A failed load keeps the old rows.
    }
  }

  _draw(notices) {
    const rows = notices
      .filter((notice) => notice.board === this._boardId)
      .slice(0, MAX_ROWS)
      .map((notice) => this._row(notice));
    this._root.replaceChildren(...rows);
    if (rows.length === 0) this._root.setAttribute("hidden", "");
    else this._root.removeAttribute("hidden");
  }

  _row(notice) {
    const row = DomBuilder.el("div", "delivery-row");
    const state = notice.state.replace("_", "-");
    row.appendChild(DomBuilder.el("span", `delivery-chip delivery-${state}`, notice.label));
    if (notice.state === "failed") row.appendChild(this._retryButton(notice));
    row.appendChild(DomBuilder.el("span", "delivery-note", NOTES[notice.state] || ""));
    return row;
  }

  _retryButton(notice) {
    const button = DomBuilder.el("button", "clay-button delivery-retry", "Retry");
    button.type = "button";
    button.addEventListener("click", () => this._retry(button, notice));
    return button;
  }

  async _retry(button, notice) {
    button.disabled = true;
    try {
      await this._api.retryNotice(this._mod, notice.notice_id);
      await this._reload();
    } catch (error) {
      button.disabled = false;
      const note = button.parentElement.querySelector(".delivery-note");
      if (note) note.textContent = String(error);
    }
  }
}
