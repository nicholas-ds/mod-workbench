// The Wake all button: one press asks every idle orchestrator to audit tracking and surface boards.

import { DomBuilder } from "./dom_builder.js";
import { FlashMessage } from "./flash_message.js";

export class WakeButton {
  constructor(api) {
    this._api = api;
  }

  build() {
    const button = DomBuilder.el("button", "clay-button wake-button", "Wake all");
    button.addEventListener("click", () => this._wake(button));
    return button;
  }

  async _wake(button) {
    button.disabled = true;
    try {
      const result = await this._api.wake();
      FlashMessage.shared().confirm(`Woke ${result.woken.length} orchestrators.`);
    } catch (error) {
      FlashMessage.shared().fail(`Wake failed: ${error.message}`);
    } finally {
      button.disabled = false;
    }
  }
}
