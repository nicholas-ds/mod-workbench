// The whiteboard stage: one large view for the selected item, tabs below.

import { DomBuilder } from "./dom_builder.js";
import { StagePager } from "./stage_pager.js";
import { StageTabs } from "./stage_tabs.js";
import { ViewContext } from "./view_context.js";

// Question views dispatch this on document when a choice option is hovered.
const HOVER_EVENT = "wb-item-hover";

export class Whiteboard {
  constructor(renderer, onItemCard = null) {
    this._renderer = renderer;
    this._onItemCard = onItemCard;
    this._stageTabs = new StageTabs();
    this._pager = new StagePager();
    this._items = [];
    this._selectedIndex = 0;
    this._linkedFile = null;
    this._stage = null;
    this._card = null;
    this._expand = null;
    document.addEventListener(HOVER_EVENT, (event) => this._onHover(event.detail));
    document.addEventListener("fullscreenchange", () => this._syncExpandLabel());
  }

  render(items) {
    this._items = items;
    this._selectedIndex = 0;
    this._linkedFile = null;
    this._stage = DomBuilder.el("div", "stage");
    if (items.length > 0) this._start(items[0]);
    if (items.length > 1) {
      this._stage.appendChild(this._pager.render(items.length, this._selectedIndex, (index) => this._page(index)));
      const onSelect = (index) => this._select(index);
      this._stage.appendChild(this._stageTabs.render(items, this._selectedIndex, onSelect));
    }
    const tools = DomBuilder.el("div", "stage-tools");
    if (items.some((item) => item.kind === "html" || item.kind === "svg")) {
      tools.appendChild(this._notesButton());
    }
    tools.appendChild(this._expandButton());
    this._stage.prepend(tools);
    return this._stage;
  }

  _expandButton() {
    const button = DomBuilder.el("button", "clay-button stage-expand", "full screen");
    button.type = "button";
    button.addEventListener("click", () => this._toggleFullscreen());
    this._expand = button;
    return button;
  }

  _notesButton() {
    const button = DomBuilder.el("button", "clay-button stage-notes", "add notes");
    button.type = "button";
    button.setAttribute("aria-pressed", "false");
    this._stage.classList.add("is-scrolling");
    button.addEventListener("click", () => this._toggleScrollMode());
    return button;
  }

  _toggleScrollMode() {
    const button = this._stage.querySelector(".stage-notes");
    const scrolling = this._stage.classList.toggle("is-scrolling");
    if (!button) return;
    button.textContent = scrolling ? "add notes" : "scroll page";
    button.setAttribute("aria-pressed", scrolling ? "false" : "true");
  }

  _toggleFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    } else {
      this._stage.requestFullscreen().catch(() => {});
    }
  }

  _syncExpandLabel() {
    if (!this._expand) return;
    this._expand.textContent =
      document.fullscreenElement === this._stage ? "exit full screen" : "full screen";
  }

  _start(item) {
    this._mount(item);
    ViewContext.shared().set({ item: item.file });
  }

  _page(index) {
    if (index < 0 || index >= this._items.length) return;
    ViewContext.shared().set({ item: this._items[index].file });
    this._select(index);
  }

  _select(index) {
    this._selectedIndex = index;
    this._pager.update(index);
    this._stageTabs.select(index);
    this._mount(this._items[index]);
  }

  _mount(item) {
    if (this._card) this._card.remove();
    this._card = this._cardFor(item);
    this._stage.insertBefore(this._card, this._stage.firstChild);
  }

  _cardFor(item) {
    const card = this._renderer.render(item);
    card.dataset.file = item.file;
    this._wrapInBezel(card);
    if (this._onItemCard) this._onItemCard(card, item);
    return card;
  }

  _wrapInBezel(card) {
    const well = card.querySelector(".item-well");
    if (!well) return;
    const bezel = DomBuilder.el("div", "stage-bezel");
    const ring = DomBuilder.el("div", "stage-ring");
    well.replaceWith(bezel);
    bezel.appendChild(ring);
    ring.appendChild(well);
  }

  _onHover(detail) {
    if (!detail) return;
    const index = this._items.findIndex((item) => item.file === detail.file);
    if (index < 0) return;
    if (detail.on) this._link(index);
    else this._unlink();
  }

  _link(index) {
    this._linkedFile = this._items[index].file;
    this._stageTabs.link(this._linkedFile, true);
    this._mount(this._items[index]);
    this._card.classList.add("is-linked");
  }

  _unlink() {
    if (!this._linkedFile) return;
    this._stageTabs.link(this._linkedFile, false);
    this._linkedFile = null;
    this._mount(this._items[this._selectedIndex]);
  }
}
