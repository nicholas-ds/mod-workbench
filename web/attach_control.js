// Shared attach UI for the chat form and the message dock: a quiet picker
// button with a hidden file input, plus drop and paste wiring through an
// UploadAttacher. One job: the attach UI around one chat input.

import { DomBuilder } from "./dom_builder.js";
import { UploadAttacher } from "./upload_attacher.js";

export class AttachControl {
  constructor(uploadAttacher, nameProvider, input) {
    this._attacher = uploadAttacher;
    this._nameProvider = nameProvider;
    this._input = input;
  }

  // extraClass lands on the button, the way chat_view built its clip button.
  // The wrapper is display:contents (clay.css), so the button stays the grid item of the
  // surrounding form or dock and keeps its old box.
  node(extraClass) {
    const wrap = DomBuilder.el("span", "attach-wrap");
    const fileInput = DomBuilder.el("input");
    fileInput.type = "file";
    fileInput.multiple = true;
    fileInput.hidden = true;
    fileInput.addEventListener("change", () => {
      const name = this._nameProvider();
      if (name !== null) this._attacher.attach(name, fileInput.files, this._input);
      fileInput.value = "";
    });
    const button = DomBuilder.el("button", `clay-button clay-quiet${extraClass ? ` ${extraClass}` : ""}`, "attach");
    button.type = "button";
    button.addEventListener("click", () => fileInput.click());
    wrap.append(button, fileInput);
    return wrap;
  }

  bindDrop(element) {
    this._attacher.bindDrop(element, this._nameProvider, this._input);
  }

  bindPaste() {
    this._attacher.bindPaste(this._input, this._nameProvider);
  }

  // Both wirings in one call, for hosts whose drop target and paste input
  // share one element.
  bindAll(element) {
    this.bindPaste();
    this.bindDrop(element);
  }
}

// The dock's control: files attach to the picked sdk chat, else to the pane's
// mod, else to the platform. Upload errors surface on the sdk thread only, so
// pane targets never grow phantom chat errors.
export function sdkAttachControl(chat, nameProvider, sdkNameProvider, input) {
  const attacher = new UploadAttacher(chat.chatStream, (text) => {
    const sdk = sdkNameProvider();
    if (sdk !== null) chat.transcripts.add(sdk, { kind: "error", text });
  });
  return new AttachControl(attacher, nameProvider, input);
}
