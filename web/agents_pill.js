// The agents pill: running GLM workers of the thread's orchestrator, blue tinted.

import { WorkingPill } from "./working_pill.js";

export class AgentsPill {
  // Nodes to add after the last message: the pill while workers run, nothing otherwise.
  static trailing(count) {
    return count > 0 ? [WorkingPill.build(`agents ${count}`, "working-in-thread agents-pill")] : [];
  }
}
