// A table with a clay scroll bar of our own, so it looks the same on every browser and screen scale.
// The native bar is hidden. Keyboard: the scroll area takes focus while it overflows; arrow keys scroll it.

import { DomBuilder } from "./dom_builder.js";

const MIN_THUMB_PX = 40;

export class ScrollableTable {
  static wrap(content) {
    const holder = DomBuilder.el("div", "scrollable");
    const scroller = DomBuilder.el("div", "table-scroll");
    scroller.appendChild(content);
    const thumb = DomBuilder.el("div", "scroll-thumb");
    const track = DomBuilder.el("div", "scroll-track");
    track.appendChild(thumb);
    holder.append(scroller, track);
    new ScrollableTable(scroller, track, thumb).bind();
    return holder;
  }

  constructor(scroller, track, thumb) {
    this._scroller = scroller;
    this._track = track;
    this._thumb = thumb;
  }

  bind() {
    const redraw = () => this._redraw();
    this._scroller.addEventListener("scroll", redraw, { passive: true });
    new ResizeObserver(redraw).observe(this._scroller);
    new ResizeObserver(redraw).observe(this._scroller.firstElementChild);
    this._thumb.addEventListener("pointerdown", (event) => this._startDrag(event));
    this._track.addEventListener("pointerdown", (event) => this._pageToward(event));
  }

  _overflow() {
    return this._scroller.scrollWidth - this._scroller.clientWidth;
  }

  // The thumb sits inset in the groove by the same amount on every side; its top offset is that inset.
  _inset() {
    return this._thumb.offsetTop;
  }

  _thumbWidth() {
    const share = this._scroller.clientWidth / this._scroller.scrollWidth;
    return Math.max(MIN_THUMB_PX, (this._track.clientWidth - 2 * this._inset()) * share);
  }

  _travel() {
    return this._track.clientWidth - 2 * this._inset() - this._thumbWidth();
  }

  _redraw() {
    const overflow = this._overflow();
    this._track.hidden = overflow <= 0;
    this._scroller.tabIndex = overflow > 0 ? 0 : -1;
    if (overflow <= 0) return;
    this._thumb.style.width = `${this._thumbWidth()}px`;
    this._thumb.style.left = `${this._inset() + (this._scroller.scrollLeft / overflow) * this._travel()}px`;
  }

  _startDrag(event) {
    event.preventDefault();
    this._thumb.setPointerCapture(event.pointerId);
    const startX = event.clientX;
    const startLeft = this._scroller.scrollLeft;
    const travel = this._travel();
    const move = (moveEvent) => {
      this._scroller.scrollLeft = startLeft + ((moveEvent.clientX - startX) / travel) * this._overflow();
    };
    const stop = () => {
      this._thumb.removeEventListener("pointermove", move);
      this._thumb.removeEventListener("pointerup", stop);
    };
    this._thumb.addEventListener("pointermove", move);
    this._thumb.addEventListener("pointerup", stop);
  }

  _pageToward(event) {
    if (event.target !== this._track) return;
    const thumbLeft = this._thumb.getBoundingClientRect().left;
    const direction = event.clientX < thumbLeft ? -1 : 1;
    this._scroller.scrollBy({ left: direction * this._scroller.clientWidth, behavior: "smooth" });
  }
}
