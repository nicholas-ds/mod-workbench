// Rendering of transcript items into chat nodes, one node per item.

import { DomBuilder } from "./dom_builder.js";
import { MarkdownView } from "./markdown_view.js";

const THINKING_TEXT = "thinking";

export class ChatItemRenderer {
  /** `markdown` is injected by the caller; defaults to the shared MarkdownView. */
  constructor(session, markdown = new MarkdownView()) {
    this._session = session;
    this._markdown = markdown;
  }

  render(items, name) {
    return items.map((item) => this._renderOne(item, name));
  }

  _renderOne(item, name) {
    if (item.kind === "user") return this._message("chat-message is-user", item.text);
    if (item.kind === "text") return this._message("chat-message is-reply", item.text);
    if (item.kind === "handoff") return this._message("chat-handoff", item.text);
    if (item.kind === "permission") return this._permissionNode(item, name);
    if (item.kind === "thinking") return DomBuilder.el("span", "chat-chip", THINKING_TEXT);
    if (item.kind === "tool") return DomBuilder.el("span", "chat-chip", this._toolLabel(item));
    if (item.kind === "error") return DomBuilder.el("div", "chat-message is-error", item.text);
    return DomBuilder.el("div", "chat-notice", item.text);
  }

  /** User and reply bubbles hold rendered Markdown instead of plain text. */
  _message(className, text) {
    const node = DomBuilder.el("div", className);
    node.appendChild(this._markdown.render(text));
    return node;
  }

  _permissionNode(item, name) {
    const card = DomBuilder.el("div", "chat-permission");
    const [first, rest] = this._splitCardText(item.text);
    card.appendChild(DomBuilder.el("div", "chat-permission-text", first));
    if (rest) {
      card.appendChild(DomBuilder.el("div", "chat-permission-detail", rest));
    }
    if (item.settled) {
      card.appendChild(DomBuilder.el("span", "chat-chip", item.settled));
      return card;
    }
    card.appendChild(this._actionButtons(item, name));
    return card;
  }

  _splitCardText(text) {
    const index = text.indexOf("\n");
    if (index === -1) return [text, null];
    return [text.slice(0, index), text.slice(index + 1)];
  }

  _actionButtons(item, name) {
    const actions = DomBuilder.el("div", "chat-permission-actions");
    const allow = DomBuilder.el("button", "clay-button chat-allow", "Allow");
    const deny = DomBuilder.el("button", "clay-button clay-quiet chat-deny", "Deny");
    allow.type = "button";
    deny.type = "button";
    allow.addEventListener("click", () => this._session.answerPermission(name, item.detail, true));
    deny.addEventListener("click", () => this._session.answerPermission(name, item.detail, false));
    actions.appendChild(allow);
    actions.appendChild(deny);
    return actions;
  }

  _toolLabel(item) {
    return [item.text, item.detail].filter(Boolean).join(" ");
  }
}
