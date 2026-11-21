// One status chip per mod: the mod name, a state color and the age of the last
// activity. Every surface that shows mod status builds its chips through this
// class. State colors come from the --chip-* tokens in tokens.css.

import { DomBuilder } from "./dom_builder.js";

// An activity older than this while a task is open counts as stalled.
const STALE_LIMIT_MS = 2 * 60 * 60 * 1000;
const SECOND_MS = 1000;
const MINUTE_MS = 60 * SECOND_MS;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

const RUNNING = "running";
const NEEDS_YOU = "needs-you";
// An agent outcome other than ok means the work went nowhere
// (workbench/agent_outcome.py): dropped, stalled, abandoned or empty.
const LOST = "lost";
const OK_OUTCOME = "ok";
// Agent source (the event feed it reports through) mapped to its chip state.
const SOURCE_STATES = { claude: "claude", opencode: "glm" };

// The chip look, from tokens only: a small calm pill in the state tint.
// min-width:0 lets the chip shrink inside a narrow rail row; flex-wrap:nowrap
// and white-space:nowrap keep name and age on one line (.rail span would
// otherwise leak flex-wrap:wrap into the chip and wrap the age underneath).
const CHIP_STYLE = "display:inline-flex;align-items:baseline;gap:var(--space-sm);"
  + "min-width:0;flex-wrap:nowrap;white-space:nowrap;max-width:100%;"
  + "padding:var(--space-xs) var(--space-md);font:800 var(--font-size-hint)/1.2 var(--font-body);"
  + "font-style:normal;color:var(--color-ink);"
  + "background:var(--clay-grain),var(--clay-lit),var(--clay-color);"
  + "border-radius:12px 16px 14px 18px / 16px 14px 18px 12px;";
const AGE_STYLE = "font:500 var(--font-size-hint) var(--font-mono);font-style:normal;";
// The name part truncates with an ellipsis when the row is too narrow. It is a
// span inside .rail, so it also resets the card look (.rail span) that would
// otherwise draw padding, background and shadow inside the chip; font:inherit
// keeps the chip font. The full name stays in the span tooltip.
const NAME_STYLE = "display:inline-block;min-width:0;overflow:hidden;"
  + "white-space:nowrap;text-overflow:ellipsis;font:inherit;"
  + "padding:0;background:none;box-shadow:none;border-radius:0;";

export class AgentChip {
  /** One chip element for a mod row (/api/mods) and the agent list (/api/agents). */
  static build(modRow, agents, now = Date.now()) {
    const state = AgentChip.state(modRow, agents, now);
    const chip = DomBuilder.el("span", "agent-chip");
    chip.style.cssText = CHIP_STYLE;
    chip.style.setProperty("--clay-color", `var(--chip-${state})`);
    const name = DomBuilder.el("span", null, modRow.name);
    name.style.cssText = NAME_STYLE;
    name.title = modRow.name;
    chip.appendChild(name);
    const age = AgentChip._ageText(AgentChip._newestActivity(modRow), now);
    chip.title = AgentChip._tooltip(state, modRow, agents, age);
    if (age) {
      const ageNode = DomBuilder.el("em", null, age);
      ageNode.style.cssText = AGE_STYLE;
      chip.appendChild(ageNode);
    }
    return chip;
  }

  /** Whether one agent (its working folder) belongs to one mod repo. */
  static covers(repo, cwd) {
    const base = AgentChip._normalize(repo);
    if (base === "") return false;
    const folder = AgentChip._normalize(cwd);
    return folder === base || folder.startsWith(`${base}/`);
  }

  /** The chip state: waits-author first, then lost, then running, then file age. */
  static state(modRow, agents, now = Date.now()) {
    const own = (agents ?? []).filter((agent) => AgentChip.covers(modRow.repo, agent.cwd));
    const statuses = (modRow.status ?? []).map((entry) => entry.values ?? {});
    if (own.some((agent) => agent.shown_state === NEEDS_YOU)
        || statuses.some((values) => values.activity === NEEDS_YOU && AgentChip._fresh(values, now))) {
      return "waits-author";
    }
    // A lost agent outranks a running one, so the loss stays visible.
    if (own.some((agent) => AgentChip._isLost(agent))) return LOST;
    for (const agent of own) {
      if (agent.shown_state === RUNNING && SOURCE_STATES[agent.source]) return SOURCE_STATES[agent.source];
    }
    const newest = AgentChip._newestActivity(modRow);
    if (newest === null) return "stale";
    const taskOpen = statuses.some((values) => typeof values.task === "string" && values.task);
    if (taskOpen && now - newest > STALE_LIMIT_MS) return "stalled";
    if (!taskOpen && now - newest <= STALE_LIMIT_MS) return "idle";
    return "stale";
  }

  /** The chip tooltip: lost agents get one "<title>: <outcome> - <reason>" line each. */
  static _tooltip(state, modRow, agents, age) {
    if (state !== LOST) return age ? `${state} · last activity ${age} ago` : state;
    return (agents ?? [])
      .filter((agent) => AgentChip.covers(modRow.repo, agent.cwd) && AgentChip._isLost(agent))
      .map((agent) => `${agent.title}: ${agent.outcome} - ${agent.outcome_reason}`)
      .join("\n");
  }

  static _isLost(agent) {
    return Boolean(agent.outcome) && agent.outcome !== OK_OUTCOME;
  }

  static _fresh(values, now) {
    const at = Date.parse(values.activity_at ?? "");
    return !Number.isNaN(at) && now - at <= STALE_LIMIT_MS;
  }

  static _newestActivity(modRow) {
    let newest = null;
    for (const entry of modRow.status ?? []) {
      const at = Date.parse((entry.values ?? {}).activity_at ?? "");
      if (!Number.isNaN(at) && (newest === null || at > newest)) newest = at;
    }
    return newest;
  }

  static _ageText(newest, now) {
    if (newest === null) return "";
    const gap = Math.max(0, now - newest);
    if (gap < MINUTE_MS) return `${Math.floor(gap / SECOND_MS)}s`;
    if (gap < HOUR_MS) return `${Math.floor(gap / MINUTE_MS)}m`;
    if (gap < DAY_MS) return `${Math.floor(gap / HOUR_MS)}h`;
    return `${Math.floor(gap / DAY_MS)}d`;
  }

  static _normalize(path) {
    return String(path ?? "").replaceAll("\\", "/").replace(/\/+$/, "").toLowerCase();
  }
}
