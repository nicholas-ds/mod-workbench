// The stage switcher: one tab per item, labels from captions.

import { ViewContext } from "./view_context.js";

export class StageTabs {
  constructor() {
    this._root = null;
    this._buttons = [];
  }

  render(items, selectedIndex, onSelect) {
    this._buttons = [];
    this._root = document.createElement("div");
    this._root.className = "stage-tabs";
    items.forEach((item, index) => {
      this._root.appendChild(this._tab(item, index, index === selectedIndex, onSelect));
    });
    return this._root;
  }

  select(index) {
    this._buttons.forEach((tab, i) => tab.classList.toggle("is-selected", i === index));
  }

  link(file, on) {
    const tab = this._buttons.find((candidate) => candidate.dataset.file === file);
    if (tab) tab.classList.toggle("is-linked", on);
  }

  _tab(item, index, selected, onSelect) {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "stage-tab";
    tab.textContent = this._label(item);
    tab.dataset.file = item.file;
    if (selected) tab.classList.add("is-selected");
    tab.addEventListener("click", () => {
      ViewContext.shared().set({ item: item.file });
      onSelect(index);
    });
    this._buttons.push(tab);
    return tab;
  }

  _label(item) {
    return item.caption || item.file;
  }
}
