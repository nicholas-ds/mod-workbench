// Per-mod status tables: one card per mod, one row per workspace.

import { AgentChip } from "./agent_chip.js";
import { DomBuilder } from "./dom_builder.js";
import { ScrollableTable } from "./scrollable_table.js";
import { TableView } from "./table_view.js";

// Shown on the mod rail, not as table columns.
const RAIL_KEYS = ["activity", "activity_at", "task"];

export class StatusView {
  constructor(table) {
    this._table = table;
  }

  render(modRows, agents = []) {
    const section = DomBuilder.el("section", "status");
    section.appendChild(DomBuilder.el("h2", "panel-title", "status"));
    for (const row of modRows) {
      section.appendChild(this._mod(row, agents));
    }
    return section;
  }

  _mod(row, agents) {
    const card = DomBuilder.el("article", "clay status-mod");
    card.appendChild(this._title(row, agents));
    card.appendChild(this._body(row));
    return card;
  }

  _title(row, agents) {
    const title = DomBuilder.el("h3");
    if (row.error) {
      title.textContent = row.repo;
      return title;
    }
    title.appendChild(AgentChip.build(row, agents));
    return title;
  }

  _body(row) {
    if (row.error) return DomBuilder.el("p", null, row.error);
    if (!row.status?.length) return DomBuilder.el("p", null, "No status files yet.");
    return ScrollableTable.wrap(this._table.render(this._statusTable(row.status)));
  }

  _statusTable(workspaces) {
    return { columns: ["workspace", ...this._keys(workspaces)], rows: this._rows(workspaces) };
  }

  _rows(workspaces) {
    return workspaces.map((entry) => ({ workspace: entry.workspace, ...this._shown(entry.values) }));
  }

  _shown(values) {
    return Object.fromEntries(Object.entries(values).filter(([key]) => !RAIL_KEYS.includes(key)));
  }

  _keys(workspaces) {
    const keys = [];
    for (const entry of workspaces) {
      for (const key of Object.keys(this._shown(entry.values))) {
        if (!keys.includes(key)) keys.push(key);
      }
    }
    return keys;
  }
}
