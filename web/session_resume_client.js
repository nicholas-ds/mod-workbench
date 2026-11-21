// Loads and switches the chat sessions of one named chat over HTTP.
// Same plain fetch style as SlashCommandsClient; any failure stays quiet.

/**
 * One chat session as the backend reports it.
 * @typedef {{session_id: string, title: string, last_modified_ms: number}} SessionSummary
 */
export {};

export class SessionResumeClient {
  /**
   * @param {string} name the chat session name
   * @returns {Promise<SessionSummary[]>} the sessions, [] on any failure
   */
  async list(name) {
    try {
      const response = await fetch(`/api/chat/${encodeURIComponent(name)}/sessions`);
      if (!response.ok) return [];
      const payload = await response.json();
      const sessions = payload["sessions"];
      if (!Array.isArray(sessions)) return [];
      return sessions.filter((entry) => entry !== null && typeof entry === "object"
        && typeof entry["session_id"] === "string" && typeof entry["title"] === "string"
        && typeof entry["last_modified_ms"] === "number");
    } catch {
      return [];
    }
  }

  /**
   * @param {string} name the chat session name
   * @param {string} sessionId the listed session to switch to
   * @returns {Promise<boolean>} true when the backend switched
   */
  async resume(name, sessionId) {
    try {
      const response = await fetch(`/api/chat/${encodeURIComponent(name)}/resume`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({session_id: sessionId}),
      });
      return response.ok;
    } catch {
      return false;
    }
  }
}
