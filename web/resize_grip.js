// A corner grip that resizes a fixed-position element and remembers the size.

const MIN_WIDTH_PX = 320;
const MIN_HEIGHT_PX = 220;

export class ResizeGrip {
  constructor(element, storageKey) {
    this.element = element;
    this.storageKey = storageKey;
    this.pointerId = null;
    this.grip = document.createElement("div");
    this.grip.className = "dock-grip";
    this.grip.title = "Drag to resize";
    element.appendChild(this.grip);
    this.grip.addEventListener("pointerdown", (event) => this.start(event));
    window.addEventListener("pointermove", this.onMove);
    window.addEventListener("pointerup", this.onEnd);
    window.addEventListener("pointercancel", this.onEnd);
  }

  reset() {
    this.element.style.width = "";
    this.element.style.height = "";
  }

  restore() {
    const saved = this.readSize();
    if (!saved || typeof saved.w !== "number" || typeof saved.h !== "number") return;
    this.apply(saved.w, saved.h);
  }

  start(event) {
    const rect = this.element.getBoundingClientRect();
    this.element.style.left = `${rect.left}px`;
    this.element.style.top = `${rect.top}px`;
    this.element.style.right = "auto";
    this.element.style.bottom = "auto";
    this.startX = event.clientX;
    this.startY = event.clientY;
    this.startWidth = rect.width;
    this.startHeight = rect.height;
    this.pointerId = event.pointerId;
    this.grip.setPointerCapture(event.pointerId);
    this.grip.classList.add("is-resizing");
    event.preventDefault();
  }

  onMove = (event) => {
    if (event.pointerId !== this.pointerId) return;
    this.apply(this.startWidth + event.clientX - this.startX, this.startHeight + event.clientY - this.startY);
  };

  onEnd = (event) => {
    if (event.pointerId !== this.pointerId) return;
    this.grip.classList.remove("is-resizing");
    this.pointerId = null;
    const rect = this.element.getBoundingClientRect();
    this.saveSize(rect.width, rect.height);
  };

  apply(width, height) {
    const left = this.element.offsetLeft;
    const top = this.element.offsetTop;
    const maxWidth = Math.max(MIN_WIDTH_PX, window.innerWidth - left);
    const maxHeight = Math.max(MIN_HEIGHT_PX, window.innerHeight - top);
    this.element.style.width = `${Math.min(Math.max(width, MIN_WIDTH_PX), maxWidth)}px`;
    this.element.style.height = `${Math.min(Math.max(height, MIN_HEIGHT_PX), maxHeight)}px`;
  }

  saveSize(w, h) {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify({ w, h }));
    } catch {
      // Storage may throw; resizing must still work.
    }
  }

  readSize() {
    try {
      return JSON.parse(localStorage.getItem(this.storageKey));
    } catch {
      return null;
    }
  }
}
