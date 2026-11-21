// The agents card: one row per running agent, workers under the orchestrator that started them.

import { AgentChip } from "./agent_chip.js";
import { DomBuilder } from "./dom_builder.js";
import { ScrollableTable } from "./scrollable_table.js";

const COLUMNS = ["agent", "state", "doing", "tool calls", "age"];

export class AgentsView {
  constructor(table) {
    this._table = table;
  }

  render(agents, modRows = []) {
    const card = DomBuilder.el("article", "clay agents-card");
    card.appendChild(DomBuilder.el("h2", "panel-title", "agents"));
    const chips = this._modChips(agents, modRows);
    if (chips.length > 0) {
      const row = DomBuilder.el("div", "row");
      for (const chip of chips) row.appendChild(chip);
      card.appendChild(row);
    }
    if (agents.length === 0) {
      card.appendChild(DomBuilder.el("p", null, "No agents are running."));
      return card;
    }
    const rows = this._ordered(agents).map((entry) => this._row(entry));
    card.appendChild(ScrollableTable.wrap(this._table.render({ columns: COLUMNS, rows })));
    return card;
  }

  // One chip per mod that has agents in the list.
  _modChips(agents, modRows) {
    return modRows
      .filter((row) => !row.error && agents.some((agent) => AgentChip.covers(row.repo, agent.cwd)))
      .map((row) => AgentChip.build(row, agents));
  }

  _ordered(agents) {
    const parentOf = (agent) => agent.parent_id || agent.orchestrator;
    const known = new Set(agents.map((agent) => agent.agent_id));
    const roots = agents.filter((agent) => !known.has(parentOf(agent)));
    return roots.flatMap((root) => [
      { agent: root, depth: 0 },
      ...agents.filter((agent) => parentOf(agent) === root.agent_id).map((agent) => ({ agent, depth: 1 })),
    ]);
  }

  _row({ agent, depth }) {
    return {
      agent: (depth ? "↳ " : "") + this._name(agent),
      state: agent.shown_state,
      doing: agent.progress ? `${agent.last_tool} · ${agent.progress}` : agent.last_tool,
      "tool calls": agent.tool_calls,
      age: this._age(agent.age_seconds),
    };
  }

  _name(agent) {
    if (agent.title) return agent.title;
    const role = this._role(agent);
    const folder = agent.cwd.split(/[\\/]/).filter(Boolean).pop() ?? "";
    const place = folder === "mods" || folder === "" ? "Main" : folder;
    return `${place} (${role})`;
  }

  _role(agent) {
    if (agent.source !== "claude") return agent.registered ? "worker" : "worker, unregistered";
    return agent.parent_id ? "subagent" : "orchestrator";
  }

  _age(seconds) {
    if (seconds < 60) return `${seconds} s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
    return `${Math.floor(seconds / 3600)} h`;
  }
}
