// Rendering of transcript items into dock exchanges: a user message, its replies and chips.

import { DomBuilder } from "./dom_builder.js";
import { MarkdownView } from "./markdown_view.js";

const THINKING_TEXT = "thinking";

export class DockItemRenderer {
  /** `markdown` is injected by the caller; defaults to the shared MarkdownView. */
  constructor(session, markdown = new MarkdownView()) {
    this._session = session;
    this._markdown = markdown;
  }

  render(items, name) {
    const nodes = [];
    let exchange = null;
    for (const item of items) {
      if (item.kind === "user") exchange = this._startExchange(nodes, item.text);
      else if (item.kind === "notice") exchange = this._addNotice(nodes, item.text);
      else exchange = this._extendExchange(exchange, nodes, item, name);
    }
    return nodes;
  }

  _startExchange(nodes, text) {
    const exchange = DomBuilder.el("div", "dock-exchange");
    exchange.appendChild(this._message("dock-message", text));
    nodes.push(exchange);
    return exchange;
  }

  _extendExchange(exchange, nodes, item, name) {
    const target = exchange ?? this._openExchange(nodes);
    target.appendChild(this._replyNode(item, name));
    return target;
  }

  _openExchange(nodes) {
    const exchange = DomBuilder.el("div", "dock-exchange");
    nodes.push(exchange);
    return exchange;
  }

  _addNotice(nodes, text) {
    nodes.push(DomBuilder.el("div", "dock-notice", text));
    return null;
  }

  _replyNode(item, name) {
    if (item.kind === "permission") return this._permissionNode(item, name);
    if (item.kind === "thinking") return DomBuilder.el("span", "dock-chip", THINKING_TEXT);
    if (item.kind === "tool") return DomBuilder.el("span", "dock-chip", this._toolLabel(item));
    if (item.kind === "error") return DomBuilder.el("div", "dock-reply is-error", item.text);
    return this._message("dock-reply", item.text);
  }

  /** User and reply bubbles hold rendered Markdown instead of plain text. */
  _message(className, text) {
    const node = DomBuilder.el("div", className);
    node.appendChild(this._markdown.render(text));
    return node;
  }

  _permissionNode(item, name) {
    const card = DomBuilder.el("div", "dock-reply dock-permission");
    card.appendChild(DomBuilder.el("div", "dock-permission-text", item.text));
    if (item.settled) {
      card.appendChild(DomBuilder.el("span", "dock-chip", item.settled));
      return card;
    }
    card.appendChild(this._actionButtons(item, name));
    return card;
  }

  _actionButtons(item, name) {
    const actions = DomBuilder.el("div", "dock-permission-actions");
    const allow = DomBuilder.el("button", "clay-button dock-allow", "Allow");
    const deny = DomBuilder.el("button", "clay-button clay-quiet dock-deny", "Deny");
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
