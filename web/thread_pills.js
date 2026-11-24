// The trailing pills of a thread: the working pill plus one detailed pill per running worker.

import { AgentsPill } from "./agents_pill.js";
import { WorkingPill } from "./working_pill.js";

export class ThreadPills {
  // Nodes to add after the last message: the working pill while the thread runs,
  // then one detailed agent pill per running worker (AgentsPill.label).
  static trailing(running, name, agents) {
    return [...WorkingPill.trailing(running, name), ...AgentsPill.trailing(agents)];
  }
}
