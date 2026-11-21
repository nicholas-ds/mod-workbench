// The /resume control of one chat input: lists saved sessions under the input
// and switches the chat to the session the author picks.

import { ResumePicker } from "./resume_picker.js";
import { SessionResumeClient } from "./session_resume_client.js";

export class ResumeControl {
  /**
   * @param {HTMLTextAreaElement|HTMLInputElement} input the chat input to watch
   * @param {import("./chat_session.js").ChatSession} session restores the transcript after a switch
   * @param {import("./chat_transcripts.js").ChatTranscripts} transcripts the shared transcript store
   * @param {() => string|null} nameOf the chat name the input talks to now
   * @param {() => void} onSwitched called after the chat shows the picked session
   */
  constructor(input, session, transcripts, nameOf, onSwitched) {
    this._session = session;
    this._transcripts = transcripts;
    this._nameOf = nameOf;
    this._onSwitched = onSwitched;
    this._client = new SessionResumeClient();
    this._picker = new ResumePicker(
      input,
      () => this._load(),
      (picked) => this._switchTo(picked.session_id),
    );
  }

  /** @returns {HTMLElement} the list element, to place next to the slash list */
  node() {
    return this._picker.node();
  }

  async _load() {
    const name = this._nameOf();
    return name === null ? [] : this._client.list(name);
  }

  async _switchTo(sessionId) {
    const name = this._nameOf();
    if (name === null) return;
    if (this._transcripts.isRunning(name) || !(await this._client.resume(name, sessionId))) {
      this._transcripts.add(name, { kind: "error", text: "Could not resume that session." });
      return;
    }
    this._transcripts.clear(name);
    await this._session.forget(name);
    await this._session.restore(name);
    this._onSwitched();
  }
}
