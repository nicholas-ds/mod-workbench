// One chat turn against the stream, recorded into the shared transcript store.

import { TranscriptItemMapper } from "./transcript_item_mapper.js";

export class ChatSession {
  constructor(chatStream, transcripts) {
    this._chatStream = chatStream;
    this._transcripts = transcripts;
    this._mapper = new TranscriptItemMapper();
    this._restored = new Set();
    this._resumed = new Set();
  }

  async send(name, text, shownText = text) {
    if (this._transcripts.isRunning(name)) return;
    this._transcripts.add(name, { kind: "user", text: shownText });
    this._transcripts.setRunning(name, true);
    try {
      await this._chatStream.send(name, text, (event) => this._apply(name, event));
    } catch (error) {
      this._transcripts.add(name, { kind: "error", text: String(error) });
    } finally {
      this._transcripts.setRunning(name, false);
    }
  }

  async resume(name) {
    if (this._resumed.has(name)) return;
    this._resumed.add(name);
    await this.follow(name);
  }

  async follow(name) {
    if (this._transcripts.isRunning(name)) return;
    let started = false;
    try {
      await this._chatStream.follow(name, (event) => {
        if (!started) {
          started = true;
          this._applyFirst(name, event);
          return;
        }
        this._apply(name, event);
      });
    } catch (error) {
      this._transcripts.add(name, { kind: "error", text: String(error) });
    } finally {
      if (started) this._transcripts.setRunning(name, false);
    }
  }

  async stop(name) {
    try {
      await this._chatStream.stop(name);
    } catch (error) {
      this._transcripts.add(name, { kind: "error", text: String(error) });
    }
  }

  async forget(name) {
    this._restored.delete(name);
    this._resumed.delete(name);
  }

  async answerPermission(name, requestId, allowed) {
    this._transcripts.settle(name, requestId, allowed ? "allowed" : "denied");
    try {
      await this._chatStream.answerPermission(name, requestId, allowed);
    } catch (error) {
      this._transcripts.add(name, { kind: "error", text: String(error) });
    }
  }

  // History replaces the transcript in one shot; live events afterwards append.
  async restore(name) {
    if (this._restored.has(name)) return;
    this._restored.add(name);
    try {
      const events = await this._chatStream.history(name);
      this._transcripts.replaceAll(name, this._mapper.items(events));
    } catch {}
  }

  // First live event of a follow: history was already replaced wholesale, so
  // the event just appends like any other.
  _applyFirst(name, event) {
    this._apply(name, event);
    this._transcripts.setRunning(name, true);
  }

  _apply(name, event) {
    if (event.kind === "permission-settled") {
      this._transcripts.settle(name, event.detail, event.text);
      return;
    }
    const item = this._mapper.item(event);
    if (item) this._transcripts.add(name, item);
  }
}
