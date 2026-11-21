// Loads the slash command list of one chat session from the workbench server.
// Same plain fetch style as ChatStream; any failure gives an empty list.

/**
 * One runnable chat command as the backend reports it.
 * @typedef {{name: string, description: string}} SlashCommand
 */
export {};

export class SlashCommandsClient {
  /**
   * @param {string} name the chat session name
   * @returns {Promise<SlashCommand[]>} the commands, [] on any failure
   */
  async load(name) {
    try {
      const response = await fetch(`/api/chat/${encodeURIComponent(name)}/commands`);
      if (!response.ok) return [];
      const payload = await response.json();
      const commands = payload["commands"];
      if (!Array.isArray(commands)) return [];
      return commands.filter((entry) => this._isCommand(entry));
    } catch {
      return [];
    }
  }

  /**
   * @param {object} entry one payload entry
   * @returns {boolean} true when it carries a name and description string
   */
  _isCommand(entry) {
    return entry !== null && typeof entry === "object"
      && typeof entry["name"] === "string" && typeof entry["description"] === "string";
  }
}
