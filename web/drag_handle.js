const DRAG_THRESHOLD_PX = 4;

export class DragHandle {
  constructor(element, storageKey) {
    this.element = element;
    this.storageKey = storageKey;
    this.pointerId = null;
    this.moved = false;
    this.persistent = true;
    this.startX = this.startY = this.offsetX = this.offsetY = 0;
    window.addEventListener("resize", () => this.clamp());
    window.addEventListener("pointermove", this.onMove);
    window.addEventListener("pointerup", this.onEnd);
    window.addEventListener("pointercancel", this.onEnd);
  }

  attach(handle = this.element) {
    this.handle = handle;
    this.addPips(handle);
    handle.addEventListener("pointerdown", (event) => this.startDrag(event));
  }

  addPips(handle) {
    if (!handle.classList.contains("dock-head")) return;
    const pips = document.createElement("span");
    pips.className = "drag-pips";
    for (let i = 0; i < 3; i++) pips.appendChild(document.createElement("i"));
    handle.prepend(pips);
  }

  setPersistent(persistent) {
    this.persistent = persistent;
  }

  wasDragged() {
    return this.moved;
  }

  restore() {
    const saved = this.readPosition();
    if (!saved || typeof saved.x !== "number" || typeof saved.y !== "number") return;
    this.applyPosition(...this.constrain(saved.x, saved.y));
  }

  reset() {
    this.element.style.left = "";
    this.element.style.top = "";
    this.element.style.right = "";
    this.element.style.bottom = "";
  }

  clamp() {
    const rect = this.element.getBoundingClientRect();
    this.applyPosition(...this.constrain(rect.left, rect.top));
  }

  startDrag(event) {
    this.moved = false;
    const interactive = event.target.closest("button:not([data-drag-through]), input, textarea, select, a");
    if (interactive && interactive !== this.handle) return;
    const rect = this.element.getBoundingClientRect();
    this.startX = event.clientX;
    this.startY = event.clientY;
    this.offsetX = event.clientX - rect.left;
    this.offsetY = event.clientY - rect.top;
    this.pointerId = event.pointerId;
  }

  onMove = (event) => {
    if (event.pointerId !== this.pointerId) return;
    if (!this.moved && Math.hypot(event.clientX - this.startX, event.clientY - this.startY) < DRAG_THRESHOLD_PX) return;
    this.moved = true;
    this.element.setPointerCapture(event.pointerId);
    this.applyPosition(...this.constrain(event.clientX - this.offsetX, event.clientY - this.offsetY));
  };

  onEnd = (event) => {
    if (event.pointerId !== this.pointerId) return;
    this.pointerId = null;
    if (!this.moved || !this.persistent) return;
    this.savePosition(this.element.offsetLeft, this.element.offsetTop);
  };

  constrain(x, y) {
    const maxX = Math.max(0, window.innerWidth - this.element.offsetWidth);
    const maxY = Math.max(0, window.innerHeight - this.element.offsetHeight);
    return [Math.min(Math.max(x, 0), maxX), Math.min(Math.max(y, 0), maxY)];
  }

  applyPosition(x, y) {
    this.element.style.left = `${x}px`;
    this.element.style.top = `${y}px`;
    this.element.style.right = "auto";
    this.element.style.bottom = "auto";
  }

  savePosition(x, y) {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify({ x, y }));
    } catch {
      // Storage throws in private mode or when full; dragging must still work.
    }
  }

  readPosition() {
    try {
      return JSON.parse(localStorage.getItem(this.storageKey));
    } catch {
      return null;
    }
  }
}
