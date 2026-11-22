// Rendering of transcript items, shared by every transcript surface.
// Layout "flat" draws one node per item (chat tab); layout "exchange" groups
// each user message with the replies that follow it (message dock popup).

import { DomBuilder } from "./dom_builder.js";
import { MarkdownView } from "./markdown_view.js";

const THINKING_TEXT = "thinking";
const HANDOFF_CLASS = "chat-handoff";

/** CSS class names per layout. Item drawing is shared; only these names differ. */
const LAYOUT_CLASSES = {
  flat: {
    user: "chat-message is-user",
    text: "chat-message is-reply",
    error: "chat-message is-error",
    chip: "chat-chip",
    notice: "chat-notice",
    permission: "chat-permission",
    permissionText: "chat-permission-text",
    permissionDetail: "chat-permission-detail",
    permissionActions: "chat-permission-actions",
    allow: "clay-button chat-allow",
    deny: "clay-button clay-quiet chat-deny",
  },
  exchange: {
    user: "dock-message",
    text: "dock-reply",
    error: "dock-reply is-error",
    chip: "dock-chip",
    notice: "dock-notice",
    permission: "dock-reply dock-permission",
    // The permission text styles are unscoped, so both layouts share them.
    permissionText: "chat-permission-text",
    permissionDetail: "chat-permission-detail",
    permissionActions: "dock-permission-actions",
    allow: "clay-button dock-allow",
    deny: "clay-button clay-quiet dock-deny",
  },
};

export class TranscriptItemRenderer {
  /** `markdown` is injected by the caller; defaults to the shared MarkdownView. */
  constructor(session, markdown = new MarkdownView(), { layout = "flat" } = {}) {
    this._session = session;
    this._markdown = markdown;
    this._classes = LAYOUT_CLASSES[layout];
    if (!this._classes) throw new Error(`unknown transcript layout: ${layout}`);
    this._grouped = layout === "exchange";
  }

  render(items, name) {
    if (!this._grouped) return items.map((item) => this._itemNode(item, name));
    return this._renderExchanges(items, name);
  }

  // Exchange layout: a user message opens an exchange that holds every reply
  // until the next user message. Notices stand alone between exchanges.
  _renderExchanges(items, name) {
    const nodes = [];
    let exchange = null;
    for (const item of items) {
      if (item.kind === "user") {
        exchange = DomBuilder.el("div", "dock-exchange");
        exchange.appendChild(this._itemNode(item, name));
        nodes.push(exchange);
      } else if (item.kind === "notice") {
        exchange = null;
        nodes.push(this._itemNode(item, name));
      } else {
        if (exchange === null) exchange = this._openExchange(nodes);
        exchange.appendChild(this._itemNode(item, name));
      }
    }
    return nodes;
  }

  _openExchange(nodes) {
    const exchange = DomBuilder.el("div", "dock-exchange");
    nodes.push(exchange);
    return exchange;
  }

  // One drawing path for both layouts; the layout only picks the CSS classes.
  _itemNode(item, name) {
    if (item.kind === "user") return this._message(this._classes.user, item.text);
    if (item.kind === "text") return this._message(this._classes.text, item.text);
    if (item.kind === "handoff") return this._message(HANDOFF_CLASS, item.text);
    if (item.kind === "permission") return this._permissionNode(item, name);
    if (item.kind === "thinking") return DomBuilder.el("span", this._classes.chip, THINKING_TEXT);
    if (item.kind === "tool") return DomBuilder.el("span", this._classes.chip, this._toolLabel(item));
    if (item.kind === "error") return DomBuilder.el("div", this._classes.error, item.text);
    return DomBuilder.el("div", this._classes.notice, item.text);
  }

  /** User, reply and handoff bubbles hold rendered Markdown instead of plain text. */
  _message(className, text) {
    const node = DomBuilder.el("div", className);
    node.appendChild(this._markdown.render(text));
    return node;
  }

  _permissionNode(item, name) {
    const card = DomBuilder.el("div", this._classes.permission);
    const [first, rest] = this._splitCardText(item.text);
    card.appendChild(DomBuilder.el("div", this._classes.permissionText, first));
    if (rest) {
      card.appendChild(DomBuilder.el("div", this._classes.permissionDetail, rest));
    }
    if (item.settled) {
      card.appendChild(DomBuilder.el("span", this._classes.chip, item.settled));
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
    const actions = DomBuilder.el("div", this._classes.permissionActions);
    const allow = DomBuilder.el("button", this._classes.allow, "Allow");
    const deny = DomBuilder.el("button", this._classes.deny, "Deny");
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
