// The chat section: an orchestrator switch, one thread per name, and the input form.

import { DomBuilder } from "./dom_builder.js";
import { AttachControl } from "./attach_control.js";
import { ChatItemRenderer } from "./chat_item_renderer.js";
import { MarkdownView } from "./markdown_view.js";
import { ChatBackends } from "./chat_backends.js";
import { ChatThreads } from "./chat_threads.js";
import { SessionIdChip } from "./session_id_chip.js";
import { SlashCommandsClient } from "./slash_commands_client.js";
import { ResumeControl } from "./resume_control.js";
import { SlashPicker } from "./slash_picker.js";
import { ThreadTabs } from "./thread_tabs.js";
import { UploadAttacher } from "./upload_attacher.js";

const TARGET_KEY = "wb-chat-target";

export class ChatView {
  constructor(chatStream, transcripts, session, agents) {
    this._chatStream = chatStream;
    this._transcripts = transcripts;
    this._session = session;
    this._commands = new SlashCommandsClient();
    this._threads = new ChatThreads(transcripts, new ChatItemRenderer(this._session, new MarkdownView()), agents);
    this._agents = agents;
    this._agentCount = 0;
    this._attacher = new UploadAttacher(chatStream, (message) => {
      if (this._selected !== null) this._transcripts.add(this._selected, { kind: "error", text: message });
    });
    this._chip = new SessionIdChip(this._chatStream, () => this._selected);
    this._tabs = new ThreadTabs(chatStream, (chatName) => this._selectChat(chatName),
                                (chatName) => this._forgetChat(chatName));
    this._backends = new ChatBackends((key) => this._flipBackend(key));
    this._buttons = new Map();
    this._orchestrator = null;
    this._section = null;
    this._switch = null;
    this._form = null;
    this._input = null;
    this._sendButton = null;
    this._stopButton = null;
    this._selected = null;
    transcripts.subscribe((name) => this._onStoreChange(name));
    agents.subscribe(() => this._onAgentsChange());
  }

  render() {
    if (!this._section) {
      this._section = this._buildSection();
      this._loadOrchestrators();
      requestAnimationFrame(() => this._focusInput());
    } else {
      // The host detaches and reattaches this node on re-render, which resets
      // the thread's scrollTop to 0. Scroll again once it is back in the DOM.
      requestAnimationFrame(() => {
        this._scrollSelectedToBottom();
        this._focusInput();
      });
    }
    return this._section;
  }

  _onStoreChange(name) {
    this._threads.refresh(name);
    if (name === this._selected) {
      this._applyFormState();
      if (!this._transcripts.isRunning(name)) {
        this._chip.refresh();
        this._focusInputIfIdle();
      }
    }
  }

  _onAgentsChange() {
    const count = this._agents.runningFor(this._selected);
    if (count === this._agentCount) return;
    this._agentCount = count;
    if (this._selected !== null) this._threads.refresh(this._selected);
  }

  _buildSection() {
    const section = DomBuilder.el("section", "clay chat");
    const head = DomBuilder.el("div", "chat-head");
    head.appendChild(DomBuilder.el("h2", "panel-title", "chat"));
    this._switch = DomBuilder.el("div", "chat-switch");
    head.appendChild(this._switch);
    head.appendChild(this._backends.node());
    this._backends.load();
    head.appendChild(this._chip.node());
    head.appendChild(this._chip.meterNode());
    this._chip.start();
    section.appendChild(head);
    section.appendChild(this._tabs.node());
    section.appendChild(this._threads.holder());
    section.appendChild(this._formNode());
    this._attach.bindPaste();
    this._attach.bindDrop(this._threads.holder());
    this._applyFormState();
    return section;
  }

  async _loadOrchestrators() {
    try {
      const orchestrators = await this._chatStream.orchestrators();
      this._buildSwitch(orchestrators);
    } catch (error) {
      this._threads.showError(DomBuilder.el("div", "chat-message is-error", String(error)));
    }
  }

  _buildSwitch(orchestrators) {
    const names = orchestrators.map((item) => item.name);
    for (const name of names) this._switch.appendChild(this._switchButton(name));
    if (names.length === 0) return;
    const stored = this._storedName();
    this._select(names.includes(stored) ? stored : names[0]);
  }

  _switchButton(name) {
    const button = DomBuilder.el("button", "stage-tab", name);
    button.type = "button";
    button.addEventListener("click", () => this._select(name));
    this._buttons.set(name, button);
    return button;
  }

