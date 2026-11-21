// The session id chip: shows the id of the chat session that is showing, copies a resume command on click.

import { ContextMeterLabel } from "./context_meter_label.js";
import { DomBuilder } from "./dom_builder.js";

const REFRESH_MS = 10000;
const COPY_MS = 1200;
const NO_SESSION = "no session yet";
const WINDOWS_PATH = /^[a-zA-Z]:/;

export class SessionIdChip {
  constructor(chatStream, nameProvider) {
    this._chatStream = chatStream;
    this._nameProvider = nameProvider;
    this._node = null;
    this._id = "";
    this._command = "";
    this._copiedTimer = null;
    this._shownName = null;
    this._known = new Map();
    this._meter = new ContextMeterLabel();
  }

  meterNode() {
    return this._meter.node();
  }

  node() {
    if (!this._node) this._build();
    return this._node;
  }

  async refresh() {
    const name = this._nameProvider();
    if (name === null) return;
    if (name !== this._shownName) {
      this._shownName = name;
      const known = this._known.get(name);
      if (known) this._show(known);
      else this._setEmpty();
    }
    try {
      const info = await this._chatStream.sessionInfo(name);
      this._known.set(name, info);
      if (this._nameProvider() === name) this._show(info);
    } catch {
      // A failed refresh keeps the chip as it is.
    }
  }

  start() {
    this.refresh();
    setInterval(() => this.refresh(), REFRESH_MS);
  }

  _build() {
    this._node = DomBuilder.el("button", "session-chip");
    this._node.type = "button";
    this._node.addEventListener("click", () => this._copy());
    this._setEmpty();
  }

  _show(info) {
    const id = info.session_id;
    this._id = id;
    this._meter.show(info.context_percent);
    if (id === "") return this._setEmpty();
    this._command = this._resumeCommand(info.folder, id);
    this._node.textContent = id;
    this._node.title = `click to copy: ${this._command}`;
    this._node.disabled = false;
  }

  _resumeCommand(folder, id) {
    const path = WINDOWS_PATH.test(folder) ? folder.replaceAll("/", "\\") : folder;
    return `cd "${path}" && claude --resume ${id}`;
  }

  _setEmpty() {
    this._id = "";
    this._command = "";
    this._meter.clear();
    this._node.textContent = NO_SESSION;
    this._node.title = "";
    this._node.disabled = true;
  }

  _copy() {
    try {
      navigator.clipboard.writeText(this._command).catch(() => {});
      this._node.textContent = "copied";
      clearTimeout(this._copiedTimer);
      this._copiedTimer = setTimeout(() => {
        this._node.textContent = this._id;
      }, COPY_MS);
    } catch {
      // A blocked clipboard leaves the chip as it is.
    }
  }
}
