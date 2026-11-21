// Session resume picker: a session list that opens on the chat input while
// the author types "/resume". The host places node() itself and handles the
// picked session; placement rules live in chat.css.

import { DomBuilder } from "./dom_builder.js";

const OPEN_RE = /^\/resume\s+$/;
const MINUTE_MS = 60000;
const HOUR_MS = 3600000;
const DAY_MS = 86400000;

/**
 * One chat session as the picker shows it.
 * @typedef {{session_id: string, title: string, last_modified_ms: number}} SessionSummary
 */
export {};

export class ResumePicker {
  /**
   * Watch one chat input and show the session list while its text is exactly
   * "/resume" plus whitespace. Sessions load fresh on every open; picking one
   * clears the input and hands the session to onPick.
   *
   * @param {HTMLTextAreaElement|HTMLInputElement} input the chat input to watch
   * @param {() => Promise<SessionSummary[]>} loadSessions loads the session list
   * @param {(session: SessionSummary) => void} onPick receives the picked session
   */
  constructor(input, loadSessions, onPick) {
    this._input = input;
    this._loadSessions = loadSessions;
    this._onPick = onPick;
    this._rows = [];
    this._selected = 0;
    this._stamp = 0;
    this._list = DomBuilder.el("ul", "slash-picker");
    this._list.hidden = true;
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
    if (!OPEN_RE.test(this._input.value)) {
      // Anything but a bare "/resume" plus spaces: the author moved on.
      this._close();
      return;
    }
    const stamp = ++this._stamp;
    let sessions;
    try {
      sessions = await this._loadSessions();
    } catch {
      sessions = [];
    }
    // A late answer for a list that closed meanwhile stays hidden.
    if (stamp !== this._stamp) return;
    this._show(sessions);
  }

  /** @param {SessionSummary[]} sessions the rows to show, closes when empty */
  _show(sessions) {
    if (sessions.length === 0) {
      this._close();
      return;
    }
    this._rows = sessions;
    this._selected = 0;
    this._list.replaceChildren(...sessions.map((session, index) => this._row(session, index)));
    this._list.hidden = false;
    this._highlight();
  }

  /**
   * @param {SessionSummary} session the row's session
   * @param {number} index the row's index in this._rows
   * @returns {HTMLElement} the list row
   */
  _row(session, index) {
    const row = DomBuilder.el("li", "slash-row");
    row.append(
      DomBuilder.el("span", "slash-row-name", session.title),
      DomBuilder.el("span", "slash-row-description", this._ageText(session.last_modified_ms)),
    );
    row.addEventListener("click", () => this._pick(index));
    return row;
  }

  /**
   * Pure: reads only the clock and its argument.
   * @param {number} ms the session's last_modified_ms timestamp
   * @returns {string} a short relative age
   */
  _ageText(ms) {
    const age = Date.now() - ms;
    if (!Number.isFinite(age) || age < MINUTE_MS) return "just now";
    if (age < HOUR_MS) return `${Math.floor(age / MINUTE_MS)} min ago`;
    if (age < DAY_MS) return `${Math.floor(age / HOUR_MS)} h ago`;
    if (age < 2 * DAY_MS) return "yesterday";
    return `${Math.floor(age / DAY_MS)} days ago`;
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

  /** @param {number} index the row to pick */
  _pick(index) {
    const session = this._rows[index];
    if (!session) return;
    this._input.value = "";
    this._close();
    this._input.focus();
    this._onPick(session);
  }

  /**
   * Keys the open list owns; closed, every key keeps its meaning.
   * @param {KeyboardEvent} event the input's keydown
   */
  _onKeydown(event) {
    if (this._list.hidden) return;
    if (event.key === "ArrowDown") this._move(1);
    else if (event.key === "ArrowUp") this._move(-1);
    else if (event.key === "Enter") this._pick(this._selected);
    else if (event.key === "Escape") this._close();
    else return;
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
  }
}
