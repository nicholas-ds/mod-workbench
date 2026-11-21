// One whiteboard item rendered as a media well plus caption, by item kind.

import { DomBuilder } from "./dom_builder.js";
import { MarkdownView } from "./markdown_view.js";

export class ItemRenderer {
  render(item) {
    const card = DomBuilder.el("div", "item");
    card.appendChild(this._media(item));
    card.appendChild(this._caption(item.caption));
    return card;
  }

  _media(item) {
    if (item.kind === "image") return this._image(item);
    if (item.kind === "html" || item.kind === "svg") return this._frame(item);
    if (item.kind === "text") return this._text(item);
    if (item.kind === "swf") return this._info(item, "SWF playback comes in Layer 2");
    return this._info(item, null);
  }

  _image(item) {
    const well = this._well();
    const image = document.createElement("img");
    image.src = item.url;
    image.alt = item.caption;
    image.loading = "lazy";
    well.appendChild(image);
    return well;
  }

  _frame(item) {
    const well = this._well();
    const frame = document.createElement("iframe");
    frame.setAttribute("sandbox", "");
    frame.src = item.url;
    frame.title = item.caption;
    well.appendChild(frame);
    const overlay = DomBuilder.el("div", "note-capture");
    overlay.title = "Click to leave a note";
    well.appendChild(overlay);
    return well;
  }

  _text(item) {
    const well = this._well();
    const holder = DomBuilder.el("pre", "item-text");
    well.appendChild(holder);
    this._fill(well, holder, item);
    return well;
  }

  _fill(well, holder, item) {
    fetch(item.url)
      .then((response) => response.text())
      .then((text) => this._show(well, holder, item, text))
      .catch(() => { holder.textContent = `could not load ${item.file}`; });
  }

  _show(well, holder, item, text) {
    if (!item.file.toLowerCase().endsWith(".md")) {
      holder.textContent = text;
      return;
    }
    well.replaceChildren(new MarkdownView().render(text));
  }

  _info(item, line) {
    const card = this._well();
    card.appendChild(DomBuilder.el("b", null, item.file));
    if (line) card.appendChild(this._line(line));
    else this._appendSize(card, item);
    return card;
  }

  _line(text) {
    return DomBuilder.el("span", "item-line", text);
  }

  _appendSize(card, item) {
    fetch(item.url, { method: "HEAD" })
      .then((response) => this._sizeOf(response))
      .then((size) => { if (size) card.appendChild(this._line(size)); })
      .catch(() => {});
  }

  _sizeOf(response) {
    const bytes = Number(response.headers.get("content-length"));
    if (!bytes) return null;
    if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} B`;
  }

  _well() {
    return DomBuilder.el("div", "clay-well item-well");
  }

  _caption(text) {
    return DomBuilder.el("span", "cap", text);
  }
}
