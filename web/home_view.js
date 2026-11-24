// The home page: mod rail, open boards in queue order, status tables per mod.

import { AgentsView } from "./agents_view.js";
import { ActivityReader } from "./activity_reader.js";
import { DomBuilder } from "./dom_builder.js";
import { LoopPillView } from "./loop_pill.js";
import { ScrollableTable } from "./scrollable_table.js";
import { OverviewView } from "./overview_view.js";
import { StatusView } from "./status_view.js";
import { TableView } from "./table_view.js";
import { WakeButton } from "./wake_button.js";
import { ViewContext } from "./view_context.js";

export class HomeView {
  constructor(api, root) {
    this._api = api;
    this._root = root;
    this._boardView = null;
    this._chatView = null;
    this._table = new TableView();
    this._status = new StatusView(new TableView());
    this._overview = new OverviewView();
    this._agents = new AgentsView(new TableView());
    this._wakeButton = new WakeButton(api);
    this._filter = null;
    this._showBoardList = true;
    this._section = "mods";
    this._loops = {};
  }

  setSection(section) {
    this.restoreSection(section);
    return this.refresh();
  }

  restoreSection(section) {
    this._section = section;
    this._showBoardList = true;
  }

  setBoardView(boardView) {
    this._boardView = boardView;
  }

  setChatView(chatView) {
    this._chatView = chatView;
  }

  start() {
    this._api.events(() => this.refresh());
    return this.refresh();
  }

  show() {
    this._showBoardList = true;
    return this.refresh();
  }

  openBoard(mod, id) {
    this._showBoardList = false;
    return this._boardView.open(mod, id);
  }

  mainNode() {
    const layout = this._root.querySelector(".layout") ?? this._shell();
    return layout.querySelector(".main");
  }

  _shell() {
    const layout = DomBuilder.el("div", "layout");
    layout.appendChild(this._rail([]));
    layout.appendChild(DomBuilder.el("section", "main"));
    this._root.replaceChildren(layout);
    this._refreshRailCounts().catch((error) => this._notice(String(error)));
    return layout;
  }

  async refresh() {
    try {
      if (this._showBoardList) {
        this._root.replaceChildren(await this._page());
        this._announceHome();
      } else {
        await this._refreshRailCounts();
      }
      this._notice("");
    } catch (error) {
      this._notice(String(error));
    }
  }

  async _refreshRailCounts() {
    const mods = await this._api.mods();
    const healthy = this._healthy(mods.rows);
    await this._fetchLoops(healthy);
    const rail = this._rail(healthy);
    const oldRail = this._root.querySelector(".rail");
    if (!oldRail) return;
    oldRail.replaceWith(rail);
  }

  async _fetchLoops(rows) {
    const loops = await Promise.all(rows.map((row) =>
      this._api.loops(row.name).then((body) => body.loops ?? []).catch(() => [])));
    this._loops = Object.fromEntries(rows.map((row, index) => [row.name, loops[index]]));
  }

  async _page() {
    if (this._section === "tasks") return this._tasksPage();
    if (this._section === "chat") return this._chatPage();
    const mods = await this._api.mods();
    const healthy = this._healthy(mods.rows);
    await this._fetchLoops(healthy);
    const boards = await this._boardsTable(this._filtered(healthy));
    const agents = await this._api.agents();
    return this._layout(mods.rows, boards, agents.agents);
  }

  _filtered(rows) {
    return this._filter ? rows.filter((row) => row.name === this._filter) : rows;
  }

  _healthy(rows) {
    return rows.filter((row) => !row.error);
  }

  async _boardsTable(modRows) {
    const lists = await Promise.all(modRows.map((row) => this._modBoards(row.name)));
    const rows = lists.flat();
    return { columns: ["mod", ...this._keys(rows)], rows };
  }

  async _modBoards(name) {
    const body = await this._api.boards(name, "open");
    return body.table.rows.map((row) => ({ mod: name, ...row }));
  }

  _keys(rows) {
    const keys = [];
    for (const row of rows) {
      for (const key of Object.keys(row)) {
        if (key !== "mod" && !keys.includes(key)) keys.push(key);
      }
    }
    return keys;
  }

  async _tasksPage() {
    const overview = await this._api.overview();
    this._announceHome();
    return this._overview.render(overview);
  }

  _chatPage() {
    this._announceHome();
    return this._chatView.render();
  }

  _layout(modRows, boardsTable, agents) {
    const layout = DomBuilder.el("div", "layout");
    layout.appendChild(this._rail(modRows));
    layout.appendChild(this._main(modRows, boardsTable, agents));
    return layout;
  }

  _main(modRows, boardsTable, agents) {
    const main = DomBuilder.el("section", "main");
    main.appendChild(this._boardsNode(boardsTable));
    main.appendChild(this._agents.render(agents));
    main.appendChild(this._status.render(this._filtered(modRows)));
    return main;
  }

  _boardsNode(boardsTable) {
    const section = DomBuilder.el("section", "clay boards");
    section.appendChild(DomBuilder.el("h2", "panel-title", "open boards"));
    const node = this._table.render(boardsTable);
    node.addEventListener("click", (event) => this._openBoard(event, boardsTable));
    section.appendChild(ScrollableTable.wrap(node));
    return section;
  }

  _openBoard(event, table) {
    const row = event.target.closest("tr[data-index]");
    if (!row || !this._boardView) return;
    const record = table.rows[Number(row.dataset.index)];
    if (record.error || !record.id) return;
    this.openBoard(record.mod, record.id);
  }

  _rail(modRows) {
    const rail = DomBuilder.el("nav", "clay on-verdigris rail");
    const head = DomBuilder.el("div", "rail-head");
    head.appendChild(DomBuilder.el("b", "panel-title", "mods"));
    head.appendChild(this._wakeButton.build());
    rail.appendChild(head);
    for (const row of modRows) {
      rail.appendChild(this._railItem(row));
    }
    return rail;
  }

  _railItem(row) {
    const item = DomBuilder.el("span");
    if (row.error) {
      item.textContent = row.repo;
      return item;
    }
    const activity = ActivityReader.read(row);
    item.appendChild(this._railTitle(row.name, activity));
    item.appendChild(DomBuilder.el("em", "count", String(row.open_boards)));
    if (activity.task) item.appendChild(DomBuilder.el("small", "rail-task", activity.task));
    if (activity.fine) item.appendChild(DomBuilder.el("small", "rail-fine", activity.fine));
    const pill = LoopPillView.render(this._loops[row.name] || [], new Date(), {
      api: this._api,
      modName: row.name,
      onRetried: () => this._refreshRailCounts(),
    });
    if (pill) item.appendChild(pill);
    item.classList.toggle("is-selected", row.name === this._filter);
    item.addEventListener("click", () => this._toggleFilter(row.name));
    return item;
  }

  _railTitle(name, activity) {
    const title = DomBuilder.el("i", "rail-title");
    const dot = DomBuilder.el("i", activity.state === "idle" ? "rail-dot" : `rail-dot is-${activity.state}`);
    dot.title = activity.tooltip;
    title.appendChild(dot);
    title.appendChild(document.createTextNode(name));
    return title;
  }

  _announceHome() {
    ViewContext.shared().set(
      { view: "home", mod: this._filter, board: null, item: null, question: null, section: this._section });
  }

  _toggleFilter(name) {
    this._filter = this._filter === name ? null : name;
    this._showBoardList = true;
    ViewContext.shared().set({ mod: this._filter });
    return this.refresh();
  }

  _notice(text) {
    document.getElementById("notice").textContent = text;
  }
}
