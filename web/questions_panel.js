// The questions panel: one view per question, posted answers, and the lifecycle button.

import { DomBuilder } from "./dom_builder.js";
import { FlashMessage } from "./flash_message.js";
import { QuestionView } from "./question_views.js";

const LEGEND_KEYS = [["1", null], ["2", null], ["3", "pick"], ["Enter", "default"], ["S", "skip"]];

export class QuestionsPanel {
  constructor(api, onChanged) {
    this._api = api;
    this._onChanged = onChanged;
    this._mod = null;
    this._boardId = null;
    this._done = false;
    this._activeId = null;
    this._views = [];
    this._root = null;
    this._noticeNode = DomBuilder.el("p", "status-line");
    document.addEventListener("keydown", (event) => this._onKey(event));
  }
  render(mod, board, answers) {
    this._mod = mod;
    this._boardId = board.id;
    this._resolved = board.resolved ?? [];
    this._done = board.state === "done";
    this._permanent = board.permanent;
    this._views = board.questions.map((question) => this._view(question, answers));
    this._keepActive();
    this._root = this._panel();
    return this._root;
  }
  _view(question, answers) {
    const current = answers.find((answer) => answer.question_id === question.id) ?? {};
    return new QuestionView(question, current, (body) => this._post(body), this._done);
  }
  _keepActive() {
    if (!this._views.some((view) => view.question.id === this._activeId)) {
      this._activeId = this._views[0]?.question.id ?? null;
    }
  }
  _panel() {
    const root = DomBuilder.el("aside", "clay on-sienna questions-panel");
    root.tabIndex = -1;
    root.appendChild(this._heading());
    this._views.forEach((view) => root.appendChild(this._question(view)));
    this._resolved.forEach((item) => root.appendChild(this._resolvedCard(item)));
    root.appendChild(this._legend());
    root.appendChild(this._lifecycle());
    root.appendChild(this._noticeNode);
    root.addEventListener("click", (event) => this._activate(event));
    return root;
  }
  _heading() { return DomBuilder.el("h3", "panel-title", "Questions"); }
  _question(view) {
    const node = view.render();
    node.dataset.question = view.question.id;
    return node;
  }
  _resolvedCard(item) {
    const node = DomBuilder.el("article", "question question-resolved");
    node.appendChild(DomBuilder.el("span", "tag", `Confirmed ${item.date}`));
    node.appendChild(DomBuilder.el("b", null, item.prompt));
    node.appendChild(DomBuilder.el("span", null, item.note));
    return node;
  }
  _legend() {
    const legend = DomBuilder.el("p");
    for (const [cap, label] of LEGEND_KEYS) {
      legend.appendChild(DomBuilder.el("span", "clay-key", cap));
      if (label) legend.appendChild(DomBuilder.el("span", null, label));
    }
    return legend;
  }
  _lifecycle() {
    const bar = DomBuilder.el("div", "row");
    const button = DomBuilder.el("button", "clay-button clay-action",
      this._done ? "Change my mind" : "Send answers");
    if (this._permanent) button.title = "Permanent board: sends answers and stays open";
    button.type = "button";
    button.addEventListener("click", () => this._lifecycleCall());
    bar.appendChild(button);
    return bar;
  }
  _lifecycleCall() {
    if (this._permanent) return this._sendOnly();
    const closing = !this._done;
    const call = closing ? this._api.close(this._mod, this._boardId)
      : this._api.reopen(this._mod, this._boardId);
    call.then((result) => this._applied(closing ? "closed" : "reopened", result))
      .catch((error) => this._fail(error));
  }
  _sendOnly() {
    this._api.send(this._mod, this._boardId)
      .then((result) => this._applied("sent", result))
      .catch((error) => this._fail(error));
  }
  _post(body) {
    this._api.answer(this._mod, this._boardId, body)
      .then(() => this._applied("answered", {}))
      .catch((error) => this._fail(error));
  }
  _applied(outcome, result) {
    this._noticeNode.textContent = "";
    this._onChanged(outcome);
    this._confirm(outcome, result);
  }
  _confirm(outcome, result) {
    const flash = FlashMessage.shared();
    if (outcome === "answered") flash.confirm("Answer saved.");
    else if (outcome === "sent") flash.confirm(result.notified ? "Answers sent. The board stays open." : "Answers saved. No pane is registered for this board.");
    else if (outcome === "closed") this._closedFlash(result, flash);
    else if (result.notified) flash.confirm(`Board ${outcome}. The agent was told.`);
    else flash.fail(`Board ${outcome}, but the agent was not told. No pane is registered for it.`);
  }
  _closedFlash(result, flash) {
    if (result.notified) flash.confirm("Answers sent and board closed. The agent was told.");
    else flash.fail("Board closed, but the agent was not told. No pane is registered for it.");
  }
  _fail(error) {
    this._noticeNode.textContent = "";
    FlashMessage.shared().fail(`Not saved: ${error.message}`);
  }
  _activate(event) {
    const node = event.target.closest("[data-question]");
    if (node) this._activeId = node.dataset.question;
  }
  _onKey(event) {
    if (!this._root?.isConnected || event.target.closest("input, textarea, select")) return;
    const view = this._views.find((item) => item.question.id === this._activeId);
    if (!view) return;
    const action = view.handleKey(event.key);
    if (!action) return;
    if (action === "skip") this._advance();
    event.preventDefault();
  }
  _advance() {
    const next = this._views[this._views.findIndex((item) => item.question.id === this._activeId) + 1];
    if (next) this._activeId = next.question.id;
  }
}
