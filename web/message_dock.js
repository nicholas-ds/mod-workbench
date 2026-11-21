// Bottom dock: the author messages an SDK orchestrator or a terminal pane with the view context.

import { sdkAttachControl } from "./attach_control.js";
import { AgentsPill } from "./agents_pill.js";
import { DragHandle } from "./drag_handle.js";
import { DockCollapsedAnchor } from "./dock_collapsed_anchor.js";
import { DockGravity } from "./dock_gravity.js";
import { DockPaneThread } from "./dock_pane_thread.js";
import { DockTargets } from "./dock_targets.js";
import { DomBuilder } from "./dom_builder.js";
import { FlashMessage } from "./flash_message.js";
import { ResizeGrip } from "./resize_grip.js";
import { SessionIdChip } from "./session_id_chip.js";
import { SlashCommandsClient } from "./slash_commands_client.js";
import { ResumeControl } from "./resume_control.js";
import { SlashPicker } from "./slash_picker.js";
import { TargetPicker } from "./target_picker.js";
import { WorkingPill } from "./working_pill.js";
import { ViewContext } from "./view_context.js";

const RELOAD_MS = 5000;
const COLLAPSED_KEY = "wb-dock-collapsed";
const MAIN_TARGET = "main-orchestrator";
const PLATFORM_UPLOAD_NAME = "main"; // the platform entry name in OrchestratorDirectory
const CHIP_FIELDS = ["view", "mod", "board", "item", "question"];

export class MessageDock {
  constructor(api, parent, chat) {
    this._api = api;
    this._parent = parent;
    this._chat = chat;
    this._agents = chat.agents;
    this._commands = new SlashCommandsClient();
    this._context = ViewContext.shared().get();
    this._timer = null;
    this._panes = [];
    this._targets = new DockTargets();
    this._paneThread = new DockPaneThread(api, (nodes) => this._renderThread(nodes), chat.agents);
    this._pickedByHand = false;
    this._scrollToTopOnNextRender = true;
    this._agentCount = 0;
  }

  start() {
    this._build();
    this._anchor = new DockCollapsedAnchor();
    this._gravity = new DockGravity(this._dock, this._anchor, document);
    this._gravity.start();
    this._openDrag = new DragHandle(this._dock, "wb-dock-pos-open");
    this._openDrag.attach(this._head);
    this._resizeGrip = new ResizeGrip(this._dock, "wb-dock-size");
    this._parent.appendChild(this._dock);
    this._chat.transcripts.subscribe((name) => this._onTranscript(name));
    this._agents.subscribe(() => this._onAgentsChange());
    this._redrawChips();
    this._updateSendState();
    this._loadTargets();
    this._applyCollapsed(this._storedCollapsed());
    document.addEventListener("wb-context", (event) => this._onContext(event.detail));
  }

  _storedCollapsed() {
    try { return localStorage.getItem(COLLAPSED_KEY) !== "0"; } catch { return false; }
  }

