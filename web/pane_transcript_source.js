// Maps pane message records to transcript items: the same item model the SDK threads render.

export class PaneTranscriptSource {
  /**
   * `records` arrive newest first (the server's read order); the reversal to
   * the render order, oldest first, lives here and nowhere else. One record
   * is one exchange: the author's message, then the reply when one exists.
   */
  items(records) {
    return [...records].reverse().flatMap((record) => this._exchange(record));
  }

  _exchange(record) {
    const items = [{ kind: "user", text: record.text }];
    if (record.reply !== null) items.push({ kind: "text", text: record.reply });
    return items;
  }
}
