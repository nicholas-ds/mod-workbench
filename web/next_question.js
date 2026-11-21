// Finds the next board with an open question, from the lists the home page loads.

export class NextQuestion {
  constructor(api) {
    this._api = api;
  }

  // The mod and id of the board holding the next open question, or null when none is open.
  async find() {
    const boards = await this.openBoards();
    return boards[0] ? { mod: boards[0].mod, id: boards[0].id } : null;
  }

  // Every board with an open question, blocking first, then oldest created.
  async openBoards() {
    const rows = await this._queue();
    const boards = await Promise.all(rows.map((row) => this._api.board(row.mod, row.id)));
    return rows.filter((row, index) => this._isOpen(boards[index]))
      .map((row) => ({ mod: row.mod, id: row.id, title: row.title, blocking: row.blocking }));
  }

  // Open boards of every healthy mod, blocking first, then oldest created.
  async _queue() {
    const mods = await this._api.mods();
    const lists = await Promise.all(mods.rows.filter((row) => !row.error)
      .map((row) => this._modRows(row.name)));
    return lists.flat().sort((a, b) => this._order(a, b));
  }

  async _modRows(name) {
    const body = await this._api.boards(name, "open");
    return body.table.rows.filter((row) => !row.error)
      .map((row) => ({ mod: name, ...row }));
  }

  _order(a, b) {
    if (a.blocking !== b.blocking) return a.blocking ? -1 : 1;
    const first = a.created ?? "";
    const second = b.created ?? "";
    if (first === second) return 0;
    return first < second ? -1 : 1;
  }

  // Permanent boards carry no questions, so they never hold an open question.
  _isOpen(board) {
    if (board.permanent || board.questions.length === 0) return false;
    const answered = new Set(board.answers.map((answer) => answer.question_id));
    return board.questions.some((question) => !answered.has(question.id));
  }
}
