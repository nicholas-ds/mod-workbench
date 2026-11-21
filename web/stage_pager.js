// The stage pager: prev and next buttons, a counter, arrow keys.

export class StagePager {
  constructor() {
    this._root = null;
    this._count = 0;
    this._index = 0;
    this._prev = null;
    this._next = null;
    this._counter = null;
    this._onSelect = null;
    this._onKeyDown = null;
  }

  render(count, selectedIndex, onSelect) {
    this._count = count;
    this._index = selectedIndex;
    this._onSelect = onSelect;
    this._root = document.createElement("div");
    this._root.className = "stage-pager";
    this._prev = this._button("pager-prev", "prev", () => onSelect(this._index - 1));
    this._next = this._button("pager-next", "next", () => onSelect(this._index + 1));
    this._counter = document.createElement("span");
    this._counter.className = "pager-count";
    this._root.appendChild(this._prev);
    this._root.appendChild(this._counter);
    this._root.appendChild(this._next);
    if (this._onKeyDown) document.removeEventListener("keydown", this._onKeyDown);
    this._onKeyDown = (event) => this._handleKey(event);
    document.addEventListener("keydown", this._onKeyDown);
    this.update(selectedIndex);
    return this._root;
  }

  update(index) {
    this._index = index;
    if (!this._counter) return;
    this._counter.textContent = `${index + 1} / ${this._count}`;
    this._prev.disabled = index <= 0;
    this._next.disabled = index >= this._count - 1;
  }

  _button(className, label, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `clay-button ${className}`;
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
  }

  _handleKey(event) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    if (event.target.closest("input, textarea, select")) return;
    if (!this._root || !this._root.isConnected) return;
    const delta = event.key === "ArrowLeft" ? -1 : 1;
    const index = this._index + delta;
    if (index < 0 || index >= this._count) return;
    event.preventDefault();
    this._onSelect(index);
  }
}
