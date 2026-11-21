// The message thread of a terminal pane: poll its messages and build one exchange node per message.

import { ActivityReader } from "./activity_reader.js";
import { AgentsPill } from "./agents_pill.js";
import { DomBuilder } from "./dom_builder.js";
import { WorkingPill } from "./working_pill.js";

export class DockPaneThread {
  constructor(api, render, agents) {
    this._api = api;
    this._render = render;
    this._agents = agents;
  }

  async refresh(paneMod) {
    try {
      const [data, working] = await Promise.all([this._api.messages(paneMod), this._isWorking(paneMod)]);
      const nodes = data.messages.map((message) => this._messageNode(message));
      const agents = AgentsPill.trailing(this._agents.runningFor(paneMod));
      this._render([...nodes, ...WorkingPill.trailing(working, paneMod), ...agents]);
    } catch {
      // A failed poll keeps the current thread; only a failed send reports.
    }
  }

  async _isWorking(paneMod) {
    try {
      const { rows } = await this._api.mods();
      const row = rows.find((entry) => entry.name === paneMod);
      return row !== undefined && ActivityReader.read(row).working;
    } catch {
      return false;
    }
  }

  _messageNode(message) {
    const exchange = DomBuilder.el("div", "dock-exchange");
    exchange.appendChild(DomBuilder.el("div", "dock-message", message.text));
    if (message.reply != null) exchange.appendChild(DomBuilder.el("div", "dock-reply", message.reply));
    return exchange;
  }
}
