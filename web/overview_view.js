// The all-tasks overview: open tasks of every mod from the master tracking file.

import { DomBuilder } from "./dom_builder.js";

export class OverviewView {
  render(overview) {
    const section = DomBuilder.el("section", "clay overview");
    section.appendChild(DomBuilder.el("h2", "panel-title", "all tasks"));
    overview.warnings.forEach((text) => section.appendChild(this._warning(text)));
    const grid = DomBuilder.el("div", "overview-grid");
    overview.repos.forEach((repo) => grid.appendChild(this._repo(repo)));
    section.appendChild(grid);
    return section;
  }

  _repo(repo) {
    const card = DomBuilder.el("article", "overview-repo");
    const head = DomBuilder.el("h3", null, repo.mod);
    head.appendChild(DomBuilder.el("em", "count", String(repo.open_count)));
    if (repo.warning) head.appendChild(this._warning(repo.warning));
    card.appendChild(head);
    const open = repo.items.filter((item) => !item.done);
    if (open.length === 0) card.appendChild(DomBuilder.el("p", "overview-empty", "nothing open"));
    open.forEach((item) => card.appendChild(this._item(item)));
    return card;
  }

  _item(item) {
    const line = DomBuilder.el("p", "overview-item");
    if (item.waits_for_author) line.appendChild(DomBuilder.el("span", "tag", "you"));
    line.appendChild(document.createTextNode(item.text.replace(/\.?\s*waits: author/i, "")));
    return line;
  }

  _warning(text) {
    return DomBuilder.el("span", "tag overview-warning", text);
  }
}
