// One board page: the whiteboard left and the questions panel right.

import { DomBuilder } from "./dom_builder.js";
import { ItemRenderer } from "./item_renderers.js";
import { NotePinner } from "./note_pinner.js";
import { ViewContext } from "./view_context.js";
import { Whiteboard } from "./whiteboard.js";

export class BoardView {
  constructor(api, getRoot, questionsPanel) {
    this._api = api;
    this._getRoot = getRoot;
    this._questions = questionsPanel;
    this._onBack = null;
    this._whiteboard = new Whiteboard(new ItemRenderer(), (card, item) => this._pin(card, item));
    this._mod = "";
    this._id = "";
  }

  setOnBack(onBack) {
    this._onBack = onBack;
  }

  open(mod, id) {
    this._mod = mod;
    this._id = id;
    return this._load(mod, id);
  }

  reopen() {
    return this.open(this._mod, this._id);
  }

  // The questions panel calls this with the outcome of each successful change.
  panelChanged(outcome) {
    if (outcome === "closed") this._onBack();
    else this.reopen();
  }

  async _load(mod, id) {
    try {
      const board = await this._api.board(mod, id);
      this._announceBoard(mod, id);
      this._getRoot().replaceChildren(this._page(mod, board));
      this._notice("");
    } catch (error) {
      this._notice(String(error));
    }
  }

  _announceBoard(mod, id) {
    ViewContext.shared().set({ view: "board", mod, board: id, item: null, question: null });
  }

  _page(mod, board) {
    const page = DomBuilder.el("section", "board");
    page.appendChild(this._header(board));
    page.appendChild(this._split(mod, board));
    page.addEventListener("focusin", (event) => this._announceQuestion(event.target));
    return page;
  }

  _announceQuestion(target) {
    const article = target.closest("article.question");
    if (!article) return;
    ViewContext.shared().set({ question: this._promptOf(article) });
  }

  _promptOf(article) {
    const prompt = article.querySelector("b");
    return prompt ? prompt.textContent : null;
  }

  _split(mod, board) {
    const split = DomBuilder.el("div", "board-split");
    split.appendChild(this._whiteboardPanel(board));
    split.appendChild(this._questions.render(mod, board, board.answers));
    return split;
  }

  _whiteboardPanel(board) {
    const panel = DomBuilder.el("section", "clay on-teal board-whiteboard");
    panel.appendChild(this._label("whiteboard"));
    panel.appendChild(this._whiteboard.render(board.items));
    panel.appendChild(this._hint());
    return panel;
  }

  _pin(card, item) {
    new NotePinner(this._api, this._mod, this._id).attach(card, item, () => {});
  }

  _header(board) {
    const head = DomBuilder.el("header", "board-bar");
    head.appendChild(this._backButton());
    const title = DomBuilder.el("b", "board-title", board.title);
    head.appendChild(title);
    head.appendChild(this._chip(board.raised_by));
    board.tags.forEach((tag) => head.appendChild(this._chip(tag)));
    if (board.stale) head.appendChild(this._chip(`stale: ${board.stale}`));
    return head;
  }

  _backButton() {
    const button = DomBuilder.el("button", "clay-button clay-quiet board-back",
      "Back to boards");
    button.type = "button";
    button.addEventListener("click", () => this._onBack());
    return button;
  }

  _chip(text) {
    const chip = DomBuilder.el("span", "board-chip", text);
    return chip;
  }

  _label(text) {
    const label = DomBuilder.el("h3", "panel-title", text);
    return label;
  }

  _hint() {
    const hint = DomBuilder.el("span", "board-hint",
      "Click a spot on an item to leave a note. The note becomes a task.");
    return hint;
  }

  _notice(text) {
    document.getElementById("notice").textContent = text;
  }
}
