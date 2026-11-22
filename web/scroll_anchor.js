// ScrollAnchor: one place decides how a transcript follows new content.
// Used by the chat tab and the message dock popup so both scroll the same way
// (conversation audit plan, task T1).

export class ScrollAnchor {
  // True when the element is scrolled to the bottom, within 40 px.
  static isNearBottom(el) {
    if (!el) return false;
    return el.scrollHeight - el.scrollTop - el.clientHeight <= 40;
  }

  // Jump to the newest content no matter where the viewer was.
  static pinToLatest(el) {
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }

  // Keep pace with new content only if the viewer was already at the bottom.
  static follow(el, wasNearBottom) {
    if (wasNearBottom) this.pinToLatest(el);
  }
}
