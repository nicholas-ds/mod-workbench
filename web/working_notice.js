// Top bar notice: one pill with a label while its activity source runs. A ring pings when work starts and when it ends.
// A click passes the source's target to onOpen.

import { WorkingPill } from "./working_pill.js";

const REPLIED_MS = 3000;

export class WorkingNotice {
  constructor(label, activity, container, onOpen) {
    this._label = label;
    this._activity = activity;
    this._container = container;
    this._onOpen = onOpen;
    this._pill = null;
    this._doneTimer = null;
  }

  start() {
    this._activity.subscribe(() => this._sync());
  }

  _sync() {
    if (this._activity.isRunning()) this._showWorking();
    else if (this._pill && !this._doneTimer) this._showDone();
  }

  _showWorking() {
    if (this._pill && !this._doneTimer) return;
    this._removePill();
    this._pill = WorkingPill.build(this._label, "ping", "button");
    this._pill.type = "button";
    this._pill.addEventListener("click", () => this._onOpen(this._activity.target()));
    this._container.appendChild(this._pill);
  }

  _showDone() {
    this._pill.firstChild.textContent = `${this._label} replied`;
    this._pill.classList.remove("ping");
    void this._pill.offsetWidth;
    this._pill.classList.add("ping", "is-done");
    this._doneTimer = setTimeout(() => this._removePill(), REPLIED_MS);
  }

  _removePill() {
    clearTimeout(this._doneTimer);
    this._doneTimer = null;
    this._pill?.remove();
    this._pill = null;
  }
}