  async _select(orchestrator) {
    this._orchestrator = orchestrator;
    this._storeName(orchestrator);
    this._updateSwitch();
    await this._tabs.load(orchestrator);
    if (this._orchestrator === orchestrator) this._selectChat(this._tabs.selectedName());
  }

  _selectChat(name) {
    this._selected = name;
    this._session.restore(name).then(() => this._session.resume(name));
    this._refreshBackend(name);
    this._threads.show(name);
    this._applyFormState();
    this._threads.scrollToBottom(name);
    this._chip.refresh();
    this._focusInput();
  }

  async _refreshBackend(name) {
    const info = await this._chatStream.sessionInfo(name);
    this._backends.setActive(info.backend ?? null);
  }

  async _flipBackend(backend) {
    if (backend === this._backends.active() || this._transcripts.isRunning(this._selected)) return;
    const name = this._selected;
    try {
      await this._chatStream.setBackend(name, backend);
    } catch (error) {
      // A refused flip (old server, bad name) must be visible, not a silent no-op.
      this._threads.showError(DomBuilder.el("div", "chat-message is-error", String(error)));
      return;
    }
    this._transcripts.clear(name);
    await this._session.restore(name);
    this._chip.refresh();
    this._backends.setActive(backend);
    await this._tabs.load(this._orchestrator);
  }

  _updateSwitch() {
    for (const [name, button] of this._buttons) {
      button.classList.toggle("is-selected", name === this._orchestrator);
      button.setAttribute("aria-current", name === this._orchestrator ? "true" : "false");
    }
  }

  // A closed thread is dead: the convo must not survive under the same name
  // when a new thread reuses it (server and page caches both).
  _forgetChat(name) {
    this._transcripts.drop(name);
    this._session.forget(name);
    this._threads.remove(name);
  }

  _storedName() {
    try {
      return localStorage.getItem(TARGET_KEY);
    } catch {
      return null;
    }
  }

  _storeName(name) {
    try {
      localStorage.setItem(TARGET_KEY, name);
    } catch {}
  }

  _formNode() {
    this._form = DomBuilder.el("form", "chat-form");
    this._input = DomBuilder.el("textarea", "clay-field chat-input");
    this._attach = new AttachControl(this._attacher, () => this._selected, this._input);
    // Build the picker before the Enter-to-send listener: both listeners sit
    // on the textarea, and the picker's keydown must win by registration order.
    this._picker = new SlashPicker(this._input, () => this._commands.load(this._selected));
    this._resume = new ResumeControl(this._input, this._session, this._transcripts,
      () => this._selected, () => this._afterResume());
    this._input.addEventListener("keydown", (event) => this._onKeydown(event));
    const inputWrap = DomBuilder.el("div", "chat-input-wrap");
    inputWrap.append(this._picker.node(), this._resume.node(), this._input);
    this._sendButton = DomBuilder.el("button", "clay-button chat-send", "send");
    this._sendButton.type = "submit";
    this._stopButton = DomBuilder.el("button", "clay-button clay-quiet chat-stop", "stop");
    this._stopButton.type = "button";
    this._stopButton.addEventListener("click", () => this._stopTurn());
    this._form.addEventListener("submit", (event) => this._onSubmit(event));
    this._form.appendChild(this._attach.node("chat-clip"));
    this._form.appendChild(inputWrap);
    this._form.appendChild(this._sendButton);
    this._form.appendChild(this._stopButton);
    return this._form;
  }

  _onKeydown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      this._form.requestSubmit();
    }
  }

  _onSubmit(event) {
    event.preventDefault();
    const name = this._selected;
    const text = this._input.value;
    this._input.value = "";
    this._session.send(name, text);
  }

  _afterResume() {
    this._chip.refresh();
    this._scrollSelectedToBottom();
  }

  _stopTurn() {
    this._session.stop(this._selected);
  }

  _applyFormState() {
    const ready = this._selected !== null && !this._transcripts.isRunning(this._selected);
    this._input.disabled = !ready;
    this._sendButton.disabled = !ready;
    this._stopButton.disabled = ready;
  }

  _focusInput() {
    if (!this._input.disabled) this._input.focus({ preventScroll: true });
  }

  // A turn that ends disables then re-enables the input, which drops focus. Restore it
  // only when nothing else holds focus, so typing elsewhere is never interrupted.
  _focusInputIfIdle() {
    const holder = document.activeElement;
    if (holder === null || holder === document.body) this._focusInput();
  }

  _scrollSelectedToBottom() {
    if (this._selected === null) return;
    this._threads.scrollToBottom(this._selected);
  }
}
