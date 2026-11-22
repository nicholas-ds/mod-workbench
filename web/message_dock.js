// Bottom dock: the author messages an SDK orchestrator or a terminal pane with the view context.

import { sdkAttachControl } from "./attach_control.js";
import { ConversationPanel } from "./conversation_panel.js";
import { DockChrome } from "./dock_chrome.js";
import { DockPaneThread } from "./dock_pane_thread.js";
import { DockTargets } from "./dock_targets.js";
import { DomBuilder } from "./dom_builder.js";
import { FlashMessage } from "./flash_message.js";
import { ScrollAnchor } from "./scroll_anchor.js";
import { SessionIdChip } from "./session_id_chip.js";
import { TargetPicker } from "./target_picker.js";
import { ViewContext } from "./view_context.js";

const RELOAD_MS = 5000;
const MAIN_TARGET = "main-orchestrator";
const PLATFORM_UPLOAD_NAME = "main"; // the platform entry name in OrchestratorDirectory
// Same prefix as UserTextCleaner.CONTEXT_PREFIX in workbench/user_text_cleaner.py.
const CONTEXT_PREFIX = "(The author is looking at board ";

export class MessageDock extends ConversationPanel {
  constructor(api, parent, chat) {
    super(chat.session, chat.transcripts);
    this._api = api;
    this._parent = parent;
    this._chat = chat;
    this._agents = chat.agents;
    this._renderer = chat.renderer;
    this._context = ViewContext.shared().get();
    this._timer = null;
    this._panes = [];
    this._targets = new DockTargets();
    this._paneThread = new DockPaneThread(api, (nodes) => this._renderThread(nodes), chat.agents, chat.renderer);
    this._pickedByHand = false;
    this._agentCount = 0;
  }

  start() {
    this._build();
    this._chrome.mount(this._parent);
    this._chat.transcripts.subscribe((name) => this._onTranscript(name));
    this._agents.subscribe(() => this._onAgentsChange());
    this._chrome.setChips(this._context);
    this._updateSendState();
    this._loadTargets();
    this._applyCollapsed(this._chrome.storedCollapsed());
    document.addEventListener("wb-context", (event) => this._onContext(event.detail));
  }

  _build() {
    this._chrome = new DockChrome(() => this._setExpanded(!this._chrome.isCollapsed()));
    this._sessionChip = new SessionIdChip(this._chat.chatStream, () => this._targetName("sdk"));
    this._chrome.head.append(this._sessionChip.node(), this._sessionChip.meterNode());
    this._input = DomBuilder.el("textarea", "dock-input clay-field");
    this._input.placeholder = "Message to the orchestrator";
    this._makeInputHelpers(() => this._targetName("sdk"), () => this._sessionChip.refresh());
    this._input.addEventListener("input", () => this._updateSendState());
    this._sendOnEnter(() => this._submit());
    this._send = DomBuilder.el("button", "dock-send clay-button", "send");
    this._send.addEventListener("click", () => this._submit());
    this._attach = sdkAttachControl(this._chat,
      () => this._targetName("sdk") ?? this._paneTarget().mod ?? PLATFORM_UPLOAD_NAME,
      () => this._targetName("sdk"), this._input);
    this._attach.bindAll(this._chrome.dock);
    this._thread = DomBuilder.el("div", "dock-thread");
    const actions = DomBuilder.el("div", "dock-actions");
    actions.append(this._send, this._attach.node());
    this._target = new TargetPicker(() => this._onTargetPicked());
    this._sessionChip.start();
    this._chrome.dock.append(this._chrome.head, this._chrome.chipsNode, this._picker.node(),
      this._resume.node(), this._input, actions, this._target.node, this._thread);
  }

  // ConversationPanel hooks: the popup draws the sdk thread itself, or clears
  // and polls the pane thread (the pane draw lands after the refresh resolves).
  _renderConversation(key) {
    if (key !== null) return this._drawSdkThread(key);
    this._thread.replaceChildren();
    return this._refreshPaneThread();
  }

  _conversationOpened() {
    this._updateSendState();
  }

  // Collapse is frame mechanics; expanding always opens the conversation.
  _setExpanded(expanded) {
    this._applyCollapsed(!expanded);
    if (expanded) this.open(this._targetName("sdk"));
  }

