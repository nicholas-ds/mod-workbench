// Notice a chat turn that the server started (a board answer) and follow it.

const POLL_MS = 4000;

export class ServerTurnWatcher {
  constructor(chatStream, transcripts, session) {
    this._chatStream = chatStream;
    this._transcripts = transcripts;
    this._session = session;
    this._names = [];
    this._checking = false;
  }

  async start() {
    try {
      const orchestrators = await this._chatStream.orchestrators();
      this._names = orchestrators.map((entry) => entry.name);
    } catch {
      this._names = [];
    }
    setInterval(() => { this._check(); }, POLL_MS);
  }

  async _check() {
    if (this._checking) return;
    this._checking = true;
    try {
      for (const name of this._names) {
        if (this._transcripts.isRunning(name)) continue;
        try {
          const info = await this._chatStream.sessionInfo(name);
          if (!info.running) continue;
          await this._session.restore(name);
          this._session.follow(name);
        } catch {}
      }
    } finally {
      this._checking = false;
    }
  }
}
