// All HTTP calls of the page. One method per server route.

export class ApiClient {
  mods() {
    return this._send("GET", "/api/mods");
  }

  agents() {
    return this._send("GET", "/api/agents");
  }

  overview() {
    return this._send("GET", "/api/overview");
  }

  boards(mod, state) {
    return this._send("GET", `${this._mod(mod)}/boards?state=${encodeURIComponent(state)}`);
  }

  board(mod, id) {
    return this._send("GET", this._entry(mod, id));
  }

  answer(mod, id, body) {
    return this._send("POST", `${this._entry(mod, id)}/answers`, body);
  }

  close(mod, id) {
    return this._send("POST", `${this._entry(mod, id)}/close`);
  }

  send(mod, id) {
    return this._send("POST", `${this._entry(mod, id)}/send`);
  }

  reopen(mod, id) {
    return this._send("POST", `${this._entry(mod, id)}/reopen`);
  }

  note(mod, id, body) {
    return this._send("POST", `${this._entry(mod, id)}/notes`, body);
  }

  notices(mod) {
    return this._send("GET", `${this._mod(mod)}/notices`);
  }

  retryNotice(mod, id) {
    return this._send("POST", `${this._mod(mod)}/notices/${encodeURIComponent(id)}/retry`);
  }

  wake() {
    return this._send("POST", "/api/wake");
  }

  handoff() {
    return this._send("GET", "/api/handoff");
  }

  nudgeHandoff(kind, target) {
    return this._send("POST", "/api/handoff/nudge", { kind, target });
  }

  detail(mod) {
    return this._send("GET", `${this._mod(mod)}/detail`);
  }

  sendMessage(mod, body, target) {
    if (target) return this._send("POST", "/api/messages", { ...body, target });
    return this._send("POST", this._messagesUrl(mod), body);
  }

  panes() {
    return this._send("GET", "/api/panes");
  }

  messages(mod) {
    return this._send("GET", this._messagesUrl(mod));
  }

  _messagesUrl(mod) {
    return mod === null ? "/api/messages" : `${this._mod(mod)}/messages`;
  }

  events(onMessage) {
    const source = new EventSource("/api/events");
    source.onmessage = onMessage;
    return source;
  }

  _entry(mod, id) {
    return `${this._mod(mod)}/boards/${encodeURIComponent(id)}`;
  }

  _mod(mod) {
    return `/api/mods/${encodeURIComponent(mod)}`;
  }

  async _send(method, url, body) {
    const init = body === undefined
      ? { method }
      : { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
    const response = await fetch(url, init);
    if (!response.ok) throw new Error(`${response.status} ${url}`);
    return response.json();
  }
}
