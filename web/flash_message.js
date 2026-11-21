// One short confirmation or failure message at the top of the page, cleared after a few seconds.

const SHOW_MS = 6000;

export class FlashMessage {
  static shared() {
    return new FlashMessage(document.getElementById("flash"));
  }

  constructor(node) {
    this._node = node;
  }

  confirm(text) {
    this._show(text, "is-ok");
  }

  fail(text) {
    this._show(text, "is-failed");
  }

  _show(text, className) {
    this._node.textContent = text;
    this._node.className = `flash ${className}`;
    this._node.classList.remove("wobble-once"); void this._node.offsetWidth; this._node.classList.add("wobble-once");
    clearTimeout(this._timer);
    this._timer = setTimeout(() => this._clear(), SHOW_MS);
  }

  _clear() {
    this._node.textContent = "";
    this._node.className = "flash";
  }
}
