# Conversation display audit and plan (Opus, 2026-11-22, read-only, unverified at runtime)

Problem: chat tab, popup (SDK target) and popup (pane target) draw and scroll differently.
Popup opens at scrollTop 0 (oldest message on SDK targets). Focus only on expand. History restore rebuilds the thread once per event.

Owning classes: ConversationPanel (base: open = restore, snapshot, render, pin to latest, focus), ScrollAnchor, PaneTranscriptSource, TranscriptItemMapper.

Tasks (one kind of change each, order T1+T2, T3+T4, T5, T6 parallel, T7 waits for author):
- T1 Scroll: scroll_anchor.js; use in chat_threads.js, message_dock.js, chat_view.js.
- T2 Bulk restore: transcript_item_mapper.js; ChatTranscripts.replaceAll; chat_session.js.
- T3 Pane source: pane_transcript_source.js; dock_pane_thread.js, message_dock.js.
- T4 One renderer: merge chat_item_renderer.js and dock_item_renderer.js.
- T5 Base class: conversation_panel.js; ChatView and MessageDock extend it (both under 250 lines). Focus on open and on target pick.
- T6 Server: tool_input_detail.py for both key sets; user_text_cleaner.py for the popup context line.
- T7 Layout (author decision): popup input below thread, oldest first, pinned to latest.

Other findings: result events dropped, notice clears transcript, pane send/read keys differ (message_dock.js:239 vs 294), no JS test harness.
Tests: pytest per new Python class. Playwright at 1500 and 1920 px: popup lands at bottom with input focused.

Author rules (2026-11-22): fix at the source. Delete old workaround and dead code each task replaces. No old and new path side by side. Well named classes, open to extension (ConversationPanel base class). Every worker brief repeats this.
