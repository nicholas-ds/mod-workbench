// The agents pills: one line per running GLM worker of the thread's orchestrator, blue tinted.

import { WorkingPill } from "./working_pill.js";

export class AgentsPill {
  // Nodes to add after the last message: one pill per running worker, nothing otherwise.
  static trailing(agents) {
    return agents.map((agent) => WorkingPill.build(AgentsPill.label(agent), "working-in-thread agents-pill"));
  }

  // "title - last step - N calls": what the worker does now, not only that it runs.
  static label(agent) {
    const step = [agent.last_tool, agent.last_file].filter(Boolean).join(" ");
    const parts = [agent.title, step, agent.progress, `${agent.tool_calls} calls`].filter(Boolean);
    return parts.join(" · ");
  }
}
