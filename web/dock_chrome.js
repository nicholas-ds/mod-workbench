// The dock's frame around the conversation: the dock element itself, the head
// with its toggle, the view-context chips, and the collapsed/expanded
// mechanics (drag position, resize grip, gravity, stored preference). The
// conversation content stays in MessageDock.

import { DomBuilder } from "./dom_builder.js";
import { DragHandle } from "./drag_handle.js";
import { DockCollapsedAnchor } from "./dock_collapsed_anchor.js";
import { DockGravity } from "./dock_gravity.js";
import { ResizeGrip } from "./resize_grip.js";

const COLLAPSED_KEY = "wb-dock-collapsed";
const CHIP_FIELDS = ["view", "mod", "board", "item", "question"];

export class DockChrome {
  constructor(onToggle) {
    this._dock = DomBuilder.el("div", "message-dock theme-classic");
    this._head = DomBuilder.el("div", "dock-head");
    const toggle = DomBuilder.el("button", "dock-toggle panel-title", "message");
    this._toggle = toggle;
    toggle.dataset.dragThrough = "";
    toggle.addEventListener("click", () => {
      if (this._openDrag.wasDragged()) return;
      onToggle();
    });
    this._chips = DomBuilder.el("div", "dock-chips");
  }

  get dock() { return this._dock; }

  get head() { return this._head; }

  get chipsNode() { return this._chips; }

  isCollapsed() {
    return this._dock.classList.contains("is-collapsed");
  }

  // Wire the frame to the page: drag, resize, gravity, then show the dock.
  mount(parent) {
    this._anchor = new DockCollapsedAnchor();
    this._openDrag = new DragHandle(this._dock, "wb-dock-pos-open");
    this._openDrag.attach(this._head);
    this._grip = new ResizeGrip(this._dock, "wb-dock-size");
    this._gravity = new DockGravity(this._dock, this._anchor, document);
    this._gravity.start();
    parent.appendChild(this._dock);
  }

  // One chip per non-null field of the view context.
  setChips(context) {
    const chips = CHIP_FIELDS.filter((field) => context[field] !== null)
      .map((field) => DomBuilder.el("span", "dock-chip", `${field}: ${context[field]}`));
    this._chips.replaceChildren(...chips);
  }

  storedCollapsed() {
    try { return localStorage.getItem(COLLAPSED_KEY) !== "0"; } catch { return false; }
  }

  // Apply the collapsed state to the frame. Timers and the open pipeline stay
  // with MessageDock.
  applyCollapsed(collapsed) {
    this._dock.classList.toggle("is-collapsed", collapsed);
    this._toggle.textContent = collapsed ? "message" : "message  ▾ hide";
    this._toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
    this._openDrag.reset();
    this._openDrag.setPersistent(!collapsed);
    if (collapsed) this._anchor.apply(this._dock, document);
    else this._openDrag.restore();
    this._grip.reset();
    if (!collapsed) this._grip.restore();
    try {
      localStorage.setItem(COLLAPSED_KEY, collapsed ? "1" : "0");
    } catch { /* storage unavailable: the state is not kept */ }
  }
}
