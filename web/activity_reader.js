// Reads one mod row and names the live rail state, with the task line and tooltip.

const STALE_MS = 30 * 60 * 1000;
const STUCK_MS = 5 * 60 * 1000;
const MIN_MS = 60 * 1000;

const COUNTING_ACTIVITY = ["working", "worker", "needs-you"];
const STATE_ORDER = ["needs-you", "stuck", "worker", "working"];
const TOOLTIP = { "needs-you": "waiting on you", worker: "waiting on a worker", working: "working" };

export class ActivityReader {
  static read(row, now = Date.now()) {
    const entries = ActivityReader._entries(row, now);
    const state = entries.length === 0 ? "idle" : ActivityReader._winningState(entries);
    const winner = entries.find((entry) => entry.state === state);
    return {
      state,
      working: entries.length > 0,
      task: ActivityReader._task(entries),
      tooltip: entries.length === 0 ? "idle" : ActivityReader._tooltip(state, winner, now),
      fine: ActivityReader._fine(row, state, winner, now),
    };
  }

  static _entries(row, now) {
    return (row.status ?? [])
      .map((entry) => entry.values ?? {})
      .filter((values) => ActivityReader._counts(values, now))
      .map((values) => ({ values, state: ActivityReader._entryState(values, now) }));
  }

  static _counts(values, now) {
    if (!COUNTING_ACTIVITY.includes(values.activity)) return false;
    const since = Date.parse(values.activity_at ?? "");
    return Number.isNaN(since) || now - since < STALE_MS;
  }

  static _entryState(values, now) {
    if (values.activity === "needs-you") return "needs-you";
    if (values.activity === "worker") return "worker";
    const since = Date.parse(values.last_tool_at ?? values.activity_at ?? "");
    return !Number.isNaN(since) && now - since > STUCK_MS ? "stuck" : "working";
  }

  static _winningState(entries) {
    return STATE_ORDER.find((state) => entries.some((entry) => entry.state === state)) ?? "working";
  }

  static _task(entries) {
    return entries.map((entry) => entry.values.task).find((text) => typeof text === "string" && text) ?? null;
  }

  static _tooltip(state, winner, now) {
    const base = state === "stuck" ? ActivityReader._stuckLine(winner, now) : (TOOLTIP[state] ?? "idle");
    return base + ActivityReader._lastToolLine(winner, now);
  }

  static _unbreakable(part) {
    return part.replaceAll(" ", " ");
  }

  static _fine(row, state, winner, now) {
    if (state === "idle") {
      const agents = row.agents ?? 0;
      const stalled = row.stalled_agents ?? 0;
      return agents === 0 && stalled === 0 ? "" : ActivityReader._agentsLine(row);
    }
    const parts = [
      ActivityReader._lastFileLine(winner),
      ActivityReader._agentsLine(row),
      ActivityReader._toolCallsLine(winner),
      state === "stuck" ? ActivityReader._quietLine(winner, now) : null,
    ].filter((part) => part);
    return parts.map(ActivityReader._unbreakable).join(" · ");
  }

  static _lastFileLine(winner) {
    const file = winner.values.last_file;
    return typeof file === "string" && file ? file : null;
  }

  static _agentsLine(row) {
    const agents = row.agents ?? 0;
    const stalled = row.stalled_agents ?? 0;
    const parts = [
      agents > 0 ? `${agents} agent${agents === 1 ? "" : "s"}` : null,
      stalled > 0 ? `${stalled} stalled` : null,
    ].filter((part) => part);
    return parts.map(ActivityReader._unbreakable).join(" · ");
  }

  static _toolCallsLine(winner) {
    const calls = winner.values.tool_calls;
    if (typeof calls !== "number" || calls <= 0) return null;
    return `${calls} tool call${calls === 1 ? "" : "s"}`;
  }

  static _quietLine(entry, now) {
    return `quiet ${ActivityReader._quietMinutes(entry, now)} min`;
  }

  static _quietMinutes(entry, now) {
    const since = Date.parse(entry.values.last_tool_at ?? entry.values.activity_at ?? "");
    return Number.isNaN(since) ? 0 : Math.floor((now - since) / MIN_MS);
  }

  static _stuckLine(entry, now) {
    return `stuck? no tool call for ${ActivityReader._quietMinutes(entry, now)} min`;
  }

  static _lastToolLine(entry, now) {
    const tool = entry.values.last_tool;
    if (typeof tool !== "string" || !tool) return "";
    const since = Date.parse(entry.values.last_tool_at ?? "");
    if (Number.isNaN(since)) return "";
    const gap = now - since;
    const age = gap < MIN_MS ? `${Math.floor(gap / 1000)} s` : `${Math.floor(gap / MIN_MS)} min`;
    return `. last tool: ${tool}, ${age} ago`;
  }
}
