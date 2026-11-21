// Tells the working notice whether an orchestrator chat turn is running, and which one.

export class ChatActivity {
  constructor(transcripts) {
    this._transcripts = transcripts;
  }

  isRunning() {
    return this.target() !== null;
  }

  target() {
    return this._transcripts.runningNames()[0] ?? null;
  }

  subscribe(listener) {
    this._transcripts.subscribe(listener);
  }
}
