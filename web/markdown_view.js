// Markdown text turned into safe HTML inside a well (marked and DOMPurify load from vendor/).

import { DomBuilder } from "./dom_builder.js";

export class MarkdownView {
  render(text) {
    const html = window.marked.parse(text, { gfm: true, breaks: false });
    const body = DomBuilder.el("div", "item-markdown");
    body.innerHTML = window.DOMPurify.sanitize(html);
    return body;
  }
}
