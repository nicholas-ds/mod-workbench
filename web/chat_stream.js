// The chat server connection: one server-sent event stream per turn, plus the stop route.

export class ChatStream {
  async orchestrators() {
    const response = await fetch("/api/chat");
    if (!response.ok) throw new Error(await this._detail(response));
    const body = await response.json();
    return body.orchestrators;
  }

  async send(name, text, onEvent) {
    const response = await fetch(`/api/chat/${encodeURIComponent(name)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) throw new Error(await this._detail(response));
    await this._readEvents(response, onEvent);
  }

  async follow(name, onEvent) {
    const response = await fetch(`/api/chat/${encodeURIComponent(name)}/stream`);
    if (!response.ok) throw new Error(await this._detail(response));
    await this._readEvents(response, onEvent);
  }

  async history(name) {
    const response = await fetch(`/api/chat/${encodeURIComponent(name)}/history`);
    if (!response.ok) throw new Error(await this._detail(response));
    const body = await response.json();
    return body.events;
  }

  async sessionInfo(name) {
    const response = await fetch(`/api/chat/${encodeURIComponent(name)}/session`);
    if (!response.ok) throw new Error(await this._detail(response));
    const body = await response.json();
    return body;
  }

  async threads(orchestrator) {
    const response = await fetch(`/api/chat/${encodeURIComponent(orchestrator)}/threads`);
    if (!response.ok) throw new Error(await this._detail(response));
    const body = await response.json();
    return body.threads;
  }

  async addThread(orchestrator) {
    const response = await fetch(`/api/chat/${encodeURIComponent(orchestrator)}/threads`, { method: "POST" });
    if (!response.ok) throw new Error(await this._detail(response));
    return response.json();
  }

  async removeThread(orchestrator, threadId) {
    const response = await fetch(`/api/chat/${encodeURIComponent(orchestrator)}/threads/${encodeURIComponent(threadId)}`, { method: "DELETE" });
    if (!response.ok) throw new Error(await this._detail(response));
  }

  async stop(name) {
    const response = await fetch(`/api/chat/${encodeURIComponent(name)}/stop`, { method: "POST" });
    if (!response.ok) throw new Error(await this._detail(response));
    return response.json();
  }

  async setBackend(name, backend) {
    const response = await fetch(`/api/chat/${encodeURIComponent(name)}/backend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ backend }),
    });
    if (!response.ok) throw new Error(await this._detail(response));
    return response.json();
  }

  async answerPermission(name, requestId, allowed) {
    const response = await fetch(`/api/chat/${encodeURIComponent(name)}/permission`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id: requestId, decision: allowed ? "allow" : "deny" }),
    });
    if (!response.ok) throw new Error(await this._detail(response));
    return response.json();
  }

  async upload(name, file) {
    const response = await fetch(`/api/chat/${encodeURIComponent(name)}/upload?filename=${encodeURIComponent(file.name)}`, {
      method: "POST",
      body: file,
    });
    if (!response.ok) throw new Error(await this._detail(response));
    const body = await response.json();
    return body.path;
  }

  async _readEvents(response, onEvent) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffered = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffered += decoder.decode(value, { stream: true });
      buffered = this._emit(buffered, onEvent);
    }
    this._emit(`${buffered}\n\n`, onEvent);
  }

  _emit(buffered, onEvent) {
    const parts = buffered.split("\n\n");
    const remainder = parts.pop();
    for (const part of parts) this._emitPart(part, onEvent);
    return remainder;
  }

  _emitPart(part, onEvent) {
    for (const line of part.split("\n")) {
      if (line.startsWith("data: ")) onEvent(JSON.parse(line.slice("data: ".length)));
    }
  }

  async _detail(response) {
    try {
      const body = await response.json();
      return body.detail ?? String(response.status);
    } catch {
      return String(response.status);
    }
  }
}
