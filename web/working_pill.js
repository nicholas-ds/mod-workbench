// The loading pill: an agent name and three dots that flicker in turn. Same shape as every clay pill.

import { DomBuilder } from "./dom_builder.js";

const DOT_COUNT = 3;

export class WorkingPill {
  static build(label, extraClass = "", tag = "span") {
    const pill = DomBuilder.el(tag, `clay-button clay-quiet working-pill ${extraClass}`.trim(), label);
    const dots = DomBuilder.el("span", "working-dots");
    for (let index = 0; index < DOT_COUNT; index += 1) dots.appendChild(DomBuilder.el("i", ""));
    pill.appendChild(dots);
    return pill;
  }

  // Nodes to add after the last message: the pill while the agent runs, nothing otherwise.
  static trailing(running, name) {
    return running ? [WorkingPill.build(name, "working-in-thread")] : [];
  }
}