  _applyCollapsed(collapsed) {
    this._chrome.applyCollapsed(collapsed);
    this._input.disabled = collapsed;
    if (this._timer !== null) clearInterval(this._timer);
    this._timer = null;
    if (!collapsed) this._armTimer();
  }

  // Jump to a conversation from outside: show the popup with the target picked by hand.
  openConversation(label) {
    this._pickedByHand = true;
    this._target.value = label;
    this._setExpanded(true);
  }

  openAgentFolder(folder) {
    const label = this._targets.paneLabelForFolder(folder) ?? this._defaultTarget();
    this.openConversation(label);
  }

  _onTargetPicked() {
    this._pickedByHand = true;
    this.open(this._targetName("sdk"));
  }

  async _loadTargets() {
    this._panes = await this._loadPanes();
    this._targets.setSdkNames(await this._loadSdkNames());
    this._targets.setPanes(this._panes);
    this._target.setNames(this._targets.labels());
    this._target.value = this._defaultTarget();
    this.open(this._targetName("sdk"));
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

  // One key for the pane conversation: send and thread read both derive their
  // keys from this, so they can never land in different message stores.
  _paneTarget() {
    const name = this._targetName("pane") ?? MAIN_TARGET;
    const pane = this._panes.find((entry) => entry.name === name);
    return { name, mod: pane && pane.mod ? pane.mod : null };
  }

  _onContext(context) {
    const previousMod = this._context.mod;
    this._context = context;
    this._chrome.setChips(context);
    this._updateSendState();
    if (context.mod !== previousMod && !this._pickedByHand) {
      this._target.value = this._defaultTarget();
      this.open(this._targetName("sdk"));
    }
    this._pickedByHand = false;
  }

  _updateSendState() {
    this._send.disabled = this._input.value.trim() === "" || this._isRunning(this._key);
  }

  _submit() {
    if (this._send.disabled) return;
    if (this._key !== null) this._submitToSdk();
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
    const line = `${CONTEXT_PREFIX}${board}, item ${item}, question ${question}. Leave out parts that are null.)`;
    return `${line}\n${typedText}`;
  }

  _submitToPane() {
    const text = this._input.value.trim();
    const { view, board, item, question } = this._context;
    const payload = { text, context: { view, board, item, question } };
    const target = this._paneTarget();
    this._input.value = "";
    this._updateSendState();
    this._api.sendMessage(target.mod, payload, target.name)
      .then((result) => this._sent(result))
      .catch(() => this._failed(text));
  }

  _sent(result) {
    const target = this._target.value || MAIN_TARGET;
    if (result.delivered) FlashMessage.shared().confirm(`Message sent to ${target}.`);
    else FlashMessage.shared().fail(`Message saved, but the ${target} pane was not reached.`);
    return this._refreshPaneThread();
  }

  _failed(text) {
    this._input.value = text;
    this._updateSendState();
    FlashMessage.shared().fail("Message not sent. Your text is still in the box.");
  }

  _onTranscript(name) {
    if (name !== this._key) return;
    this._drawSdkThread(name);
    this._updateSendState();
    if (this._isRunning(name)) return;
    this._sessionChip.refresh();
    if (!this._chrome.isCollapsed()) this.focusInput();
  }

  _armTimer() {
    this._timer = setInterval(() => {
      if (this._key === null) this._refreshPaneThread();
    }, RELOAD_MS);
  }

  _drawSdkThread(name) {
    this._renderThread(this._conversationNodes(name));
  }

  _onAgentsChange() {
    const count = this._agents.runningFor(this._key ?? this._paneTarget().mod);
    if (count === this._agentCount) return;
    this._agentCount = count;
    if (this._key === null) this._refreshPaneThread();
    else this._drawSdkThread(this._key);
  }

  _refreshPaneThread() {
    return this._paneThread.refresh(this._paneTarget().mod);
  }

  _renderThread(nodes) {
    const wasNearBottom = ScrollAnchor.isNearBottom(this._thread);
    this._thread.replaceChildren(...nodes);
    ScrollAnchor.follow(this._thread, wasNearBottom);
  }
}
