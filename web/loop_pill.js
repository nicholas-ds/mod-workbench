// The live-loop pill shown in a rail row, worst loop first.

import { DomBuilder } from "./dom_builder.js";

const LABEL = { sending: "Sending", got_it: "Got it", working: "Working", done: "Done", stuck: "Stuck" };
const MIN_S = 60;
const HOUR_S = 3600;

export class LoopPillView {
  static render(loops, now) {
    const loop = loops[0];
    if (!loop) return null;
    const pill = DomBuilder.el("i", `loop-pill loop-${String(loop.stage ?? "").replaceAll("_", "-")}`);
    pill.appendChild(DomBuilder.el("i", "loop-dot"));
    pill.appendChild(document.createTextNode(LoopPillView._text(loop, now)));
    if (loops.length > 1) pill.appendChild(DomBuilder.el("i", "loop-more", `+${loops.length - 1}`));
    pill.title = LoopPillView._title(loop);
    const slot = DomBuilder.el("i", "loop-slot");
    slot.appendChild(pill);
    return slot;
  }

  static _text(loop, now) {
    let text = `${LoopPillView._label(loop.stage)}${loop.reason ? ` · ${loop.reason}` : ""}`;
    const age = LoopPillView._age(loop.since, now);
    return age ? `${text} ${age}` : text;
  }

  static _label(stage) {
    return LABEL[stage] ?? String(stage ?? "");
  }

  static _age(since, now) {
    const start = Date.parse(since ?? "");
    if (Number.isNaN(start)) return null;
    const nowMs = now instanceof Date ? now.getTime() : now;
    const seconds = Math.max(0, Math.floor((nowMs - start) / 1000));
    if (seconds < MIN_S) return `${seconds}s`;
    if (seconds < HOUR_S) return `${Math.floor(seconds / MIN_S)}m`;
    return `${Math.floor(seconds / HOUR_S)}h`;
  }

  static _title(loop) {
    const parts = [loop.board];
    if (loop.last_action) parts.push(loop.last_action);
    if (loop.summary) parts.push(loop.summary);
    return parts.join(" · ");
  }
}
