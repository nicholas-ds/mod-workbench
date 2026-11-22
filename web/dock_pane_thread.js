// The message thread of a terminal pane: poll its records and render them as dock exchanges.

import { ActivityReader } from "./activity_reader.js";
import { AgentsPill } from "./agents_pill.js";
import { PaneTranscriptSource } from "./pane_transcript_source.js";
import { WorkingPill } from "./working_pill.js";

export class DockPaneThread {
  constructor(api, render, agents, renderer) {
    this._api = api;
    this._render = render;
    this._agents = agents;
    this._source = new PaneTranscriptSource();
    this._renderer = renderer;
  }

  async refresh(paneMod) {
    try {
      const [data, working] = await Promise.all([this._api.messages(paneMod), this._isWorking(paneMod)]);
      const nodes = this._renderer.render(this._source.items(data.messages), paneMod);
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
}
