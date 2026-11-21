// The view of one question: prompt, answer controls for its type, and a comment field.

import { DomBuilder } from "./dom_builder.js";
import { KeyMap } from "./key_map.js";

// An option with an item dispatches this on document so the whiteboard can highlight it.
const HOVER_EVENT = "wb-item-hover";

export class QuestionView {
  constructor(question, current, onAnswer, readOnly = false) {
    this._question = question;
    this._current = { picked: null, text: null, comment: null, ...current };
    this._onAnswer = onAnswer;
    this._readOnly = readOnly;
    this._optionNodes = new Map();
  }
  get question() { return this._question; }
  render() {
    const node = DomBuilder.el("article", "question");
    node.appendChild(DomBuilder.el("b", null, this._question.prompt));
    this._appendSuggestion(node);
    node.appendChild(this._controls());
    node.appendChild(this._field("Comment (optional)", this._current.comment,
      (value) => this._save({ comment: value })));
    return node;
  }
  // Returns the action type when the key was consumed, null otherwise.
  handleKey(key) {
    if (this._readOnly) return null;
    const action = KeyMap.actionFor(key, this._question);
    if (!action) return null;
    if (action.type === "pick") this._pick(action.id);
    if (action.type === "default") this._takeDefault();
    if (action.type === "skip" && !this._current.picked && !this._current.text) this._save({ picked: null, text: null });
    return action.type;
  }
  _appendSuggestion(node) {
    if (this._question.type !== "yes") return;
    node.appendChild(DomBuilder.el("span", null, `My suggestion: ${this._question.suggestion ?? ""}`));
  }
  _controls() {
    const wrap = DomBuilder.el("div", "stack");
    if (this._question.type === "choice") this._choiceControls(wrap);
    if (this._question.type === "yes") this._yesControls(wrap);
    if (this._question.type === "text") this._textControls(wrap);
    return wrap;
  }
  _choiceControls(wrap) { this._question.options.forEach((option, index) => wrap.appendChild(this._option(option, index))); }
  _option(option, index) {
    const node = DomBuilder.el("button", "opt");
    node.type = "button";
    node.classList.toggle("is-default", option.id === this._question.default);
    node.classList.toggle("is-chosen", this._current.picked === option.id);
    this._optionNodes.set(option.id, node);
    node.appendChild(this._optionLabel(option, index));
    if (option.id === this._question.default) node.appendChild(this._defaultFlag());
    if (this._readOnly) {
      node.disabled = true;
      return node;
    }
    node.addEventListener("click", () => this._pick(option.id));
    if (option.item) {
      node.addEventListener("mouseenter", () => this._hover(option.item, true));
      node.addEventListener("mouseleave", () => this._hover(option.item, false));
    }
    return node;
  }
  _optionLabel(option, index) {
    const label = DomBuilder.el("span", "opt-label");
    label.appendChild(DomBuilder.el("span", "clay-key", String(index + 1)));
    label.appendChild(DomBuilder.el("span", null, option.label));
    return label;
  }
  _defaultFlag() { return DomBuilder.el("i", "opt-flag", "default"); }
  _yesControls(wrap) {
    const row = DomBuilder.el("div", "row");
    const yes = DomBuilder.el("button", "clay-button clay-action", "Yes");
    yes.type = "button";
    yes.setAttribute("aria-pressed", this._isYes() ? "true" : "false");
    if (this._readOnly) yes.disabled = true;
    else yes.addEventListener("click", () => this._takeDefault());
    row.appendChild(yes);
    row.appendChild(this._field("Different answer", this._current.text,
      (value) => this._setText(value)));
    wrap.appendChild(row);
  }
  _isYes() { return Boolean(this._question.suggestion) && this._current.text === this._question.suggestion; }
  _textControls(wrap) {
    wrap.appendChild(this._field("Write your answer", this._current.text,
      (value) => this._setText(value)));
  }
  _takeDefault() {
    if (this._question.type === "yes") this._setText(this._question.suggestion); else this._pick(this._question.default);
  }
  _field(placeholder, value, onCommit) {
    const field = DomBuilder.el("input", "clay-field");
    Object.assign(field, { type: "text", placeholder, value: value ?? "" });
    if (this._readOnly) field.readOnly = true;
    field.addEventListener("change", () => onCommit(field.value));
    return field;
  }
  _pick(id) {
    this._save({ picked: id });
    this._refreshChosen();
  }
  _refreshChosen() {
    for (const [id, node] of this._optionNodes) {
      node.classList.toggle("is-chosen", id === this._current.picked);
    }
  }
  _setText(value) { this._save({ text: value }); }
  // The server replaces the whole answer entry, so every post carries all fields.
  _save(patch) {
    this._current = { ...this._current, ...patch };
    this._onAnswer({
      question_id: this._question.id,
      picked: QuestionView._clean(this._current.picked),
      text: QuestionView._clean(this._current.text),
      comment: QuestionView._clean(this._current.comment),
    });
  }
  _hover(file, on) { document.dispatchEvent(new CustomEvent(HOVER_EVENT, { detail: { file, on } })); }
  static _clean(value) { return value === "" ? null : value; }
}
