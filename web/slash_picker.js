// Slash command picker: a filtered command list that opens on an input while
// the author types a "/command". One picker serves the chat form and the
// message dock; the host places node() itself (placement rules in chat.css).

import { DomBuilder } from "./dom_builder.js";

const CACHE_MS = 60000;

/**
 * One runnable chat command as the backend reports it.
 * @typedef {{name: string, description: string}} SlashCommand
 */
export {};

export class SlashPicker {
  /**
   * Watch one chat input and show the command list while its text starts
   * with a single leading "/". Fetches through loadCommands on first open,
   * then serves a 60 second cache.
   *
   * @param {HTMLTextAreaElement|HTMLInputElement} input the chat input to watch
   * @param {() => Promise<SlashCommand[]>} loadCommands loads the command list
   */
  constructor(input, loadCommands) {
    this._input = input;
    this._loadCommands = loadCommands;
    this._commands = [];
    this._fetchedAt = 0;
    this._pending = null;
    this._stamp = 0;
    this._rows = [];
    this._selected = 0;
    this._list = DomBuilder.el("ul", "slash-picker");
    this._list.hidden = true;
    // Load on focus: the first load starts a session client and takes seconds.
    this._input.addEventListener("focus", () => this._cachedCommands());
    this._input.addEventListener("input", () => this._onInput());
    // The capture flag does not order listeners on the input itself, so the
    // host must build this picker before it adds its Enter-to-send listener;
    // stopImmediatePropagation then keeps sending out of the way.
    this._input.addEventListener("keydown", (event) => this._onKeydown(event), true);
  }

  /** @returns {HTMLElement} the list element, to place just above the input */
  node() {
    return this._list;
  }

  /** @returns {void} */
  _close() {
    this._stamp += 1;
    this._list.hidden = true;
    this._rows = [];
  }

  /** @returns {Promise<void>} */
  async _onInput() {
    const value = this._input.value;
    const query = value.startsWith("/") ? value.slice(1) : "";
    if (!value.startsWith("/") || /\s/.test(query)) {
      // No leading slash, or space after a full name: the author moved on.
      this._close();
      return;
    }
    const stamp = ++this._stamp;
    const commands = await this._cachedCommands();
    if (stamp !== this._stamp) return;
    this._show(this._filter(commands, query));
  }

  /** @returns {Promise<SlashCommand[]>} the cached list, refreshed at most every 60 s */
  async _cachedCommands() {
    if (Date.now() - this._fetchedAt < CACHE_MS) return this._commands;
    // The first load starts a session client and is slow: share one request.
    if (!this._pending) this._pending = this._fetchCommands();
    return this._pending;
  }

  /** @returns {Promise<SlashCommand[]>} a fresh list, [] on failure */
  async _fetchCommands() {
    try {
      this._commands = await this._loadCommands();
    } catch {
      this._commands = [];
    }
    this._fetchedAt = Date.now();
    this._pending = null;
    return this._commands;
  }

  /**
   * Name matches first, then description, case-insensitive; names that start
   * with the typed text come first.
   *
   * @param {SlashCommand[]} commands the full command list
   * @param {string} query the text typed after the "/"
   * @returns {SlashCommand[]} the filtered, ranked commands
   */
  _filter(commands, query) {
    const needle = query.toLowerCase();
    const ranked = [];
    for (const command of commands) {
      const name = String(command.name ?? "").toLowerCase();
      const description = String(command.description ?? "").toLowerCase();
      let rank = -1;
      if (name.startsWith(needle)) rank = 0;
      else if (name.includes(needle)) rank = 1;
      else if (description.includes(needle)) rank = 2;
      if (rank >= 0) ranked.push({rank: rank, command: command});
    }
    ranked.sort((a, b) => a.rank - b.rank || a.command.name.localeCompare(b.command.name));
    return ranked.map((entry) => entry.command);
  }

  /** @param {SlashCommand[]} commands the rows to show, closes when empty */
  _show(commands) {
    if (commands.length === 0) {
      this._close();
      return;
    }
    this._rows = commands;
    this._selected = 0;
    this._list.replaceChildren(...commands.map((command, index) => this._row(command, index)));
    this._list.hidden = false;
    this._highlight();
  }

  /**
   * @param {SlashCommand} command the row's command
   * @param {number} index the row's index in this._rows
   * @returns {HTMLElement} the list row
   */
  _row(command, index) {
    const row = DomBuilder.el("li", "slash-row");
    row.append(
      DomBuilder.el("span", "slash-row-name", `/${command.name}`),
      DomBuilder.el("span", "slash-row-description", command.description),
    );
    row.addEventListener("click", () => this._insert(index));
    return row;
  }

  /** @returns {void} */
  _highlight() {
    const rows = this._list.children;
    for (let index = 0; index < rows.length; index += 1) {
      rows[index].classList.toggle("is-selected", index === this._selected);
    }
    const selected = rows[this._selected];
    if (selected) selected.scrollIntoView({block: "nearest"});
  }

  /** @param {number} delta the step, wraps at both ends */
  _move(delta) {
    const count = this._rows.length;
    if (count === 0) return;
    this._selected = (this._selected + delta + count) % count;
    this._highlight();
  }

  /** @param {number} index the row to insert as "/name " into the input */
  _insert(index) {
    const command = this._rows[index];
    if (!command) return;
    this._input.value = `/${command.name} `;
    this._close();
    this._input.focus();
  }

  /**
   * Handle the keys the open list owns; with the list closed every key keeps
   * its meaning, so Enter still sends as before.
   *
   * @param {KeyboardEvent} event the input's keydown
   * @returns {void}
   */
  _onKeydown(event) {
    if (this._list.hidden) return;
    if (event.key === "ArrowDown") this._move(1);
    else if (event.key === "ArrowUp") this._move(-1);
    else if (event.key === "Enter" || event.key === "Tab") this._insert(this._selected);
    else if (event.key === "Escape") this._close();
    else return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
  }
}
