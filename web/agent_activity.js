// Polls the agent registry and repo rows, and tells listeners when any agent or worker is running.

const POLL_MS = 3000;
const SURFACES_MS = 15000;
const RUNNING_STATE = "running";
const CHAT_SOURCE = "claude";
const SURFACE_KEY = "wmux_surface";
const THREAD_SEPARATOR = "~";

// Pane ids per mod row: each status file may register its orchestrator pane (wmux_surface).
function surfacesByMod(rows) {
  const map = new Map();
  for (const row of rows) {
    if (row.error) continue;
    const surfaces = new Set((row.status ?? [])
      .map((entry) => entry.values?.[SURFACE_KEY])
      .filter((surface) => typeof surface === "string" && surface !== ""));
    if (surfaces.size > 0) map.set(row.name, surfaces);
  }
  return map;
}

// A chat thread name is "<orchestrator>~<id>"; dock pane threads pass the bare mod name.
function orchestratorOf(threadName) {
  const at = threadName.lastIndexOf(THREAD_SEPARATOR);
  return at === -1 ? threadName : threadName.slice(0, at);
}

export class AgentActivity {
  constructor(api) {
    this._api = api;
    this._runningCwd = null;
    this._agents = [];
    this._surfaces = new Map();
    this._listeners = new Set();
  }

  start() {
    this._poll();
    this._pollSurfaces();
    setInterval(() => this._poll(), POLL_MS);
    setInterval(() => this._pollSurfaces(), SURFACES_MS);
  }

  isRunning() {
    return this._runningCwd !== null;
  }

  // Working folder of the first running agent: it names the repo whose terminal pane holds the conversation.
  target() {
    return this._runningCwd;
  }

  // Running GLM workers of the orchestrator that owns the thread: the thread name maps to
  // a repo row, the row's status files carry the pane ids the workers report.
  runningFor(threadName) {
    if (!threadName) return 0;
    const surfaces = this._surfaces.get(orchestratorOf(threadName));
    if (surfaces === undefined) return 0;
    return this._agents.filter((agent) => agent.shown_state === RUNNING_STATE
      && agent.source !== CHAT_SOURCE && agent.registered
      && surfaces.has(agent.orchestrator)).length;
  }

  subscribe(listener) {
    this._listeners.add(listener);
  }

  async _poll() {
    try {
      const { agents } = await this._api.agents();
      const running = agents.find((agent) => agent.shown_state === RUNNING_STATE);
      this._runningCwd = running ? running.cwd : null;
      this._agents = agents;
    } catch {
      return;
    }
    for (const listener of this._listeners) listener();
  }

  async _pollSurfaces() {
    try {
      const { rows } = await this._api.mods();
      this._surfaces = surfacesByMod(rows);
    } catch {
      return;
    }
  }
}
