// Maps chat stream events to transcript items. Events that draw nothing map to null.

const IGNORED_KINDS = ["result"];

export class TranscriptItemMapper {
  item(event) {
    if (!event || IGNORED_KINDS.includes(event.kind)) return null;
    switch (event.kind) {
      case "user": return { kind: "user", text: event.text };
      case "text": return { kind: "text", text: event.text };
      case "thinking": return { kind: "thinking" };
      case "tool": return { kind: "tool", text: event.tool_name, detail: event.detail };
      case "permission": return { kind: "permission", text: event.text, detail: event.detail };
      case "error": return { kind: "error", text: event.text };
      case "handoff": return { kind: "handoff", text: event.text };
      case "notice": return { kind: "notice", text: event.text };
      default: return null;
    }
  }

  items(events) {
    return events.map((event) => this.item(event)).filter((item) => item !== null);
  }
}
