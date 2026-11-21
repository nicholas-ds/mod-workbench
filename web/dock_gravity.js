// Pulls the collapsed message button back to its anchor, slowly, when the author is not using it.
const IDLE_MS = 200;
const PULL = 520;
const AIR_DRAG = 1.3;
const SETTLE_DRAG = 9;
const SETTLE_RADIUS = 48;
const SNAP_DISTANCE = 0.5;
const SNAP_SPEED = 6;
const MAX_STEP_S = 0.05;

export class DockGravity {
  constructor(dock, anchor, root) {
    this._dock = dock;
    this._anchor = anchor;
    this._root = root;
    this._held = false;
    this._velocity = { x: 0, y: 0 };
    this._frame = null;
    this._idleUntil = 0;
    this._lastTime = 0;
    this._placed = false;
  }

  start() {
    const wake = () => this.wake();
    window.addEventListener("resize", wake);
    // A font swap reflows the nav pills without a DOM mutation, so the observer
    // below misses it and a position measured with fallback metrics goes stale.
    if (document.fonts) {
      document.fonts.ready.then(wake);
      document.fonts.addEventListener("loadingdone", wake);
    }
    new MutationObserver(wake).observe(this._root.body, { childList: true, subtree: true });
    this._dock.addEventListener("pointerenter", () => this.hold());
    this._dock.addEventListener("pointerleave", () => this.release());
  }

  hold() {
    this._held = true;
    this._velocity = { x: 0, y: 0 };
  }

  release() {
    this._held = false;
    this._idleUntil = performance.now() + IDLE_MS;
    this.wake();
  }

  wake() {
    if (this._frame !== null || !this._isCollapsed()) return;
    this._lastTime = performance.now();
    this._frame = requestAnimationFrame((time) => this._step(time));
  }

  _isCollapsed() {
    return this._dock.classList.contains("is-collapsed");
  }

  _step(time) {
    this._frame = null;
    if (!this._isCollapsed() || this._held) return;
    const target = this._anchor.corner(this._dock, this._root);
    if (!target) return this._anchor.clear(this._dock);
    if (!this._placed) return this._snap(target);
    if (time < this._idleUntil) return this._continue();
    const settled = this._fall(target, Math.min((time - this._lastTime) / 1000, MAX_STEP_S));
    this._lastTime = time;
    if (!settled) this._continue();
  }

  _continue() {
    this._frame = requestAnimationFrame((time) => this._step(time));
  }

  _snap(target) {
    this._placed = true;
    this._anchor.apply(this._dock, this._root);
    this._velocity = { x: 0, y: 0 };
    return target;
  }

  _fall(target, seconds) {
    const rect = this._dock.getBoundingClientRect();
    const dx = target.left - rect.left;
    const dy = target.top - rect.top;
    const distance = Math.hypot(dx, dy);
    const speed = Math.hypot(this._velocity.x, this._velocity.y);
    if (distance < SNAP_DISTANCE && speed < SNAP_SPEED) return this._arrive(target);
    const pull = distance > 0 ? PULL / distance : 0;
    const drag = Math.exp(-(distance < SETTLE_RADIUS ? SETTLE_DRAG : AIR_DRAG) * seconds);
    this._velocity = {
      x: (this._velocity.x + dx * pull * seconds) * drag,
      y: (this._velocity.y + dy * pull * seconds) * drag,
    };
    this._move(rect.left + this._velocity.x * seconds, rect.top + this._velocity.y * seconds);
    return false;
  }

  _arrive(target) {
    this._velocity = { x: 0, y: 0 };
    this._move(target.left, target.top);
    return true;
  }

  _move(left, top) {
    this._dock.style.left = `${left}px`;
    this._dock.style.top = `${top}px`;
    this._dock.style.right = "auto";
    this._dock.style.bottom = "auto";
  }
}
