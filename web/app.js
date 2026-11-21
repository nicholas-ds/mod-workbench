// Page start: the home view with its event stream, the board view, and the header's more menu.

import { AgentActivity } from "./agent_activity.js";
import { ApiClient } from "./api_client.js";
import { ChatActivity } from "./chat_activity.js";
import { BoardView } from "./board_view.js";
import { ChatSession } from "./chat_session.js";
import { ChatStream } from "./chat_stream.js";
import { ChatTranscripts } from "./chat_transcripts.js";
import { ChatView } from "./chat_view.js";
import { DockItemRenderer } from "./dock_item_renderer.js";
import { HandoffChip } from "./handoff_chip.js";
import { HomeView } from "./home_view.js";
import { MessageDock } from "./message_dock.js";
import { NextQuestion } from "./next_question.js";
import { PageLocation } from "./page_location.js";
import { QuestionsPanel } from "./questions_panel.js";
import { ScrollDebugOverlay } from "./scroll_debug.js";
import { SectionNav } from "./section_nav.js";
import { ServerTurnWatcher } from "./server_turn_watcher.js";
import { LookMenu } from "./look_menu.js";
import { MoreMenu } from "./more_menu.js";
import { VersionsChip } from "./versions_chip.js";
import { WorkingNotice } from "./working_notice.js";

const app = document.getElementById("app");
const api = new ApiClient();
let boardView;
const home = new HomeView(api, app);
const questionsPanel = new QuestionsPanel(api, (outcome) => boardView.panelChanged(outcome));
boardView = new BoardView(api, () => home.mainNode(), questionsPanel);
boardView.setOnBack(() => home.show());
home.setBoardView(boardView);
const transcripts = new ChatTranscripts();
const chatStream = new ChatStream();
const chatSession = new ChatSession(chatStream, transcripts);
const agentActivity = new AgentActivity(api);
new ServerTurnWatcher(chatStream, transcripts, chatSession).start();
home.setChatView(new ChatView(chatStream, transcripts, chatSession, agentActivity));
const pageLocation = new PageLocation();
pageLocation.start();
const nav = new SectionNav(document.querySelector(".shell"),
  [["mods", "mods and boards"], ["tasks", "all tasks"], ["chat", "chat"]],
  (section) => { nav.select(section); home.setSection(section); });
nav.select("mods");
const saved = pageLocation.read();
if (saved && saved.kind === "section") {
  nav.select(saved.section);
  home.restoreSection(saved.section);
}
if (saved && saved.kind === "board") home.openBoard(saved.mod, saved.id);
const homeReady = home.start();
// A bare load opens the first open question once home is up; no answer or a failure stays on home.
if (!saved) {
  homeReady.then(() => new NextQuestion(api).find())
    .then((next) => { if (next) home.openBoard(next.mod, next.id); })
    .catch(() => {});
}
const more = new MoreMenu(document.querySelector(".shell"));
more.start();
const lookButton = document.getElementById("look");
const tasksTab = [...document.querySelectorAll(".top-nav button")].find((button) => button.textContent === "all tasks");
more.host().appendChild(tasksTab);
more.host().appendChild(lookButton);
new LookMenu(lookButton).start();
new VersionsChip(lookButton).start();
new HandoffChip(api, more.button()).start();
const dock = new MessageDock(api, document.body,
  { chatStream, transcripts, session: chatSession, agents: agentActivity, renderer: new DockItemRenderer(chatSession) });
dock.start();
const workingNotices = [
  ["orchestrator", new ChatActivity(transcripts), (name) => dock.openConversation(name)],
  ["agents", agentActivity, (folder) => dock.openAgentFolder(folder)],
];
for (const [label, activity, onOpen] of workingNotices) {
  const slot = document.createElement("div");
  slot.className = "working-slot";
  more.button().before(slot);
  new WorkingNotice(label, activity, slot, onOpen).start();
}
agentActivity.start();
if (ScrollDebugOverlay.enabled()) new ScrollDebugOverlay().start();
