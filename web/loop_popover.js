// Popover opened from the loop pill: one entry per loop, with Retry where allowed.

import { DomBuilder } from "./dom_builder.js";

export class LoopPopover {
  static open(anchor, loops, options) {
    LoopPopover.close();
    const popover = DomBuilder.el("div", "loop-popover");
    for (const loop of loops) popover.appendChild(LoopPopover._entry(loop, options));
    anchor.appendChild(popover);
    document.addEventListener("keydown", LoopPopover._onKey);
    document.addEventListener("click", LoopPopover._onOutside);
  }

  static close() {
    const open = document.querySelector(".loop-popover");
    if (open) open.remove();
    document.removeEventListener("keydown", LoopPopover._onKey);
    document.removeEventListener("click", LoopPopover._onOutside);
  }

  static _onKey(event) {
    if (event.key === "Escape") LoopPopover.close();
  }

  static _onOutside(event) {
    if (!event.target.closest(".loop-popover")) LoopPopover.close();
  }

  static _entry(loop, options) {
    const entry = DomBuilder.el("div", "loop-entry");
    entry.appendChild(DomBuilder.el("b", "loop-board", String(loop.board ?? "")));
    if (loop.reason) entry.appendChild(DomBuilder.el("p", "loop-reason", String(loop.reason)));
    if (loop.summary) entry.appendChild(DomBuilder.el("p", "loop-summary", String(loop.summary)));
    if (loop.can_retry) entry.appendChild(LoopPopover._retry(loop, options));
    return entry;
  }

  static _retry(loop, options) {
    const button = DomBuilder.el("button", "loop-retry", "Retry");
    button.addEventListener("click", async () => {
      LoopPopover.close();
      await options.api.retryNotice(options.modName, loop.notice_id);
      options.onRetried();
    });
    return button;
  }
}
