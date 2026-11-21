// Page-wide record of what the author is looking at, announced on document.

const CONTEXT_EVENT = "wb-context";
let shared = null;

export class ViewContext {
  static shared() {
    if (!shared) shared = new ViewContext();
    return shared;
  }

  constructor() {
    this._context = { view: null, mod: null, board: null, item: null, question: null, section: null };
  }

  set(patch) {
    this._context = { ...this._context, ...patch };
    document.dispatchEvent(new CustomEvent(CONTEXT_EVENT, { detail: this.get() }));
  }

  get() {
    return { ...this._context };
  }
}