  _build() {
    this._dock = DomBuilder.el("div", "message-dock theme-classic");
    this._head = DomBuilder.el("div", "dock-head");
    const toggle = DomBuilder.el("button", "dock-toggle panel-title", "message");
    this._toggleButton = toggle;
    toggle.dataset.dragThrough = "";
    toggle.addEventListener("click", () => {
      if (this._openDrag.wasDragged()) return;
      this._applyCollapsed(!this._dock.classList.contains("is-collapsed"));
    });
    this._sessionChip = new SessionIdChip(this._chat.chatStream, () => this._targetName("sdk"));
    this._head.append(toggle, this._sessionChip.node(), this._sessionChip.meterNode());
    this._chips = DomBuilder.el("div", "dock-chips");
    this._input = DomBuilder.el("textarea", "dock-input clay-field");
    this._input.placeholder = "Message to the orchestrator";
    // Build the picker before the Enter-to-send listener below: both listeners
    // sit on the textarea, and the picker's keydown must win by registration order.
    this._picker = new SlashPicker(this._input, () => this._commands.load(this._targetName("sdk")));
    this._resume = new ResumeControl(this._input, this._chat.session, this._chat.transcripts,
      () => this._targetName("sdk"), () => this._sessionChip.refresh());
    this._input.addEventListener("input", () => this._updateSendState());
    this._input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
      event.preventDefault();
      this._submit();
    });
    this._send = DomBuilder.el("button", "dock-send clay-button", "send");
    this._send.addEventListener("click", () => this._submit());
    this._attach = sdkAttachControl(this._chat,
      () => this._targetName("sdk") ?? this._threadMod() ?? PLATFORM_UPLOAD_NAME, () => this._targetName("sdk"), this._input);
    this._attach.bindAll(this._dock);
    this._thread = DomBuilder.el("div", "dock-thread");
    this._target = new TargetPicker(() => this._onTargetPicked());
    this._sessionChip.start();
    this._dock.append(this._head, this._chips, this._picker.node(), this._resume.node(), this._input, this._actionColumn(), this._target.node, this._thread);
  }

  _actionColumn() {
    const column = DomBuilder.el("div", "dock-actions");
    column.append(this._send, this._attach.node());
    return column;
  }

  _onTargetPicked() {
    this._pickedByHand = true;
    this._thread.replaceChildren();
    this._scrollToTopOnNextRender = true;
    this._refreshThread();
  }

  async _loadTargets() {
    this._panes = await this._loadPanes();
    this._targets.setSdkNames(await this._loadSdkNames());
    this._targets.setPanes(this._panes);
    this._target.setNames(this._targets.labels());
    this._target.value = this._defaultTarget();
    this._refreshThread();
  }

  async _loadPanes() {
    try { return (await this._api.panes()).panes; } catch { return []; }
  }

  async _loadSdkNames() {
    try { return (await this._chat.chatStream.orchestrators()).map((entry) => entry.name); } catch { return []; }
  }

  _defaultTarget() {
    return this._targets.defaultLabel(this._context.mod);
  }

  _targetName(kind) {
    const target = this._targets.resolve(this._target.value);
    return target && target.kind === kind ? target.name : null;
  }

  _paneName() {
    return this._targetName("pane") ?? MAIN_TARGET;
  }

  _threadMod() {
    const pane = this._panes.find((entry) => entry.name === this._paneName());
    return pane && pane.mod ? pane.mod : null;
  }

  _applyCollapsed(collapsed) {
    this._dock.classList.toggle("is-collapsed", collapsed);
    this._toggleButton.textContent = collapsed ? "message" : "message  ▾ hide";
    this._toggleButton.setAttribute("aria-expanded", collapsed ? "false" : "true");
    this._openDrag.reset();
    this._openDrag.setPersistent(!collapsed);
    if (collapsed) this._anchor.apply(this._dock, document);
    else this._openDrag.restore();
    this._resizeGrip.reset();
    if (!collapsed) this._resizeGrip.restore();
    try {
      localStorage.setItem(COLLAPSED_KEY, collapsed ? "1" : "0");
    } catch { /* storage unavailable: the state is not kept */ }
    if (this._timer !== null) clearInterval(this._timer);
    this._timer = null;
    if (!collapsed) {
      this._refreshThread();
      this._armTimer();
      requestAnimationFrame(() => this._input.focus({ preventScroll: true }));
    }
  }

  // Jump to a conversation from outside: show the popup with the target picked by hand.
  openConversation(label) {
    this._pickedByHand = true;
    this._target.value = label;
    this._applyCollapsed(false);
    this._scrollToTopOnNextRender = true;
    this._updateSendState();
    this._refreshThread();
  }

  openAgentFolder(folder) {
    const label = this._targets.paneLabelForFolder(folder) ?? this._defaultTarget();
    this.openConversation(label);
  }

  _onContext(context) {
    const previousMod = this._context.mod;
    this._context = context;
    this._redrawChips();
    this._updateSendState();
    if (context.mod !== previousMod && !this._pickedByHand) {
      this._target.value = this._defaultTarget();
      this._scrollToTopOnNextRender = true;
      this._refreshThread();
    }
    this._pickedByHand = false;
  }

  _redrawChips() {
    const chips = CHIP_FIELDS.filter((field) => this._context[field] !== null)
      .map((field) => DomBuilder.el("span", "dock-chip", `${field}: ${this._context[field]}`));
    this._chips.replaceChildren(...chips);
  }

  _updateSendState() {
    const name = this._targetName("sdk");
    const running = name !== null && this._chat.transcripts.isRunning(name);
    this._send.disabled = this._input.value.trim() === "" || running;
  }

  _submit() {
    if (this._send.disabled) return;
    if (this._targetName("sdk") !== null) this._submitToSdk();
    else this._submitToPane();
  }

  _submitToSdk() {
    const typedText = this._input.value.trim();
    this._chat.session.send(this._targetName("sdk"), this._sdkPrompt(typedText), typedText);
    this._input.value = "";
    this._updateSendState();
  }

  _sdkPrompt(typedText) {
    const { board, item, question } = this._context;
    if (board === null || typedText.startsWith("/")) return typedText;
    const line = `(The author is looking at board ${board}, item ${item}, question ${question}. Leave out parts that are null.)`;
    return `${line}\n${typedText}`;
  }

  _submitToPane() {
    const text = this._input.value.trim();
    const { view, board, item, question } = this._context;
    const payload = { text, context: { view, board, item, question } };
    this._input.value = "";
    this._updateSendState();
    this._api.sendMessage(this._threadMod(), payload, this._paneName())
      .then((result) => this._sent(result))
      .catch(() => this._failed(text));
  }

  _sent(result) {
    const target = this._target.value || MAIN_TARGET;
    if (result.delivered) FlashMessage.shared().confirm(`Message sent to ${target}.`);
    else FlashMessage.shared().fail(`Message saved, but the ${target} pane was not reached.`);
    return this._refreshThread();
  }

  _failed(text) {
    this._input.value = text;
    this._updateSendState();
    FlashMessage.shared().fail("Message not sent. Your text is still in the box.");
  }

  _onTranscript(name) {
    if (name !== this._targetName("sdk")) return;
    this._refreshThread();
    this._updateSendState();
    if (!this._chat.transcripts.isRunning(name)) this._sessionChip.refresh();
  }

  _armTimer() {
    this._timer = setInterval(() => {
      if (this._targetName("sdk") === null) this._refreshPaneThread();
    }, RELOAD_MS);
  }

  async _refreshThread() {
    const name = this._targetName("sdk");
    if (name === null) return this._refreshPaneThread();
    this._chat.session.restore(name).then(() => this._chat.session.resume(name));
    this._drawSdkThread(name);
  }

  _drawSdkThread(name) {
    const messages = this._chat.renderer.render(this._chat.transcripts.items(name), name);
    const pill = WorkingPill.trailing(this._chat.transcripts.isRunning(name), name);
    const agents = AgentsPill.trailing(this._agents.runningFor(name));
    this._renderThread([...messages, ...pill, ...agents]);
  }

  _onAgentsChange() {
    const name = this._targetName("sdk");
    const count = this._agents.runningFor(name ?? this._threadMod());
    if (count === this._agentCount) return;
    this._agentCount = count;
    if (name === null) this._refreshPaneThread();
    else this._drawSdkThread(name);
  }

  _refreshPaneThread() {
    return this._paneThread.refresh(this._threadMod());
  }

  _renderThread(nodes) {
    const keptScroll = this._thread.scrollTop;
    this._thread.replaceChildren(...nodes);
    this._thread.scrollTop = this._scrollToTopOnNextRender ? 0 : keptScroll;
    this._scrollToTopOnNextRender = false;
  }
}
