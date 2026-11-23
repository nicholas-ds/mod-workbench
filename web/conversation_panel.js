// One conversation surface: open a conversation, draw it once, pin it to the
// latest message, and keep the input focused (conversation audit plan, task T5).
// ChatView (chat tab) and MessageDock (bottom popup) extend this and add only
// what differs for their surface.

import { AgentsPill } from "./agents_pill.js";
import { ScrollAnchor } from "./scroll_anchor.js";
import { ResumeControl } from "./resume_control.js";
import { SlashCommandsClient } from "./slash_commands_client.js";
import { SlashPicker } from "./slash_picker.js";
import { WorkingPill } from "./working_pill.js";

export class ConversationPanel {
  constructor(session, transcripts) {
    this._session = session;
    this._transcripts = transcripts;
    this._agents = null;    // set by subclasses that draw agent pills
    this._renderer = null;  // set by subclasses that draw from a transcript renderer
    this._key = null;       // the conversation currently shown
    this._input = null;     // the text field, created by the subclass form
  }

  // One pipeline per open: restore the history, take the snapshot, render it,
  // pin the view to the latest message, focus the input. One refresh per open;
  // history that lands later redraws through the transcript store event.
  async open(key) {
    this._key = key;
    if (key !== null) this._restore(key);
    await this._renderConversation(key);
    this._conversationOpened(key);
    this._pinToLatest();
    this.focusInput();
  }

  // History lands after the snapshot is drawn; the store event redraws with it.
  _restore(key) {
    this._session.restore(key).then(() => this._session.resume(key));
  }

  /** Draw conversation `key` and make it the visible one. May return a promise. */
  _renderConversation(key) {
    this._threadNode().replaceChildren(...this._conversationNodes(key));
  }

  /** The snapshot of `key`: messages plus the trailing working and agents pills. */
  _conversationNodes(key) {
    const nodes = this._renderer.render(this._transcripts.items(key), key);
    const working = WorkingPill.trailing(this._transcripts.isRunning(key), key);
    const agents = AgentsPill.trailing(this._agents.runningAgentsFor(key));
    return [...nodes, ...working, ...agents];
  }

  /** Called after the draw, before pin and focus: update the surface state. */
  _conversationOpened() {}

  /** The scroll container holding the drawn conversation. */
  _threadNode() {
    return this._thread;
  }

  // Jump to the newest content no matter where the viewer was.
  _pinToLatest() {
    ScrollAnchor.pinToLatest(this._threadNode());
  }

  // The one focus path: on open, on target pick, on switch, after a turn ends.
  focusInput() {
    if (this._input !== null && !this._input.disabled) {
      this._input.focus({ preventScroll: true });
    }
  }

  /** True while conversation `key` is mid-turn. */
  _isRunning(key) {
    return key !== null && this._transcripts.isRunning(key);
  }

  // The picker and resume control for the input. The picker is created before
  // the Enter-to-send listener so its keydown wins by registration order.
  _makeInputHelpers(getKey, onResumeDone) {
    this._commands = new SlashCommandsClient();
    this._picker = new SlashPicker(this._input, () => this._commands.load(getKey()));
    this._resume = new ResumeControl(this._input, this._session, this._transcripts, getKey, onResumeDone);
  }

  // Enter sends; Shift+Enter makes a new line.
  _sendOnEnter(action) {
    this._input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
      event.preventDefault();
      action();
    });
  }
}
