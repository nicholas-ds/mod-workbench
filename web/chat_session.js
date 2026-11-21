// One chat turn against the stream, recorded into the shared transcript store.

export class ChatSession {
  constructor(chatStream, transcripts) {
    this._chatStream = chatStream;
    this._transcripts = transcripts;
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

  async restore(name) {
    if (this._restored.has(name)) return;
    if (this._transcripts.items(name).length > 0) return;
    this._restored.add(name);
    try {
      const events = await this._chatStream.history(name);
      if (this._transcripts.items(name).length > 0) return;
      for (const event of events) {
        if (event.kind === "user") this._transcripts.add(name, { kind: "user", text: event.text });
        else this._apply(name, event);
      }
    } catch {}
  }

  _applyFirst(name, event) {
    if (event.kind !== "user") {
      this._transcripts.dropAfterLastUser(name);
      this._apply(name, event);
    } else if (this._lastUserText(name) === event.text) {
      this._transcripts.dropAfterLastUser(name);
    } else {
      this._transcripts.add(name, { kind: "user", text: event.text });
    }
    this._transcripts.setRunning(name, true);
  }

  _lastUserText(name) {
    const users = this._transcripts.items(name).filter((item) => item.kind === "user");
    return users.length === 0 ? null : users[users.length - 1].text;
  }

  _apply(name, event) {
    if (event.kind === "user") this._transcripts.add(name, { kind: "user", text: event.text });
    else if (event.kind === "text") this._transcripts.add(name, { kind: "text", text: event.text });
    else if (event.kind === "thinking") this._transcripts.add(name, { kind: "thinking" });
    else if (event.kind === "tool") this._transcripts.add(name, { kind: "tool", text: event.tool_name, detail: event.detail });
    else if (event.kind === "permission") this._transcripts.add(name, { kind: "permission", text: event.text, detail: event.detail });
    else if (event.kind === "permission-settled") this._transcripts.settle(name, event.detail, event.text);
    else if (event.kind === "error") this._transcripts.add(name, { kind: "error", text: event.text });
    else if (event.kind === "handoff") this._transcripts.add(name, { kind: "handoff", text: event.text });
    else if (event.kind === "notice") {
      this._transcripts.clear(name);
      this._transcripts.add(name, { kind: "notice", text: event.text });
    }
  }
}
